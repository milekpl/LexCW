#!/usr/bin/env python3
"""
Debug script to check actual LIFT ranges parser output.
"""

from app.parsers.lift_parser import LIFTRangesParser
import json

# Sample XML from the test
sample_ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <!-- Simple range without hierarchy -->
    <range id="etymology">
        <range-element id="borrowed">
            <label><form lang="en"><text>Borrowed</text></form></label>
            <description><form lang="en"><text>The word is borrowed from another language</text></form></description>
        </range-element>
        <range-element id="inherited">
            <label><form lang="en"><text>Inherited</text></form></label>
            <description><form lang="en"><text>The word is inherited from an earlier form</text></form></description>
        </range-element>
    </range>
    
    <!-- Hierarchical range -->
    <range id="lexical-relation">
        <range-element id="synonym">
            <label><form lang="en"><text>Synonym</text></form></label>
            <description><form lang="en"><text>Words with the same meaning</text></form></description>
            <abbrev><form lang="en"><text>syn</text></form></abbrev>
        </range-element>
        <range-element id="antonym">
            <label><form lang="en"><text>Antonym</text></form></label>
            <description><form lang="en"><text>Words with opposite meaning</text></form></description>
        </range-element>
    </range>
    
    <!-- Test semantic domain hierarchy -->
    <range id="semantic-domain-ddp4">
        <range-element id="1" parent="">
            <label><form lang="en"><text>Universe, creation</text></form></label>
            <description><form lang="en"><text>Universe, creation</text></form></description>
        </range-element>
        <range-element id="1.1" parent="1">
            <label><form lang="en"><text>Sky</text></form></label>
            <description><form lang="en"><text>Sky</text></form></description>
        </range-element>
        <range-element id="1.1.1" parent="1.1">
            <label><form lang="en"><text>Sun</text></form></label>
            <description><form lang="en"><text>Sun</text></form></description>
        </range-element>
        <range-element id="2" parent="">
            <label><form lang="en"><text>Person</text></form></label>
            <description><form lang="en"><text>Person</text></form></description>
            <abbrev><form lang="en"><text>2.1</text></form></abbrev>
        </range-element>
    </range>
</lift-ranges>'''

parser = LIFTRangesParser()
ranges = parser.parse_string(sample_ranges_xml)

print("=== ACTUAL PARSER OUTPUT ===")
print(json.dumps(ranges, indent=2))

print("\n=== ETYMOLOGY RANGE BORROWED ELEMENT ===")
etymology_range = ranges['etymology']
borrowed = next(v for v in etymology_range['values'] if v['id'] == 'borrowed')
print(f"borrowed: {json.dumps(borrowed, indent=2)}")

print("\n=== LEXICAL-RELATION RANGE SYNONYM ELEMENT ===")
lexical_range = ranges['lexical-relation']
synonym = lexical_range['values'][0]
print(f"synonym: {json.dumps(synonym, indent=2)}")

print("\n=== SEMANTIC DOMAIN STRUCTURE ===")
semantic_range = ranges['semantic-domain-ddp4']
print(f"Number of root elements: {len(semantic_range['values'])}")
for val in semantic_range['values']:
    print(f"  {val['id']}: {val.get('description', {}).get('en', 'NO DESCRIPTION')} (children: {len(val['children'])})")
    for child in val['children']:
        print(f"    {child['id']}: {child.get('description', {}).get('en', 'NO DESCRIPTION')} (children: {len(child.get('children', []))})")
        for subchild in child.get('children', []):
            print(f"      {subchild['id']}: {subchild.get('description', {}).get('en', 'NO DESCRIPTION')}")
