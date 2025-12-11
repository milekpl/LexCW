"""
XML Entry Service

Provides high-level Python API for CRUD operations on LIFT XML entries in BaseX database.
Abstracts XQuery complexity behind clean Python methods.

This service:
- Creates, reads, updates, and deletes dictionary entries
- Validates LIFT XML against schema
- Manages sense operations
- Handles BaseX database interactions
- Provides error handling and logging
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

from BaseXClient import BaseXClient

# LIFT XML namespace
LIFT_NS = "http://fieldworks.sil.org/schemas/lift/0.13"
LIFT_NS_MAP = {"lift": LIFT_NS}

# Register namespace for ElementTree
ET.register_namespace("", LIFT_NS)

logger = logging.getLogger(__name__)


class XMLEntryServiceError(Exception):
    """Base exception for XML Entry Service errors."""
    pass


class EntryNotFoundError(XMLEntryServiceError):
    """Raised when entry is not found in database."""
    pass


class InvalidXMLError(XMLEntryServiceError):
    """Raised when XML is invalid or doesn't conform to LIFT schema."""
    pass


class DatabaseConnectionError(XMLEntryServiceError):
    """Raised when connection to BaseX database fails."""
    pass


class DuplicateEntryError(XMLEntryServiceError):
    """Raised when attempting to create an entry that already exists."""
    pass


