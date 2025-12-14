"""Service for managing LIFT ranges."""

from __future__ import annotations
import logging
import uuid
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

from app.database.basex_connector import BaseXConnector
from app.parsers.lift_parser import LIFTRangesParser
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError


class RangesService:
    """Service for CRUD operations on LIFT ranges."""
    
    def __init__(self, db_connector: BaseXConnector):
        """
        Initialize RangesService.
        
        Args:
            db_connector: BaseX database connector instance.
        """
        self.db_connector = db_connector
        self.ranges_parser = LIFTRangesParser()
        self.logger = logging.getLogger(__name__)
    
    def _ensure_connection(self) -> None:
        """Ensure database connection is established."""
        if not self.db_connector.is_connected():
            try:
                self.db_connector.connect()
                self.logger.info("Connected to BaseX server")
            except Exception as e:
                self.logger.error(f"Failed to connect to BaseX: {e}")
                raise DatabaseError(f"Database connection failed: {e}")
    
    # --- Range CRUD ---
    
    def get_all_ranges(self, project_id: int = 1) -> Dict[str, Any]:
        """
        Retrieve all ranges from database and custom ranges.

        Args:
            project_id: Project ID for custom ranges

        Returns:
            Dict mapping range IDs to range data with structure:
            {
                'range_id': {
                    'id': str,
                    'guid': str,
                    'description': Dict[str, str],  # lang -> text
                    'values': List[Dict]  # hierarchical elements
                }
            }
        """
        self._ensure_connection()
        db_name = self.db_connector.database

        # Query ranges document
        query = f"collection('{db_name}')//lift-ranges"
        ranges_xml = self.db_connector.execute_query(query)

        ranges = {}
        if ranges_xml and ranges_xml.strip():
            # Parse XML to dict
            try:
                ranges = self.ranges_parser.parse_string(ranges_xml)
            except ET.ParseError as e:
                self.logger.error(f"Error parsing ranges XML: {e}")
                ranges = {}
        else:
            self.logger.warning("No ranges found in database")

        # Load and merge custom ranges
        custom_ranges = self._load_custom_ranges(project_id)

        # Merge custom ranges into the main ranges dict
        for range_name, elements in custom_ranges.items():
            if range_name not in ranges:
                ranges[range_name] = {
                    'id': range_name,
                    'guid': f'custom-{range_name}',
                    'description': {},
                    'values': []
                }
            # Add custom elements to the range
            ranges[range_name]['values'].extend(elements)

        return ranges

    def _load_custom_ranges(self, project_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load custom ranges from database.

        Args:
            project_id: Project ID

        Returns:
            Dict mapping range names to lists of range elements
        """
        from app.models.custom_ranges import CustomRange, CustomRangeValue

        custom_ranges = {}

        try:
            ranges = CustomRange.query.filter_by(project_id=project_id).all()
            for cr in ranges:
                elements = []
                for val in cr.values:
                    elements.append({
                        'id': val.value,
                        'label': val.label or val.value,
                        'description': val.description,
                        'custom': True,
                        'range_id': cr.id
                    })
                custom_ranges[cr.range_name] = elements
        except Exception as e:
            self.logger.error(f"Error loading custom ranges: {e}")

        return custom_ranges

    def get_range(self, range_id: str, project_id: int = 1) -> Dict[str, Any]:
        """
        Get single range by ID.
        
        Args:
            range_id: ID of the range to retrieve.
            
        Returns:
            Range data dictionary.
            
        Raises:
            NotFoundError: If range not found.
        """
        # Try parsing all ranges first
        ranges = self.get_all_ranges()
        if ranges and range_id in ranges:
            return ranges[range_id]

        # If not found, query for the specific range to avoid parsing whole doc
        db_name = self.db_connector.database
        query = f"for $range in collection('{db_name}')//range[@id='{range_id}'] return $range"
        result_xml = self.db_connector.execute_query(query)
        if not result_xml or not result_xml.strip():
            raise NotFoundError(f"Range '{range_id}' not found")
        try:
            parsed = self.ranges_parser.parse_string(result_xml)
            if range_id in parsed:
                return parsed[range_id]
        except ET.ParseError:
            # Log and raise NotFound to keep behavior consistent
            self.logger.error(f"Error parsing specific range XML for {range_id}")
            raise NotFoundError(f"Range '{range_id}' not found")
        raise NotFoundError(f"Range '{range_id}' not found")
    
    def create_range(self, range_data: Dict[str, Any]) -> str:
        """
        Create new range.
        
        Args:
            range_data: {
                'id': str (required),
                'labels': Dict[str, str],  # lang -> text
                'descriptions': Dict[str, str]  # optional
            }
        
        Returns:
            GUID of created range.
            
        Raises:
            ValidationError: If range ID already exists or validation fails.
        """
        range_id = range_data.get('id')
        if not range_id:
            raise ValidationError("Range ID is required")
        
        # Validate ID uniqueness
        if not self.validate_range_id(range_id):
            raise ValidationError(f"Range ID '{range_id}' already exists")
        
        # Generate GUID
        guid = str(uuid.uuid4())
        
        # Build XML
        labels_xml = self._build_multilingual_xml('label', range_data.get('labels', {}))
        descriptions_xml = self._build_multilingual_xml('description', range_data.get('descriptions', {}))
        
        # Execute XQuery insert
        db_name = self.db_connector.database
        query = f"""
        let $lift-ranges := collection('{db_name}')//lift-ranges
        let $new-range := 
          <range id="{range_id}" guid="{guid}">
            {labels_xml}
            {descriptions_xml}
          </range>
        return insert node $new-range into $lift-ranges
        """
        
        self.db_connector.execute_update(query)
        self.logger.info(f"Created range '{range_id}' with GUID {guid}")
        
        return guid
    
    def update_range(self, range_id: str, range_data: Dict[str, Any]) -> None:
        """
        Update existing range.
        
        Args:
            range_id: ID of the range to update.
            range_data: Updated range data.
            
        Raises:
            NotFoundError: If range not found.
        """
        # Verify range exists
        self.get_range(range_id)
        
        db_name = self.db_connector.database
        
        # Delete old range
        delete_query = f"""
        delete node collection('{db_name}')//range[@id='{range_id}']
        """
        self.db_connector.execute_update(delete_query)
        
        # Create updated range
        guid = range_data.get('guid', str(uuid.uuid4()))
        labels_xml = self._build_multilingual_xml('label', range_data.get('labels', {}))
        descriptions_xml = self._build_multilingual_xml('description', range_data.get('descriptions', {}))
        
        # Reconstruct range with existing elements if any
        elements_xml = ""
        if 'values' in range_data and range_data['values']:
            for element in range_data['values']:
                elements_xml += self._build_range_element_xml(element)
        
        insert_query = f"""
        let $lift-ranges := collection('{db_name}')//lift-ranges
        let $updated-range := 
          <range id="{range_id}" guid="{guid}">
            {labels_xml}
            {descriptions_xml}
            {elements_xml}
          </range>
        return insert node $updated-range into $lift-ranges
        """
        
        self.db_connector.execute_update(insert_query)
        self.logger.info(f"Updated range '{range_id}'")
    
    def delete_range(self, range_id: str, migration: Optional[Dict] = None) -> None:
        """
        Delete range with optional data migration.
        
        Args:
            range_id: ID of range to delete.
            migration: Optional migration config:
                {
                    'operation': 'remove' | 'replace',
                    'new_value': str  # Only for 'replace'
                }
                
        Raises:
            NotFoundError: If range not found.
            ValidationError: If range is in use and no migration provided.
        """
        # Check if range exists
        self.get_range(range_id)
        
        # Find usage in entries
        usage = self.find_range_usage(range_id)
        
        # If used and no migration, raise error
        if usage and not migration:
            raise ValidationError(
                f"Range '{range_id}' is used in {len(usage)} entries. "
                "Provide migration strategy or remove usage first."
            )
        
        # If migration provided, execute it
        if migration:
            operation = migration.get('operation')
            new_value = migration.get('new_value')
            
            if operation == 'replace' and not new_value:
                raise ValidationError("new_value required for 'replace' operation")
            
            # Migrate all values in the range
            # Note: This is a simplified approach - in production you'd want to
            # migrate each element individually
            self.migrate_range_values(range_id, None, operation, new_value, dry_run=False)
        
        # Delete range
        db_name = self.db_connector.database
        query = f"""
        delete node collection('{db_name}')//range[@id='{range_id}']
        """
        
        self.db_connector.execute_update(query)
        self.logger.info(f"Deleted range '{range_id}'")
    
    # --- Range Element CRUD ---
    
    def create_range_element(
        self, range_id: str, element_data: Dict[str, Any]
    ) -> str:
        """
        Create new element in range.
        
        Args:
            range_id: ID of the parent range.
            element_data: {
                'id': str,
                'parent': Optional[str],
                'labels': Dict[str, str],
                'abbrevs': Optional[Dict[str, str]],
                'descriptions': Optional[Dict[str, str]],
                'traits': Optional[Dict[str, str]]
            }
        
        Returns:
            GUID of created element.
            
        Raises:
            NotFoundError: If range not found.
            ValidationError: If validation fails.
        """
        # Verify range exists
        range_obj = self.get_range(range_id)
        
        element_id = element_data.get('id')
        if not element_id:
            raise ValidationError("Element ID is required")
        
        # Validate element ID unique within range
        if not self.validate_element_id(range_id, element_id):
            raise ValidationError(f"Element ID '{element_id}' already exists in range '{range_id}'")
        
        # Validate parent exists (if specified)
        parent_id = element_data.get('parent')
        if parent_id:
            if not self.validate_parent_reference(range_id, element_id, parent_id):
                raise ValidationError(f"Invalid parent reference: would create circular dependency")
        
        # Generate GUID
        guid = str(uuid.uuid4())
        
        # Build element XML
        element_xml = self._build_range_element_xml({
            **element_data,
            'guid': guid
        })
        
        # Insert into range
        db_name = self.db_connector.database
        query = f"""
        let $range := collection('{db_name}')//range[@id='{range_id}']
        let $new-element := {element_xml}
        return insert node $new-element into $range
        """
        
        self.db_connector.execute_update(query)
        self.logger.info(f"Created element '{element_id}' in range '{range_id}' with GUID {guid}")
        
        return guid
    
    def update_range_element(
        self, range_id: str, element_id: str, element_data: Dict[str, Any]
    ) -> None:
        """
        Update existing range element.
        
        Args:
            range_id: ID of the parent range.
            element_id: ID of the element to update.
            element_data: Updated element data.
            
        Raises:
            NotFoundError: If range or element not found.
        """
        # Verify range and element exist
        range_obj = self.get_range(range_id)
        
        # Find element in range
        element_found = False
        for value in range_obj.get('values', []):
            if value.get('id') == element_id:
                element_found = True
                break
        
        if not element_found:
            raise NotFoundError(f"Element '{element_id}' not found in range '{range_id}'")
        
        # Delete old element
        db_name = self.db_connector.database
        delete_query = f"""
        delete node collection('{db_name}')//range[@id='{range_id}']//range-element[@id='{element_id}']
        """
        self.db_connector.execute_update(delete_query)
        
        # Insert updated element
        guid = element_data.get('guid', str(uuid.uuid4()))
        element_xml = self._build_range_element_xml({
            **element_data,
            'id': element_id,
            'guid': guid
        })
        
        insert_query = f"""
        let $range := collection('{db_name}')//range[@id='{range_id}']
        let $updated-element := {element_xml}
        return insert node $updated-element into $range
        """
        
        self.db_connector.execute_update(insert_query)
        self.logger.info(f"Updated element '{element_id}' in range '{range_id}'")
    
    def delete_range_element(
        self, range_id: str, element_id: str, migration: Optional[Dict] = None
    ) -> None:
        """
        Delete range element with optional migration.
        
        Args:
            range_id: ID of the parent range.
            element_id: ID of the element to delete.
            migration: Optional migration config.
            
        Raises:
            NotFoundError: If range or element not found.
            ValidationError: If element is in use and no migration provided.
        """
        # Verify range and element exist
        range_obj = self.get_range(range_id)
        
        # Find usage
        usage = self.find_range_usage(range_id, element_id)
        
        if usage and not migration:
            raise ValidationError(
                f"Element '{element_id}' is used in {len(usage)} entries. "
                "Provide migration strategy or remove usage first."
            )
        
        # Migrate if needed
        if migration:
            operation = migration.get('operation')
            new_value = migration.get('new_value')
            
            self.migrate_range_values(range_id, element_id, operation, new_value, dry_run=False)
        
        # Delete element
        db_name = self.db_connector.database
        query = f"""
        delete node collection('{db_name}')//range[@id='{range_id}']//range-element[@id='{element_id}']
        """
        
        self.db_connector.execute_update(query)
        self.logger.info(f"Deleted element '{element_id}' from range '{range_id}'")
    
    # --- Validation ---
    
    def validate_range_id(self, range_id: str) -> bool:
        """
        Check if range ID is unique (not already in use).
        
        Args:
            range_id: Range ID to validate.
        
        Returns:
            True if ID is available, False if already exists.
        """
        db_name = self.db_connector.database
        query = f"""
        exists(collection('{db_name}')//range[@id='{range_id}'])
        """
        result = self.db_connector.execute_query(query)
        return result.strip().lower() == 'false'
    
    def validate_element_id(self, range_id: str, element_id: str) -> bool:
        """
        Check if element ID is unique within range.
        
        Args:
            range_id: Parent range ID.
            element_id: Element ID to validate.
        
        Returns:
            True if ID is available, False if already exists.
        """
        db_name = self.db_connector.database
        query = f"""
        exists(collection('{db_name}')//range[@id='{range_id}']//range-element[@id='{element_id}'])
        """
        result = self.db_connector.execute_query(query)
        return result.strip().lower() == 'false'
    
    def validate_parent_reference(
        self, range_id: str, element_id: str, parent_id: str
    ) -> bool:
        """
        Check if setting parent would create circular reference.
        
        Algorithm:
            1. Start from parent_id
            2. Follow parent chain to root
            3. If element_id appears in chain, it's circular
        
        Args:
            range_id: Parent range ID.
            element_id: ID of element being updated.
            parent_id: Proposed parent ID.
        
        Returns:
            True if valid, False if circular.
        """
        # Get range
        range_obj = self.get_range(range_id)
        
        # Build parent map
        parent_map: Dict[str, Optional[str]] = {}
        
        def collect_parents(elements: List[Dict[str, Any]]):
            for value in elements:
                vid = value.get('id')
                vparent = value.get('parent')
                if vid:
                    parent_map[vid] = vparent
                
                # Recurse for children
                if 'children' in value and value['children']:
                    collect_parents(value['children'])
        
        collect_parents(range_obj.get('values', []))
        
        # Check if parent_id exists
        if parent_id not in parent_map:
            raise ValidationError(f"Parent element '{parent_id}' not found in range '{range_id}'")
        
        # Walk up parent chain from parent_id
        current = parent_id
        visited = set()
        
        while current:
            if current == element_id:
                # Circular reference detected
                return False
            
            if current in visited:
                # Already visited, avoid infinite loop
                break
            
            visited.add(current)
            current = parent_map.get(current)
        
        return True
    
    # --- Usage Analysis & Migration ---
    
    def find_range_usage(
        self, range_id: str, element_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find entries using specific range or element.
        
        Args:
            range_id: Range ID to search for.
            element_id: Optional element ID to search for.
        
        Returns:
            List of dicts with structure:
            {
                'entry_id': str,
                'headword': str,
                'count': int
            }
        """
        # Build XQuery based on range type
        if range_id == 'grammatical-info':
            # Search in grammatical-info elements
            if element_id:
                query = f"""
                for $entry in //entry[
                  .//grammatical-info[@value = '{element_id}']
                ]
                return concat(
                  $entry/@id, '|||',
                  string($entry/lexical-unit/form[1]/text[1]), '|||',
                  count($entry//grammatical-info[@value = '{element_id}'])
                )
                """
            else:
                # Find any usage (for range deletion check)
                query = """
                for $entry in //entry[
                  .//grammatical-info
                ]
                return concat($entry/@id, '|||', string($entry/lexical-unit/form[1]/text[1]), '|||1')
                """
        elif range_id in ['lexical-relation', 'lexical-relations']:
            # Search in relation elements
            if element_id:
                query = f"""
                for $entry in //entry[
                  .//relation[@type = '{element_id}']
                ]
                return concat(
                  $entry/@id, '|||',
                  string($entry/lexical-unit/form[1]/text[1]), '|||',
                  count($entry//relation[@type = '{element_id}'])
                )
                """
            else:
                query = """
                for $entry in //entry[
                  .//relation
                ]
                return concat($entry/@id, '|||', string($entry/lexical-unit/form[1]/text[1]), '|||1')
                """
        else:
            # Search in traits for other ranges
            if element_id:
                query = f"""
                for $entry in //entry[
                  .//trait[@name = '{range_id}' and @value = '{element_id}']
                ]
                return concat(
                  $entry/@id, '|||',
                  string($entry/lexical-unit/form[1]/text[1]), '|||',
                  count($entry//trait[@name = '{range_id}' and @value = '{element_id}'])
                )
                """
            else:
                query = f"""
                for $entry in //entry[
                  .//trait[@name = '{range_id}']
                ]
                return concat($entry/@id, '|||', string($entry/lexical-unit/form[1]/text[1]), '|||1')
                """
        
        result = self.db_connector.execute_query(query)
        
        # Parse triple-pipe-delimited results
        usage = []
        if result and result.strip():
            for line in result.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|||')
                if len(parts) >= 3:
                    try:
                        usage.append({
                            'entry_id': parts[0],
                            'headword': parts[1],
                            'count': int(parts[2])
                        })
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Failed to parse usage line: {line}, error: {e}")
                        continue
        
        return usage
    
    def get_usage_by_element(self, range_id: str) -> Dict[str, Any]:
        """
        Get usage statistics grouped by element value.
        
        Args:
            range_id: Range ID to analyze.
        
        Returns:
            Dict with structure:
            {
                'total_entries': int,
                'elements': {
                    'element_id': {
                        'count': int,
                        'label': str,
                        'sample_entries': [{'entry_id': str, 'headword': str}, ...]
                    }
                }
            }
        """
        # Get all elements in the range
        range_data = self.get_range(range_id)
        elements = {elem['id']: elem for elem in range_data.get('values', [])}
        
        # Build query to get all usage grouped by value
        if range_id == 'grammatical-info':
            query = """
            for $value in distinct-values(//entry//grammatical-info/@value)
            return concat(
              $value, '|||',
              count(//entry[.//grammatical-info[@value = $value]])
            )
            """
        elif range_id in ['lexical-relation', 'lexical-relations']:
            query = """
            for $type in distinct-values(//entry//relation/@type)
            return concat(
              $type, '|||',
              count(//entry[.//relation[@type = $type]])
            )
            """
        else:
            query = f"""
            for $value in distinct-values(//entry//trait[@name = '{range_id}']/@value)
            return concat(
              $value, '|||',
              count(//entry[.//trait[@name = '{range_id}' and @value = $value]])
            )
            """
        
        result = self.db_connector.execute_query(query)
        
        # Parse results
        usage_by_element = {}
        total_entries = set()
        
        if result and result.strip():
            for line in result.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|||')
                if len(parts) >= 2:
                    element_id = parts[0]
                    try:
                        count = int(parts[1])
                        
                        # Get element label
                        elem_data = elements.get(element_id, {})
                        label = ''
                        if 'description' in elem_data and elem_data['description']:
                            label = elem_data['description'].get('en', list(elem_data['description'].values())[0] if elem_data['description'] else '')
                        elif 'abbrev' in elem_data:
                            label = elem_data['abbrev']
                        
                        # Get sample entries for this element
                        sample_usage = self.find_range_usage(range_id, element_id)
                        
                        usage_by_element[element_id] = {
                            'count': count,
                            'label': label or element_id,
                            'sample_entries': sample_usage[:5]  # First 5 samples
                        }
                        
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Failed to parse usage stats line: {line}, error: {e}")
                        continue
        
        return {
            'total_entries': len(set(entry['entry_id'] for elem_usage in usage_by_element.values() for entry in elem_usage['sample_entries'])),
            'elements': usage_by_element
        }
    
    def migrate_range_values(
        self,
        range_id: str,
        old_value: Optional[str],
        operation: str,
        new_value: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Bulk migrate range values in entries.
        
        Args:
            range_id: Range ID.
            old_value: Value to replace/remove (None for all values).
            operation: 'replace' or 'remove'.
            new_value: New value (required for 'replace').
            dry_run: If True, only count affected entries.
        
        Returns:
            {'entries_affected': int, 'fields_updated': int}
            
        Raises:
            ValidationError: If operation is invalid.
        """
        if operation not in ('replace', 'remove'):
            raise ValidationError("operation must be 'replace' or 'remove'")

        if operation == 'replace' and not new_value:
            raise ValidationError("new_value required for 'replace' operation")
        
        # Find affected entries
        usage = self.find_range_usage(range_id, old_value)
        entries_affected = len(usage)
        
        if dry_run:
            return {
                'entries_affected': entries_affected,
                'fields_updated': 0
            }
        
        # Execute migration
        db_name = self.db_connector.database
        
        if operation == 'replace':
            # Replace operation
            if range_id == 'grammatical-info':
                if old_value:
                    update_query = f"""
                    for $gi in collection('{db_name}')//grammatical-info[@value = '{old_value}']
                    return replace value of node $gi/@value with '{new_value}'
                    """
                else:
                    # Replace all grammatical-info values
                    update_query = f"""
                    for $gi in collection('{db_name}')//grammatical-info
                    return replace value of node $gi/@value with '{new_value}'
                    """
            else:
                if old_value:
                    update_query = f"""
                    for $trait in collection('{db_name}')//trait[@name = '{range_id}' and @value = '{old_value}']
                    return replace value of node $trait/@value with '{new_value}'
                    """
                else:
                    update_query = f"""
                    for $trait in collection('{db_name}')//trait[@name = '{range_id}']
                    return replace value of node $trait/@value with '{new_value}'
                    """
        else:  # operation == 'remove'
            # Delete operation
            if range_id == 'grammatical-info':
                if old_value:
                    update_query = f"""
                    delete node collection('{db_name}')//grammatical-info[@value = '{old_value}']
                    """
                else:
                    update_query = f"""
                    delete node collection('{db_name}')//grammatical-info
                    """
            else:
                if old_value:
                    update_query = f"""
                    delete node collection('{db_name}')//trait[@name = '{range_id}' and @value = '{old_value}']
                    """
                else:
                    update_query = f"""
                    delete node collection('{db_name}')//trait[@name = '{range_id}']
                    """
        
        self.db_connector.execute_update(update_query)
        self.logger.info(
            f"Migrated {entries_affected} entries: {operation} '{old_value}' "
            + (f"with '{new_value}'" if new_value else "")
        )
        
        return {
            'entries_affected': entries_affected,
            'fields_updated': entries_affected  # Simplified
        }
    
    # --- Helper methods ---
    
    def _build_multilingual_xml(self, element_name: str, content: Dict[str, str]) -> str:
        """
        Build multilingual XML structure.
        
        Args:
            element_name: 'label', 'description', or 'abbrev'.
            content: Dict mapping language codes to text.
        
        Returns:
            XML string like:
            <label>
              <form lang="en"><text>English label</text></form>
              <form lang="pl"><text>Polish label</text></form>
            </label>
        """
        if not content:
            return ''
        
        root = ET.Element(element_name)
        for lang, text in content.items():
            form = ET.SubElement(root, 'form')
            form.set('lang', lang)
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        return ET.tostring(root, encoding='unicode')
    
    def _build_range_element_xml(self, element_data: Dict[str, Any]) -> str:
        """
        Build XML for a range element.
        
        Args:
            element_data: Element data dictionary.
        
        Returns:
            XML string for the range element.
        """
        element_id = element_data.get('id', '')
        guid = element_data.get('guid', '')
        parent = element_data.get('parent', '')
        
        # Build element
        elem = ET.Element('range-element')
        elem.set('id', element_id)
        if guid:
            elem.set('guid', guid)
        if parent:
            elem.set('parent', parent)
        
        # Add labels
        labels = element_data.get('labels', {})
        if labels:
            label_elem = ET.SubElement(elem, 'label')
            for lang, text in labels.items():
                form = ET.SubElement(label_elem, 'form')
                form.set('lang', lang)
                text_elem = ET.SubElement(form, 'text')
                text_elem.text = text
        
        # Add descriptions
        descriptions = element_data.get('descriptions', {})
        if descriptions:
            desc_elem = ET.SubElement(elem, 'description')
            for lang, text in descriptions.items():
                form = ET.SubElement(desc_elem, 'form')
                form.set('lang', lang)
                text_elem = ET.SubElement(form, 'text')
                text_elem.text = text
        
        # Add abbreviations
        abbrevs = element_data.get('abbrevs', {})
        if abbrevs:
            abbrev_elem = ET.SubElement(elem, 'abbrev')
            for lang, text in abbrevs.items():
                form = ET.SubElement(abbrev_elem, 'form')
                form.set('lang', lang)
                text_elem = ET.SubElement(form, 'text')
                text_elem.text = text
        
        # Add traits
        traits = element_data.get('traits', {})
        for trait_name, trait_value in traits.items():
            trait_elem = ET.SubElement(elem, 'trait')
            trait_elem.set('name', trait_name)
            trait_elem.set('value', trait_value)
        
        return ET.tostring(elem, encoding='unicode')
