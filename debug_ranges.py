#!/usr/bin/env python3
"""
Debug script to check ranges functionality
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.parsers.lift_parser import LIFTRangesParser
from app.services.dictionary_service import DictionaryService

def main():
    print("=== Testing LIFT Ranges Parser ===")
    try:
        parser = LIFTRangesParser()
        ranges_file = 'sample-lift-file/sample-lift-file.lift-ranges'
        
        if not os.path.exists(ranges_file):
            print(f"ERROR: Ranges file not found: {ranges_file}")
            return
        
        print(f"Parsing ranges file: {ranges_file}")
        ranges = parser.parse_file(ranges_file)
        
        print(f"\nFound {len(ranges)} ranges:")
        for range_id in ranges.keys():
            print(f"  - {range_id}")
        
        # Check grammatical-info range specifically
        if 'grammatical-info' in ranges:
            gi_range = ranges['grammatical-info']
            print(f"\nGrammatical Info Range:")
            print(f"  Total values: {len(gi_range.get('values', []))}")
            
            values = gi_range.get('values', [])
            for i, val in enumerate(values[:20]):  # First 20 values
                val_id = val.get('id', 'Unknown')
                label = val.get('description', {}).get('en', val_id)
                abbrev = val.get('abbrev', '')
                parent = val.get('parent', '')
                
                indent = "  " if not parent else "    "
                abbrev_text = f" ({abbrev})" if abbrev else ""
                parent_text = f" [parent: {parent}]" if parent else ""
                
                print(f"{indent}{i+1:2d}. {val_id} - {label}{abbrev_text}{parent_text}")
                
                # Show children if any
                children = val.get('children', [])
                if children:
                    for j, child in enumerate(children[:3]):
                        child_id = child.get('id', 'Unknown')
                        child_label = child.get('description', {}).get('en', child_id)
                        child_abbrev = child.get('abbrev', '')
                        child_abbrev_text = f" ({child_abbrev})" if child_abbrev else ""
                        print(f"      └─ {child_id} - {child_label}{child_abbrev_text}")
                    if len(children) > 3:
                        print(f"      └─ ... and {len(children) - 3} more children")
            
            if len(values) > 20:
                print(f"  ... and {len(values) - 20} more values")
        else:
            print("\nERROR: 'grammatical-info' range not found!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== Testing DictionaryService default ranges ===")
    try:
        service = DictionaryService()
        default_ranges = service._get_default_ranges()
        
        print(f"Default ranges: {list(default_ranges.keys())}")
        
        if 'grammatical-info' in default_ranges:
            gi_default = default_ranges['grammatical-info']
            values = gi_default.get('values', [])
            print(f"Default grammatical-info values ({len(values)}):")
            for i, val in enumerate(values):
                if isinstance(val, dict):
                    val_id = val.get('id', val.get('value', 'Unknown'))
                else:
                    val_id = str(val)
                print(f"  {i+1}. {val_id}")
        
    except Exception as e:
        print(f"ERROR with DictionaryService: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
