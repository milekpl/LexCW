#!/usr/bin/env python3
"""
Debug script to trace the LIFT ranges loading process in test environment.
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG)

from app import create_app
from app.parsers.lift_parser import LIFTRangesParser

def main():
    print("=== LIFT Ranges Debug ===")
    
    # Test the parser directly
    print("\n1. Testing LIFTRangesParser directly:")
    parser = LIFTRangesParser()
    sample_file = 'sample-lift-file/sample-lift-file.lift-ranges'
    
    if os.path.exists(sample_file):
        ranges = parser.parse_file(sample_file)
        print(f"   Parsed {len(ranges)} range types from sample file")
        print(f"   Range types: {sorted(ranges.keys())}")
        
        # Check a few specific ranges
        test_ranges = ['etymology', 'status', 'users', 'location']
        for range_type in test_ranges:
            if range_type in ranges:
                print(f"   ✓ {range_type}: {len(ranges[range_type].get('values', []))} values")
            else:
                print(f"   ✗ {range_type}: not found")
    else:
        print(f"   Sample file not found: {sample_file}")
    
    # Test the API directly  
    print("\n2. Testing Flask app API:")
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        response = client.get('/api/ranges')
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print(f"   Response keys: {list(data.keys())}")
            
            ranges = data.get('data', data.get('ranges', {}))
            print(f"   API returned {len(ranges)} range types")
            print(f"   Range types: {sorted(ranges.keys())}")
            
            # Check the same test ranges
            test_ranges = ['etymology', 'status', 'users', 'location']
            for range_type in test_ranges:
                if range_type in ranges:
                    print(f"   ✓ {range_type}: found in API")
                else:
                    print(f"   ✗ {range_type}: not found in API")
        else:
            print(f"   Error: {response.get_data(as_text=True)}")

if __name__ == '__main__':
    main()
