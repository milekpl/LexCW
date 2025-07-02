#!/usr/bin/env python3
"""
Debug script to understand the semantic domain hierarchy structure.
"""

import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def analyze_semantic_domain():
    """Analyze the structure of semantic-domain-ddp4 in the sample file."""
    sample_file = 'sample-lift-file/sample-lift-file.lift-ranges'
    
    if not os.path.exists(sample_file):
        print(f"Sample file not found: {sample_file}")
        return
    
    tree = ET.parse(sample_file)
    root = tree.getroot()
    
    # Find the semantic domain range
    for range_elem in root.findall('.//range[@id="semantic-domain-ddp4"]'):
        print("Found semantic-domain-ddp4 range")
        
        # Count total range elements at all levels
        all_elements = range_elem.findall('.//range-element')
        print(f"Total range elements found: {len(all_elements)}")
        
        # Count top-level elements
        top_level = range_elem.findall('./range-element')
        print(f"Top-level elements: {len(top_level)}")
        
        # Show structure of first few elements
        for i, elem in enumerate(top_level[:3]):
            elem_id = elem.get('id', '')
            children = elem.findall('.//range-element')
            print(f"  Element {i+1}: id='{elem_id}', total children: {len(children)}")
            
            # Show first few children
            direct_children = elem.findall('./range-element')
            for j, child in enumerate(direct_children[:3]):
                child_id = child.get('id', '')
                grandchildren = child.findall('.//range-element')
                print(f"    Child {j+1}: id='{child_id}', total descendants: {len(grandchildren)}")

def analyze_parent_attributes():
    """Analyze elements with parent attributes."""
    sample_file = 'sample-lift-file/sample-lift-file.lift-ranges'
    
    if not os.path.exists(sample_file):
        print(f"Sample file not found: {sample_file}")
        return
    
    tree = ET.parse(sample_file)
    root = tree.getroot()
    
    # Find elements with parent attributes
    parent_elements = root.findall('.//range-element[@parent]')
    print(f"\nFound {len(parent_elements)} elements with parent attributes")
    
    for i, elem in enumerate(parent_elements[:5]):
        elem_id = elem.get('id', '')
        parent_id = elem.get('parent', '')
        print(f"  Element {i+1}: id='{elem_id}', parent='{parent_id}'")

if __name__ == '__main__':
    analyze_semantic_domain()
    analyze_parent_attributes()
