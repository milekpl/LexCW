"""Service for managing LIFT ranges."""

from __future__ import annotations
import logging
import uuid
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET
import os

from app.database.basex_connector import BaseXConnector
from app.parsers.lift_parser import LIFTRangesParser
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError

# Human-friendly labels and descriptions for well-known standard ranges.
# These are used in the Ranges Editor to present readable labels for
# lexicographers (labels are not always present in the LIFT ranges file).
STANDARD_RANGE_METADATA = {
    'etymology': {'label': 'Etymology', 'description': 'Borrowed / proto origin types'},
    'grammatical-info': {'label': 'Grammatical Info (Parts of Speech)', 'description': 'Parts of speech'},
    'lexical-relation': {'label': 'Lexical Relations', 'description': 'Lexical reference types'},
    'note-type': {'label': 'Note Types', 'description': 'Note categories (anthropology, bibliography, etc.)'},
    'paradigm': {'label': 'Paradigm', 'description': 'Grammatical paradigm markers'},
    'reversal-type': {'label': 'Reversal Types', 'description': 'Reversal index writing systems'},
    'semantic-domain-ddp4': {'label': 'Semantic Domains', 'description': 'Semantic domain classifications'},
    'status': {'label': 'Status', 'description': 'Entry status values'},
    'users': {'label': 'Users (People)', 'description': 'People / researchers'},
    'location': {'label': 'Locations', 'description': 'Location possibilities'},
    'anthro-code': {'label': 'Anthropology Codes', 'description': 'Anthropological codes'},
    'translation-type': {'label': 'Translation Types', 'description': 'Translation tag types'},
    'exception-feature': {'label': 'Exception Features', 'description': 'Production restrictions'},
    'inflection-feature': {'label': 'Inflection Features', 'description': 'Morphosyntactic features'},
    'inflection-feature-type': {'label': 'Inflection Feature Types', 'description': 'Feature type structures'},
    'from-part-of-speech': {'label': 'From Parts of Speech', 'description': 'Parts of speech for affixes'},
    'morph-type': {'label': 'Morph Types', 'description': 'Morpheme type classifications'},
    'feature-values': {'label': 'Feature Values', 'description': 'Values for closed features'},
    'affix-categories': {'label': 'Affix Slots', 'description': 'Slot positions by part of speech'},
    'infl-class': {'label': 'Inflection Classes', 'description': 'Inflection class hierarchies'},
    'stem-names': {'label': 'Stem Names', 'description': 'Stem name definitions'},
    'Publications': {'label': 'Publications', 'description': 'Publication types'},
    'usage-type': {'label': 'Usage Types', 'description': 'Usage type list'},
    'domain-type': {'label': 'Domain Types', 'description': 'Domain types'},

    'complex-form-type': {
        'label': 'Complex form types',
        'description': 'How component subentries relate to main entries',
    },
    'is-primary': {
        'label': 'Is primary (trait)',
        'description': 'Marks a component as primary in complex forms',
    },
    'hide-minor-entry': {
        'label': 'Hide minor entry (trait)',
        'description': 'Control publication visibility of minor entries',
    },
    'variant-type': {'label': 'Variant types', 'description': 'Variant type classifications'},
}

