#!/usr/bin/env python3
"""
Quick test to verify that entries with senses are displayed correctly.
"""

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

def test_sense_display():
    """Test that senses are displayed correctly."""
    # BaseX connection parameters
    basex_host = 'localhost'
    basex_port = 1984
    basex_username = 'admin'
    basex_password = 'admin'
    basex_database = 'dictionary'
    
    # Create a BaseX connector
    connector = BaseXConnector(
        host=basex_host,
        port=basex_port,
        username=basex_username,
        password=basex_password,
        database=basex_database
    )
    
    try:
        # Connect to BaseX server
        connector.connect()
        service = DictionaryService(connector)
        
        # Get a few entries
        entries, total = service.list_entries(limit=3)
        
        print(f"Found {total} total entries, displaying first {len(entries)}:")
        print()
        
        for entry in entries:
            print(f"Entry ID: {entry.id}")
            print(f"Headword: {entry.headword}")
            print(f"Number of senses: {len(entry.senses)}")
            
            for i, sense in enumerate(entry.senses, 1):
                print(f"  Sense {i}:")
                print(f"    Type: {type(sense)}")
                
                if hasattr(sense, 'definition'):
                    print(f"    Definition: {sense.definition}")
                else:
                    print(f"    Definition: (no definition property)")
                    
                if hasattr(sense, 'gloss'):
                    print(f"    Gloss: {sense.gloss}")
                else:
                    print(f"    Gloss: (no gloss property)")
                    
                if hasattr(sense, 'definitions'):
                    print(f"    Definitions dict: {sense.definitions}")
                    
                if hasattr(sense, 'glosses'):
                    print(f"    Glosses dict: {sense.glosses}")
                    
                if hasattr(sense, 'examples'):
                    print(f"    Examples: {len(sense.examples) if sense.examples else 0}")
                
            print("-" * 50)
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if connector.is_connected():
            connector.disconnect()
    
    return True

if __name__ == "__main__":
    test_sense_display()
