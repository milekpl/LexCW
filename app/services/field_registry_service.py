#!/usr/bin/env python3
"""
Field Registry Service for Query Builder.

Provides field discovery and autocomplete functionality for the query builder UI.
Aggregates fields from:
- LIFT element registry (standard LIFT fields)
- Database ranges (controlled vocabularies like parts of speech, semantic domains)
- Discovered custom fields/traits from dictionary data

Usage:
    service = FieldRegistryService()
    fields = service.get_fields()
    # Returns: [{"label": "Headword", "path": "lexical_unit", "category": "Entry"}, ...]
"""

from __future__ import annotations

from typing import Dict, Any, List, Set, Optional
import logging
import re
from functools import lru_cache

from app.services.ranges_service import STANDARD_RANGE_METADATA

logger = logging.getLogger(__name__)


class FieldRegistryService:
    """
    Service for discovering and managing query-builder searchable fields.
    
    Aggregates fields from multiple sources to provide a unified list
    of searchable fields with human-friendly labels.
    """
    
    # Standard LIFT fields with their categories
    LIFT_REGISTRY_FIELDS: List[Dict[str, str]] = [
        # Entry-level fields
        {"label": "Headword", "path": "lexical_unit", "category": "Entry"},
        {"label": "Citation Form", "path": "citation_forms", "category": "Entry"},
        {"label": "Pronunciation", "path": "pronunciations", "category": "Entry"},
        {"label": "Part of Speech", "path": "grammatical_info", "category": "Entry"},
        {"label": "Morph Type", "path": "morph_type", "category": "Entry"},
        {"label": "Note (General)", "path": "notes.general", "category": "Entry"},
        {"label": "Note (Grammar)", "path": "notes.grammar", "category": "Entry"},
        {"label": "Note (Anthropology)", "path": "notes.anthropology", "category": "Entry"},
        {"label": "Note (Bibliography)", "path": "notes.bibliography", "category": "Entry"},
        {"label": "Note (Sociolinguistics)", "path": "notes.sociolinguistics", "category": "Entry"},
        {"label": "Etymology", "path": "etymologies", "category": "Entry"},
        {"label": "Variant", "path": "variants", "category": "Entry"},
        {"label": "Relation", "path": "relations", "category": "Entry"},
        {"label": "Entry ID", "path": "id", "category": "Entry"},
        {"label": "Date Created", "path": "date_created", "category": "Entry"},
        {"label": "Date Modified", "path": "date_modified", "category": "Entry"},
        
        # Sense-level fields
        {"label": "Sense Definition", "path": "senses.definition", "category": "Sense"},
        {"label": "Sense Gloss", "path": "senses.gloss", "category": "Sense"},
        {"label": "Sense Note", "path": "senses.note", "category": "Sense"},
        {"label": "Sense Semantic Domain", "path": "senses.semantic_domain", "category": "Sense"},
        {"label": "Sense Grammatical Info", "path": "senses.grammatical_info", "category": "Sense"},
        {"label": "Sense Scientific Name", "path": "senses.scientific_name", "category": "Sense"},
        {"label": "Sense Anthropology Note", "path": "senses.anthropology_notes", "category": "Sense"},
        {"label": "Sense Usage Note", "path": "senses.usage_notes", "category": "Sense"},
        {"label": "Sense Sociolinguistics Note", "path": "senses.sociolinguistics_notes", "category": "Sense"},
        {"label": "Sense Reversal", "path": "senses.reversals", "category": "Sense"},
        
        # Example-level fields
        {"label": "Example Form", "path": "senses.examples.form", "category": "Example"},
        {"label": "Example Translation", "path": "senses.examples.translation", "category": "Example"},
        {"label": "Example Reference", "path": "senses.examples.reference", "category": "Example"},
    ]
    
    # Range-based field paths (these map to ranges that have controlled vocabularies)
    RANGE_FIELD_PATHS: Dict[str, str] = {
        'grammatical-info': 'grammatical_info',
        'semantic-domain-ddp4': 'trait[semantic-domain-ddp4]',
        'lexical-relation': 'relation.type',
        'variant-type': 'variant.type',
        'note-type': 'note',
        'usage-type': 'usage_type',
        'complex-form-type': 'trait[complex-form-type]',
        'morph-type': 'morph_type',
        'status': 'status',
        'location': 'location',
    }
    
    def __init__(self, ranges_service=None):
        """
        Initialize the field registry service.
        
        Args:
            ranges_service: Optional RangesService instance for fetching dynamic ranges
        """
        self.ranges_service = ranges_service
        self.logger = logging.getLogger(__name__)
    
    @lru_cache(maxsize=1)
    def get_fields(self, project_id: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get all available searchable fields.
        
        Aggregates fields from:
        - LIFT registry (standard fields)
        - Database ranges (controlled vocabularies)
        - Discovered custom fields (from project data)
        
        Args:
            project_id: Optional project ID to fetch project-specific ranges
            
        Returns:
            List of field definitions with label, path, and category
        """
        fields: List[Dict[str, str]] = []
        seen_paths: Set[str] = set()
        
        # 1. Add LIFT registry fields
        lift_fields = self._load_registry_fields()
        for field in lift_fields:
            fields.append(field)
            seen_paths.add(field['path'])
        
        # 2. Add range-based fields
        range_fields = self._load_range_fields(project_id)
        for field in range_fields:
            if field['path'] not in seen_paths:
                fields.append(field)
                seen_paths.add(field['path'])
        
        # 3. Add discovered custom fields
        discovered_fields = self._load_discovered_fields(project_id)
        for field in discovered_fields:
            if field['path'] not in seen_paths:
                fields.append(field)
                seen_paths.add(field['path'])
        
        # Sort by label for consistent ordering
        fields.sort(key=lambda f: f['label'].lower())
        
        return fields
    
    def _load_registry_fields(self) -> List[Dict[str, str]]:
        """
        Load standard LIFT registry fields.
        
        Returns:
            List of standard LIFT field definitions
        """
        return self.LIFT_REGISTRY_FIELDS.copy()
    
    def _load_range_fields(self, project_id: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Load fields from controlled vocabularies (ranges).
        
        These are fields that have predefined values from the database.
        
        Args:
            project_id: Optional project ID to fetch project-specific ranges
            
        Returns:
            List of range-based field definitions
        """
        fields: List[Dict[str, str]] = []
        
        # Add standard range metadata as fields
        for range_id, metadata in STANDARD_RANGE_METADATA.items():
            label = metadata.get('label', range_id)
            
            # Map to appropriate field path
            field_path = self.RANGE_FIELD_PATHS.get(range_id, range_id.replace('-', '_'))
            
            # Determine category based on range type
            category = self._get_category_for_range(range_id)
            
            fields.append({
                "label": f"Range: {label}",
                "path": field_path,
                "category": category
            })
        
        # If we have a ranges service, fetch dynamic ranges
        if self.ranges_service and project_id:
            try:
                dynamic_ranges = self._fetch_dynamic_ranges(project_id)
                for range_data in dynamic_ranges:
                    path = range_data.get('path')
                    if path and path not in [f['path'] for f in fields]:
                        fields.append(range_data)
            except Exception as e:
                self.logger.warning(f"Failed to fetch dynamic ranges: {e}")
        
        return fields
    
    def _load_discovered_fields(self, project_id: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Load discovered custom fields from dictionary data.
        
        These are fields found by scanning the dictionary data
        that aren't in the standard LIFT schema.
        
        Args:
            project_id: Optional project ID to scan for custom fields
            
        Returns:
            List of discovered custom field definitions
        """
        fields: List[Dict[str, str]] = []
        
        # Common custom fields found in FieldWorks/LIFT data
        common_custom_fields = [
            {"label": "Custom: Exemplar", "path": "field[exemplar]", "category": "Custom Field"},
            {"label": "Custom: Scientific Name", "path": "field[scientific-name]", "category": "Custom Field"},
            {"label": "Custom: Literal Meaning", "path": "field[literal-meaning]", "category": "Custom Field"},
            {"label": "Trait: Morph Type", "path": "trait[morph-type]", "category": "Trait"},
            {"label": "Trait: Complex Form Type", "path": "trait[complex-form-type]", "category": "Trait"},
            {"label": "Trait: Semantic Domain", "path": "trait[semantic-domain-ddp4]", "category": "Trait"},
        ]
        
        fields.extend(common_custom_fields)
        
        # TODO: If we have dictionary service access, scan for actual custom fields
        
        return fields
    
    def _fetch_dynamic_ranges(self, project_id: int) -> List[Dict[str, str]]:
        """
        Fetch dynamic ranges from the ranges service.
        
        Args:
            project_id: Project ID to fetch ranges for
            
        Returns:
            List of range-based field definitions
        """
        fields: List[Dict[str, str]] = []
        
        try:
            ranges = self.ranges_service.get_ranges()
            
            for range_id, range_data in ranges.items():
                if range_id in STANDARD_RANGE_METADATA:
                    # Already handled in standard metadata
                    continue
                
                label = range_data.get('label', range_id)
                category = "Custom Range"
                
                fields.append({
                    "label": f"Custom Range: {label}",
                    "path": f"trait[{range_id}]",
                    "category": category
                })
        
        except Exception as e:
            self.logger.warning(f"Error fetching ranges: {e}")
        
        return fields
    
    def _get_category_for_range(self, range_id: str) -> str:
        """
        Determine the category for a range field.
        
        Args:
            range_id: The range identifier
            
        Returns:
            Category string for the field
        """
        # Map ranges to appropriate categories
        category_map = {
            'grammatical-info': 'Sense/Part of Speech',
            'semantic-domain-ddp4': 'Sense/Trait',
            'lexical-relation': 'Entry/Relation',
            'variant-type': 'Entry/Variant',
            'note-type': 'Entry/Note',
            'etymology': 'Entry/Etymology',
            'morph-type': 'Entry/Morphology',
            'complex-form-type': 'Entry/Complex Form',
            'usage-type': 'Sense/Usage',
            'status': 'Entry/Status',
            'location': 'Entry/Location',
            'anthro-code': 'Entry/Anthropology',
            'Publications': 'Entry/Publication',
        }
        
        return category_map.get(range_id, 'Range')
    
    def resolve_field_path(self, path: str) -> str:
        """
        Resolve a field path to LIFT XPath notation.
        
        Converts user-friendly paths to XPath fragments for searching.
        
        Examples:
            lexical_unit -> lexical-unit
            senses.gloss -> sense/gloss
            senses.examples.form -> sense/example/form
            trait[semantic-domain-ddp4] -> trait[@name='semantic-domain-ddp4']/@value
        
        Args:
            path: User-friendly field path
            
        Returns:
            LIFT XPath fragment
        """
        # Handle bracket notation for traits
        if '[' in path and ']' in path:
            match = re.match(r'(.+)\[([^\]]+)\](.*)$', path)
            if match:
                base, key, rest = match.groups()
                
                # Determine if it's a trait or field
                if 'trait' in base:
                    if rest == '/@value' or rest == '':
                        return f"{base}[@name='{key}']/@value"
                    else:
                        return f"{base}[@name='{key}']{rest}"
                elif 'field' in base:
                    return f"{base}[@type='{key}']{rest}"
                elif 'note' in base:
                    return f"{base}[@type='{key}']{rest}"
        
        # Handle dot notation to XPath
        path = path.replace('.', '/')
        
        # Convert underscores to hyphens (LIFT convention)
        path = path.replace('_', '-')
        
        # Handle special pluralizations
        path = path.replace('senses/', 'sense/')
        path = path.replace('examples/', 'example/')
        path = path.replace('etymologies/', 'etymology/')
        path = path.replace('variants/', 'variant/')
        path = path.replace('relations/', 'relation/')
        path = path.replace('pronunciations/', 'pronunciation/')
        path = path.replace('citation-forms/', 'citation/')
        
        return path
    
    def search_fields(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Search for fields matching a query string.
        
        Args:
            query: Search string to match against labels and paths
            limit: Maximum number of results to return
            
        Returns:
            Filtered and limited list of field definitions
        """
        all_fields = self.get_fields()
        query_lower = query.lower()
        
        # Filter fields matching the query
        matching = [
            field for field in all_fields
            if query_lower in field['label'].lower() 
            or query_lower in field['path'].lower()
            or query_lower in field['category'].lower()
        ]
        
        # Return limited results
        return matching[:limit]


# Global singleton instance
_field_registry_service: Optional[FieldRegistryService] = None


def get_field_registry_service(ranges_service=None) -> FieldRegistryService:
    """Get the global field registry service instance."""
    global _field_registry_service
    if _field_registry_service is None:
        _field_registry_service = FieldRegistryService(ranges_service)
    return _field_registry_service
