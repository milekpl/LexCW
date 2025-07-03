"""
Capture the HTML of the Protestantism entry form and save it for examination.
"""

import requests

def capture_entry_form():
    """Capture the HTML of the Protestantism entry form."""
    url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            print(f"Error: Got status code {response.status_code}")
            return
        
        # Save the HTML to a file
        with open("protestantism_entry_form.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        print(f"HTML saved to protestantism_entry_form.html")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    capture_entry_form()
