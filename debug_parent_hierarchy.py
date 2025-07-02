#!/usr/bin/env python3
"""
Debug script to test the parent-based hierarchy parsing for semantic domain.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.parsers.lift_parser import LIFTRangesParser

def test_semantic_domain_parsing():
    """Test semantic domain parsing step by step."""
    sample_file = 'sample-lift-file/sample-lift-file.lift-ranges'
    
    if not os.path.exists(sample_file):
        print(f"Sample file not found: {sample_file}")
        return
    
    parser = LIFTRangesParser()
    ranges = parser.parse_file(sample_file)
    
    if 'semantic-domain-ddp4' not in ranges:
        print("semantic-domain-ddp4 not found in parsed ranges")
        return
    
    semantic_domain = ranges['semantic-domain-ddp4']
    print(f"Semantic domain found: {len(semantic_domain['values'])} top-level values")
    
    # Check if we're getting the parent-based hierarchy correctly
    total_with_children = 0
    total_children = 0
    
    for i, value in enumerate(semantic_domain['values'][:10]):  # First 10
        children_count = len(value.get('children', []))
        if children_count > 0:
            total_with_children += 1
            total_children += children_count
        print(f"Value {i+1}: id='{value.get('id', '')}', abbrev='{value.get('abbrev', '')}', children: {children_count}")
    
    print(f"\nSummary of first 10:")
    print(f"Elements with children: {total_with_children}")
    print(f"Total children: {total_children}")
    
    # Test if we should find many more elements
    if len(semantic_domain['values']) < 50:
        print(f"\nERROR: Expected many more elements. Only found {len(semantic_domain['values'])}")
        print("This suggests the parent-based hierarchy parsing isn't working correctly.")

if __name__ == '__main__':
    test_semantic_domain_parsing()
