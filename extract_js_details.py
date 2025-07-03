#!/usr/bin/env python3

"""
Extract and analyze the exact JavaScript from the entry form.
"""

def extract_javascript_details():
    """Extract the exact JavaScript code from entry form."""
    
    from app import create_app
    
    app = create_app('testing')
    
    with app.app_context():
        with app.test_client() as client:
            response = client.get('/entries/test_entry/edit')
            html = response.get_data(as_text=True)
            
            # Find the script section that contains rangesLoader
            import re
            
            # Extract the entire script block
            script_pattern = r'<script>\s*document\.addEventListener\(.*?</script>'
            script_match = re.search(script_pattern, html, re.DOTALL)
            
            if script_match:
                script_content = script_match.group(0)
                print("=== FULL JAVASCRIPT CONTENT ===")
                print(script_content)
                
                # Check for specific patterns
                print("\n=== ANALYSIS ===")
                if 'await window.rangesLoader.populateSelectWithFallback' in script_content:
                    print("✅ Found: await window.rangesLoader.populateSelectWithFallback")
                else:
                    print("❌ Missing: await window.rangesLoader.populateSelectWithFallback")
                    
                if 'window.rangesLoader.populateSelectWithFallback' in script_content:
                    print("✅ Found: window.rangesLoader.populateSelectWithFallback (without await)")
                else:
                    print("❌ Missing: window.rangesLoader.populateSelectWithFallback")
                    
                # Look for the specific grammatical info section
                if 'grammatical-info' in script_content:
                    print("✅ Found: grammatical-info reference")
                    
                    # Extract that specific section
                    gram_pattern = r'// Load grammatical info.*?}'
                    gram_match = re.search(gram_pattern, script_content, re.DOTALL)
                    if gram_match:
                        print("\n=== GRAMMATICAL INFO SECTION ===")
                        print(gram_match.group(0))
                        
            else:
                print("❌ Could not find script section")


if __name__ == '__main__':
    extract_javascript_details()
