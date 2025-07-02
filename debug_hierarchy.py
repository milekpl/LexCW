#!/usr/bin/env python3

"""
Debug script to understand the hierarchy building issue.
"""

import sys
from app.parsers.lift_parser import LIFTRangesParser

def main():
    test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="semantic-domain-ddp4">
        <range-element id="1">
            <label><form lang="en"><text>Universe, creation</text></form></label>
            <abbrev><form lang="en"><text>1</text></form></abbrev>
        </range-element>
        <range-element id="1.1" parent="1">
            <label><form lang="en"><text>Sky</text></form></label>
            <abbrev><form lang="en"><text>1.1</text></form></abbrev>
        </range-element>
        <range-element id="1.1.1" parent="1.1">
            <label><form lang="en"><text>Sun</text></form></label>
            <abbrev><form lang="en"><text>1.1.1</text></form></abbrev>
        </range-element>
        <range-element id="2">
            <label><form lang="en"><text>Person</text></form></label>
            <abbrev><form lang="en"><text>2</text></form></abbrev>
        </range-element>
        <range-element id="2.1" parent="2">
            <label><form lang="en"><text>Body</text></form></label>
            <abbrev><form lang="en"><text>2.1</text></form></abbrev>
        </range-element>
    </range>
</lift-ranges>'''
    
    parser = LIFTRangesParser()
    ranges = parser.parse_string(test_xml)
    
    print("=== PARSED RANGES ===")
    print(f"Total ranges: {len(ranges)}")
    
    if 'semantic-domain-ddp4' in ranges:
        semantic_range = ranges['semantic-domain-ddp4']
        print(f"\nSemantic domain values: {len(semantic_range['values'])}")
        
        for i, value in enumerate(semantic_range['values']):
            print(f"\nRoot element {i}: {value['id']} - {value.get('description', {}).get('en', 'No description')}")
            print(f"  Children: {len(value['children'])}")
            
            for j, child in enumerate(value['children']):
                print(f"    Child {j}: {child['id']} - {child.get('description', {}).get('en', 'No description')}")
                print(f"      Grandchildren: {len(child['children'])}")
                
                for k, grandchild in enumerate(child['children']):
                    print(f"        Grandchild {k}: {grandchild['id']} - {grandchild.get('description', {}).get('en', 'No description')}")

if __name__ == '__main__':
    main()
