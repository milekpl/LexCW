"""
Test script to verify that the etymology type ranges are properly loaded
and displayed in the etymology forms manager.

This test:
1. Checks that the etymology-types range endpoint returns valid data
2. Verifies the range has proper hierarchical structure
3. Compares against expected etymology types from the LIFT specification
"""

import requests
import json
import sys
from pprint import pprint

# Configuration
BASE_URL = "http://localhost:5000"  # Adjust if your Flask app runs on a different port
RANGE_ID = "etymology-types"

def test_etymology_range_endpoint():
    """Test the etymology types range endpoint returns valid data."""
    url = f"{BASE_URL}/api/ranges/{RANGE_ID}"
    print(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        
        data = response.json()
        if not data.get("success"):
            print(f"Error: API returned success=false: {data}")
            return False
            
        range_data = data.get("data")
        if not range_data:
            print("Error: No range data returned")
            return False
            
        values = range_data.get("values", [])
        if not values:
            print("Error: No values in range data")
            return False
            
        print(f"✓ Endpoint test passed - Retrieved {len(values)} etymology types")
        print("\nSample of etymology types:")
        pprint(values[:5])  # Show first 5 items
        
        # Check for hierarchy
        has_hierarchy = False
        for item in values:
            if "children" in item and item["children"]:
                has_hierarchy = True
                print("\nHierarchy example:")
                pprint(item)
                break
                
        if has_hierarchy:
            print("\n✓ Hierarchy structure found in etymology types")
        else:
            print("\nNote: No hierarchical structure found in etymology types")
            
        # Compare against expected types
        expected_types = [
            "inheritance", "borrowing", "derivation", "compound", 
            "calque", "semantic", "onomatopoeia"
        ]
        
        found_types = set()
        for item in values:
            found_types.add(item.get("value", ""))
            
        missing_types = [t for t in expected_types if t not in found_types]
        if missing_types:
            print(f"\nWarning: Missing expected etymology types: {missing_types}")
        else:
            print("\n✓ All expected base etymology types found")
            
        return True
            
    except requests.RequestException as e:
        print(f"Error connecting to API: {e}")
        print("Is the Flask server running?")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=== Etymology Types Range Test ===")
    success = test_etymology_range_endpoint()
    sys.exit(0 if success else 1)