# Optionally load localized/overriding metadata from `app/config/custom_ranges.json`.
# Keys present in that file are usually FieldWorks-only lists (not stored in LIFT)
# and are recorded in CONFIG_PROVIDED_RANGES so they can be marked when added.
CONFIG_PROVIDED_RANGES: set[str] = set()
CONFIG_RANGE_TYPES: Dict[str, str] = {}
# NOTE: keep the in-code STANDARD_RANGE_METADATA as the primary fallback
# for friendly labels; the JSON file now only contains custom FieldWorks lists.
try:
    import json
    _app_dir = os.path.dirname(os.path.dirname(__file__))
    _cfg_path = os.path.join(_app_dir, 'config', 'custom_ranges.json')
    if os.path.exists(_cfg_path):
        with open(_cfg_path, 'r', encoding='utf-8') as _f:
            _cfg = json.load(_f)
            # Merge: allow config file to provide localized labels/descriptions
            for _k, _v in _cfg.items():
                if _k in STANDARD_RANGE_METADATA:
                    # augment existing metadata
                    STANDARD_RANGE_METADATA[_k].setdefault('label', STANDARD_RANGE_METADATA[_k]['label'])
                    STANDARD_RANGE_METADATA[_k].setdefault('description', STANDARD_RANGE_METADATA[_k]['description'])
                # record that this key was provided by the config file
                CONFIG_PROVIDED_RANGES.add(_k)
                # store optional type (fieldworks/custom)
                CONFIG_RANGE_TYPES[_k] = _v.get('type', 'fieldworks')
                # Normalize to simple dict with 'label' and 'description' strings
                if isinstance(_v.get('label'), dict):
                    # use English label if available
                    STANDARD_RANGE_METADATA[_k] = {
                        'label': _v['label'].get('en', next(iter(_v['label'].values()))),
                        'description': _v.get('description', {}).get('en', '')
                    }
                else:
                    STANDARD_RANGE_METADATA[_k] = {
                        'label': _v.get('label') or STANDARD_RANGE_METADATA.get(_k, {}).get('label'),
                        'description': _v.get('description') or STANDARD_RANGE_METADATA.get(_k, {}).get('description')
                    }
except Exception:
    # Do not fail startup if config file missing or invalid
    pass


def reload_custom_ranges_config() -> None:
    """Reload custom_ranges.json and update in-memory metadata sets."""
    global CONFIG_PROVIDED_RANGES
    try:
        import json
        _app_dir = os.path.dirname(os.path.dirname(__file__))
        _cfg_path = os.path.join(_app_dir, 'config', 'custom_ranges.json')
        if not os.path.exists(_cfg_path):
            CONFIG_PROVIDED_RANGES = set()
            return
        with open(_cfg_path, 'r', encoding='utf-8') as f:
            _cfg = json.load(f)
        CONFIG_PROVIDED_RANGES.clear()
        for _k, _v in _cfg.items():
            CONFIG_PROVIDED_RANGES.add(_k)
            CONFIG_RANGE_TYPES[_k] = _v.get('type', 'fieldworks')
            if isinstance(_v.get('label'), dict):
                label = _v['label'].get('en', next(iter(_v['label'].values())))
                desc = _v.get('description', {}).get('en', '')
            else:
                label = _v.get('label')
                desc = _v.get('description')
            STANDARD_RANGE_METADATA[_k] = {
                'label': label or STANDARD_RANGE_METADATA.get(_k, {}).get('label'),
                'description': desc or STANDARD_RANGE_METADATA.get(_k, {}).get('description')
            }
    except Exception:
        # ignore reload errors
        pass


