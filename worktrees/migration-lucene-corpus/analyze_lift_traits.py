#!/usr/bin/env python3
"""
Script to analyze LIFT file for traits not defined in ranges file,
and collate possible values from list.xml.
"""

import xml.etree.ElementTree as ET
import sys
from collections import defaultdict

def parse_lift_file(lift_path):
    """Parse LIFT file to extract all trait names and values, and relation types."""
    tree = ET.parse(lift_path)
    root = tree.getroot()

    traits = defaultdict(set)
    relation_types = set()

    # Find all trait elements
    for trait in root.iter('trait'):
        name = trait.get('name')
        value = trait.get('value')
        if name and value:
            traits[name].add(value)

    # Find all relation types
    for relation in root.iter('relation'):
        rel_type = relation.get('type')
        if rel_type:
            relation_types.add(rel_type)

    return traits, relation_types

def parse_ranges_file(ranges_path):
    """Parse ranges file to extract defined range ids and element ids."""
    tree = ET.parse(ranges_path)
    root = tree.getroot()

    ranges = set()
    for range_elem in root.iter('range'):
        range_id = range_elem.get('id')
        if range_id:
            ranges.add(range_id)
        # Also add range-element ids
        for elem in range_elem.iter('range-element'):
            elem_id = elem.get('id')
            if elem_id:
                ranges.add(elem_id)

    return ranges

def parse_list_xml(list_path):
    """Parse list.xml to extract lists and their items."""
    tree = ET.parse(list_path)
    root = tree.getroot()

    lists = {}
    for list_elem in root.iter('list'):
        name_elem = list_elem.find('name')
        if name_elem is not None:
            name = name_elem.find('str').text if name_elem.find('str') is not None else None
            if name:
                items = []
                for item in list_elem.iter('letitem'):
                    item_name = item.find('name')
                    if item_name is not None:
                        str_elem = item_name.find('str')
                        if str_elem is not None and str_elem.text:
                            items.append(str_elem.text)
                if items:
                    lists[name] = items

    return lists

def main():
    if len(sys.argv) != 4:
        print("Usage: python analyze_lift_traits.py <lift_file> <ranges_file> <list_xml>")
        sys.exit(1)

    lift_path = sys.argv[1]
    ranges_path = sys.argv[2]
    list_path = sys.argv[3]

    print("Parsing LIFT file...")
    lift_traits, relation_types = parse_lift_file(lift_path)
    print(f"Found {len(lift_traits)} unique trait names and {len(relation_types)} relation types in LIFT file")

    print("Parsing ranges file...")
    defined_ranges = parse_ranges_file(ranges_path)
    print(f"Found {len(defined_ranges)} defined ranges")

    print("Parsing list.xml...")
    lists = parse_list_xml(list_path)
    print(f"Found {len(lists)} lists in list.xml")

    # Identify undefined traits
    undefined_traits = {}
    for trait_name, values in lift_traits.items():
        if trait_name not in defined_ranges:
            undefined_traits[trait_name] = values

    # Identify undefined relation types
    undefined_relations = set()
    for rel_type in relation_types:
        if rel_type not in defined_ranges:
            undefined_relations.add(rel_type)

    print(f"\nUndefined traits: {len(undefined_traits)}")
    print(f"Undefined relation types: {len(undefined_relations)}")
    if undefined_relations:
        print(f"Undefined relations: {sorted(undefined_relations)}")

    # Try to match with lists
    for trait_name, values in undefined_traits.items():
        print(f"\nTrait: {trait_name}")
        print(f"Values used in LIFT: {sorted(values)}")

        # Look for matching list (case insensitive)
        matching_list = None
        for list_name, list_items in lists.items():
            if trait_name.lower().replace('-', ' ') in list_name.lower() or list_name.lower().replace(' ', '-') in trait_name.lower():
                matching_list = (list_name, list_items)
                break

        if matching_list:
            list_name, list_items = matching_list
            print(f"Matching list: {list_name}")
            print(f"Possible values: {sorted(list_items)}")

            # Check if all used values are in the list
            missing = values - set(list_items)
            if missing:
                print(f"WARNING: Values not in list: {sorted(missing)}")
        else:
            print("No matching list found")

if __name__ == "__main__":
    main()