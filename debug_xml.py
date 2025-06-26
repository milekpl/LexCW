#!/usr/bin/env python3
"""
Debug the XML structure returned by BaseX queries.
"""

import logging
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_xml_structure():
    """Debug what XML structure is being returned"""
    config = Config()
    connector = BaseXConnector(config.BASEX_HOST, config.BASEX_PORT, config.BASEX_USERNAME, config.BASEX_PASSWORD)
    connector.database = config.BASEX_DATABASE
    service = DictionaryService(connector)
    
    print("Testing XML structure returned by queries...")
    
    # Test 1: What does a simple list query return?
    try:
        db_name = connector.database
        query = f"xquery (for $entry in collection('{db_name}')//*:entry order by $entry/lexical-unit/form/text return $entry)[position() = 1 to 2]"
        result = connector.execute_query(query)
        print(f"✓ Raw XML from list query (first 500 chars):\n{result[:500]}...")
        print(f"✓ Full length: {len(result)} characters")
    except Exception as e:
        print(f"✗ List query failed: {e}")
        return False
    
    # Test 2: What does a search query return?
    try:
        search_condition = "contains(lower-case(string-join($entry/lexical-unit/form/text, '')), 'test')"
        query_str = f"xquery (for $entry in collection('{db_name}')//*:entry where {search_condition} order by $entry/lexical-unit/form/text return $entry)[position() = 1 to 2]"
        result = connector.execute_query(query_str)
        print(f"✓ Raw XML from search query (first 500 chars):\n{result[:500]}...")
        print(f"✓ Full length: {len(result)} characters")
    except Exception as e:
        print(f"✗ Search query failed: {e}")
        return False
    
    # Test 3: Try to parse the XML with LIFT parser
    try:
        from app.parsers.lift_parser import LIFTParser
        parser = LIFTParser()
        
        # Try with the search result
        wrapped_xml = f"<lift>{result}</lift>"
        print(f"✓ Wrapped XML (first 500 chars):\n{wrapped_xml[:500]}...")
        
        entries = parser.parse_string(wrapped_xml)
        print(f"✓ LIFT parser successfully parsed {len(entries)} entries")
        
        if entries:
            entry = entries[0]
            print(f"✓ First entry: {entry.headword} (ID: {entry.id})")
            print(f"✓ Senses: {len(entry.senses)}")
            if entry.senses:
                sense = entry.senses[0]
                print(f"✓ First sense type: {type(sense)}")
                if hasattr(sense, 'get_definition'):
                    print(f"✓ Definition: {sense.get_definition()}")
                if hasattr(sense, 'get_gloss'):
                    print(f"✓ Gloss: {sense.get_gloss()}")
    except Exception as e:
        print(f"✗ LIFT parser failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 XML structure debugging complete!")
    return True

if __name__ == "__main__":
    debug_xml_structure()
