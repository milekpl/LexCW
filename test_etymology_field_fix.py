#!/usr/bin/env python3
"""
Test script to understand the etymology field duplication issue.
This will be removed after the fix is implemented.
"""

import tempfile
import os
from bs4 import BeautifulSoup


def test_etymology_fields_in_template():
    """Test to identify the duplicate etymology fields."""
    template_path = r"d:\Dokumenty\slownik-wielki\flask-app\app\templates\entry_form.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find all elements with name="etymology"
    etymology_fields = soup.find_all(attrs={'name': 'etymology'})
    
    print(f"Found {len(etymology_fields)} fields with name='etymology':")
    for i, field in enumerate(etymology_fields, 1):
        print(f"\nField {i}:")
        print(f"  Tag: {field.name}")
        print(f"  ID: {field.get('id', 'No ID')}")
        print(f"  Class: {field.get('class', 'No class')}")
        print(f"  Type: {field.get('type', 'N/A')}")
        print(f"  Context: {str(field)[:100]}...")
        
        # Find parent context
        parent = field.parent
        if parent:
            # Look for a label or heading near this field
            label = parent.find('label')
            heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if label:
                print(f"  Associated label: {label.get_text()}")
            if heading:
                print(f"  Near heading: {heading.get_text()}")
    
    # Also check for etymology-related IDs and containers
    etymology_containers = soup.find_all(id=lambda x: x and 'etymology' in x.lower())
    print(f"\nFound {len(etymology_containers)} containers with etymology-related IDs:")
    for container in etymology_containers:
        print(f"  ID: {container.get('id')}")
        print(f"  Tag: {container.name}")
        print(f"  Class: {container.get('class', 'No class')}")


if __name__ == "__main__":
    test_etymology_fields_in_template()
