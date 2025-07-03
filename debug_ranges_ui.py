#!/usr/bin/env python3

"""
Debug script to test the ranges integration in the UI.
"""

def debug_ranges_ui_integration():
    """Debug the ranges UI integration issue."""
    
    from app import create_app
    
    app = create_app('testing')
    
    with app.app_context():
        with app.test_client() as client:
            print("=== TESTING RANGES API ===")
            # Test ranges API directly
            response = client.get('/api/ranges')
            print(f"API Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"API Success: {data.get('success')}")
                print(f"Range Count: {len(data.get('data', {}))}")
                print(f"Sample ranges: {list(data.get('data', {}).keys())[:5]}")
            
            print("\n=== TESTING STATIC FILES ===")
            # Test if ranges-loader.js is accessible
            js_response = client.get('/static/js/ranges-loader.js')
            print(f"ranges-loader.js Status: {js_response.status_code}")
            
            print("\n=== TESTING ENTRY FORM ===")
            # Test entry form - try with existing entry
            form_response = client.get('/entries/test_entry/edit')
            print(f"Entry Form Status: {form_response.status_code}")
            
            if form_response.status_code == 200:
                html = form_response.get_data(as_text=True)
                
                # Check for key indicators
                indicators = [
                    ('ranges-loader.js script included', 'ranges-loader.js' in html),
                    ('rangesLoader referenced', 'rangesLoader' in html),
                    ('API ranges called', '/api/ranges' in html),
                    ('grammatical-info class present', 'dynamic-grammatical-info' in html),
                    ('populateSelectWithFallback called', 'populateSelectWithFallback' in html),
                ]
                
                for desc, check in indicators:
                    status = "✅" if check else "❌"
                    print(f"  {status} {desc}")
                
                # Check for hardcoded fallback usage
                print(f"\n=== CHECKING FOR FALLBACK USAGE ===")
                fallback_indicators = [
                    'option value="Noun"',
                    'option value="Verb"', 
                    'option value="synonym"',
                    'option value="antonym"'
                ]
                
                for indicator in fallback_indicators:
                    if indicator in html:
                        print(f"  ⚠️  Found hardcoded: {indicator}")
                    else:
                        print(f"  ✅ No hardcoded: {indicator}")


if __name__ == '__main__':
    debug_ranges_ui_integration()
