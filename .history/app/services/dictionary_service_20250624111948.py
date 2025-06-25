"""
Dictionary service for managing dictionary entries.

This module provides services for interacting with the dictionary database,
including CRUD operations for entries, searching, and other dictionary-related operations.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Tuple
import re

from app.database.basex_connector import BaseXConnector
from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser, LIFTRangesParser
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError, ExportError


class DictionaryService:
    """
    Service for managing dictionary entries.
    
    This class provides methods for CRUD operations on dictionary entries,
    as well as more complex operations like searching and batch processing.
    """
    
    def __init__(self, db_connector: BaseXConnector):
        """
        Initialize a dictionary service.
        
        Args:
            db_connector: Database connector for accessing the BaseX database.
        """
        self.db_connector = db_connector
        self.logger = logging.getLogger(__name__)
        self.lift_parser = LIFTParser()
        self.ranges_parser = LIFTRangesParser()
        self.ranges: Dict[str, Any] = {}  # Cache for ranges data
    
    def initialize_database(self, lift_path: str, ranges_path: Optional[str] = None) -> None:
        """
        Initialize the database with LIFT data.
        
        Args:
            lift_path: Path to the LIFT file.
            ranges_path: Optional path to the LIFT ranges file.
            
        Raises:
            FileNotFoundError: If the LIFT file does not exist.
            DatabaseError: If there is an error initializing the database.
        """
        try:
            # Connect to the database
            if not self.db_connector.connect():
                raise DatabaseError("Failed to connect to BaseX database")
            
            # Create database if it doesn't exist
            database_exists = self.db_connector.execute_query("list-db") or ""
            db_name = self.db_connector.database or "dictionary"
            
            if db_name not in database_exists:
                self.logger.info("Creating database: %s", db_name)
                self.db_connector.execute_update(f"CREATE DB {db_name}")
            
            # Load LIFT file
            self.logger.info("Loading LIFT file: %s", lift_path)
            entries = self.lift_parser.parse_file(lift_path)
            
            # Store LIFT data in the database
            self.db_connector.execute_update(f"OPEN {db_name}")
            self.db_connector.execute_update("DELETE /*")  # Clear existing data
            
            # Import entries one by one
            for entry in entries:
                self.create_or_update_entry(entry)
            
            # Load ranges file if provided
            if ranges_path and os.path.exists(ranges_path):
                self.logger.info("Loading LIFT ranges file: %s", ranges_path)
                self.ranges = self.ranges_parser.parse_file(ranges_path)
                # Store ranges as JSON in the database for future reference
                self.db_connector.execute_update("ADD to ranges.json")
            
            self.logger.info("Database initialization complete")
            
        except Exception as e:
            self.logger.error("Error initializing database: %s", str(e))
            raise DatabaseError("Failed to initialize database: %s" % str(e)) from e
    
    def get_entry(self, entry_id: str) -> Entry:
        """
        Get an entry by ID.
        
        Args:
            entry_id: ID of the entry to retrieve.
            
        Returns:
            Entry object.
            
        Raises:
            NotFoundError: If the entry does not exist.
            DatabaseError: If there is an error retrieving the entry.
        """
        try:
            query = f"""
            for $entry in /lift/entry[@id="{entry_id}"]
            return $entry
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                raise NotFoundError(f"Entry not found: {entry_id}")
            
            # Parse the XML string into an Entry object
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            if not entries:
                raise NotFoundError(f"Entry not found or could not be parsed: {entry_id}")
            
            return entries[0]
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error("Error retrieving entry %s: %s", entry_id, str(e))
            raise DatabaseError("Failed to retrieve entry: %s" % str(e)) from e
    
    def create_entry(self, entry: Entry) -> str:
        """
        Create a new entry.
        
        Args:
            entry: Entry object to create.
            
        Returns:
            ID of the created entry.
            
        Raises:
            ValidationError: If the entry fails validation.
            DatabaseError: If there is an error creating the entry.
        """
        try:
            # Validate the entry
            if not entry.validate():
                raise ValidationError("Entry validation failed")
            
            # Check if entry with this ID already exists
            try:
                existing_entry = self.get_entry(entry.id)
                if existing_entry:
                    raise ValidationError(f"Entry with ID {entry.id} already exists")
            except NotFoundError:
                pass  # Entry doesn't exist, which is what we want
            
            # Generate LIFT XML for the entry
            entry_xml = self.lift_parser.generate_lift_string([entry])
            
            # Extract just the entry element (without the lift root)
            entry_element = re.search(r'<entry.*?</entry>', entry_xml, re.DOTALL)
            if not entry_element:
                raise ValueError("Failed to extract entry element from generated XML")
            
            entry_xml = entry_element.group(0)
            
            # Insert the entry into the database
            query = f"""
            insert node {entry_xml} into /lift
            """
            
            self.db_connector.execute_update(query)
            
            return entry.id
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error("Error creating entry: %s", str(e))
            raise DatabaseError("Failed to create entry: %s" % str(e)) from e
    
    def update_entry(self, entry: Entry) -> None:
        """
        Update an existing entry.
        
        Args:
            entry: Entry object to update.
            
        Raises:
            NotFoundError: If the entry does not exist.
            ValidationError: If the entry fails validation.
            DatabaseError: If there is an error updating the entry.
        """
        try:
            # Validate the entry
            if not entry.validate():
                raise ValidationError("Entry validation failed")
            
            # Check if entry exists
            try:
                self.get_entry(entry.id)
            except NotFoundError:
                raise NotFoundError(f"Entry not found: {entry.id}")
            
            # Generate LIFT XML for the entry
            entry_xml = self.lift_parser.generate_lift_string([entry])
            
            # Extract just the entry element (without the lift root)
            entry_element = re.search(r'<entry.*?</entry>', entry_xml, re.DOTALL)
            if not entry_element:
                raise ValueError("Failed to extract entry element from generated XML")
            
            entry_xml = entry_element.group(0)
            
            # Update the entry in the database
            query = f"""
            replace node /lift/entry[@id="{entry.id}"] with {entry_xml}
            """
            
            self.db_connector.execute_update(query)
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error("Error updating entry %s: %s", entry.id, str(e))
            raise DatabaseError("Failed to update entry: %s" % str(e)) from e
    
    def delete_entry(self, entry_id: str) -> None:
        """
        Delete an entry by ID.
        
        Args:
            entry_id: ID of the entry to delete.
            
        Raises:
            NotFoundError: If the entry does not exist.
            DatabaseError: If there is an error deleting the entry.
        """
        try:
            # Check if entry exists
            try:
                self.get_entry(entry_id)
            except NotFoundError:
                raise NotFoundError(f"Entry not found: {entry_id}")
            
            # Delete the entry from the database
            query = f"""
            delete node /lift/entry[@id="{entry_id}"]
            """
            
            self.db_connector.execute_update(query)
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error("Error deleting entry %s: %s", entry_id, str(e))
            raise DatabaseError("Failed to delete entry: %s" % str(e)) from e
      def list_entries(self, limit: int = None, offset: int = 0, sort_by: str = "lexical_unit") -> Tuple[List[Entry], int]:
        """
        List entries.
        
        Args:
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.
            sort_by: Field to sort by (lexical_unit, id, etc.).
            
        Returns:
            Tuple of (list of Entry objects, total count).
            
        Raises:
            DatabaseError: If there is an error listing entries.
        """
        try:
            # Get total count
            count_query = """
            count(/lift/entry)
            """
            
            total_count = int(self.db_connector.execute_query(count_query))
            
            # Determine sort expression
            if sort_by == "lexical_unit":
                sort_expr = "sort($entry/lexical-unit/form/text)"
            else:  # Default to id
                sort_expr = "sort(@id)"
            
            # Build pagination expressions
            pagination_expr = ""
            if limit is not None and offset > 0:
                pagination_expr = f"[position() > {offset} and position() <= {offset + limit}]"
            elif limit is not None:
                pagination_expr = f"[position() <= {limit}]"
            elif offset > 0:
                pagination_expr = f"[position() > {offset}]"
            
            # List entries
            query = f"""
            (for $entry in /lift/entry
            order by {sort_expr}
            return $entry){pagination_expr}
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                return [], total_count
            
            # Parse the XML string into Entry objects
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries, total_count
            
        except Exception as e:
            self.logger.error("Error listing entries: %s", str(e))
            raise DatabaseError("Failed to list entries: %s" % str(e)) from e
    
    def search_entries(self, 
                      query: str, 
                      fields: Optional[List[str]] = None) -> Tuple[List[Entry], int]:
        """
        Search for entries.
        
        Args:
            query: Search query.
            fields: Fields to search in (default: lexical_unit, glosses, definitions).
            
        Returns:
            Tuple of (list of Entry objects, total count).
            
        Raises:
            DatabaseError: If there is an error searching entries.
        """
        if not fields:
            fields = ["lexical_unit", "glosses", "definitions"]
        
        try:
            # Construct the search conditions
            conditions: List[str] = []
            
            if "lexical_unit" in fields:
                conditions.append(f'contains(lower-case($entry/lexical-unit/form/text), "{query.lower()}")')
            
            if "glosses" in fields:
                conditions.append(f'some $gloss in $entry/sense/gloss/text satisfies contains(lower-case($gloss), "{query.lower()}")')
            
            if "definitions" in fields:
                conditions.append(f'some $def in $entry/sense/definition/form/text satisfies contains(lower-case($def), "{query.lower()}")')
            
            search_condition = " or ".join(conditions)
            
            # Get total count
            count_query = f"""
            count(for $entry in /lift/entry
            where {search_condition}
            return $entry)
            """
            
            total_count = int(self.db_connector.execute_query(count_query))
            
            # Search entries
            query = f"""
            for $entry in /lift/entry
            where {search_condition}
            order by $entry/lexical-unit/form/text
            return $entry
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                return [], total_count
            
            # Parse the XML string into Entry objects
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries, total_count
            
        except Exception as e:
            self.logger.error("Error searching entries: %s", str(e))
            raise DatabaseError("Failed to search entries: %s" % str(e)) from e
    
    def get_entry_count(self) -> int:
        """
        Get the total number of entries in the dictionary.
        
        Returns:
            Total number of entries.
            
        Raises:
            DatabaseError: If there is an error getting the entry count.
        """
        try:
            query = """
            count(/lift/entry)
            """
            
            result = self.db_connector.execute_query(query)
            
            return int(result)
            
        except Exception as e:
            self.logger.error("Error getting entry count: %s", str(e))
            raise DatabaseError("Failed to get entry count: %s" % str(e)) from e
    
    def get_related_entries(self, entry_id: str, relation_type: Optional[str] = None) -> List[Entry]:
        """
        Get entries related to the specified entry.
        
        Args:
            entry_id: ID of the entry to get related entries for.
            relation_type: Optional type of relation to filter by.
            
        Returns:
            List of related Entry objects.
            
        Raises:
            NotFoundError: If the entry does not exist.
            DatabaseError: If there is an error getting related entries.
        """
        try:
            # Check if entry exists
            try:
                self.get_entry(entry_id)
            except NotFoundError:
                raise NotFoundError(f"Entry not found: {entry_id}")
            
            # Construct the relation condition
            relation_condition = f'@type="{relation_type}"' if relation_type else '1=1'
            
            # Get related entries
            query = f"""
            let $entry_relations := /lift/entry[@id="{entry_id}"]/relation[{relation_condition}]/@ref
            for $related in /lift/entry[@id = $entry_relations]
            return $related
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                return []
            
            # Parse the XML string into Entry objects
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error("Error getting related entries for %s: %s", entry_id, str(e))
            raise DatabaseError("Failed to get related entries: %s" % str(e)) from e
    
    def get_entries_by_grammatical_info(self, grammatical_info: str) -> List[Entry]:
        """
        Get entries with the specified grammatical information.
        
        Args:
            grammatical_info: Grammatical information to filter by.
            
        Returns:
            List of Entry objects.
            
        Raises:
            DatabaseError: If there is an error getting entries.
        """
        try:
            query = f"""
            for $entry in /lift/entry[grammatical-info/@value="{grammatical_info}"]
            return $entry
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                return []
            
            # Parse the XML string into Entry objects
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries
            
        except Exception as e:
            self.logger.error("Error getting entries by grammatical info %s: %s", grammatical_info, str(e))
            raise DatabaseError("Failed to get entries by grammatical info: %s" % str(e)) from e
    
    def count_entries(self) -> int:
        """
        Count the total number of entries in the dictionary.
        
        Returns:
            The total number of entries.
            
        Raises:
            DatabaseError: If there is an error accessing the database.
        """
        try:
            query = "count(//lift:entry)"
            result = self.db_connector.execute_query(query)
            
            # Convert the result to an integer
            return int(result) if result else 0
            
        except Exception as e:
            self.logger.error("Error counting entries: %s", str(e))
            raise DatabaseError("Failed to count entries: %s" % str(e)) from e
    
    def count_senses_and_examples(self) -> Tuple[int, int]:
        """
        Count the total number of senses and examples in the dictionary.
        
        Returns:
            A tuple containing (sense_count, example_count).
            
        Raises:
            DatabaseError: If there is an error accessing the database.
        """
        try:
            # Count senses
            sense_query = "count(//lift:sense)"
            sense_result = self.db_connector.execute_query(sense_query)
            sense_count = int(sense_result) if sense_result else 0
            
            # Count examples
            example_query = "count(//lift:example)"
            example_result = self.db_connector.execute_query(example_query)
            example_count = int(example_result) if example_result else 0
            
            return sense_count, example_count
            
        except Exception as e:
            self.logger.error("Error counting senses and examples: %s", str(e))
            raise DatabaseError("Failed to count senses and examples: %s" % str(e)) from e
    
    def import_lift(self, lift_path: str) -> int:
        """
        Import entries from a LIFT file.
        
        Args:
            lift_path: Path to the LIFT file.
            
        Returns:
            Number of entries imported.
            
        Raises:
            FileNotFoundError: If the LIFT file does not exist.
            DatabaseError: If there is an error importing the data.
        """
        try:
            if not os.path.exists(lift_path):
                raise FileNotFoundError(f"LIFT file not found: {lift_path}")
            
            # Parse the LIFT file
            entries = self.lift_parser.parse_file(lift_path)
            
            # Add entries to the database
            for entry in entries:
                self.create_or_update_entry(entry)
            
            self.logger.info("Imported %d entries from LIFT file", len(entries))
            return len(entries)
            
        except Exception as e:
            self.logger.error("Error importing LIFT file: %s", str(e))
            raise DatabaseError("Failed to import LIFT file: %s" % str(e)) from e
    
    def export_lift(self) -> str:
        """
        Export all entries to LIFT format.
        
        Returns:
            LIFT content as a string.
            
        Raises:
            ExportError: If there is an error exporting the data.
        """
        try:
            # Get all entries
            entries, _ = self.list_entries()  # Get all entries
            
            # Generate LIFT XML
            lift_xml = self.lift_parser.generate_lift_string(entries)
            
            self.logger.info("Exported %d entries to LIFT format", len(entries))
            return lift_xml
            
        except Exception as e:
            self.logger.error("Error exporting to LIFT format: %s", str(e))
            raise ExportError("Failed to export to LIFT format: %s" % str(e)) from e
    
    def export_to_kindle(self, output_path: str, title: str = "Dictionary", 
                       source_lang: str = "en", target_lang: str = "pl",
                       author: str = "Dictionary Writing System", kindlegen_path: Optional[str] = None) -> str:
        """
        Export the dictionary to Kindle format.
        
        Args:
            output_path: Path to the output directory.
            title: Title of the dictionary.
            source_lang: Source language code.
            target_lang: Target language code.
            author: Author name for the dictionary.
            kindlegen_path: Optional path to the kindlegen executable.
            
        Returns:
            Path to the exported files.
            
        Raises:
            ExportError: If there is an error exporting the dictionary.
        """
        try:
            from app.exporters.kindle_exporter import KindleExporter
            
            # Get all entries
            entries, _ = self.list_entries()  # Get all entries
            
            # Create exporter
            exporter = KindleExporter(self)
            
            # Export
            output_dir = exporter.export(
                output_path, 
                entries, 
                title=title, 
                source_lang=source_lang, 
                target_lang=target_lang, 
                author=author,
                kindlegen_path=kindlegen_path
            )
            
            self.logger.info("Dictionary exported to Kindle format at %s", output_dir)
            return output_dir
            
        except Exception as e:
            self.logger.error("Error exporting dictionary to Kindle format: %s", str(e))
            raise ExportError("Failed to export dictionary to Kindle format: %s" % str(e)) from e
    
    def export_to_sqlite(self, output_path: str, source_lang: str = "en", target_lang: str = "pl",
                        batch_size: int = 500) -> str:
        """
        Export the dictionary to SQLite format for mobile apps.
        
        Args:
            output_path: Path to the output SQLite database.
            source_lang: Source language code.
            target_lang: Target language code.
            batch_size: Number of entries to process in each batch.
            
        Returns:
            Path to the exported SQLite database.
            
        Raises:
            ExportError: If there is an error exporting the dictionary.
        """
        try:
            from app.exporters.sqlite_exporter import SQLiteExporter
            
            # Get all entries
            entries, _ = self.list_entries()  # Get all entries
            
            # Create exporter
            exporter = SQLiteExporter(self)
            
            # Export
            output_file = exporter.export(
                output_path, 
                entries, 
                source_lang=source_lang, 
                target_lang=target_lang, 
                batch_size=batch_size
            )
            
            self.logger.info("Dictionary exported to SQLite format at %s", output_file)
            return output_file
            
        except Exception as e:
            self.logger.error("Error exporting dictionary to SQLite format: %s", str(e))
            raise ExportError("Failed to export dictionary to SQLite format: %s" % str(e)) from e

    def create_or_update_entry(self, entry: Entry) -> str:
        """
        Create a new entry or update an existing one.
        
        Args:
            entry: Entry object to create or update.
            
        Returns:
            ID of the created or updated entry.
            
        Raises:
            ValidationError: If the entry fails validation.
            DatabaseError: If there is an error creating or updating the entry.
        """
        try:
            # Check if entry exists
            try:
                self.get_entry(entry.id)
                # Entry exists, update it
                self.update_entry(entry)
                return entry.id
            except NotFoundError:
                # Entry doesn't exist, create it
                return self.create_entry(entry)
        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            self.logger.error("Error creating or updating entry %s: %s", entry.id, str(e))
            raise DatabaseError("Failed to create or update entry: %s" % str(e)) from e
    
    def export_to_lift(self, output_path: str) -> None:
        """
        Export all entries to a LIFT file.
        
        Args:
            output_path: Path to the output LIFT file.
            
        Raises:
            ExportError: If there is an error exporting the data.
        """
        try:
            # Get all entries
            lift_content = self.export_lift()
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(lift_content)
            
            self.logger.info("LIFT file exported to %s", output_path)
            
        except Exception as e:
            self.logger.error("Error exporting LIFT file: %s", str(e))
            raise ExportError("Failed to export LIFT file: %s" % str(e)) from e
    
    def get_ranges(self) -> Dict[str, Any]:
        """
        Get the ranges data for the dictionary.
        
        Returns:
            Dictionary containing ranges data.
            
        Raises:
            DatabaseError: If there is an error getting the ranges.
        """
        try:
            # Check if ranges are cached
            if self.ranges:
                return self.ranges
            
            # Try to get ranges from database
            query = """
            /lift-ranges
            """
            
            result = self.db_connector.execute_query(query)
            
            if result:
                # Parse ranges data (placeholder - would need proper parsing)
                self.ranges = {"ranges": {"data": result}}
            else:
                # Return empty ranges structure
                self.ranges = {"ranges": {}}
            
            return self.ranges
            
        except Exception as e:
            self.logger.error("Error getting ranges: %s", str(e))
            # Return empty ranges on error
            return {"ranges": {}}
    
    def get_range_values(self, range_id: str) -> List[Dict[str, Any]]:
        """
        Get the values for a specific range.
        
        Args:
            range_id: ID of the range.
            
        Returns:
            List of range values.
            
        Raises:
            NotFoundError: If the range does not exist.
            DatabaseError: If there is an error getting the range values.
        """
        try:
            # Get ranges
            ranges = self.get_ranges()
            
            # Look for the specific range
            if "ranges" in ranges and range_id in ranges["ranges"]:
                range_data = ranges["ranges"][range_id]
                if isinstance(range_data, list):
                    return range_data
                elif isinstance(range_data, dict) and "values" in range_data:
                    return range_data["values"]
            
            # Try to query the database directly
            query = f"""
            /lift-ranges/range[@id="{range_id}"]/range-element
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                raise NotFoundError(f"Range not found: {range_id}")
            
            # Parse range elements (placeholder - would need proper parsing)
            return [{"id": range_id, "value": result}]
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error("Error getting range values for %s: %s", range_id, str(e))
            raise DatabaseError("Failed to get range values: %s" % str(e)) from e
