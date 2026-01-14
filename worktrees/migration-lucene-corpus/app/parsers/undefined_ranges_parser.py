"""Extension to LIFT parser for undefined ranges detection."""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict


class UndefinedRangesParser:
    """Parser extension to identify undefined ranges in LIFT files."""
    
    def __init__(self):
        """Initialize the undefined ranges parser."""
        self.logger = logging.getLogger(__name__)
    
    def identify_undefined_ranges(self, lift_xml: str, ranges_xml: Optional[str] = None, 
                                 list_xml: Optional[str] = None) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """
        Identify relation types and traits not defined in ranges.
        
        Args:
            lift_xml: LIFT XML string containing entries
            ranges_xml: Optional ranges XML string defining allowed values
            list_xml: Optional list.xml string for additional value mapping
        
        Returns:
            Tuple of (undefined_relations, undefined_traits)
            - undefined_relations: Set of relation types not in ranges
            - undefined_traits: Dict mapping trait names to sets of values not in ranges
        """
        undefined_relations = set()
        undefined_traits = defaultdict(set)
        
        # Parse LIFT for used relations and traits
        lift_tree = ET.fromstring(lift_xml)
        relations = set()
        traits = defaultdict(set)
        
        # Find all relation elements and extract their types
        for rel in lift_tree.iter():
            if rel.tag.endswith('relation'):
                rel_type = rel.get('type')
                if rel_type:
                    relations.add(rel_type)
            
            # Also look for trait elements
            if rel.tag.endswith('trait'):
                name = rel.get('name')
                value = rel.get('value')
                if name and value:
                    traits[name].add(value)
        
        # Parse ranges for defined elements
        if ranges_xml:
            defined_elements = self._parse_defined_elements(ranges_xml)
            
            # Find undefined relations
            for rel in relations:
                if rel not in defined_elements:
                    undefined_relations.add(rel)
            
            # Find undefined traits
            for trait_name, values in traits.items():
                if trait_name not in defined_elements:
                    undefined_traits[trait_name] = values
                else:
                    # Check which specific values are undefined
                    for value in values:
                        if value not in defined_elements[trait_name]:
                            undefined_traits[trait_name].add(value)
        else:
            # If no ranges provided, all used relations and traits are undefined
            undefined_relations = relations
            undefined_traits = dict(traits)
        
        return undefined_relations, dict(undefined_traits)
    
    def _parse_defined_elements(self, ranges_xml: str) -> Dict[str, Set[str]]:
        """
        Parse ranges XML to get defined elements.
        
        Args:
            ranges_xml: Ranges XML string
        
        Returns:
            Dict mapping range names to sets of defined element values
        """
        defined_elements = {}
        
        try:
            ranges_tree = ET.fromstring(ranges_xml)
            
            for range_elem in ranges_tree.iter():
                if range_elem.tag.endswith('range'):
                    range_id = range_elem.get('id')
                    if range_id:
                        defined_elements[range_id] = set()
                        
                        # Collect all range-element IDs within this range
                        for elem in range_elem.iter():
                            if elem.tag.endswith('range-element'):
                                elem_id = elem.get('id')
                                if elem_id:
                                    defined_elements[range_id].add(elem_id)
                                    
                                # Also check for value attribute
                                elem_value = elem.get('value')
                                if elem_value:
                                    defined_elements[range_id].add(elem_value)
        
        except ET.ParseError as e:
            self.logger.error(f"Error parsing ranges XML: {e}")
        
        return defined_elements