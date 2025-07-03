#!/usr/bin/env python3
"""
Generate the HTML for the AIDS test entry and save it to file.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dictionary_service import DictionaryService
from flask import current_app

def main():
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Get the entry form HTML for AIDS test
            response = client.get('/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit')
            
            if response.status_code == 200:
                html_content = response.get_data(as_text=True)
                
                # Write to file
                with open('aids_test_entry_form.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"HTML written to aids_test_entry_form.html (length: {len(html_content)} chars)")
                
                # Check key sections
                if 'pronunciation-container' in html_content:
                    print("✅ Pronunciation container found")
                else:
                    print("❌ Pronunciation container NOT found")
                
                if 'PronunciationFormsManager' in html_content:
                    print("✅ PronunciationFormsManager found")
                else:
                    print("❌ PronunciationFormsManager NOT found")
                
                # Look for the pronunciation data
                if 'seh-fonipa' in html_content:
                    print("✅ Language code found")
                else:
                    print("❌ Language code NOT found")
                    
                # Look for Unicode characters that might indicate IPA
                if '\\u026a' in html_content or 'u026a' in html_content:
                    print("✅ IPA Unicode characters found")
                else:
                    print("❌ IPA Unicode characters NOT found")
                    
            else:
                print(f"Error: HTTP {response.status_code}")

if __name__ == "__main__":
    main()
