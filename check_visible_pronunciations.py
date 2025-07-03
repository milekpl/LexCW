"""
Create a script to check for visible pronunciation fields in the Protestantism entry form.
"""

import requests
from bs4 import BeautifulSoup

def check_visible_pronunciations():
    """Check if the pronunciation fields are visible in the UI."""
    url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            print(f"Error: Got status code {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if the form has the expected structure
        form = soup.find('form', {'id': 'entry-form'})
        if not form:
            print("Entry form not found")
            return
        
        # Look for the pronunciation section
        pron_section = soup.find(lambda tag: tag.name == 'h5' and 'Pronunciation' in tag.text)
        if pron_section:
            print(f"Found pronunciation section: {pron_section}")
            
            # Look for the add pronunciation button
            add_btn = soup.find('button', {'id': 'add-pronunciation-btn'})
            if add_btn:
                print(f"Found add pronunciation button: {add_btn}")
            else:
                print("Add pronunciation button not found")
            
            # Check if any pronunciation items are visible
            pron_items = soup.find_all(class_='pronunciation-item')
            if pron_items:
                print(f"Found {len(pron_items)} pronunciation items")
                for i, item in enumerate(pron_items):
                    print(f"Item {i+1}: {item.prettify()[:200]}...")
                    
                    # Check the input field value
                    input_field = item.find('input', {'name': lambda x: x and 'pronunciations' in x and 'value' in x})
                    if input_field:
                        print(f"Input field value: '{input_field.get('value')}'")
                    else:
                        print("No pronunciation input field found in this item")
            else:
                print("No pronunciation items found in the HTML")
                
                # Check if there's a placeholder where they should be
                container = soup.find(id='pronunciation-container')
                if container:
                    print(f"Pronunciation container content: {container}")
                    
                    # Check if the container has any children
                    children = container.find_all()
                    if children:
                        print(f"Container has {len(children)} child elements")
                    else:
                        print("Container is empty")
        else:
            print("Pronunciation section not found")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_visible_pronunciations()
