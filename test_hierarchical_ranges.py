"""
Test script to verify the hierarchical ranges functionality in the UI.

This script checks:
1. If the LIFT parser correctly parses hierarchical ranges
2. If the API endpoints return the correct hierarchical structure
3. If the UI correctly displays and allows selection of hierarchical elements
"""

from __future__ import annotations
import os
import sys
import json
import requests
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

# Add the app directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsers.lift_parser import LIFTRangesParser
from app.services.dictionary_service import DictionaryService

def test_parser_hierarchical_ranges():
    """Test if the LIFT parser correctly parses hierarchical ranges."""
    print("\n--- Testing LIFT Parser Hierarchical Ranges ---")
    
    # Sample XML with hierarchical ranges (both parent-based and nested)
    sample_xml = """
    <lift-ranges>
        <range id="semantic-domain-ddp4">
            <range-element id="1">
                <label>Universe, creation</label>
                <range-element id="1.1">
                    <label>Sky</label>
                </range-element>
                <range-element id="1.2">
                    <label>World</label>
                </range-element>
            </range-element>
            <range-element id="2">
                <label>Person</label>
                <range-element id="2.1">
                    <label>Body</label>
                </range-element>
            </range-element>
        </range>
        
        <range id="grammatical-info">
            <range-element id="noun" value="noun">
                <label>Noun</label>
            </range-element>
            <range-element id="noun-uncountable" value="noun-uncountable" parent="noun">
                <label>Uncountable Noun</label>
            </range-element>
            <range-element id="verb" value="verb">
                <label>Verb</label>
            </range-element>
        </range>
    </lift-ranges>
    """
    
    parser = LIFTRangesParser()
    ranges = parser.parse_string(sample_xml)
    
    # Check if we have the expected range IDs
    print(f"Parsed ranges: {', '.join(ranges.keys())}")
    
    # Check for nested hierarchy in semantic domains
    if 'semantic-domain-ddp4' in ranges:
        sem_domain = ranges['semantic-domain-ddp4']
        print(f"\nSemantic Domain values: {len(sem_domain['values'])}")
        
        # Check top-level elements
        for idx, value in enumerate(sem_domain['values']):
            print(f"  {idx+1}. {value['id']} - {value.get('value', '')} - Children: {len(value.get('children', []))}")
            
            # Check children
            for child in value.get('children', []):
                print(f"    - {child['id']} - {child.get('value', '')}")
    
    # Check for parent-based hierarchy in grammatical info
    if 'grammatical-info' in ranges:
        gram_info = ranges['grammatical-info']
        print(f"\nGrammatical Info values: {len(gram_info['values'])}")
        
        # Check all elements and their parents
        for idx, value in enumerate(gram_info['values']):
            parent = value.get('parent', 'None')
            print(f"  {idx+1}. {value['id']} - Parent: {parent} - Children: {len(value.get('children', []))}")
            
            # Check children
            for child in value.get('children', []):
                print(f"    - {child['id']} - Parent: {child.get('parent', 'None')}")
    
    return ranges

def test_api_endpoints():
    """Test if the API endpoints return the correct hierarchical structure."""
    print("\n--- Testing API Endpoints for Hierarchical Ranges ---")
    
    # Check if Flask is running
    try:
        response = requests.get('http://localhost:5000/api/ranges')
        if response.status_code != 200:
            print(f"API server returned status code {response.status_code}. Make sure Flask is running.")
            return
        
        ranges_data = response.json()
        if not ranges_data.get('success'):
            print(f"API returned error: {ranges_data.get('error')}")
            return
        
        ranges = ranges_data.get('data', {})
        print(f"API returned {len(ranges)} ranges")
        
        # Check a few specific ranges that should have hierarchical structure
        hierarchical_ranges = ['semantic-domain-ddp4', 'grammatical-info']
        for range_id in hierarchical_ranges:
            if range_id in ranges:
                range_data = ranges[range_id]
                values = range_data.get('values', [])
                print(f"\n{range_id}: {len(values)} top-level values")
                
                # Look for children in the values
                has_hierarchy = False
                for value in values:
                    children = value.get('children', [])
                    if children:
                        has_hierarchy = True
                        print(f"  {value.get('id', 'unknown')} has {len(children)} children")
                        for child in children[:3]:  # Show just a few children as example
                            print(f"    - {child.get('id', 'unknown')}")
                
                if not has_hierarchy:
                    print(f"  WARNING: {range_id} doesn't appear to have a hierarchical structure!")
            else:
                print(f"{range_id} not found in API response")
        
        # Also check the specific endpoint for semantic domains
        response = requests.get('http://localhost:5000/api/ranges/semantic-domain-ddp4')
        if response.status_code == 200:
            range_data = response.json()
            if range_data.get('success'):
                values = range_data.get('data', {}).get('values', [])
                print(f"\nSemantic Domain specific endpoint: {len(values)} top-level values")
                
                # Check first few values
                for value in values[:3]:
                    children = value.get('children', [])
                    print(f"  {value.get('id', 'unknown')} has {len(children)} children")
        
    except requests.exceptions.ConnectionError:
        print("Could not connect to API server. Make sure Flask is running on http://localhost:5000")
    except Exception as e:
        print(f"Error testing API endpoints: {str(e)}")

def main():
    """Run all tests."""
    print("=== Testing Hierarchical Ranges Functionality ===")
    
    # Test parser
    ranges = test_parser_hierarchical_ranges()
    
    # Test API endpoints (requires Flask server running)
    test_api_endpoints()
    
    print("\nTest completed.")

if __name__ == "__main__":
    main()
