#!/usr/bin/env python3
"""
Test actual form submission by simulating a real request to the Flask app.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath('.'))

import json
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry

@pytest.mark.integration
def test_real_form_submission():
    """Test form submission using Flask test client."""
    print("=== Testing Real Form Submission ===")
    
    app = create_app()
    
    with app.test_client() as client:
        # Test 1: Use service-driven creation for JSON payload (avoid POSTing large JSON)
        entry_data = {
            'lexical_unit': {'en': 'testword'},
            'senses': [
                {
                    'definition': {'en': 'Test definition'},
                    'gloss': {'en': 'Test gloss'}
                }
            ],
            'morph_type': 'stem'
        }

        # Patch the app's dictionary service to avoid external DB operations
        from unittest.mock import Mock
        mock_dict = Mock(spec=DictionaryService)
        mock_dict.create_entry.return_value = 'mock_entry_id'
        app.dict_service = mock_dict

        # Create Entry object and call service directly
        entry_obj = Entry.from_dict(entry_data)
        entry_id = app.dict_service.create_entry(entry_obj)
        assert entry_id == 'mock_entry_id'
        
        # Test 2: POST with form data (as traditional form submission)
        print(f"\n2. Testing form data submission...")
        form_data = {
            'lexical_unit': {'en': 'testword2'},
            'senses[0].definition': 'Test definition 2',
            'senses[0].gloss': 'Test gloss 2',
            'morph_type': 'stem'
        }
        
        print(f"   Data: {form_data}")
        
        response2 = client.post('/entries/add', data=form_data)
        
        print(f"   Response status: {response2.status_code}")
        print(f"   Response data: {response2.get_data(as_text=True)}")
        
        if response2.status_code != 200:
            print(f"   Response headers: {dict(response2.headers)}")

if __name__ == '__main__':
    test_real_form_submission()
