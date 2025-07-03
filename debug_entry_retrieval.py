"""Script to debug entry retrieval issues.

This script will attempt to retrieve the problematic entry directly from the
BaseX database and help identify issues with the query or XML parsing.
"""

import os
import sys
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
from app.utils.exceptions import DatabaseError, NotFoundError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Entry ID to test
TEST_ENTRY_ID = "Protestantism_b97495fb-d52f-4755-94bf-a7a762339605"

def pretty_print_xml(xml_string):
    """Format XML string for better readability."""
    try:
        parsed = minidom.parseString(xml_string)
        return parsed.toprettyxml(indent="  ")
    except Exception as e:
        logger.error(f"Error formatting XML: {e}")
        return xml_string

def debug_entry_retrieval():
    """Debug the entry retrieval process."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get dictionary service
            dict_service = app.injector.get(DictionaryService)
            
            # Get database connector
            db_connector = dict_service.db_connector
            
            # First, test if the database is accessible
            logger.info("Testing database connection...")
            db_name = db_connector.database
            logger.info(f"Using database: {db_name}")
            
            # Check if the entry exists
            logger.info(f"Checking if entry {TEST_ENTRY_ID} exists...")
            has_ns = dict_service._detect_namespace_usage()
            
            # Get the raw query
            query_builder = dict_service._query_builder
            query = query_builder.build_entry_by_id_query(TEST_ENTRY_ID, db_name, has_ns)
            logger.info(f"Query: {query}")
            
            # Execute the query
            try:
                logger.info("Executing query...")
                xml_result = db_connector.execute_query(query)
                
                if not xml_result:
                    logger.error(f"Entry {TEST_ENTRY_ID} not found in the database")
                    return
                
                # Try to parse the XML
                logger.info("Parsing XML...")
                logger.info(f"Raw XML length: {len(xml_result)}")
                logger.info(f"Raw XML sample: {xml_result[:500]}...")
                
                # Try to pretty print
                pretty_xml = pretty_print_xml(xml_result)
                logger.info(f"Formatted XML sample: {pretty_xml[:500]}...")
                
                # Save XML to a file for inspection
                with open("debug_entry.xml", "w", encoding="utf-8") as f:
                    f.write(pretty_xml)
                logger.info("Saved XML to debug_entry.xml")
                
                # Try to parse with ElementTree
                try:
                    root = ET.fromstring(xml_result)
                    logger.info(f"XML parsed successfully. Root tag: {root.tag}")
                    
                    # Check for entry elements
                    entry_elems = []
                    
                        # Check if root is an entry
                    if root.tag.endswith('entry'):
                        entry_elems.append(root)
                        logger.info("Root element is an entry")
                    else:
                        # Try namespace-aware first
                        nsmap = {
                            'lift': 'http://fieldworks.sil.org/schemas/lift/0.13',
                            'flex': 'http://fieldworks.sil.org/schemas/flex/0.1'
                        }
                        entry_elems = root.findall('.//lift:entry', nsmap)
                        if entry_elems:
                            logger.info(f"Found {len(entry_elems)} entry elements with namespace")
                        else:
                            # Try without namespace
                            entry_elems = root.findall('.//entry')
                            if entry_elems:
                                logger.info(f"Found {len(entry_elems)} entry elements without namespace")
                            else:
                                logger.error("No entry elements found in the XML")
                    
                    # If we found entries, examine them
                    for i, entry_elem in enumerate(entry_elems):
                        logger.info(f"Entry {i+1}:")
                        logger.info(f"  ID: {entry_elem.get('id')}")
                        logger.info(f"  Tag: {entry_elem.tag}")
                        logger.info(f"  Attributes: {entry_elem.attrib}")
                        
                        # Check for lexical-unit
                        nsmap = {
                            'lift': 'http://fieldworks.sil.org/schemas/lift/0.13',
                            'flex': 'http://fieldworks.sil.org/schemas/flex/0.1'
                        }
                        lex_units = entry_elem.findall('.//lexical-unit') or entry_elem.findall('.//lift:lexical-unit', nsmap)
                        if lex_units:
                            logger.info(f"  Found {len(lex_units)} lexical-unit elements")
                            for lex_unit in lex_units:
                                forms = lex_unit.findall('.//form') or lex_unit.findall('.//lift:form', nsmap)
                                for form in forms:
                                    text_elem = form.find('.//text') or form.find('.//lift:text', nsmap)
                                    if text_elem is not None and text_elem.text:
                                        logger.info(f"  Lexical unit: {text_elem.text} (lang: {form.get('lang')})")
                        else:
                            logger.warning("  No lexical-unit found")
                            
                        # Check for pronunciations
                        prons = entry_elem.findall('.//pronunciation') or entry_elem.findall('.//lift:pronunciation', nsmap)
                        if prons:
                            logger.info(f"  Found {len(prons)} pronunciation elements")
                            for pron in prons:
                                forms = pron.findall('.//form') or pron.findall('.//lift:form', nsmap)
                                for form in forms:
                                    text_elem = form.find('.//text') or form.find('.//lift:text', nsmap)
                                    if text_elem is not None and text_elem.text:
                                        logger.info(f"  Pronunciation: {text_elem.text} (lang: {form.get('lang')})")
                        else:
                            logger.warning("  No pronunciations found")
                    
                except ET.ParseError as e:
                    logger.error(f"XML parse error: {e}")
                
                # Now try to get the entry through the dictionary service
                try:
                    logger.info("\nTrying to get the entry through the dictionary service...")
                    entry = dict_service.get_entry(TEST_ENTRY_ID)
                    logger.info(f"Entry retrieved successfully: ID = {entry.id}")
                    logger.info(f"Entry lexical unit: {entry.lexical_unit}")
                    logger.info(f"Entry pronunciations: {entry.pronunciations}")
                    
                    # Try to serialize and deserialize the entry
                    entry_dict = entry.to_dict()
                    logger.info(f"Entry serialized to dict successfully")
                    
                    # Check pronunciation serialization
                    if 'pronunciations' in entry_dict:
                        logger.info(f"Pronunciations in dict: {entry_dict['pronunciations']}")
                    else:
                        logger.warning("No pronunciations in serialized dict")
                    
                    # Now try to generate LIFT XML
                    entry_xml = dict_service.lift_parser.generate_entry_xml(entry)
                    logger.info(f"Entry XML generated successfully")
                    logger.info(f"Generated XML sample: {entry_xml[:500]}...")
                    
                    # Save generated XML to a file
                    with open("debug_generated_entry.xml", "w", encoding="utf-8") as f:
                        f.write(entry_xml)
                    logger.info("Saved generated XML to debug_generated_entry.xml")
                    
                except NotFoundError as e:
                    logger.error(f"Entry not found: {e}")
                except Exception as e:
                    logger.error(f"Error getting entry via service: {e}")
            
            except Exception as e:
                logger.error(f"Error executing query: {e}")
        
        except Exception as e:
            logger.error(f"General error: {e}")

if __name__ == "__main__":
    debug_entry_retrieval()
