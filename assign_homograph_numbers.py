#!/usr/bin/env python3
"""
Assign homograph numbers to existing entries that share the same lexical unit.
"""

from __future__ import annotations

import sys
import os
from collections import defaultdict
from typing import Dict, List

# Add the app to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry


def assign_homograph_numbers() -> None:
    """Assign homograph numbers to existing entries."""
    app = create_app()
    with app.app_context():
        from app import injector
        dict_service = injector.get(DictionaryService)
        
        print("Scanning all entries for homograph assignment...")
        
        # Get all entries
        all_entries: List[Entry] = []
        offset = 0
        limit = 100
        
        while True:
            entries, total = dict_service.search_entries("", limit=limit, offset=offset)
            all_entries.extend(entries)
            offset += limit
            if offset >= total:
                break
        
        print(f"Found {len(all_entries)} total entries")
        
        # Group entries by lexical unit
        lexical_unit_groups: Dict[str, List[Entry]] = defaultdict(list)
        
        for entry in all_entries:
            # Convert lexical unit to a consistent string for grouping
            if isinstance(entry.lexical_unit, dict):
                # Sort keys to ensure consistent grouping
                lexical_unit_str = str(sorted(entry.lexical_unit.items()))
            else:
                lexical_unit_str = str(entry.lexical_unit)
            
            lexical_unit_groups[lexical_unit_str].append(entry)
        
        # Find groups with multiple entries (homographs)
        homograph_groups = {k: v for k, v in lexical_unit_groups.items() if len(v) > 1}
        
        print(f"Found {len(homograph_groups)} groups with homographs:")
        
        updates_needed = []
        
        for lexical_unit_str, entries in homograph_groups.items():
            print(f"\nLexical unit: {lexical_unit_str}")
            print(f"  {len(entries)} entries need homograph numbers")
            
            # Sort entries by ID for consistent numbering
            entries.sort(key=lambda e: e.id)
            
            for i, entry in enumerate(entries, 1):
                current_homograph = getattr(entry, 'homograph_number', None)
                if current_homograph != i:
                    print(f"    {entry.id}: {current_homograph} -> {i}")
                    entry.homograph_number = i
                    updates_needed.append(entry)
                else:
                    print(f"    {entry.id}: already has correct homograph number {i}")
        
        if updates_needed:
            print(f"\nUpdating {len(updates_needed)} entries...")
            
            # Update entries in the database
            for entry in updates_needed:
                try:
                    dict_service.update_entry(entry)
                    print(f"✅ Updated {entry.id} with homograph number {entry.homograph_number}")
                except Exception as e:
                    print(f"❌ Failed to update {entry.id}: {e}")
            
            print(f"\n✅ Homograph number assignment complete!")
        else:
            print("\n✅ All entries already have correct homograph numbers!")
        
        # Summary
        print(f"\nSummary:")
        print(f"- Total entries: {len(all_entries)}")
        print(f"- Homograph groups: {len(homograph_groups)}")
        print(f"- Entries updated: {len(updates_needed)}")


if __name__ == '__main__':
    print("Assigning homograph numbers to existing entries...")
    assign_homograph_numbers()
