"""
Simple test script to check the hierarchical structure of ranges from the API
"""

import requests

def main():
    print("=== Testing Hierarchical Ranges API ===")
    
    # Check if Flask is running
    try:
        response = requests.get('http://localhost:5000/api/ranges/semantic-domain-ddp4')
        if response.status_code != 200:
            print(f"API server returned status code {response.status_code}. Make sure Flask is running.")
            return
        
        data = response.json()
        if not data.get('success'):
            print(f"API returned error: {data.get('error')}")
            return
        
        range_data = data.get('data', {})
        values = range_data.get('values', [])
        
        print(f"Semantic Domain has {len(values)} top-level values")
        
        # Look at the first few values to see if they have children
        for i, value in enumerate(values[:5]):  # Just look at first 5
            children = value.get('children', [])
            print(f"{i+1}. {value.get('id', 'unknown')} - {value.get('value', '')} has {len(children)} children")
            
            # Print a few children to verify hierarchical structure
            for j, child in enumerate(children[:3]):  # Just show first 3 children
                grandchildren = child.get('children', [])
                print(f"   {j+1}. {child.get('id', 'unknown')} - {child.get('value', '')} has {len(grandchildren)} grandchildren")
        
    except requests.exceptions.ConnectionError:
        print("Could not connect to API server. Make sure Flask is running on http://localhost:5000")
    except Exception as e:
        print(f"Error testing API endpoint: {str(e)}")

if __name__ == "__main__":
    main()
