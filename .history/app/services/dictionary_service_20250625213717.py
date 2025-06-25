"""
Dictionary service for managing dictionary entries.

This module provides services for interacting with the dictionary database,
including CRUD operations for entries, searching, and other dictionary-related operations.
"""

import logging
import os
import random
from typing import Dict, List, Any, Optional, Tuple, Union
import xml.etree.ElementTree as ET

from app.database.basex_connector import BaseXConnector
from app.database.mock_connector import MockDatabaseConnector
from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser, LIFTRangesParser
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError, ExportError
from app.utils.constants import DB_NAME_NOT_CONFIGURED


class DictionaryService:
    """
    Service for managing dictionary entries.
    
    This class provides methods for CRUD operations on dictionary entries,
    as well as more complex operations like searching and batch processing.
    """
    
    def __init__(self, db_connector: Union[BaseXConnector, MockDatabaseConnector]):
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

        try:
            db_name = self.db_connector.database
            if db_name:
                # Check if DB exists before trying to open
                if db_name in (self.db_connector.execute_query("LIST") or ""):
                    self.db_connector.execute_update(f"OPEN {db_name}")
                    self.logger.info("Successfully opened database '%s'", db_name)
                else:
                    self.logger.warning(
                        "Database '%s' not found on BaseX server. "
                        "Application will not function correctly until the database is initialized. "
                        "Please run `scripts/import_lift.py --init`.",
                        db_name,
                    )
        except Exception as e:
            self.logger.error("Failed to connect to BaseX server on startup: %s", e, exc_info=True)

    def _prepare_entry_xml(self, entry: Entry) -> str:
        """
        Generates and prepares the XML string for an entry, stripping namespaces.
        """
        entry_xml_full = self.lift_parser.generate_lift_string([entry])
        root = ET.fromstring(entry_xml_full)
        entry_elem_ns = root.find('.//lift:entry', self.lift_parser.NSMAP)
        if entry_elem_ns is None:
            entry_elem_ns = root.find('.//entry')  # fallback

        if entry_elem_ns is None:
            raise ValueError("Failed to find entry element in generated XML")

        # Strip namespaces
        for elem in entry_elem_ns.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
            for key in elem.attrib.keys():
                if '}' in key:
                    new_key = key.split('}', 1)[1]
                    elem.attrib[new_key] = elem.attrib.pop(key)
                if key.startswith('xmlns'):
                    del elem.attrib[key]
        
        return ET.tostring(entry_elem_ns, encoding='unicode')

    def initialize_database(self, lift_path: str, ranges_path: Optional[str] = None) -> None:
        """
        Initialize the database with LIFT data. This will create a new database,
        or replace an existing one.
        
        Args:
            lift_path: Path to the LIFT file.
            ranges_path: Optional path to the LIFT ranges file.
            
        Raises:
            FileNotFoundError: If the LIFT file does not exist.
            DatabaseError: If there is an error initializing the database.
        """
        try:
            if not os.path.exists(lift_path):
                raise FileNotFoundError(f"LIFT file not found: {lift_path}")

            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)
            self.logger.info("Initializing database '%s' from LIFT file: %s", db_name, lift_path)

            # Drop the database if it exists, to ensure a clean start
            if db_name in (self.db_connector.execute_query("LIST") or ""):
                self.logger.info("Dropping existing database: %s", db_name)
                self.db_connector.execute_update(f"DROP DB {db_name}")

            # Create the database from the LIFT file
            self.logger.info("Creating new database '%s' from %s", db_name, lift_path)
            # Use forward slashes for paths in BaseX commands
            lift_path_basex = lift_path.replace('\\', '/')
            self.db_connector.execute_update(f'CREATE DB {db_name} "{lift_path_basex}"')
            
            # Now open the newly created database for subsequent operations
            self.db_connector.execute_update(f"OPEN {db_name}")

            # Load ranges file if provided and add it to the db
            if ranges_path and os.path.exists(ranges_path):
                self.logger.info("Adding LIFT ranges file to database: %s", ranges_path)
                ranges_path_basex = ranges_path.replace('\\', '/')
                self.db_connector.execute_update(f'ADD TO ranges.xml "{ranges_path_basex}"')
                self.logger.info("LIFT ranges file added as ranges.xml")
            else:
                self.logger.warning("No LIFT ranges file provided. Creating empty ranges document.")
                self.db_connector.execute_update('ADD TO ranges.xml "<lift-ranges/>"')

            self.logger.info("Database initialization complete")

        except Exception as e:
            self.logger.error("Error initializing database: %s", str(e), exc_info=True)
            raise DatabaseError(f"Failed to initialize database: {e}") from e
    
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
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            query = f"""
            xquery for $entry in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id="{entry_id}"]
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
            raise DatabaseError(f"Failed to retrieve entry: {str(e)}") from e
    
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
            if not entry.validate():
                raise ValidationError("Entry validation failed")
            
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            try:
                if self.get_entry(entry.id):
                    raise ValidationError(f"Entry with ID {entry.id} already exists")
            except NotFoundError:
                pass  # Entry doesn't exist, which is what we want

            entry_xml = self._prepare_entry_xml(entry)
            
            query = f"""
            xquery insert node {entry_xml} into collection('{db_name}')/*[local-name()='lift']
            """
            
            self.db_connector.execute_update(query)
            
            return entry.id
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error("Error creating entry: %s", str(e))
            raise DatabaseError(f"Failed to create entry: {str(e)}") from e
    
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
            if not entry.validate():
                raise ValidationError("Entry validation failed")
            
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            # Check if entry exists
            self.get_entry(entry.id)

            entry_xml = self._prepare_entry_xml(entry)
            
            query = f"""
            xquery replace node collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id="{entry.id}"] with {entry_xml}
            """
            
            self.db_connector.execute_update(query)
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error("Error updating entry %s: %s", entry.id, str(e))
            raise DatabaseError(f"Failed to update entry: {str(e)}") from e

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
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            # Check if entry exists
            self.get_entry(entry_id)
            
            query = f"""
            xquery delete node collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id="{entry_id}"]
            """
            
            self.db_connector.execute_update(query)
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error("Error deleting entry %s: %s", entry_id, str(e))
            raise DatabaseError(f"Failed to delete entry: {str(e)}") from e

    def list_entries(self, limit: Optional[int] = None, offset: int = 0, sort_by: str = "lexical_unit") -> Tuple[List[Entry], int]:
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
            total_count = self.count_entries()

            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)
            
            if sort_by == "lexical_unit":
                sort_expr = "$entry/lexical-unit/form/text/text()"
            else:
                sort_expr = "$entry/@id"
            
            pagination_expr = ""
            if limit is not None:
                start = offset + 1
                end = offset + limit
                pagination_expr = f"[position() = {start} to {end}]"

            query = f"""
            xquery (for $entry in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry']
            order by {sort_expr}
            return $entry){pagination_expr}
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                return [], total_count
            
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries, total_count            
        except Exception as e:
            self.logger.error("Error listing entries: %s", str(e))
            raise DatabaseError(f"Failed to list entries: {str(e)}") from e

    def search_entries(self, 
                      query: str, 
                      fields: Optional[List[str]] = None,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None) -> Tuple[List[Entry], int]:
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
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            conditions: List[str] = []
            q_lower = query.lower()
            if "lexical_unit" in fields:
                conditions.append(f'contains(lower-case($entry/lexical-unit/form/text), "{q_lower}")')
            if "glosses" in fields:
                conditions.append(f'some $gloss in $entry/sense/gloss/text satisfies contains(lower-case($gloss), "{q_lower}")')
            if "definitions" in fields:
                conditions.append(f'some $def in $entry/sense/definition/form/text satisfies contains(lower-case($def), "{q_lower}")')
            
            search_condition = " or ".join(conditions)
            
            count_query = f"""
            xquery count(for $entry in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry']
            where {search_condition}
            return $entry)
            """
            
            count_result = self.db_connector.execute_query(count_query)
            total_count = int(count_result) if count_result else 0
            
            pagination_expr = ""
            if limit is not None and offset is not None:
                start = offset + 1
                end = offset + limit
                pagination_expr = f"[position() = {start} to {end}]"

            query_str = f"""
            xquery (for $entry in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry']
            where {search_condition}
            order by $entry/lexical-unit/form/text/text()
            return $entry){pagination_expr}
            """
            
            result = self.db_connector.execute_query(query_str)
            
            if not result:
                return [], total_count
            
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries, total_count
            
        except Exception as e:
            self.logger.error("Error searching entries: %s", str(e))
            raise DatabaseError(f"Failed to search entries: {str(e)}") from e
    
    def get_entry_count(self) -> int:
        """
        Get the total number of entries in the dictionary.
        
        Returns:
            Total number of entries.
            
        Raises:
            DatabaseError: If there is an error getting the entry count.
        """
        return self.count_entries()
    
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
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            self.get_entry(entry_id)
            
            relation_condition = f'[@type="{relation_type}"]' if relation_type else ''
            
            query = f"""
            xquery let $entry_relations := collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id="{entry_id}"]/relation{relation_condition}/@ref
            for $related in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id = $entry_relations]
            return $related
            """
            
            result = self.db_connector.execute_query(query)
            
            if not result:
                return []
            
            return self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error("Error getting related entries for %s: %s", entry_id, str(e))
            raise DatabaseError(f"Failed to get related entries: {str(e)}") from e

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
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            query = f"""
            xquery for $entry in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry']
            where $entry/*[local-name()='sense']/*[local-name()='grammatical-info'][@value="{grammatical_info}"]
            return $entry
            """

            result = self.db_connector.execute_query(query)

            if not result:
                return []

            return self.lift_parser.parse_string(f"<lift>{result}</lift>")

        except Exception as e:
            self.logger.error("Error getting entries by grammatical info %s: %s", grammatical_info, str(e))
            raise DatabaseError(f"Failed to get entries by grammatical info: {str(e)}") from e

    def count_entries(self) -> int:
        """
        Count the total number of entries in the dictionary.
        
        Returns:
            The total number of entries.
            
        Raises:
            DatabaseError: If there is an error accessing the database.
        """
        try:
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            # Use collection() instead of doc() to handle multiple documents
            query = f"xquery count(collection('{db_name}')//*:entry)"
            result = self.db_connector.execute_query(query)
            
            return int(result) if result else 0
            
        except Exception as e:
            self.logger.error("Error counting entries: %s", str(e), exc_info=True)
            raise DatabaseError(f"Failed to count entries: {e}") from e
    
    def count_senses_and_examples(self) -> Tuple[int, int]:
        """
        Count the total number of senses and examples in the dictionary.
        
        Returns:
            A tuple containing (sense_count, example_count).
            
        Raises:
            DatabaseError: If there is an error accessing the database.
        """
        try:
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            # Use collection() instead of doc() to handle multiple documents
            sense_query = f"xquery count(collection('{db_name}')//*:sense)"
            sense_result = self.db_connector.execute_query(sense_query)
            sense_count = int(sense_result) if sense_result else 0
            
            example_query = f"xquery count(collection('{db_name}')//*:example)"
            example_result = self.db_connector.execute_query(example_query)
            example_count = int(example_result) if example_result else 0
            
            return sense_count, example_count
            
        except Exception as e:
            self.logger.error("Error counting senses and examples: %s", str(e), exc_info=True)
            raise DatabaseError(f"Failed to count senses and examples: {e}") from e

    def import_lift(self, lift_path: str) -> int:
        """
        Import entries from a LIFT file into the existing database.
        This will update existing entries and add new ones.
        
        Args:
            lift_path: Path to the LIFT file.
            
        Returns:
            Number of entries imported/updated.
            
        Raises:
            FileNotFoundError: If the LIFT file does not exist.
            DatabaseError: If there is an error importing the data.
        """
        try:
            if not os.path.exists(lift_path):
                raise FileNotFoundError(f"LIFT file not found: {lift_path}")

            lift_path_basex = lift_path.replace('\\', '/')
            temp_db_name = f"import_{os.path.basename(lift_path).replace('.', '_')}_{random.randint(1000, 9999)}"
            
            try:
                self.db_connector.execute_update(f'CREATE DB {temp_db_name} "{lift_path_basex}"')
                
                total_in_file_query = f"xquery count(db:open('{temp_db_name}')//entry)"
                total_count = int(self.db_connector.execute_query(total_in_file_query) or 0)

                update_query = f"""
                xquery
                let $source_entries := db:open('{temp_db_name}')//entry
                for $source_entry in $source_entries
                let $entry_id := $source_entry/@id/string()
                let $target_entry := doc('{self.db_connector.database}')/lift/entry[@id = $entry_id]
                return if (exists($target_entry))
                then replace node $target_entry with $source_entry
                else insert node $source_entry into doc('{self.db_connector.database}')/lift
                """
                self.db_connector.execute_update(update_query)
                
                self.logger.info("Imported/updated %d entries from LIFT file", total_count)
                return total_count

            finally:
                if temp_db_name in (self.db_connector.execute_query("LIST") or ""):
                    self.db_connector.execute_update(f"DROP DB {temp_db_name}")

        except Exception as e:
            self.logger.error("Error importing LIFT file: %s", str(e), exc_info=True)
            raise DatabaseError(f"Failed to import LIFT file: {e}") from e
    
    def export_lift(self) -> str:
        """
        Export all entries to LIFT format by dumping the database content.
        
        Returns:
            LIFT content as a string.
            
        Raises:
            ExportError: If there is an error exporting the data.
        """
        try:
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)
            
            query = f"xquery collection('{db_name}')"
            lift_xml = self.db_connector.execute_query(query)
            
            if not lift_xml:
                self.logger.warning("No LIFT document found in the database. Returning empty LIFT structure.")
                return self.lift_parser.generate_lift_string([])

            self.logger.info("Exported database content to LIFT format")
            return lift_xml
            
        except Exception as e:
            self.logger.error("Error exporting to LIFT format: %s", str(e), exc_info=True)
            raise ExportError(f"Failed to export to LIFT format: {e}") from e
    
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
            
            entries, _ = self.list_entries()
            
            exporter = KindleExporter(self)
            
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
            raise ExportError(f"Failed to export dictionary to Kindle format: {str(e)}") from e
    
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
            
            entries, _ = self.list_entries()
            
            exporter = SQLiteExporter(self)
            
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
            self.logger.error("Error exporting dictionary to SQLite format: %s", str(e), exc_info=True)
            raise ExportError(f"Failed to export dictionary to SQLite format: {str(e)}") from e

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
            self.get_entry(entry.id)
            self.update_entry(entry)
            return entry.id
        except NotFoundError:
            return self.create_entry(entry)
        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            self.logger.error("Error creating or updating entry %s: %s", entry.id, str(e))
            raise DatabaseError(f"Failed to create or update entry: {str(e)}") from e
    
    def export_to_lift(self, output_path: str) -> None:
        """
        Export all entries to a LIFT file.
        
        Args:
            output_path: Path to the output LIFT file.
            
        Raises:
            ExportError: If there is an error exporting the data.
        """
        try:
            lift_content = self.export_lift()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(lift_content)
            
            self.logger.info("LIFT file exported to %s", output_path)
            
        except Exception as e:
            self.logger.error("Error exporting LIFT file: %s", str(e))
            raise ExportError(f"Failed to export LIFT file: {str(e)}") from e

    def get_ranges(self) -> Dict[str, Any]:
        """
        Retrieves LIFT ranges data from the database.
        Caches the result for subsequent calls.
        """
        if self.ranges:
            return self.ranges

        try:
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            ranges_xml = self.db_connector.execute_query(f"xquery collection('{db_name}/ranges.xml')")

            if not ranges_xml:
                self.logger.warning("LIFT ranges not found in database.")
                self.ranges = {}  # Cache empty result
                return {}

            self.ranges = self.ranges_parser.parse_string(ranges_xml)
            return self.ranges
        except Exception as e:
            self.logger.error("Error retrieving ranges from database: %s", str(e), exc_info=True)
            self.ranges = {}  # Cache empty result on error
            return {}
