"""
Dictionary service for managing dictionary entries.

This module provides services for interacting with the dictionary database,
including CRUD operations for entries, searching, and other dictionary-related operations.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Tuple
import re
import json

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
        self.ranges = {}  # Cache for ranges data
    
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
            database_exists = self.db_connector.execute_query("list-db")
            db_name = self.db_connector.database
            
            if db_name not in database_exists:
                self.logger.info(f"Creating database: {db_name}")
                self.db_connector.execute_command(f"CREATE DB {db_name}")
            
            # Load LIFT file
            self.logger.info(f"Loading LIFT file: {lift_path}")
            with open(lift_path, 'r', encoding='utf-8') as f:
                lift_data = f.read()
            
            # Store LIFT data in the database
            self.db_connector.execute_command(f"OPEN {db_name}")
            self.db_connector.execute_command("DELETE /*")  # Clear existing data
            self.db_connector.execute_command("ADD to lift.xml", lift_data)
            
            # Load ranges file if provided
            if ranges_path and os.path.exists(ranges_path):
                self.logger.info(f"Loading LIFT ranges file: {ranges_path}")
                self.ranges = self.ranges_parser.parse_file(ranges_path)
                
                # Store ranges as JSON in the database for future reference
                ranges_json = json.dumps(self.ranges)
                self.db_connector.execute_command("ADD to ranges.json", ranges_json)
            
            self.logger.info("Database initialization complete")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")
    
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
            self.logger.error(f"Error retrieving entry {entry_id}: {e}")
            raise DatabaseError(f"Failed to retrieve entry: {e}")
    
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
            
            self.db_connector.execute_command(query)
            
            return entry.id
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error creating entry: {e}")
            raise DatabaseError(f"Failed to create entry: {e}")
    
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
            
            self.db_connector.execute_command(query)
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error updating entry {entry.id}: {e}")
            raise DatabaseError(f"Failed to update entry: {e}")
    
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
            
            self.db_connector.execute_command(query)
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error deleting entry {entry_id}: {e}")
            raise DatabaseError(f"Failed to delete entry: {e}")
    
    def list_entries(self, 
                    limit: int = 100, 
                    offset: int = 0, 
                    sort_by: str = "lexical_unit") -> Tuple[List[Entry], int]:
        """
        List entries with pagination.
        
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
            
            # List entries with pagination
            query = f"""
            for $entry in /lift/entry
            order by {sort_expr}
            return $entry
            """
            
            result = self.db_connector.execute_query(query, limit=limit, offset=offset)
            
            if not result:
                return [], total_count
            
            # Parse the XML string into Entry objects
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries, total_count
            
        except Exception as e:
            self.logger.error(f"Error listing entries: {e}")
            raise DatabaseError(f"Failed to list entries: {e}")
    
    def search_entries(self, 
                      query: str, 
                      fields: List[str] = None, 
                      limit: int = 100, 
                      offset: int = 0) -> Tuple[List[Entry], int]:
        """
        Search for entries.
        
        Args:
            query: Search query.
            fields: Fields to search in (default: lexical_unit, glosses, definitions).
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.
            
        Returns:
            Tuple of (list of Entry objects, total count).
            
        Raises:
            DatabaseError: If there is an error searching entries.
        """
        if not fields:
            fields = ["lexical_unit", "glosses", "definitions"]
        
        try:
            # Construct the search conditions
            conditions = []
            
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
            
            # Search entries with pagination
            query = f"""
            for $entry in /lift/entry
            where {search_condition}
            order by $entry/lexical-unit/form/text
            return $entry
            """
            
            result = self.db_connector.execute_query(query, limit=limit, offset=offset)
            
            if not result:
                return [], total_count
            
            # Parse the XML string into Entry objects
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries, total_count
            
        except Exception as e:
            self.logger.error(f"Error searching entries: {e}")
            raise DatabaseError(f"Failed to search entries: {e}")
    
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
            self.logger.error(f"Error getting entry count: {e}")
            raise DatabaseError(f"Failed to get entry count: {e}")
    
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
            self.logger.error(f"Error getting related entries for {entry_id}: {e}")
            raise DatabaseError(f"Failed to get related entries: {e}")
    
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
            self.logger.error(f"Error getting entries by grammatical info {grammatical_info}: {e}")
            raise DatabaseError(f"Failed to get entries by grammatical info: {e}")
    
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
            self.logger.error(f"Error counting entries: {e}")
            raise DatabaseError(f"Failed to count entries: {e}")
    
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
            self.logger.error(f"Error counting senses and examples: {e}")
            raise DatabaseError(f"Failed to count senses and examples: {e}")
    
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
            
            self.logger.info(f"Imported {len(entries)} entries from LIFT file")
            return len(entries)
            
        except Exception as e:
            self.logger.error(f"Error importing LIFT file: {e}")
            raise DatabaseError(f"Failed to import LIFT file: {e}")
    
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
            entries, _ = self.list_entries(limit=100000)  # Get all entries
            
            # Generate LIFT XML
            lift_xml = self.lift_parser.generate_lift_string(entries)
            
            self.logger.info(f"Exported {len(entries)} entries to LIFT format")
            return lift_xml
            
        except Exception as e:
            self.logger.error(f"Error exporting to LIFT format: {e}")
            raise ExportError(f"Failed to export to LIFT format: {e}")
    
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
            entries, _ = self.list_entries(limit=100000)  # Assuming the dictionary is not too large
            
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
            
            self.logger.info(f"Dictionary exported to Kindle format at {output_dir}")
            return output_dir
            
        except Exception as e:
            self.logger.error(f"Error exporting dictionary to Kindle format: {e}")
            raise ExportError(f"Failed to export dictionary to Kindle format: {e}")
    
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
            entries, _ = self.list_entries(limit=100000)  # Assuming the dictionary is not too large
            
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
            
            self.logger.info(f"Dictionary exported to SQLite format at {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error exporting dictionary to SQLite format: {e}")
            raise ExportError(f"Failed to export dictionary to SQLite format: {e}")
