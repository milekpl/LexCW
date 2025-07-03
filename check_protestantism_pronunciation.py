"""
Test script to check pronunciation extraction and display for the Protestantism entry.
"""

from app import create_app
from app.services.dictionary_service import DictionaryService
import requests
from bs4 import BeautifulSoup

def check_protestantism_entry():
    """Check if the Protestantism entry's pronunciation is correctly extracted and displayed."""
    app = create_app()
    
    with app.app_context():
        # Get the DictionaryService
        dict_service = app.injector.get(DictionaryService)
        
        # Try to get the Protestantism entry
        entry_id = "Protestantism_b97495fb-d52f-4755-94bf-a7a762339605"
        try:
            entry = dict_service.get_entry(entry_id)
            print(f"Entry found: {entry.id}")
            print(f"Lexical Unit: {entry.lexical_unit}")
            print(f"Pronunciations: {entry.pronunciations}")
            
            if not entry.pronunciations:
                print("WARNING: Entry has no pronunciations in the model!")
        except Exception as e:
            print(f"Error retrieving entry: {e}")
            return
        
        # Check the edit form
        url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                print(f"Error: Got status code {response.status_code}")
                return
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if there's a pronunciation section
            pron_container = soup.find(id='pronunciation-container')
            if not pron_container:
                print("Error: Pronunciation container not found")
            else:
                print("Found pronunciation container")
                
                # Look for any pronunciation input fields
                pron_fields = soup.find_all('input', {'name': lambda x: x and 'pronunciations' in x})
                if pron_fields:
                    for field in pron_fields:
                        print(f"Found pronunciation field: {field.get('name')}, value: {field.get('value')}")
                else:
                    print("No pronunciation input fields found")
            
            # Check for any pronunciation-related script content
            for script in soup.find_all('script'):
                script_text = script.string or ""
                if 'pronunciations.push(' in script_text:
                    print("Found pronunciations.push() in script")
                    if 'ˈprɒtɪstəntɪzm' in script_text:
                        print("Found the pronunciation value in the script")
                    else:
                        print("Pronunciation value not found in the script")
                    
                    # Try to extract the pronunciations array
                    import re
                    for line in script_text.split('\n'):
                        if 'const pronunciations = [];' in line:
                            print("Found empty pronunciations array initialization")
                            
                    # Look for any push operations
                    push_count = script_text.count('pronunciations.push(')
                    print(f"Found {push_count} push operations")
            
        except Exception as e:
            print(f"Error checking edit form: {e}")
            return

if __name__ == '__main__':
    check_protestantism_entry()
