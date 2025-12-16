#!/usr/bin/env python3
"""
Script to check if lexical relations in LIFT files are bidirectional.
This will examine if for every relation A -> B, there is also a relation B -> A.
"""

import xml.etree.ElementTree as ET
from collections import defaultdict


def extract_relations_from_file(file_path):
    """
    Extract all relations from a LIFT file.
    Handle both namespace and non-namespace versions.

    Returns:
        A dict with the structure: {entry_id: [(relation_type, target_ref), ...]}
    """
    relations = defaultdict(list)

    tree = ET.parse(file_path)
    root = tree.getroot()

    # Define namespace
    namespace = {'lift': 'http://fieldworks.sil.org/schemas/lift/0.13'}

    # Find all entry elements and their relations with namespace
    for entry in root.findall('.//lift:entry', namespace):
        entry_id = entry.get('id')
        if not entry_id:
            continue

        # Look for relations in senses
        for sense in entry.findall('.//lift:sense', namespace):
            for relation in sense.findall('lift:relation', namespace):
                rel_type = relation.get('type')
                ref = relation.get('ref')
                if rel_type and ref:
                    relations[entry_id].append((rel_type, ref))

        # Also look for relations directly on the entry (not just in senses)
        for relation in entry.findall('lift:relation', namespace):
            rel_type = relation.get('type')
            ref = relation.get('ref')
            if rel_type and ref:
                relations[entry_id].append((rel_type, ref))

    # If no relations found with namespace, try without namespace
    if not any(relations.values()):
        print("Trying without namespace...")
        relations = defaultdict(list)
        for entry in root.findall('.//entry'):  # No namespace
            entry_id = entry.get('id')
            if not entry_id:
                continue

            # Look for relations in senses
            for sense in entry.findall('.//sense'):  # No namespace
                for relation in sense.findall('relation'):  # No namespace
                    rel_type = relation.get('type')
                    ref = relation.get('ref')
                    if rel_type and ref:
                        relations[entry_id].append((rel_type, ref))

            # Also look for relations directly on the entry (not just in senses)
            for relation in entry.findall('relation'):  # No namespace
                rel_type = relation.get('type')
                ref = relation.get('ref')
                if rel_type and ref:
                    relations[entry_id].append((rel_type, ref))

    return relations


def check_bidirectional_relations(relations):
    """
    Check if relations are bidirectional.
    
    Args:
        relations: Dict of {entry_id: [(rel_type, target_ref), ...]}
        
    Returns:
        List of unidirectional relations that don't have reverse counterparts
    """
    all_relations = []
    # Collect all (source, type, target) tuples
    for source_id, rel_list in relations.items():
        for rel_type, target_id in rel_list:
            all_relations.append((source_id, rel_type, target_id))
    
    # Find relations that don't have reverses
    unidirectional = []
    for source, rel_type, target in all_relations:
        # Check if there's a reverse relation: target -> source with same type
        has_reverse = False
        for rev_source, rev_type, rev_target in all_relations:
            if rev_source == target and rev_type == rel_type and rev_target == source:
                has_reverse = True
                break
        
        if not has_reverse:
            unidirectional.append((source, rel_type, target))
    
    return unidirectional


def main():
    file_path = "sample_3/lift150322.lift"
    
    print(f"Analyzing relations in {file_path}...")
    relations = extract_relations_from_file(file_path)
    
    print(f"Found {sum(len(rel_list) for rel_list in relations.values())} total relations")
    print(f"Across {len(relations)} entries")
    
    # Print some statistics about relation types
    rel_types = {}
    for source_id, rel_list in relations.items():
        for rel_type, target_id in rel_list:
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
    
    print(f"\nRelation type counts:")
    for rel_type, count in sorted(rel_types.items()):
        print(f"  {rel_type}: {count}")
    
    unidirectional = check_bidirectional_relations(relations)
    
    print(f"\nFound {len(unidirectional)} unidirectional relations (no reverse found):")
    if len(unidirectional) <= 20:  # Print all if not too many
        for source, rel_type, target in unidirectional:
            print(f"  {source} --({rel_type})--> {target}")
    else:
        print("  (Too many to display - showing first 20)")
        for source, rel_type, target in unidirectional[:20]:
            print(f"  {source} --({rel_type})--> {target}")
    
    # Count bidirectional relations
    total_relations = len(all_relations) if 'all_relations' in locals() else sum(len(rel_list) for rel_list in relations.values())
    bidirectional_count = total_relations - len(unidirectional)
    
    print(f"\nTotal relations: {total_relations}")
    print(f"Bidirectional: {bidirectional_count}")
    print(f"Unidirectional: {len(unidirectional)}")
    print(f"Percentage bidirectional: {bidirectional_count/total_relations*100:.2f}%" if total_relations > 0 else "N/A")


if __name__ == "__main__":
    main()