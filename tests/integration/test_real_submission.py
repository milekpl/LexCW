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

@pytest.mark.integration
def test_real_form_submission():
    """Test form submission using Flask test client."""
    print("=== Testing Real Form Submission ===")
    
    app = create_app()
    
    with app.test_client() as client:
        # Test 1: POST with JSON data (as the frontend sends it)
        entry_data = {
            'lexical_unit': 'testword',
            'senses': [
                {
                    'definition': 'Test definition',
                    'gloss': 'Test gloss'
                }
            ],
            'morph_type': 'stem'
        }
        
        print(f"1. Testing JSON submission...")
        print(f"   Data: {json.dumps(entry_data, indent=2)}")
        
        response = client.post('/entries/add',
                             data=json.dumps(entry_data),
                             content_type='application/json')
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response data: {response.get_data(as_text=True)}")
        
        if response.status_code != 200:
            print(f"   Response headers: {dict(response.headers)}")
        
        # Test 2: POST with form data (as traditional form submission)
        print(f"\n2. Testing form data submission...")
        form_data = {
            'lexical_unit': 'testword2',
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
