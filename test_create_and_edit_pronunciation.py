#!/usr/bin/env python3
"""
Create a test entry with pronunciation data to test the edit form.
"""

import sys
sys.path.insert(0, '.')

import requests
import json

def create_test_entry_with_pronunciation():
    """Create a test entry with pronunciation data via the API."""
    
    base_url = "http://localhost:5000"
    
    try:
        # Create a test entry with pronunciation data
        entry_data = {
            "lexical_unit": "test_pronunciation_entry",
            "citation_form": "test_pronunciation_entry",
            "senses": [],
            "pronunciations": {
                "seh-fonipa": "test_ipa_pronunciation"
            }
        }
        
        # POST to create the entry
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{base_url}/entries/add", 
                               json=entry_data, 
                               headers=headers)
        
        if response.status_code in [200, 201, 302]:  # 302 is redirect after successful creation
            print("✓ Test entry created successfully")
            
            # If it's a redirect, follow it to get the new entry ID
            if response.status_code == 302:
                redirect_url = response.headers.get('Location', '')
                print(f"Redirected to: {redirect_url}")
                
                # Extract entry ID from redirect URL
                import re
                match = re.search(r'/entries/([^/]+)', redirect_url)
                if match:
                    entry_id = match.group(1)
                    print(f"Created entry ID: {entry_id}")
                    
                    # Now test the edit form
                    edit_url = f"{base_url}/entries/{entry_id}/edit"
                    edit_response = requests.get(edit_url)
                    
                    if edit_response.status_code == 200:
                        print("✓ Edit form accessible")
                        
                        html = edit_response.text
                        
                        # Check if pronunciation data is passed correctly
                        pattern = r'const pronunciations = ({[^}]*});'
                        match = re.search(pattern, html, re.DOTALL)
                        if match:
                            print(f"Pronunciation data in edit form: {match.group(1)}")
                            
                            # Save the HTML for inspection
                            with open('edit_entry_form_debug.html', 'w', encoding='utf-8') as f:
                                f.write(html)
                            print("Saved edit entry form HTML to edit_entry_form_debug.html")
                            
                            # Check if pronunciation fields are rendered
                            if 'pronunciation-item' in html:
                                print("✓ Pronunciation fields are rendered in edit form")
                            else:
                                print("✗ Pronunciation fields NOT rendered in edit form")
                            
                        else:
                            print("✗ No pronunciation data found in edit form")
                    else:
                        print(f"✗ Could not access edit form: {edit_response.status_code}")
            else:
                print(f"Unexpected response: {response.status_code}")
                print(response.text[:500])
        else:
            print(f"✗ Could not create test entry: {response.status_code}")
            print(response.text[:500])
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to the application. Make sure it's running on localhost:5000")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_test_entry_with_pronunciation()
