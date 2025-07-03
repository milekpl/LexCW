"""
Check if Protestant1 entry's pronunciation is displayed in the edit form.

This script tries to load the entry form for the Protestant1 entry
and verifies if the pronunciation is properly displayed.
"""

import requests
import re
from bs4 import BeautifulSoup

def check_entry_form():
    """Check if the pronunciation is displayed in the entry form."""
    # The URL of the entry edit form
    url = "http://127.0.0.1:5000/entries/Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69/edit"
    
    try:
        # Make the request
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error: Got status code {response.status_code}")
            return
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if there's a pronunciation section
        pron_container = soup.find(id='pronunciation-container')
        if not pron_container:
            print("Error: Pronunciation container not found")
            return
        
        # Look for the pronunciation-forms.js script
        script_found = False
        for script in soup.find_all('script'):
            if 'pronunciation-forms.js' in str(script.get('src', '')):
                script_found = True
                break
        
        if not script_found:
            print("Error: pronunciation-forms.js script not found")
            return
        
        # Find the script that initializes the pronunciation manager
        init_script_found = False
        for script in soup.find_all('script'):
            script_text = script.string or ""
            if 'PronunciationFormsManager' in script_text:
                init_script_found = True
                
                # Check if the pronunciation value is in the script
                if 'ˈprɒtɪstənt' in script_text:
                    print("Success: Found the pronunciation value 'ˈprɒtɪstənt' in the script")
                else:
                    print("Error: Pronunciation value 'ˈprɒtɪstənt' not found in the script")
                
                # Check if there's a push operation for adding pronunciations
                if 'pronunciations.push(' in script_text:
                    print("Success: Found push operation for adding pronunciations")
                else:
                    print("Error: No push operation found for adding pronunciations")
                break
        
        if not init_script_found:
            print("Error: Script initializing PronunciationFormsManager not found")
            return
        
        print("Pronunciation check completed.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_entry_form()
