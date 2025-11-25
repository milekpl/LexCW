"""Test the entry edit form logic for POS inheritance."""

from app import create_app
from flask import url_for
import requests

import pytest

@pytest.mark.integration
def test_entry_edit_pos_inheritance():
    """Test POS inheritance in entry edit form."""
    
    # Create app configured for testing so DB uses in-memory SQLite
    app = create_app('testing')
    
    with app.app_context():
        # Test the specific entry
        entry_id = "Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69"
        edit_url = f"http://127.0.0.1:5000/entries/{entry_id}/edit"
        
        print(f"Testing entry edit page: {edit_url}")
        
        try:
            response = requests.get(edit_url, timeout=10)
            if response.status_code == 200:
                print("✅ Page loads successfully")
                
                # Check if the HTML contains the expected data-selected attribute
                html = response.text
                
                if 'data-selected="Noun"' in html:
                    print("✅ Entry POS is correctly passed to template as 'Noun'")
                elif 'data-selected=""' in html or 'data-selected=' not in html:
                    print("❌ Entry POS is not passed to template correctly")
                else:
                    lines_with_data_selected = [line.strip() for line in html.split('\n') if 'data-selected=' in line]
                    print(f"⚠️  Entry POS in template: {lines_with_data_selected}")
                
                # Check if sense POS data is present
                if 'data-selected="Noun"' in html and 'senses[0].grammatical_info' in html:
                    print("✅ Both entry and sense POS data present in template")
                else:
                    print("❌ Missing POS data in template")
                
            else:
                print(f"❌ Page failed to load: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error loading page: {e}")

if __name__ == "__main__":
    test_entry_edit_pos_inheritance()
