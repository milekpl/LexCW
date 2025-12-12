#!/usr/bin/env python3
"""
Debug script to check the specific failing test cases
"""

from app.parsers.lift_parser import LIFTRangesParser

# Test case 1: Deep hierarchy
sample_xml_deep = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <!-- Large hierarchical range (semantic domains) -->
    <range id="semantic-domain-ddp4">
        <range-element id="1">
            <label><form lang="en"><text>Universe, creation</text></form></label>
            <abbrev><form lang="en"><text>1</text></form></abbrev>
        </range-element>
        <range-element id="1.1" parent="1">
            <label><form lang="en"><text>Sky</text></form></label>
            <abbrev><form lang="en"><text>1.1</text></form></abbrev>
        </range-element>
    </range>
</lift-ranges>'''

# Test case 2: Namespace handling
sample_xml_namespace = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges xmlns="http://fieldworks.sil.org/schemas/lift/0.13/ranges">
    <range id="test">
        <range-element id="item">
            <label><form lang="en"><text>Test Item</text></form></label>
        </range-element>
    </range>
</lift-ranges>'''

def main():
    parser = LIFTRangesParser()
    
    print("=== TEST CASE 1: Deep hierarchy ===")
    ranges = parser.parse_string(sample_xml_deep)
    semantic_range = ranges['semantic-domain-ddp4']
    universe = next(v for v in semantic_range['values'] if v['id'] == '1')
    print(f"Universe element keys: {list(universe.keys())}")
    print(f"Has 'description': {'description' in universe}")
    print(f"Has 'descriptions': {'descriptions' in universe}")
    if 'description' in universe:
        print(f"description content: {universe['description']}")
    if 'descriptions' in universe:
        print(f"descriptions content: {universe['descriptions']}")
    
    print("\n=== TEST CASE 2: Namespace handling ===")
    ranges2 = parser.parse_string(sample_xml_namespace)
    test_range = ranges2['test']
    item = test_range['values'][0]
    print(f"Item element keys: {list(item.keys())}")
    print(f"Has 'description': {'description' in item}")
    print(f"Has 'descriptions': {'descriptions' in item}")
    if 'description' in item:
        print(f"description content: {item['description']}")
    if 'descriptions' in item:
        print(f"descriptions content: {item['descriptions']}")

if __name__ == "__main__":
    main()