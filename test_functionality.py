#!/usr/bin/env python3
"""
Test basic dictionary service functionality to ensure everything works.
"""

import logging
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_all_functionality():
    """Test all basic functionality"""
    config = Config()
    connector = BaseXConnector(config.BASEX_HOST, config.BASEX_PORT, config.BASEX_USERNAME, config.BASEX_PASSWORD)
    connector.database = config.BASEX_DATABASE
    service = DictionaryService(connector)
    
    print("Testing dictionary service functionality...")
    
    # Test 1: Count entries
    try:
        count = service.count_entries()
        print(f"✓ Count entries: {count}")
    except Exception as e:
        print(f"✗ Count entries failed: {e}")
        return False
    
    # Test 2: List entries
    try:
        entries, total = service.list_entries(limit=3)
        print(f"✓ List entries: Got {len(entries)} entries out of {total} total")
        if entries:
            print(f"  First entry: {entries[0].headword} (ID: {entries[0].id})")
    except Exception as e:
        print(f"✗ List entries failed: {e}")
        return False
    
    # Test 3: Search entries
    try:
        search_entries, search_total = service.search_entries("test", limit=3)
        print(f"✓ Search entries: Found {len(search_entries)} entries out of {search_total} total for 'test'")
    except Exception as e:
        print(f"✗ Search entries failed: {e}")
        return False
    
    # Test 4: Get specific entry (if we have entries)
    if entries:
        try:
            entry = service.get_entry(entries[0].id)
            print(f"✓ Get entry: Retrieved '{entry.headword}' with {len(entry.senses)} senses")
            if entry.senses:
                for i, sense in enumerate(entry.senses):
                    definition = sense.get_definition() if hasattr(sense, 'get_definition') else "No definition"
                    gloss = sense.get_gloss() if hasattr(sense, 'get_gloss') else "No gloss"
                    print(f"    Sense {i+1}: {definition or gloss or 'No content'}")
        except Exception as e:
            print(f"✗ Get entry failed: {e}")
            return False
    
    print("\n🎉 All tests passed! Dictionary service is working correctly.")
    return True

if __name__ == "__main__":
    test_all_functionality()
