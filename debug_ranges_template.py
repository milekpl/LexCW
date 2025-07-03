#!/usr/bin/env python3
"""
Debug script to analyze ranges loading and pronunciation display in entry form template.
This script will help identify issues with JavaScript execution and element rendering.
"""

import os
from app import create_app
from app.services.dictionary_service import DictionaryService


def main():
    """Main function to debug ranges and pronunciation display."""
    print("=== DEBUGGING RANGES AND PRONUNCIATION TEMPLATE ===")
    
    # Set testing environment to enable test entry access
    os.environ['TESTING'] = 'true'
    
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Get a test entry for debugging
            dict_service = app.injector.get(DictionaryService)
            
            # Try to get the test entry used in the tests
            try:
                entry = dict_service.get_entry("test_pronunciation_entry")
                print(f"✅ Found test entry: {entry.id}")
                print(f"   Lexical unit: {entry.lexical_unit}")
                print(f"   Pronunciations: {entry.pronunciations}")
            except Exception as e:
                print(f"❌ Could not get test entry: {e}")
                # Use a simpler test entry
                entry = dict_service.get_entry("test_entry")
                if entry:
                    print(f"✅ Using fallback test entry: {entry.id}")
                else:
                    print("❌ No test entry available")
                    return
            
            # Get the entry form HTML
            response = client.get(f'/entries/{entry.id}/edit')
            
            if response.status_code != 200:
                print(f"❌ Failed to load entry form: {response.status_code}")
                return
                
            html = response.get_data(as_text=True)
            
            print("\n=== ANALYZING HTML TEMPLATE ===")
            
            # Check for script inclusions
            scripts_to_check = [
                'ranges-loader.js',
                'pronunciation-forms.js',
                'variant-forms.js',
                'relations.js',
                'etymology-forms.js',
                'entry-form.js'
            ]
            
            for script in scripts_to_check:
                if script in html:
                    print(f"✅ {script} script included")
                else:
                    print(f"❌ {script} script MISSING")
            
            # Check for specific JavaScript objects/functions
            js_objects_to_check = [
                'window.rangesLoader',
                'PronunciationFormsManager',
                'populateSelectWithFallback',
                'window.pronunciationFormsManager'
            ]
            
            for js_obj in js_objects_to_check:
                if js_obj in html:
                    print(f"✅ {js_obj} found in HTML")
                else:
                    print(f"❌ {js_obj} NOT found in HTML")
            
            # Check for pronunciation data structure
            print("\n=== PRONUNCIATION DATA ANALYSIS ===")
            
            if 'pronunciationData' in html:
                print("✅ pronunciationData variable found")
                
                # Extract the pronunciation data line
                lines = html.split('\n')
                for line in lines:
                    if 'pronunciationData' in line and '=' in line:
                        print(f"   Data line: {line.strip()}")
                        break
            else:
                print("❌ pronunciationData variable NOT found")
            
            # Check for required DOM elements
            print("\n=== DOM ELEMENTS ANALYSIS ===")
            
            dom_elements = [
                'pronunciation-container',
                'add-pronunciation-btn',
                'variants-container',
                'relations-container',
                'etymology-container'
            ]
            
            for element_id in dom_elements:
                if f'id="{element_id}"' in html:
                    print(f"✅ #{element_id} element found")
                else:
                    print(f"❌ #{element_id} element MISSING")
            
            # Check for data-range-id attributes
            print("\n=== LIFT RANGES ATTRIBUTES ===")
            
            range_ids = [
                'grammatical-info',
                'semantic-domain-ddp4',
                'usage-type',
                'status',
                'morph-type'
            ]
            
            for range_id in range_ids:
                if f'data-range-id="{range_id}"' in html:
                    print(f"✅ data-range-id='{range_id}' found")
                else:
                    print(f"❌ data-range-id='{range_id}' MISSING")
            
            # Save HTML for manual inspection
            debug_file = 'entry_form_debug.html'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\n💾 Full HTML saved to {debug_file}")
            
            # Check pronunciation script details
            print("\n=== PRONUNCIATION SCRIPT ANALYSIS ===")
            
            # Look for the pronunciation data in the script
            import re
            pronunciation_data_match = re.search(r'const pronunciationData = ({[^;]+});', html)
            if pronunciation_data_match:
                data_str = pronunciation_data_match.group(1)
                print(f"✅ Pronunciation data found: {data_str}")
                
                # Parse the data to see the actual content
                try:
                    import json
                    # Remove Unicode escapes for display
                    clean_data = data_str.replace('\\u026a', 'ɪ').replace('\\u0283', 'ʃ').replace('\\u0259', 'ə')
                    print(f"   Readable format: {clean_data}")
                except Exception as e:
                    print(f"   Could not parse data: {e}")
            else:
                print("❌ Pronunciation data NOT found in script")
            
            # Check if the array conversion is happening
            if 'pronunciationArray.push(' in html:
                print("✅ Pronunciation array conversion found")
            else:
                print("❌ Pronunciation array conversion NOT found")
            
            # Check for the manager initialization
            if 'new PronunciationFormsManager(' in html:
                print("✅ PronunciationFormsManager initialization found")
            else:
                print("❌ PronunciationFormsManager initialization NOT found")
            
            # Check if there are any syntax errors in the script
            script_start = html.find('<script>')
            script_end = html.find('</script>')
            if script_start != -1 and script_end != -1:
                script_content = html[script_start:script_end]
                if 'SyntaxError' in script_content or 'Error:' in script_content:
                    print("❌ Potential JavaScript errors found")
                else:
                    print("✅ No obvious JavaScript errors detected")
            
            print("\n=== JAVASCRIPT EXECUTION ORDER ===")
            
            # Check script loading order
            scripts_found = []
            for match in re.finditer(r'<script[^>]*src="([^"]+)"', html):
                scripts_found.append(match.group(1))
            
            print("📜 Script loading order:")
            for i, script in enumerate(scripts_found):
                if 'js/' in script:
                    print(f"   {i+1}. {script}")
            
            # Check if the initialization script comes after the required scripts
            pronunciation_js_pos = -1
            entry_form_js_pos = -1
            init_script_pos = -1
            
            for i, script in enumerate(scripts_found):
                if 'pronunciation-forms.js' in script:
                    pronunciation_js_pos = i
                elif 'entry-form.js' in script:
                    entry_form_js_pos = i
            
            init_script_match = re.search(r'document\.addEventListener\(\'DOMContentLoaded\'', html)
            if init_script_match:
                init_script_pos = init_script_match.start()
                print(f"✅ Initialization script found at position {init_script_pos}")
            
            if pronunciation_js_pos > -1 and init_script_pos > -1:
                print("✅ Scripts appear to be in correct order")
            else:
                print("❌ Script order may be incorrect")
                
            # Test ranges API directly
            print("\n=== TESTING RANGES API ===")
            
            api_endpoints = [
                '/api/ranges',
                '/api/ranges/grammatical-info',
                '/api/ranges/semantic-domain-ddp4'
            ]
            
            for endpoint in api_endpoints:
                api_response = client.get(endpoint)
                if api_response.status_code == 200:
                    data = api_response.get_json()
                    print(f"✅ {endpoint}: {api_response.status_code} - {len(data.get('data', {}).get('values', []))} items")
                else:
                    print(f"❌ {endpoint}: {api_response.status_code}")


if __name__ == '__main__':
    main()