class XMLEntryService:
    """
    Service for managing LIFT XML entries in BaseX database.
    
    Provides high-level CRUD operations, XML validation, and search functionality.
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 1984,
        username: str = 'admin',
        password: str = 'admin',
        database: str = 'dictionary'
    ) -> None:
        """
        Initialize XML Entry Service.
        
        Args:
            host: BaseX server hostname
            port: BaseX server port
            username: BaseX username
            password: BaseX password
            database: BaseX database name
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        
        # Test connection on initialization
        self._test_connection()
    
    def _get_session(self) -> BaseXClient.Session:
        """
        Get a new BaseX session.
        
        Returns:
            BaseX session object
            
        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            session = BaseXClient.Session(
                self.host,
                self.port,
                self.username,
                self.password
            )
            session.execute(f"OPEN {self.database}")
            return session
        except Exception as e:
            logger.error(f"Failed to connect to BaseX: {e}")
            raise DatabaseConnectionError(f"Cannot connect to BaseX database: {e}") from e
    
    def _test_connection(self) -> None:
        """Test database connection during initialization."""
        try:
            session = self._get_session()
            session.close()
            logger.info(f"Successfully connected to BaseX database '{self.database}'")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    def _validate_lift_xml(self, xml_string: str) -> ET.Element:
        """
        Validate LIFT XML string and parse to ElementTree.
        
        Args:
            xml_string: LIFT XML as string
            
        Returns:
            Parsed ElementTree Element
            
        Raises:
            InvalidXMLError: If XML is malformed or missing required elements
        """
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            raise InvalidXMLError(f"Malformed XML: {e}") from e
        
        # Check for entry element
        tag_name = root.tag
        if tag_name.endswith('entry'):
            # Valid - either with or without namespace
            pass
        else:
            raise InvalidXMLError(
                f"Root element must be <entry>, found <{tag_name}>"
            )
        
        # Check for required attributes
        if 'id' not in root.attrib:
            raise InvalidXMLError("Entry element must have 'id' attribute")
        
        # Check for at least one lexical-unit or sense
        has_lexical_unit = False
        has_sense = False
        
        for child in root:
            tag = child.tag.split('}')[-1]  # Remove namespace
            if tag == 'lexical-unit':
                has_lexical_unit = True
            elif tag == 'sense':
                has_sense = True
        
        if not has_lexical_unit and not has_sense:
            raise InvalidXMLError(
                "Entry must have at least one <lexical-unit> or <sense> element"
            )
        
        return root
    
    def _generate_filename(self, entry_id: str) -> str:
        """
        Generate unique filename for entry XML document.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            Filename for XML document
        """
        # Use entry ID with timestamp to ensure uniqueness
        timestamp = datetime.now().isoformat().replace(':', '_')
        return f"{entry_id}_{timestamp}.xml"
    
    def create_entry(self, xml_string: str) -> dict[str, Any]:
        """
        Create a new entry in the database.
        
        Args:
            xml_string: LIFT XML string for the entry
            
        Returns:
            Dictionary with entry ID and status
            
        Raises:
            InvalidXMLError: If XML is invalid
            DatabaseConnectionError: If database operation fails
        """
        # Validate XML
        root = self._validate_lift_xml(xml_string)
        entry_id = root.attrib['id']
        
        logger.info(f"Creating entry: {entry_id}")
        
        # Check if entry already exists
        if self.entry_exists(entry_id):
            raise DuplicateEntryError(f"Entry with ID '{entry_id}' already exists")
        
        # Generate filename
        filename = self._generate_filename(entry_id)
        
        # Strip XML declaration if present
        xml_clean = xml_string.strip()
        if xml_clean.startswith('<?xml'):
            # Remove XML declaration line
            xml_clean = '\n'.join(xml_clean.split('\n')[1:]).strip()
        
        # Remove xmlns declaration from entry element - namespace is declared in XQuery prologue
        import re
        xml_clean = re.sub(r'<entry\s+xmlns="[^"]*"\s+', '<entry ', xml_clean, count=1)
        
        # Add to database using XQuery insert (same approach as DictionaryService)
        # This inserts the entry as a child node of the <lift> root element
        session = self._get_session()
        try:
            logger.info(f"Creating entry {entry_id}")
            
            # Build XQuery insert statement
            # NOTE: Query without namespace prefix since root stored as 'lift' not 'lift:lift'
            # The entry XML is embedded directly in the query
            query = f"""
            insert node {xml_clean} into collection('{self.database}')//lift
            """
            
            logger.debug(f"Executing insert query for entry {entry_id}")
            q = session.query(query)
            q.execute()
            q.close()
            
            # CRITICAL: Flush changes to ensure they're persisted before returning
            # This makes the changes visible to other sessions immediately
            try:
                session.execute("FLUSH")
                logger.debug(f"Flushed database changes for entry {entry_id}")
            except Exception as flush_error:
                logger.warning(f"Failed to flush database after create: {flush_error}")
            
            logger.info(f"Successfully created entry: {entry_id}")
            
            return {
                'id': entry_id,
                'status': 'created',
                'filename': filename
            }
            
        except Exception as e:
            logger.error(f"Failed to create entry {entry_id}: {e}", exc_info=True)
            raise XMLEntryServiceError(f"Failed to create entry: {e}") from e
        finally:
            session.close()
    
    def get_entry(self, entry_id: str) -> dict[str, Any]:
        """
        Retrieve an entry from the database.
        
        Args:
            entry_id: Entry ID to retrieve
            
        Returns:
            Dictionary containing entry data
            
        Raises:
            EntryNotFoundError: If entry doesn't exist
            DatabaseConnectionError: If database operation fails
        """
        logger.info(f"Retrieving entry: {entry_id}")
        
        session = self._get_session()
        try:
            # Use variable binding to avoid injection and escaping issues
            # NOTE: Entries in BaseX are stored WITHOUT namespace prefix (just 'entry', not 'lift:entry')
            # even though they have xmlns attribute. This is because xmlns is stripped during insert.
            query = f"""
            declare variable $entryId external;
            
            let $entry := collection("{self.database}")//entry[@id=$entryId]
            return if ($entry) then
                $entry
            else
                <error>Entry not found</error>
            """
            
            q = session.query(query)
            q.bind('entryId', entry_id)
            result = q.execute()
            q.close()
            
            if '<error>' in result:
                raise EntryNotFoundError(f"Entry '{entry_id}' not found")
            
            # NOTE: Do NOT add xmlns here - entries in database don't have explicit xmlns
            # (they inherit it from document context). Adding xmlns causes issues with
            # replace node operations. The XML parser can handle both cases.
            
            # Parse XML result
            root = ET.fromstring(result)
            
            # Extract basic information
            entry_data = {
                'id': root.attrib.get('id'),
                'guid': root.attrib.get('guid'),
                'dateCreated': root.attrib.get('dateCreated'),
                'dateModified': root.attrib.get('dateModified'),
                'xml': result,
                'lexical_units': [],
                'senses': []
            }
            
            # Extract lexical units
            for lu in root.findall('.//{%s}lexical-unit' % LIFT_NS):
                forms = []
                for form in lu.findall('.//{%s}form' % LIFT_NS):
                    text_elem = form.find('.//{%s}text' % LIFT_NS)
                    if text_elem is not None and text_elem.text:
                        forms.append({
                            'lang': form.attrib.get('lang'),
                            'text': text_elem.text
                        })
                entry_data['lexical_units'].append({'forms': forms})
            
            # Extract senses
            for sense in root.findall('.//{%s}sense' % LIFT_NS):
                sense_data = {
                    'id': sense.attrib.get('id'),
                    'order': sense.attrib.get('order'),
                    'glosses': []
                }
                
                for gloss in sense.findall('.//{%s}gloss' % LIFT_NS):
                    text_elem = gloss.find('.//{%s}text' % LIFT_NS)
                    if text_elem is not None and text_elem.text:
                        sense_data['glosses'].append({
                            'lang': gloss.attrib.get('lang'),
                            'text': text_elem.text
                        })
                
                entry_data['senses'].append(sense_data)
            
            logger.info(f"Successfully retrieved entry: {entry_id}")
            return entry_data
            
        except EntryNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve entry {entry_id}: {e}")
            raise XMLEntryServiceError(f"Failed to retrieve entry: {e}") from e
        finally:
            session.close()
    
    def update_entry(self, entry_id: str, xml_string: str) -> dict[str, Any]:
        """
        Update an existing entry.
        
        Uses delete + add approach for simplicity and reliability.
        
        Args:
            entry_id: Entry ID to update
            xml_string: New LIFT XML string
            
        Returns:
            Dictionary with entry ID and status
            
        Raises:
            EntryNotFoundError: If entry doesn't exist
            InvalidXMLError: If XML is invalid
            DatabaseConnectionError: If database operation fails
        """
        print(f"[DEBUG] update_entry called for {entry_id}")
        
        with open('/tmp/sense_deletion_debug.log', 'a') as f:
            f.write(f"\nValidating XML and checking senses...\n")
        
        try:
            # Validate XML
            root = self._validate_lift_xml(xml_string)
            xml_entry_id = root.attrib['id']
            
            # Count senses in the ACTUAL XML received
            import xml.etree.ElementTree as ET
            sense_elements = root.findall('.//{http://fieldworks.sil.org/schemas/lift/0.13}sense') or root.findall('.//sense')
            actual_sense_count_in_xml = len(sense_elements)
            with open('/tmp/sense_deletion_debug.log', 'a') as f:
                f.write(f"Actual XML has {actual_sense_count_in_xml} <sense> elements (by parsing)\n")
            xml_entry_id = root.attrib['id']
            
            # Ensure IDs match
            if entry_id != xml_entry_id:
                raise InvalidXMLError(
                    f"Entry ID mismatch: URL has '{entry_id}', XML has '{xml_entry_id}'"
                )
            
            logger.info(f"Updating entry: {entry_id}")
            
            # Check if entry exists
            if not self.entry_exists(entry_id):
                raise EntryNotFoundError(f"Entry '{entry_id}' not found")
            
            # Strip XML declaration if present
            xml_clean = xml_string.strip()
            if xml_clean.startswith('<?xml'):
                xml_clean = '\n'.join(xml_clean.split('\n')[1:]).strip()
            
            # Debug logging
            logger.info(f"[XML UPDATE] Entry {entry_id}: XML length {len(xml_clean)}")
            
            # Count senses in the incoming XML
            import re
            sense_count = len(re.findall(r'<sense\s+', xml_clean))
            logger.info(f"[XML UPDATE] Incoming XML has {sense_count} senses")
            
            logger.info(f"[XML UPDATE] Has <relation> tags: {'<relation' in xml_clean}")
            if '<relation' in xml_clean:
                relations = re.findall(r'<relation[^>]*>', xml_clean)
                logger.info(f"[XML UPDATE] Found {len(relations)} relation(s): {relations[:3]}")
            logger.debug(f"Update XML for {entry_id} (first 500 chars): {xml_clean[:500]}")
            logger.debug(f"Update XML length: {len(xml_clean)}")
            
            # CRITICAL: Strip xmlns from root element
            # Entries in database don't have explicit xmlns (inherited from document context)
            # If we try to replace a non-namespaced node with a namespaced one, BaseX deletes it!
            # Must remove xmlns before parse-xml() to match database structure
            import re
            xml_clean = re.sub(r'<entry\s+xmlns="[^"]*"\s+', '<entry ', xml_clean, count=1)
            logger.debug(f"After xmlns removal: {xml_clean[:200]}")
            
            session = self._get_session()
        except Exception as prep_error:
            logger.error(f"Error preparing XML for update: {prep_error}")
            raise
        try:
            # Use DELETE + INSERT in a single query for atomicity and reliability
            # CRITICAL: Must use namespace declarations to match namespaced elements
            combined_query = f"""
            declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
            declare variable $entryId external;
            (
                for $entry in collection("{self.database}")//lift:entry[@id=$entryId]
                return delete node $entry,
                insert node {xml_clean} into collection('{self.database}')//lift:lift
            )
            """
            
            q = session.query(combined_query)
            q.bind('entryId', entry_id)
            
            try:
                result = q.execute()
                logger.debug(f"Combined DELETE+INSERT executed for entry {entry_id}")
            except Exception as e:
                logger.error(f"Combined query failed for entry {entry_id}: {e}")
                raise
            finally:
                q.close()
            
            # Verify the entry was updated correctly
            verify_query = f"""
            declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
            declare variable $entryId external;
            collection("{self.database}")//lift:entry[@id=$entryId]
            """
            q_verify = session.query(verify_query)
            q_verify.bind('entryId', entry_id)
            saved_xml = q_verify.execute()
            q_verify.close()
            
            # Count senses in the saved XML
            saved_sense_count = len(re.findall(r'<sense\s+', saved_xml))
            logger.info(f"[XML UPDATE] Saved XML has {saved_sense_count} senses (was {sense_count} in incoming)")
            
            # CRITICAL: Flush changes to ensure they're persisted before returning
            try:
                session.execute("FLUSH")
                logger.debug(f"Flushed database changes for entry {entry_id}")
            except Exception as flush_error:
                logger.warning(f"Failed to flush database: {flush_error}")
            
            # Verify entry exists after update
            check_query = f"""
            declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
            declare variable $entryId external;
            count(collection("{self.database}")//lift:entry[@id=$entryId])
            """
            q_check2 = session.query(check_query)
            q_check2.bind('entryId', entry_id)
            count_after = q_check2.execute()
            q_check2.close()
            logger.debug(f"Entry count after update: {count_after}")
            
            if count_after == "0":
                logger.error(f"CRITICAL: Entry {entry_id} was DELETED during update!")
                raise XMLEntryServiceError("Entry was deleted during update operation")
            
            logger.info(f"Successfully updated entry: {entry_id}")
            
            return {
                'id': entry_id,
                'status': 'updated'
            }
            
        except Exception as e:
            logger.error(f"Failed to update entry {entry_id}: {e}")
            with open('/tmp/sense_deletion_debug.log', 'a') as f:
                f.write(f"UPDATE FAILED with exception: {e}\n")
            raise XMLEntryServiceError(f"Failed to update entry: {e}") from e
        finally:
            session.close()
    
    def delete_entry(self, entry_id: str) -> dict[str, Any]:
        """
        Delete an entry from the database.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            Dictionary with entry ID and status
            
        Raises:
            EntryNotFoundError: If entry doesn't exist
            DatabaseConnectionError: If database operation fails
        """
        logger.info(f"Deleting entry: {entry_id}")
        
        # Check if entry exists
        if not self.entry_exists(entry_id):
            raise EntryNotFoundError(f"Entry '{entry_id}' not found")
        
        session = self._get_session()
        try:
            # Use variable binding to avoid injection and escaping issues
            # NOTE: Query without namespace prefix
            query = f"""
            declare variable $entryId external;
            
            for $entry in collection("{self.database}")//entry[@id=$entryId]
            return delete node $entry
            """
            
            q = session.query(query)
            q.bind('entryId', entry_id)
            q.execute()
            q.close()
            
            logger.info(f"Successfully deleted entry: {entry_id}")
            
            return {
                'id': entry_id,
                'status': 'deleted'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete entry {entry_id}: {e}")
            raise XMLEntryServiceError(f"Failed to delete entry: {e}") from e
        finally:
            session.close()
    
    def entry_exists(self, entry_id: str) -> bool:
        """
        Check if an entry exists in the database.
        
        Args:
            entry_id: Entry ID to check
            
        Returns:
            True if entry exists, False otherwise
        """
        session = self._get_session()
        try:
            # CRITICAL: Use namespace declaration to match namespaced elements
            # The lift element has xmlns="http://fieldworks.sil.org/schemas/lift/0.13"
            query = f"""
            declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
            declare variable $entryId external;
            
            exists(collection("{self.database}")//lift:entry[@id=$entryId])
            """
            
            q = session.query(query)
            q.bind('entryId', entry_id)
            result = q.execute()
            q.close()
            
            logger.debug(f"entry_exists check for '{entry_id}': result='{result}'")
            
            return result.strip().lower() == 'true'
            
        except Exception as e:
            logger.error(f"Failed to check entry existence {entry_id}: {e}", exc_info=True)
            return False
        finally:
            session.close()
    
    def search_entries(
        self,
        query_text: str = '',
        limit: int = 50,
        offset: int = 0
    ) -> dict[str, Any]:
        """
        Search for entries by lexical unit text.
        
        Args:
            query_text: Text to search for in lexical units
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            
        Returns:
            Dictionary with search results and metadata
        """
        logger.info(f"Searching entries: query='{query_text}', limit={limit}, offset={offset}")
        
        session = self._get_session()
        try:
            if query_text:
                # Search with filter
                query = f"""
                declare namespace lift = "{LIFT_NS}";
                
                let $entries := //lift:entry[
                    .//lift:lexical-unit//lift:text[contains(lower-case(.), lower-case('{query_text}'))]
                ]
                let $total := count($entries)
                let $results := subsequence($entries, {offset + 1}, {limit})
                
                return <search-results total="{{$total}}" limit="{limit}" offset="{offset}">
                {{
                    for $entry in $results
                    return <entry id="{{$entry/@id/string()}}">
                        <lexical-unit>
                        {{
                            for $lu in $entry//lift:lexical-unit//lift:text
                            return <text>{{$lu/string()}}</text>
                        }}
                        </lexical-unit>
                    </entry>
                }}
                </search-results>
                """
            else:
                # Get all entries
                query = f"""
                declare namespace lift = "{LIFT_NS}";
                
                let $entries := //lift:entry
                let $total := count($entries)
                let $results := subsequence($entries, {offset + 1}, {limit})
                
                return <search-results total="{{$total}}" limit="{limit}" offset="{offset}">
                {{
                    for $entry in $results
                    return <entry id="{{$entry/@id/string()}}">
                        <lexical-unit>
                        {{
                            for $lu in $entry//lift:lexical-unit//lift:text
                            return <text>{{$lu/string()}}</text>
                        }}
                        </lexical-unit>
                    </entry>
                }}
                </search-results>
                """
            
            q = session.query(query)
            result = q.execute()
            q.close()
            
            # Parse results
            root = ET.fromstring(result)
            total = int(root.attrib.get('total', 0))
            
            entries = []
            for entry_elem in root.findall('entry'):
                entry_id = entry_elem.attrib.get('id')
                texts = [
                    text.text
                    for text in entry_elem.findall('.//text')
                    if text.text
                ]
                
                entries.append({
                    'id': entry_id,
                    'lexical_units': texts
                })
            
            logger.info(f"Search returned {len(entries)} of {total} results")
            
            return {
                'entries': entries,
                'total': total,
                'limit': limit,
                'offset': offset,
                'count': len(entries)
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise XMLEntryServiceError(f"Search failed: {e}") from e
        finally:
            session.close()
    
    def get_database_stats(self) -> dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with entry and sense counts
        """
        session = self._get_session()
        try:
            query = f"""
            declare namespace lift = "{LIFT_NS}";
            
            let $entries := //lift:entry
            let $senses := //lift:sense
            
            return <stats>
                <entries>{{count($entries)}}</entries>
                <senses>{{count($senses)}}</senses>
                <avgSenses>{{
                    if (count($entries) > 0) then
                        count($senses) div count($entries)
                    else
                        0
                }}</avgSenses>
            </stats>
            """
            
            q = session.query(query)
            result = q.execute()
            q.close()
            
            root = ET.fromstring(result)
            
            return {
                'entries': int(root.find('entries').text or 0),
                'senses': int(root.find('senses').text or 0),
                'avg_senses': float(root.find('avgSenses').text or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise XMLEntryServiceError(f"Failed to get database stats: {e}") from e
        finally:
            session.close()
