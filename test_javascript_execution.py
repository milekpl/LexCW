#!/usr/bin/env python3

"""
Test to check actual JavaScript execution in entry form.
"""

def test_javascript_execution():
    """Test if JavaScript is executing properly."""
    
    from app import create_app
    
    app = create_app('testing')
    
    with app.app_context():
        with app.test_client() as client:
            print("=== CHECKING JAVASCRIPT EXECUTION CONTEXT ===")
            
            # Get the entry form HTML
            response = client.get('/entries/test_entry/edit')
            html = response.get_data(as_text=True)
            
            # Extract the JavaScript section
            print("Looking for JavaScript section...")
            
            # Find the ranges-loader script tag
            if 'ranges-loader.js' in html:
                print("✅ ranges-loader.js script tag found")
            else:
                print("❌ ranges-loader.js script tag NOT found")
            
            # Check for window.rangesLoader usage
            if 'window.rangesLoader' in html:
                print("✅ window.rangesLoader reference found")
                
                # Find the specific call
                if 'populateSelectWithFallback' in html:
                    print("✅ populateSelectWithFallback call found")
                    
                    # Extract the relevant JavaScript code
                    import re
                    
                    # Find the DOMContentLoaded section
                    dom_match = re.search(
                        r"document\.addEventListener\('DOMContentLoaded'.*?}\);", 
                        html, 
                        re.DOTALL
                    )
                    
                    if dom_match:
                        js_code = dom_match.group(0)
                        print("\n=== EXTRACTED JAVASCRIPT CODE ===")
                        print(js_code[:500] + "..." if len(js_code) > 500 else js_code)
                        
                        # Check for async/await usage
                        if 'async function' in js_code:
                            print("✅ Async function detected")
                        else:
                            print("❌ No async function found")
                            
                        if 'await window.rangesLoader' in js_code:
                            print("✅ Await rangesLoader call detected") 
                        else:
                            print("❌ No await rangesLoader call found")
                    
            # Check console for any errors by looking at the structure
            print("\n=== CHECKING TEMPLATE STRUCTURE ===")
            
            # Check if the blocks are properly structured
            if '{% block extra_js %}' in html and '{% endblock %}' in html:
                print("✅ Template blocks properly structured")
            else:
                print("❌ Template blocks may be malformed")
            
            # Check if scripts are in the right order
            script_order = [
                'select2.min.js',
                'ranges-loader.js', 
                'window.rangesLoader'
            ]
            
            last_pos = -1
            for script in script_order:
                pos = html.find(script)
                if pos > last_pos:
                    print(f"✅ {script} in correct order (pos: {pos})")
                    last_pos = pos
                else:
                    print(f"❌ {script} in wrong order or missing (pos: {pos})")


if __name__ == '__main__':
    test_javascript_execution()
