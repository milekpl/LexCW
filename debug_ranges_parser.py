#!/usr/bin/env python3
"""
Debug script to check what the LIFTRangesParser is actually producing
"""

from app.parsers.lift_parser import LIFTRangesParser

# Sample XML from the test
sample_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <!-- Simple range without hierarchy -->
    <range id="etymology">
        <range-element id="borrowed">
            <label><form lang="en"><text>borrowed</text></form></label>
            <description><form lang="en"><text>The word is borrowed from another language</text></form></description>
        </range-element>
    </range>
</lift-ranges>'''

def main():
    parser = LIFTRangesParser()
    ranges = parser.parse_string(sample_xml)
    
    print("=== PARSED DATA ===")
    import json
    print(json.dumps(ranges, indent=2))
    
    print("\n=== CHECKING 'borrowed' ELEMENT ===")
    etymology_range = ranges['etymology']
    borrowed = next(v for v in etymology_range['values'] if v['id'] == 'borrowed')
    
    print(f"Available keys: {list(borrowed.keys())}")
    print(f"Has 'description' key: {'description' in borrowed}")
    print(f"Has 'descriptions' key: {'descriptions' in borrowed}")
    
    if 'descriptions' in borrowed:
        print(f"descriptions content: {borrowed['descriptions']}")
    
    if 'description' in borrowed:
        print(f"description content: {borrowed['description']}")

if __name__ == "__main__":
    main()