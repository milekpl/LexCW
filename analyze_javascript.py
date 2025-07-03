"""
Check the JavaScript in the Protestantism entry form.
"""

import re
from bs4 import BeautifulSoup

def analyze_javascript():
    """Analyze the JavaScript in the entry form."""
    try:
        with open("protestantism_entry_form.html", "r", encoding="utf-8") as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all script tags
        scripts = soup.find_all('script')
        for i, script in enumerate(scripts):
            script_text = script.string
            if script_text and 'PronunciationFormsManager' in script_text:
                print(f"Script {i} initializes PronunciationFormsManager:")
                
                # Extract and print the relevant part of the script
                lines = script_text.split('\n')
                start_index = next((i for i, line in enumerate(lines) if 'PronunciationFormsManager' in line), -1)
                if start_index >= 0:
                    # Go back to find the beginning of the block
                    block_start = max(0, start_index - 10)
                    block_end = min(len(lines), start_index + 15)
                    print("Script block:")
                    for j in range(block_start, block_end):
                        print(f"{j-block_start:2d}: {lines[j].strip()}")
                
                # Try to extract the pronunciation data
                match = re.search(r'const pronunciations = \[(.*?)\];', script_text, re.DOTALL)
                if match:
                    print("\nPronunciations array initialization:")
                    print(match.group(0))
                
                # Look for any push operations
                push_matches = re.findall(r'pronunciations\.push\((.*?)\);', script_text, re.DOTALL)
                if push_matches:
                    print("\nPronunciation push operations:")
                    for push in push_matches:
                        print(f"push({push})")
                
    except Exception as e:
        print(f"Error analyzing JavaScript: {e}")

if __name__ == '__main__':
    analyze_javascript()
