#!/usr/bin/env python3
"""
Test script to verify the architectural constraint: variant entries must not have senses.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.services.dictionary_service import DictionaryService

def test_variant_entries_have_no_senses():
    """Test that variant entries do not have senses."""
    app = create_app()
    
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        
        # Find all entries that have variant relations (outgoing)
        # Use search with empty query to get all entries
        all_entries, total = dict_service.search_entries("", limit=10000)
        variant_entries = []
        
        for entry in all_entries:
            if hasattr(entry, 'variant_relations') and entry.variant_relations():
                variant_entries.append(entry)
        
        print(f"Found {len(variant_entries)} entries with variant relations:")
        
        violations = []
        for entry in variant_entries:
            senses_count = len(entry.senses) if entry.senses else 0
            print(f"  - {entry.id}: {senses_count} senses")
            
            if senses_count > 0:
                # Extract refs properly as dicts
                variant_refs = []
                for rel in entry.variant_relations():
                    if isinstance(rel, dict):
                        variant_refs.append(rel.get('ref', 'unknown'))
                    else:
                        variant_refs.append(str(rel))
                
                violations.append({
                    'entry_id': entry.id,
                    'senses_count': senses_count,
                    'variant_relations': variant_refs
                })
        
        if violations:
            print(f"\n❌ ARCHITECTURAL CONSTRAINT VIOLATION: {len(violations)} variant entries have senses:")
            for violation in violations:
                print(f"  - Entry '{violation['entry_id']}' has {violation['senses_count']} senses")
                print(f"    Variants of: {violation['variant_relations']}")
        else:
            print(f"\n✅ All variant entries correctly have no senses")
        
        return violations

if __name__ == '__main__':
    violations = test_variant_entries_have_no_senses()
    if violations:
        sys.exit(1)
    else:
        sys.exit(0)
