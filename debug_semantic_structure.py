#!/usr/bin/env python3
"""
Debug script to understand the exact structure of semantic domain elements.
"""

import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def examine_semantic_domain_structure():
    """Examine the detailed structure of the semantic domain."""
    sample_file = 'sample-lift-file/sample-lift-file.lift-ranges'
    
    if not os.path.exists(sample_file):
        print(f"Sample file not found: {sample_file}")
        return
    
    tree = ET.parse(sample_file)
    root = tree.getroot()
    
    # Find the semantic domain range
    for range_elem in root.findall('.//range[@id="semantic-domain-ddp4"]'):
        print("=== SEMANTIC DOMAIN STRUCTURE ===")
        
        # Check if elements have parent attributes
        elements_with_parents = range_elem.findall('.//range-element[@parent]')
        print(f"Elements with parent attributes: {len(elements_with_parents)}")
        
        # Check top-level elements vs all elements
        top_level = range_elem.findall('./range-element')
        all_elements = range_elem.findall('.//range-element')
        print(f"Top-level elements: {len(top_level)}")
        print(f"All elements: {len(all_elements)}")
        
        # Examine first few elements for structure
        print(f"\nFirst 5 top-level elements:")
        for i, elem in enumerate(top_level[:5]):
            elem_id = elem.get('id', '')
            abbrev = ''
            abbrev_elem = elem.find('./abbrev')
            if abbrev_elem is not None and abbrev_elem.text:
                abbrev = abbrev_elem.text.strip()
            
            children = elem.findall('./range-element')
            print(f"  {i+1}. id='{elem_id}', abbrev='{abbrev}', direct children: {len(children)}")
            
            # Show first child if any
            if children:
                child = children[0]
                child_id = child.get('id', '')
                child_abbrev = ''
                child_abbrev_elem = child.find('./abbrev')
                if child_abbrev_elem is not None and child_abbrev_elem.text:
                    child_abbrev = child_abbrev_elem.text.strip()
                print(f"     First child: id='{child_id}', abbrev='{child_abbrev}'")
        
        # Check if there are elements that should be hierarchical
        print(f"\nSample elements with potential hierarchy indicators:")
        for elem in all_elements[:10]:
            elem_id = elem.get('id', '')
            abbrev = ''
            abbrev_elem = elem.find('./abbrev')
            if abbrev_elem is not None and abbrev_elem.text:
                abbrev = abbrev_elem.text.strip()
            
            if '.' in abbrev and abbrev.count('.') <= 2:  # Like 1.1.1
                print(f"  Element: id='{elem_id}', abbrev='{abbrev}'")

if __name__ == '__main__':
    examine_semantic_domain_structure()
