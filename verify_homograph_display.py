#!/usr/bin/env python3
"""
Quick verification script to test homograph number parsing and display from the actual LIFT file.
This will parse the sample LIFT file and show how homograph numbers are handled.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from parsers.lift_parser import LIFTParser

def main():
    """Parse the sample LIFT file and display entries with homograph numbers."""
    
    # Path to the sample LIFT file
    lift_file_path = Path(__file__).parent / "sample-lift-file" / "sample-lift-file.lift"
    
    if not lift_file_path.exists():
        print(f"Error: LIFT file not found at {lift_file_path}")
        return
    
    print("=== Homograph Number Verification ===")
    print(f"Parsing LIFT file: {lift_file_path}")
    print()
    
    # Parse the LIFT file
    parser = LIFTParser()
    entries = parser.parse_file(str(lift_file_path))
    
    # Find entries with homograph numbers
    homograph_entries = [entry for entry in entries if entry.homograph_number is not None]
    
    if not homograph_entries:
        print("No entries with homograph numbers found.")
        return
    
    print(f"Found {len(homograph_entries)} entries with homograph numbers:")
    print()
    
    # Group by lexical unit to show homographs together
    from collections import defaultdict
    homograph_groups = defaultdict(list)
    
    for entry in homograph_entries:
        if isinstance(entry.lexical_unit, dict):
            # Get the first available lexical unit value
            lexical_form = next(iter(entry.lexical_unit.values()), "")
        else:
            lexical_form = str(entry.lexical_unit or "")
        
        homograph_groups[lexical_form].append(entry)
    
    # Display homograph groups
    for lexical_form, group_entries in sorted(homograph_groups.items()):
        print(f"'{lexical_form}' homographs:")
        
        for entry in sorted(group_entries, key=lambda e: e.homograph_number or 0):
            homograph_display = f"{lexical_form}"
            if entry.homograph_number:
                # Use Unicode subscript characters for display
                subscript_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
                subscript = str(entry.homograph_number).translate(subscript_map)
                homograph_display += subscript
            
            print(f"  - {homograph_display} (ID: {entry.id}, Order: {entry.homograph_number})")
            
            # Show first sense definition if available
            if entry.senses and len(entry.senses) > 0:
                first_sense = entry.senses[0]
                if hasattr(first_sense, 'definition') and first_sense.definition:
                    if isinstance(first_sense.definition, dict):
                        def_text = next(iter(first_sense.definition.values()), "")
                    else:
                        def_text = str(first_sense.definition)
                    print(f"    Definition: {def_text[:80]}{'...' if len(def_text) > 80 else ''}")
        print()
    
    print("=== Verification Complete ===")
    print()
    print("Key findings:")
    print("1. Homograph numbers are parsed from the 'order' attribute in LIFT XML")
    print("2. They are displayed with Unicode subscript characters")
    print("3. Entries are grouped by lexical form to show homograph relationships")

if __name__ == "__main__":
    main()
