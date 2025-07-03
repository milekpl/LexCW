#!/usr/bin/env python3
"""
Check if entries have homograph numbers in the database.
"""

from __future__ import annotations

import sys
import os

# Add the app to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dictionary_service import DictionaryService


def check_homograph_numbers():
    """Check if entries have homograph numbers."""
    app = create_app()
    with app.app_context():
        from app import injector
        dict_service = injector.get(DictionaryService)
        
        # Get some entries to check for homograph numbers
        entries, total = dict_service.search_entries("", limit=50)
        print(f'Found {len(entries)} entries (total: {total})')
        
        homograph_entries = []
        protestant_entries = []
        
        for entry in entries:
            # Check for homograph numbers
            if hasattr(entry, 'homograph_number') and entry.homograph_number:
                homograph_entries.append(entry)
                print(f'Entry {entry.id}: {entry.lexical_unit} - Homograph: {entry.homograph_number}')
            
            # Check for Protestant entries specifically
            if 'Protestant' in str(entry.lexical_unit):
                protestant_entries.append(entry)
                print(f'Protestant entry {entry.id}: {entry.lexical_unit} - Homograph: {getattr(entry, "homograph_number", "None")}')
        
        print(f'\nSummary:')
        print(f'- Total entries: {len(entries)}')
        print(f'- Entries with homograph numbers: {len(homograph_entries)}')
        print(f'- Protestant entries: {len(protestant_entries)}')
        
        # Check if we have any entries with the same lexical unit
        lexical_units = {}
        for entry in entries:
            lexical_unit_str = str(entry.lexical_unit)
            if lexical_unit_str not in lexical_units:
                lexical_units[lexical_unit_str] = []
            lexical_units[lexical_unit_str].append(entry)
        
        duplicates = {k: v for k, v in lexical_units.items() if len(v) > 1}
        print(f'- Entries with duplicate lexical units: {len(duplicates)}')
        
        for lexical_unit, entries_list in duplicates.items():
            print(f'  {lexical_unit}: {len(entries_list)} entries')
            for entry in entries_list:
                print(f'    - {entry.id}: homograph={getattr(entry, "homograph_number", "None")}')


if __name__ == '__main__':
    check_homograph_numbers()
