#!/usr/bin/env python3
"""
TDD test for hierarchical range parsing
"""

import xml.etree.ElementTree as ET
from app.parsers.lift_parser import LIFTRangesParser


def test_parser_handles_parent_attributes():
    """Test that the LIFT parser correctly parses parent attributes from range elements"""
    
    # Create sample XML with hierarchical range structure
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<lift>
    <lift-ranges>
        <range id="test-hierarchy">
            <range-element id="Parent1" guid="guid1">
                <label><form lang="en"><text>Parent Item 1</text></form></label>
            </range-element>
            <range-element id="Child1" guid="guid2" parent="Parent1">
                <label><form lang="en"><text>Child Item 1</text></form></label>
            </range-element>
            <range-element id="Child2" guid="guid3" parent="Parent1">
                <label><form lang="en"><text>Child Item 2</text></form></label>  
            </range-element>
            <range-element id="GrandChild1" guid="guid4" parent="Child1">
                <label><form lang="en"><text>Grand Child Item 1</text></form></label>
            </range-element>
        </range>
    </lift-ranges>
</lift>'''
    
    # Parse the XML
    parser = LIFTRangesParser()
    
    # Debug: Let's manually check the parent detection logic
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_content)
    
    # Find the range element
    range_elem = root.find('.//range[@id="test-hierarchy"]')
    if range_elem is not None:
        print("Found range element")
        
        # Check for parent attributes (mimicking the parser logic)
        has_parent_attributes = False
        range_elements = range_elem.findall('.//range-element')
        print(f"Found {len(range_elements)} range-element nodes")
        
        for elem in range_elements:
            parent_attr = elem.get('parent')
            print(f"  Element {elem.get('id')}: parent='{parent_attr}'")
            if parent_attr:
                has_parent_attributes = True
        
        print(f"Has parent attributes: {has_parent_attributes}")
    else:
        print("Range element not found!")
    
    # Parse the ranges 
    ranges = parser.parse_string(xml_content)
    
    # Debug: Check which parsing method was used
    print("Parsed ranges keys:", list(ranges.keys()))
    if 'test-hierarchy' in ranges:
        values = ranges['test-hierarchy'].get('values', [])
        print("Number of top-level values:", len(values))
        
        # Check structure: is it flat or nested?
        if len(values) > 1:
            print("Appears to be FLAT structure (multiple top-level items)")
            for i, value in enumerate(values[:3]):
                print(f"  Item {i}: {value.get('id')} (parent: {value.get('parent', 'MISSING')})")
        else:
            print("Appears to be NESTED structure (single root with children)")
            print(f"  Root: {values[0].get('id')}")
            print(f"  Children: {len(values[0].get('children', []))}")
    else:
        print("No test-hierarchy found!")
    
    # Check that we have the test range
    assert 'test-hierarchy' in ranges
    range_data = ranges['test-hierarchy']
    assert 'values' in range_data
    
    values = range_data['values']
    
    # Find items by ID for easier testing
    items_by_id = {item['id']: item for item in values}
    
    # Test parent attributes are correctly parsed
    assert 'Parent1' in items_by_id
    assert 'Child1' in items_by_id  
    assert 'Child2' in items_by_id
    assert 'GrandChild1' in items_by_id
    
    # Check parent relationships
    parent1 = items_by_id['Parent1']
    child1 = items_by_id['Child1']
    child2 = items_by_id['Child2'] 
    grandchild1 = items_by_id['GrandChild1']
    
    # Parent should have no parent (empty string)
    assert parent1['parent'] == ''
    
    # Children should have correct parent
    assert child1['parent'] == 'Parent1'
    assert child2['parent'] == 'Parent1'
    
    # Grandchild should have correct parent
    assert grandchild1['parent'] == 'Child1'
    
    print("✅ All parent attributes parsed correctly!")
    

if __name__ == '__main__':
    test_parser_handles_parent_attributes()
    print("✅ Test passed!")
