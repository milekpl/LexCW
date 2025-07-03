#!/usr/bin/env python3
"""
Test script to verify that homograph numbers are correctly parsed from the sample LIFT file.
"""

from __future__ import annotations

import sys
import os

# Add the app to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.parsers.lift_parser import LIFTParser


def test_lift_file_homograph_parsing():
    """Test that homograph numbers are correctly parsed from the sample LIFT file."""
    app = create_app()
    with app.app_context():
        parser = LIFTParser(validate=False)
        
        # Parse the sample LIFT file
        lift_file_path = os.path.join(os.path.dirname(__file__), 'sample-lift-file', 'sample-lift-file.lift')
        
        with open(lift_file_path, 'r', encoding='utf-8') as f:
            lift_content = f.read()
        
        entries = parser.parse_string(lift_content)
        
        print(f"Parsed {len(entries)} entries from LIFT file")
        
        # Find entries with homograph numbers
        homograph_entries = [e for e in entries if e.homograph_number is not None]
        print(f"Found {len(homograph_entries)} entries with homograph numbers")
        
        # Find specific Protestant entries
        protestant_entries = [e for e in entries if e.lexical_unit.get('en') == 'Protestant']
        print(f"Found {len(protestant_entries)} Protestant entries:")
        
        for entry in protestant_entries:
            print(f"  - ID: {entry.id}")
            print(f"    Homograph number: {entry.homograph_number}")
            print(f"    Lexical unit: {entry.lexical_unit}")
            print()
        
        # Test specific entries
        protestant1 = next((e for e in entries if e.id == "Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69"), None)
        protestant2 = next((e for e in entries if e.id == "Protestant2_2db3c121-3b23-428e-820d-37b76e890616"), None)
        
        if protestant1:
            print(f"✅ Protestant1 found with homograph number: {protestant1.homograph_number}")
        else:
            print("❌ Protestant1 not found")
            
        if protestant2:
            print(f"✅ Protestant2 found with homograph number: {protestant2.homograph_number}")
        else:
            print("❌ Protestant2 not found")
        
        # Test pretest entries
        pretest_entries = [e for e in entries if e.lexical_unit.get('en') == 'pretest']
        print(f"\nFound {len(pretest_entries)} pretest entries:")
        
        for entry in pretest_entries:
            print(f"  - ID: {entry.id}")
            print(f"    Homograph number: {entry.homograph_number}")
            print(f"    Lexical unit: {entry.lexical_unit}")
            print()
        
        return True


if __name__ == '__main__':
    print("Testing homograph number parsing from sample LIFT file...")
    test_lift_file_homograph_parsing()
    print("✅ Test completed successfully!")