class RangesService:
    """Service for CRUD operations on LIFT ranges."""

    def save_custom_ranges(self, custom_ranges: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Save custom trait-based ranges to config/custom_ranges.json, merging with any existing values.
        Args:
            custom_ranges: Dict mapping range names to lists of range elements (id, label, definition)
        """
        import json
        _app_dir = os.path.dirname(os.path.dirname(__file__))
        _cfg_path = os.path.join(_app_dir, 'config', 'custom_ranges.json')
        # Load existing custom_ranges.json if present
        if os.path.exists(_cfg_path):
            with open(_cfg_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = {}
        # Merge new custom_ranges into existing
        for range_name, elements in custom_ranges.items():
            # Format for each element: id, label, definition
            formatted = [
                {
                    'id': e['id'],
                    'label': e.get('label', e['id']),
                    'description': e.get('definition', '')
                } for e in elements
            ]
            existing[range_name] = {
                'type': 'custom',
                'values': formatted
            }
        # Save merged result
        with open(_cfg_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Saved custom trait ranges to {os.path.relpath(_cfg_path)}: {list(custom_ranges.keys())}")

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
        # Ensure config-driven metadata is up-to-date (reload if the config file changed)
        try:
            reload_custom_ranges_config()
        except Exception:
            pass

        self._ensure_connection()
        db_name = self.db_connector.database

        # Query ranges document. Must be namespace-insensitive because
        # FieldWorks ranges typically use the ranges namespace.
        query = f"collection('{db_name}')//*[local-name() = 'lift-ranges']"
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

        # Annotate parsed ranges with helpful UI metadata: human-friendly
        # label (preferred language 'en') and whether the range is a standard
        # range (from our known list). Also normalize 'description' field
        # to be a dict for compatibility with custom ranges.
        for rid, rdata in list(ranges.items()):
            # Normalize descriptions: parser provides 'description'; keep it
            descriptions = rdata.get('description') or {}
            labels = rdata.get('labels') or {}

            # Normalize strings to dicts if parser returned simple strings
            if isinstance(descriptions, str):
                descriptions = {'en': descriptions}
            if isinstance(labels, str):
                labels = {'en': labels}

            # Prefer label from labels, then from descriptions.
            # If none present in LIFT, fall back to STANDARD_RANGE_METADATA label
            label_str = labels.get('en') or next(iter(labels.values()), None) or descriptions.get('en') or next(iter(descriptions.values()), None)
            # Fallback for label/description from metadata
            if not label_str or not descriptions:
                meta = STANDARD_RANGE_METADATA.get(rid)
                if isinstance(meta, dict):
                    if not label_str:
                        label_str = meta.get('label')
                    if not descriptions:
                        desc = meta.get('description')
                        if desc:
                            descriptions = {'en': desc}
            rdata['label'] = label_str or rid
            rdata['description'] = descriptions
            rdata['official'] = True
            rdata['standard'] = rid in STANDARD_RANGE_METADATA
            # For ranges parsed from LIFT, prefer LIFT as authoritative.
            # Even if a config entry exists for the same standard, do not
            # mark the parsed LIFT range as "provided_by_config" or
            # as a FieldWorks-standard; those flags are only meaningful
            # for ranges that are absent from LIFT and provided by the
            # configuration file.
            rdata['fieldworks_standard'] = False
            rdata['provided_by_config'] = False

        # Load and merge custom ranges
        custom_ranges = self._load_custom_ranges(project_id)

        # If there are no ranges in the database, no custom ranges, and no
        # config-provided ranges, return empty dict to reflect an empty ranges state.
        # If config provides FieldWorks-only lists, still expose them so the editor
        # can reflect those ranges even when LIFT has none.
        if not ranges and not custom_ranges and not CONFIG_PROVIDED_RANGES:
            return {}

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

        # Mark custom ranges as not official and ensure top-level label field
        for rid, rdata in ranges.items():
            if not rdata.get('official'):
                # custom ranges (from DB) - provide a label if present on elements
                values = rdata.get('values', [])
                rdata['official'] = False
                rdata['standard'] = rid in STANDARD_RANGE_METADATA
                # if the metadata provides a label for a known standard, use it
                if not rdata.get('label'):
                    if rdata['standard']:
                        # Use metadata label only when the range isn't present
                        # in the LIFT data; but since we're iterating ranges
                        # that do exist, prefer empty label (admin should set it).
                        rdata['label'] = rdata.get('label') or rid
                    else:
                        rdata['label'] = rid

        # Now ensure that any known standard ranges that are entirely absent
        # from the parsed ranges are included for the editor (these are
        # typically FieldWorks-related lists that cannot be stored in LIFT).
        for std_id, meta in STANDARD_RANGE_METADATA.items():
            if std_id not in ranges:
                label = meta.get('label') if isinstance(meta, dict) else meta
                desc = meta.get('description') if isinstance(meta, dict) else ''
                ranges[std_id] = {
                    'id': std_id,
                    'guid': f'provided-{std_id}',
                    'label': label or std_id,
                    'description': {'en': desc} if desc else {},
                    'values': [],
                    'official': False,
                    'standard': True,
                    # Only mark provided_by_config when the config file actually
                    # declared the FieldWorks-only list (custom_ranges.json)
                    'provided_by_config': std_id in CONFIG_PROVIDED_RANGES,
                    # Treat config-provided ranges as FieldWorks-standard by default
                    # (tests expect config-only ranges to be flagged as fieldworks_standard)
                    'fieldworks_standard': (std_id in CONFIG_PROVIDED_RANGES) or (CONFIG_RANGE_TYPES.get(std_id) == 'fieldworks'),
                    'config_type': CONFIG_RANGE_TYPES.get(std_id)
                }


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
        except RuntimeError as e:
            # Unit tests may mock CustomRange.query without an application context.
            # In production, SQLAlchemy access without app context raises this.
            if "Working outside of application context" in str(e):
                return {}
            self.logger.error("Error loading custom ranges: %s", e)
        except Exception as e:
            self.logger.error("Error loading custom ranges: %s", e)

        return custom_ranges

    def get_range(self, range_id: str, project_id: int = 1, resolved: bool = False) -> Dict[str, Any]:
        """
        Get single range by ID.

        Args:
            range_id: ID of the range to retrieve.
            project_id: Project ID for custom ranges.
            resolved: If True, return a non-mutating resolved view with
                      effective_label/effective_abbrev computed for each value.

        Returns:
            Range data dictionary.

        Raises:
            NotFoundError: If range not found.
        """
        # Try parsing all ranges first
        ranges = self.get_all_ranges()
        if ranges and range_id in ranges:
            cached_range = ranges[range_id]

            # Sanity check: ensure cached ranges are not already mutated with effective_ keys
            try:
                def contains_effective(node_list):
                    for n in node_list:
                        if 'effective_label' in n or 'effective_abbrev' in n:
                            return True
                        children = n.get('children') or []
                        if children and contains_effective(children):
                            return True
                    return False
                cached_vals = cached_range.get('values', [])
                if contains_effective(cached_vals):
                    self.logger.warning(f"Cached range '{range_id}' already contains effective_* fields; this may indicate mutation.")
            except Exception:
                pass

            # If the cached range has values from the database, return it directly
            if cached_range.get('values'):
                if resolved:
                    import copy
                    rcopy = copy.deepcopy(cached_range)
                    rcopy['values'] = self.ranges_parser.resolve_values_with_inheritance(rcopy['values'], prefer_lang='en')
                    return rcopy
                return cached_range

            # If cached range has empty values BUT came from STANDARD_RANGE_METADATA
            # (indicated by guid starting with 'provided-'), we should still check
            # the database for actual elements that may have been added
            if cached_range.get('guid', '').startswith('provided-'):
                # Query database for this specific range - it might have elements now
                # Use local-name() for namespace-insensitive matching
                db_name = self.db_connector.database
                query = f"for $range in collection('{db_name}')//*[local-name()='range'][@id='{range_id}'] return $range"
                self.logger.debug(f"Checking database for range '{range_id}' (empty cached version)")
                result_xml = self.db_connector.execute_query(query)
                self.logger.debug(f"Database query result for '{range_id}': {len(result_xml) if result_xml else 0} chars")
                if result_xml and result_xml.strip():
                    try:
                        parsed = self.ranges_parser.parse_string(result_xml)
                        self.logger.debug(f"Parsed {len(parsed)} ranges from database")
                        if range_id in parsed:
                            self.logger.debug(f"Found '{range_id}' in parsed database ranges with {len(parsed[range_id].get('values', []))} values")
                            # Merge the database version with metadata (label/description from cache)
                            db_range = parsed[range_id]
                            db_range['label'] = cached_range.get('label', range_id)
                            db_range['description'] = cached_range.get('description', {})
                            db_range['official'] = cached_range.get('official', False)
                            db_range['standard'] = cached_range.get('standard', True)
                            db_range['provided_by_config'] = cached_range.get('provided_by_config', False)
                            db_range['fieldworks_standard'] = cached_range.get('fieldworks_standard', False)
                            db_range['config_type'] = cached_range.get('config_type')

                            if resolved:
                                import copy
                                rcopy = copy.deepcopy(db_range)
                                if rcopy.get('values'):
                                    rcopy['values'] = self.ranges_parser.resolve_values_with_inheritance(rcopy['values'], prefer_lang='en')
                                return rcopy
                            return db_range
                        else:
                            self.logger.debug(f"Range '{range_id}' not in parsed results, keys: {list(parsed.keys())}")
                    except ET.ParseError:
                        self.logger.debug(f"Error parsing database range XML for {range_id}")

            # Return cached version (may have empty values from STANDARD_RANGE_METADATA)
            if resolved:
                import copy
                rcopy = copy.deepcopy(cached_range)
                if rcopy.get('values'):
                    rcopy['values'] = self.ranges_parser.resolve_values_with_inheritance(rcopy['values'], prefer_lang='en')
                return rcopy
            return cached_range

        # If not found, query for the specific range to avoid parsing whole doc
        # Use local-name() for namespace-insensitive matching
        db_name = self.db_connector.database
        query = f"for $range in collection('{db_name}')//*[local-name()='range'][@id='{range_id}'] return $range"
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
                'description': Dict[str, str]  # optional
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
        descriptions_xml = self._build_multilingual_xml('description', range_data.get('description', {}))
        
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
        descriptions_xml = self._build_multilingual_xml('description', range_data.get('description', {}))
        
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
        # Also remove any custom range rows stored in the SQL database
        try:
            from app.models.custom_ranges import CustomRange, db as custom_db

            deleted = CustomRange.query.filter_by(range_name=range_id).delete(synchronize_session=False)
            if deleted:
                custom_db.session.commit()
                self.logger.info(f"Deleted {deleted} custom range rows for '{range_id}' from SQL DB")
        except Exception as e:
            # Log but do not fail deletion if SQL DB not available or table missing
            self.logger.debug(f"Error deleting custom ranges from SQL DB for '{range_id}': {e}")
    
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
        # Verify range exists
        range_obj = self.get_range(range_id)

        # Recursive helper to find element anywhere in hierarchy
        def find_element(values, eid):
            for value in values:
                if value.get('id') == eid:
                    return True
                children = value.get('children', [])
                if children and find_element(children, eid):
                    return True
            return False

        # Find element in range (handles hierarchical ranges)
        if not find_element(range_obj.get('values', []), element_id):
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
        elif range_id == 'lexical-relation':
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
        elif range_id == 'lexical-relation':
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
        
        # Add descriptions (accept either 'description' or legacy 'descriptions')
        descriptions = element_data.get('description', element_data.get('descriptions', {}))
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
        
        # Add language preference as a trait if provided
        language_preference = element_data.get('language')
        if language_preference:
            # Add language preference as a special trait
            lang_trait = ET.SubElement(elem, 'trait')
            lang_trait.set('name', 'display-language')
            lang_trait.set('value', language_preference)

        # Add other traits
        traits = element_data.get('traits', {})
        for trait_name, trait_value in traits.items():
            # Skip the 'display-language' trait if it's also in the traits dict to avoid duplication
            if trait_name != 'display-language':
                trait_elem = ET.SubElement(elem, 'trait')
                trait_elem.set('name', trait_name)
                trait_elem.set('value', trait_value)

        return ET.tostring(elem, encoding='unicode')
