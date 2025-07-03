"""
Analyze the captured entry form HTML to look for pronunciation-related elements.
"""

from bs4 import BeautifulSoup

def analyze_entry_form():
    """Analyze the entry form HTML to find pronunciation-related elements."""
    try:
        with open("protestantism_entry_form.html", "r", encoding="utf-8") as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for the pronunciation container
        pron_container = soup.find(id='pronunciation-container')
        if pron_container:
            print("Found pronunciation container:")
            print(pron_container.prettify()[:500] + "..." if len(pron_container.prettify()) > 500 else pron_container.prettify())
        else:
            print("Pronunciation container not found")
        
        # Check for any hidden sections that might hide pronunciations
        hidden_sections = soup.find_all(class_=lambda x: x and 'hidden' in x.lower())
        for section in hidden_sections:
            if 'pronunciation' in str(section).lower():
                print("\nFound hidden pronunciation section:")
                print(section.prettify()[:500] + "..." if len(section.prettify()) > 500 else section.prettify())
        
        # Find the PronunciationFormsManager initialization
        for script in soup.find_all('script'):
            script_text = script.string or ""
            if 'PronunciationFormsManager' in script_text:
                print("\nFound PronunciationFormsManager initialization:")
                for line in script_text.split('\n'):
                    if 'pronunciations' in line or 'PronunciationFormsManager' in line:
                        print(line.strip())
        
        # CSS that might affect visibility
        styles = soup.find_all('style')
        for style in styles:
            if 'pronunciation' in style.string.lower():
                print("\nFound pronunciation-related CSS:")
                print(style.string)
        
    except Exception as e:
        print(f"Error analyzing HTML: {e}")

if __name__ == '__main__':
    analyze_entry_form()
