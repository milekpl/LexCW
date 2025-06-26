#!/usr/bin/env python3
"""
Test the API endpoints directly without Flask server.
"""

import logging
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from flask import Flask
from app import create_app
from app.api.entries import get_dictionary_service

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_api_endpoints():
    """Test API endpoints directly"""
    print("Testing API endpoints...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Test getting dictionary service
            dict_service = get_dictionary_service()
            print(f"✓ Dictionary service created successfully")
            
            # Test list entries
            entries, total = dict_service.list_entries(limit=2)
            print(f"✓ List entries: Got {len(entries)} entries out of {total} total")
            
            if entries:
                # Test converting to dict
                entry_dict = entries[0].to_dict()
                print(f"✓ Entry to_dict: {entry_dict.get('headword', 'No headword')} with {len(entry_dict.get('senses', []))} senses")
                
                # Test search entries  
                search_entries, search_total = dict_service.search_entries("test", limit=2)
                print(f"✓ Search entries: Found {len(search_entries)} entries out of {search_total} total")
                
                if search_entries:
                    search_dict = search_entries[0].to_dict()
                    print(f"✓ Search result to_dict: {search_dict.get('headword', 'No headword')}")
                
        except Exception as e:
            print(f"✗ API test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("🎉 API endpoints working correctly!")
    return True

if __name__ == "__main__":
    test_api_endpoints()
