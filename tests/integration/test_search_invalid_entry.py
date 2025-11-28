#!/usr/bin/env python
"""
Test to verify that invalid entries appear in search results.
"""

import sys
from pathlib import Path

import pytest
from flask import Flask

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

# Set up Flask app context
from app.services.dictionary_service import DictionaryService

@pytest.mark.integration
def test_invalid_entry_in_search(app: Flask, dict_service_with_db: DictionaryService):
    """Test that invalid entries appear in search results."""
    
    with app.app_context():
        print("Testing search for invalid entry")
        print("=" * 50)
        
        # Get the dictionary service
        dict_service = dict_service_with_db
        
        # Search for the problematic entry
        entries, total = dict_service.search_entries("Scholastic Assessment Test", limit=10)
        
        print(f"Search results for 'Scholastic Assessment Test':")
        print(f"  Total found: {total}")
        print(f"  Entries returned: {len(entries)}")
        
        # Check if our problematic entry is in the results
        target_id = "Scholastic Assessment Test_25645cb1-c7de-4560-be73-9505d9e9c33f"
        found_entry = None
        
        for entry in entries:
            print(f"  - {entry.id}: {entry.lexical_unit}")
            if entry.id == target_id:
                found_entry = entry
                
        if found_entry:
            print(f"\n✓ SUCCESS: Invalid entry found in search results!")
            print(f"  Entry ID: {found_entry.id}")
            print(f"  This means invalid entries are visible and searchable.")
            return True
        else:
            print(f"\n✗ FAILED: Invalid entry not found in search results.")
            print(f"  This means invalid entries are being filtered out somewhere.")
            return False

if __name__ == "__main__":
    success = test_invalid_entry_in_search()
    sys.exit(0 if success else 1)
