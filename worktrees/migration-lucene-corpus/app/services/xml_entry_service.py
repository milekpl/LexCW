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
from app.utils.xquery_builder import XQueryBuilder
from app.utils.namespace_manager import LIFTNamespaceManager

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
        database: str | None = None
    ) -> None:
        """
        Initialize XML Entry Service.
        
        Args:
            host: BaseX server hostname
            port: BaseX server port
            username: BaseX username
            password: BaseX password
            database: BaseX database name (if None, will use TEST_DB_NAME or BASEX_DATABASE env var)
        """
        import os

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        # Prefer explicit database, then Flask app config (if in app context), then TEST_DB_NAME (set by tests),
        # then BASEX_DATABASE env, then default
        db_from_flask = None
        try:
            from flask import has_app_context, current_app
            if has_app_context():
                db_from_flask = current_app.config.get('BASEX_DATABASE')
        except Exception:
            db_from_flask = None

        self.database = (
            database
            or db_from_flask
            or os.environ.get('TEST_DB_NAME')
            or os.environ.get('BASEX_DATABASE')
            or 'dictionary'
        )
        
        # Initialize namespace manager and query builder
        self._detect_namespace_usage()
        self._query_builder = XQueryBuilder()
        
        # Test connection on initialization
        self._test_connection()
    
    def _detect_namespace_usage(self) -> bool:
        """
        Detect if the database uses namespaces.
        
        Returns:
            True if namespaces are used, False otherwise
        """
        # Default to True until we check
        self._has_namespace = True
        
        try:
            session = self._get_session()
            
            # Check for namespace in root element
            query = """
            declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
            exists(collection('%s')/lift:lift)
            """ % self.database
            
            q = session.query(query)
            result = q.execute()
            q.close()
            session.close()
            
            self._has_namespace = (result.lower() == 'true')
            logger.info(f"Detected namespace usage for '{self.database}': {self._has_namespace}")
            return self._has_namespace
            
        except Exception as e:
            logger.warning(f"Failed to detect namespace usage: {e}")
            # Fallback to True as LIFT standard uses namespaces
            return True
    
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
        
        # Normalize XML based on detected namespace usage
        xml_clean = LIFTNamespaceManager.normalize_lift_xml(
            xml_string, 
            LIFTNamespaceManager.LIFT_NAMESPACE if self._has_namespace else None
        )
        
        # Add to database using XQuery insert
        session = self._get_session()
        try:
            logger.info(f"Creating entry {entry_id}")
            
            # Build XQuery insert statement using builder
            query = XQueryBuilder.build_insert_entry_query(
                xml_clean, self.database, self._has_namespace
            )
            
            logger.debug(f"Executing insert query for entry {entry_id}")
            logger.debug(f"Insert query:\n{query}")
            q = session.query(query)
            q.execute()
            q.close()
            
            # CRITICAL: Flush changes to ensure they're persisted before returning
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
            # Build query using builder
            query = XQueryBuilder.build_entry_by_id_query(
                entry_id, self.database, self._has_namespace
            )
            
            q = session.query(query)
            result = q.execute()
            q.close()
            
            # Check if entry was not found or returned an error
            if not result or result.strip() == '' or 'error' in result.lower() or 'not found' in result.lower():
                raise EntryNotFoundError(f"Entry '{entry_id}' not found")
            
            # Parse XML result
            # Use namespace manager to parse correctly regardless of namespace presence
            try:
                root = ET.fromstring(result)
            except ET.ParseError:
                # Defensive parsing: wrap the result in a single root element and find the first <entry>
                wrapped = f"<wrapper>{result}</wrapper>"
                try:
                    wrapper_root = ET.fromstring(wrapped)
                except ET.ParseError as wrap_exc:
                    # If wrapping didn't help, re-raise original parse error
                    raise

                # Try to find namespaced entry first, then non-namespaced
                entry_elem = wrapper_root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}entry')
                if entry_elem is None:
                    entry_elem = wrapper_root.find('.//entry')

                if entry_elem is None:
                    raise ET.ParseError("No <entry> element found in query result")

                # Use the first entry element as the root
                root = entry_elem
                # Also narrow the returned xml to the single entry string for consistency
                result = ET.tostring(root, encoding='unicode')
            
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
            
            # Get namespace URI for findall - try both with and without namespace
            ns = LIFTNamespaceManager.LIFT_NAMESPACE if self._has_namespace else ""
            ns_prefix = f"{{{ns}}}" if ns else ""
            
            # Extract lexical units - try both namespace and non-namespace forms
            lexical_units_found = False
            for lu in root.findall(f'.//{ns_prefix}lexical-unit'):
                forms = []
                for form in lu.findall(f'.//{ns_prefix}form'):
                    text_elem = form.find(f'.//{ns_prefix}text')
                    if text_elem is not None and text_elem.text:
                        forms.append({
                            'lang': form.attrib.get('lang'),
                            'text': text_elem.text
                        })
                entry_data['lexical_units'].append({'forms': forms})
                lexical_units_found = True
            
            # If no namespace lexical units found, try without namespace
            if not lexical_units_found:
                for lu in root.findall('.//lexical-unit'):
                    forms = []
                    for form in lu.findall('.//form'):
                        text_elem = form.find('.//text')
                        if text_elem is not None and text_elem.text:
                            forms.append({
                                'lang': form.attrib.get('lang'),
                                'text': text_elem.text
                            })
                    entry_data['lexical_units'].append({'forms': forms})
            
            # Extract senses - try both namespace and non-namespace forms
            senses_found = False
            for sense in root.findall(f'.//{ns_prefix}sense'):
                sense_data = {
                    'id': sense.attrib.get('id'),
                    'order': sense.attrib.get('order'),
                    'glosses': []
                }
                
                for gloss in sense.findall(f'.//{ns_prefix}gloss'):
                    text_elem = gloss.find(f'.//{ns_prefix}text')
                    if text_elem is not None and text_elem.text:
                        sense_data['glosses'].append({
                            'lang': gloss.attrib.get('lang'),
                            'text': text_elem.text
                        })
                
                entry_data['senses'].append(sense_data)
                senses_found = True
            
            # If no namespace senses found, try without namespace
            if not senses_found:
                for sense in root.findall('.//sense'):
                    sense_data = {
                        'id': sense.attrib.get('id'),
                        'order': sense.attrib.get('order'),
                        'glosses': []
                    }
                    
                    for gloss in sense.findall('.//gloss'):
                        text_elem = gloss.find('.//text')
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
        
        try:
            # Validate XML
            root = self._validate_lift_xml(xml_string)
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
            
            # Generate normalized XML with appropriate namespace
            xml_clean = LIFTNamespaceManager.normalize_lift_xml(
                xml_string,
                LIFTNamespaceManager.LIFT_NAMESPACE if self._has_namespace else None
            )
            
            session = self._get_session()
        except Exception as prep_error:
            logger.error(f"Error preparing XML for update: {prep_error}")
            raise
        try:
            # Use XQueryBuilder for update query
            # Ideally we would use replace node, but delete+insert is safer for complex structures
            
            # Before inserting, sanitize XML to remove empty/template senses
            try:
                root_elem = ET.fromstring(xml_clean)
                # remove empty <sense> elements: those with no child text or meaningful content
                removed = []
                # iterate parents to allow removal
                for parent in root_elem.iter():
                    for child in list(parent):
                        tag_local = child.tag.split('}')[-1]
                        if tag_local == 'sense':
                            # Determine if it has meaningful text content in any descendant
                            has_content = False
                            for desc in child.iter():
                                if desc is child:
                                    continue
                                text = (desc.text or '').strip()
                                if text:
                                    has_content = True
                                    break
                            if not has_content:
                                removed.append(child.attrib.get('id'))
                                parent.remove(child)
                if removed:
                    logger.info(f"Removed empty/template senses during XML update: {removed}")
                xml_clean = ET.tostring(root_elem, encoding='unicode')
                logger.info(f"[XML UPDATE] Final sanitized XML (truncated): {xml_clean[:500]}")
            except ET.ParseError as e:
                logger.warning(f"Failed to parse XML for sanitization: {e}")

            # Delete old entry
            delete_query = XQueryBuilder.build_delete_entry_query(
                entry_id, self.database, self._has_namespace
            )
            
            # Insert new entry
            insert_query = XQueryBuilder.build_insert_entry_query(
                xml_clean, self.database, self._has_namespace
            )
            
            # Execute as transaction-like (though BaseX doesn't support full ACID trans across multiple queries without script)
            # We'll execute them sequentially
            
            logger.debug(f"Deleting old entry {entry_id}")
            q_del = session.query(delete_query)
            q_del.execute()
            q_del.close()
            
            logger.debug(f"Inserting updated entry {entry_id}")
            q_ins = session.query(insert_query)
            q_ins.execute()
            q_ins.close()
            
            # CRITICAL: Flush changes
            try:
                session.execute("FLUSH")
                logger.debug(f"Flushed database changes for entry {entry_id}")
            except Exception as flush_error:
                logger.warning(f"Failed to flush database: {flush_error}")
            
            logger.info(f"Successfully updated entry: {entry_id}")
            
            return {
                'id': entry_id,
                'status': 'updated'
            }
            
        except Exception as e:
            logger.error(f"Failed to update entry {entry_id}: {e}")
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
            # Build query using builder
            query = XQueryBuilder.build_delete_entry_query(
                entry_id, self.database, self._has_namespace
            )
            
            q = session.query(query)
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
            # Build query using builder
            query = XQueryBuilder.build_entry_exists_query(
                entry_id, self.database, self._has_namespace
            )
            
            q = session.query(query)
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
            # Use XQueryBuilder to construct search query
            # Note: The builder returns a sequence of entries, we need to wrap them
            # to match the expected format
            
            if query_text:
                query = XQueryBuilder.build_search_query(
                    query_text, self.database, self._has_namespace, limit, offset
                )
            else:
                query = XQueryBuilder.build_all_entries_query(
                    self.database, self._has_namespace, limit, offset
                )
            
            # TODO: Improve XQueryBuilder to return total count as well
            # For now, we will execute the query and parse results
            
            q = session.query(query)
            result = q.execute()
            q.close()
            
            # Since result is a sequence of entry elements, we wrap them in a root element
            # to parse with ElementTree
            wrapped_result = f"<results>{result}</results>"
            
            try:
                root = ET.fromstring(wrapped_result)
                entries_elems = list(root)
            except ET.ParseError:
                entries_elems = []
            
            # Get total count - for test compatibility, use a simple count
            count_query = XQueryBuilder.build_count_entries_query(
                self.database, self._has_namespace, query_text if query_text else None
            )
            q_count = session.query(count_query)
            total_str = q_count.execute()
            q_count.close()
            total = int(total_str.strip()) if total_str.strip().isdigit() else 0
            
            # Process entries - try both namespace and non-namespace forms
            entries = []
            ns = LIFTNamespaceManager.LIFT_NAMESPACE if self._has_namespace else ""
            ns_prefix = f"{{{ns}}}" if ns else ""
            
            for entry_elem in entries_elems:
                entry_id = entry_elem.attrib.get('id')
                
                # Try to find text elements with namespace first
                texts = [
                    text.text
                    for text in entry_elem.findall(f'.//{ns_prefix}text')
                    if text.text
                ]
                
                # If no namespace texts found, try without namespace
                if not texts:
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
            # Build query using builder
            query = XQueryBuilder.build_statistics_query(self.database, self._has_namespace)
            
            q = session.query(query)
            result = q.execute()
            q.close()
            
            root = ET.fromstring(result)
            
            # Calculate average separately as it might not be in the XML if relying on custom builder query
            # (Though our builder includes it, safety check)
            entries_count = int(root.find('entries').text or 0)
            senses_count = int(root.find('senses').text or 0)
            avg_senses = senses_count / entries_count if entries_count > 0 else 0
            
            return {
                'entries': entries_count,
                'senses': senses_count,
                'avg_senses': avg_senses
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise XMLEntryServiceError(f"Failed to get database stats: {e}") from e
        finally:
            session.close()
