"""
LIFT Element Registry Service.

Provides access to LIFT element metadata for display profile configuration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataclasses import dataclass


@dataclass
class ElementMetadata:
    """Metadata for a LIFT element."""
    
    name: str
    display_name: str
    category: str
    description: str
    level: int
    parent: Optional[str]
    allowed_children: List[str]
    required: bool
    attributes: Dict[str, Any]
    default_css: str
    default_visibility: str
    typical_order: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "level": self.level,
            "parent": self.parent,
            "allowed_children": self.allowed_children,
            "required": self.required,
            "attributes": self.attributes,
            "default_css": self.default_css,
            "default_visibility": self.default_visibility,
            "typical_order": self.typical_order
        }


class LIFTElementRegistry:
    """Registry of LIFT element metadata."""
    
    def __init__(self, registry_path: Optional[Path] = None) -> None:
        """Initialize the element registry.
        
        Args:
            registry_path: Path to the LIFT elements JSON file.
                          Defaults to app/data/lift_elements.json
        """
        if registry_path is None:
            # Default to app/data/lift_elements.json
            app_dir = Path(__file__).parent.parent
            registry_path = app_dir / "data" / "lift_elements.json"
        
        self.registry_path = registry_path
        self._elements: Dict[str, ElementMetadata] = {}
        self._categories: Dict[str, Dict[str, str]] = {}
        self._visibility_options: List[Dict[str, str]] = []
        self._relation_types: List[str] = []
        self._note_types: List[str] = []
        self._grammatical_categories: List[str] = []
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load the element registry from JSON file."""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"LIFT element registry not found at {self.registry_path}")
        
        with open(self.registry_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Load elements
        for element_data in data.get("elements", []):
            element = ElementMetadata(
                name=element_data["name"],
                display_name=element_data["display_name"],
                category=element_data["category"],
                description=element_data["description"],
                level=element_data["level"],
                parent=element_data["parent"],
                allowed_children=element_data["allowed_children"],
                required=element_data["required"],
                attributes=element_data["attributes"],
                default_css=element_data["default_css"],
                default_visibility=element_data["default_visibility"],
                typical_order=element_data["typical_order"]
            )
            self._elements[element.name] = element
        
        # Load metadata
        self._categories = data.get("categories", {})
        self._visibility_options = data.get("visibility_options", [])
        self._relation_types = data.get("relation_types", [])
        self._note_types = data.get("note_types", [])
        self._grammatical_categories = data.get("grammatical_categories", [])
    
    def get_element(self, name: str) -> Optional[ElementMetadata]:
        """Get metadata for a specific element.
        
        Args:
            name: Element name (e.g., 'lexical-unit')
        
        Returns:
            ElementMetadata or None if not found
        """
        return self._elements.get(name)
    
    def get_all_elements(self) -> List[ElementMetadata]:
        """Get all element metadata.
        
        Returns:
            List of all ElementMetadata objects
        """
        return list(self._elements.values())
    
    def get_elements_by_category(self, category: str) -> List[ElementMetadata]:
        """Get all elements in a specific category.
        
        Args:
            category: Category name (e.g., 'entry', 'sense')
        
        Returns:
            List of ElementMetadata objects in the category
        """
        return [elem for elem in self._elements.values() if elem.category == category]
    
    def get_entry_level_elements(self) -> List[ElementMetadata]:
        """Get elements that can appear directly under entry.
        
        Returns:
            List of entry-level ElementMetadata objects
        """
        return [elem for elem in self._elements.values() if elem.parent == "entry"]
    
    def get_sense_level_elements(self) -> List[ElementMetadata]:
        """Get elements that can appear within a sense.
        
        Returns:
            List of sense-level ElementMetadata objects
        """
        return [elem for elem in self._elements.values() if elem.parent == "sense"]
    
    def get_displayable_elements(self) -> List[ElementMetadata]:
        """Get elements suitable for display configuration.
        
        Excludes purely structural elements like 'form' and 'text'.
        
        Returns:
            List of displayable ElementMetadata objects
        """
        # Elements that are typically configured in display profiles
        displayable = [
            "lexical-unit", "citation", "pronunciation", "variant",
            "sense", "subsense", "grammatical-info", "gloss", "definition",
            "example", "reversal", "illustration", "relation", "etymology",
            "note", "field", "trait"
        ]
        return [self._elements[name] for name in displayable if name in self._elements]
    
    def get_categories(self) -> Dict[str, Dict[str, str]]:
        """Get all element categories.
        
        Returns:
            Dictionary of category metadata
        """
        return self._categories
    
    def get_visibility_options(self) -> List[Dict[str, str]]:
        """Get available visibility options.
        
        Returns:
            List of visibility option definitions
        """
        return self._visibility_options
    
    def get_relation_types(self) -> List[str]:
        """Get available relation types.
        
        Returns:
            List of relation type names
        """
        return self._relation_types
    
    def get_note_types(self) -> List[str]:
        """Get available note types.
        
        Returns:
            List of note type names
        """
        return self._note_types
    
    def get_grammatical_categories(self) -> List[str]:
        """Get available grammatical categories.
        
        Returns:
            List of grammatical category names
        """
        return self._grammatical_categories
    
    def create_default_profile_elements(self) -> List[Dict[str, Any]]:
        """Create default element configuration for a new profile.
        
        Returns:
            List of element configurations with sensible defaults
        """
        # Comprehensive list of ALL LIFT elements for complete rendering
        # Format: (element_name, display_mode, visibility, css_class_override)
        default_elements = [
            # Entry-level elements (order 10-90)
            ("lexical-unit", "inline", "always", None),
            ("citation", "inline", "if-content", None),
            ("pronunciation", "inline", "if-content", None),
            ("variant", "inline", "if-content", None),
            
            # Sense structure (order 100-190)
            ("sense", "block", "if-content", None),
            ("subsense", "block", "if-content", None),
            
            # Sense content (order 200-290)
            ("grammatical-info", "inline", "if-content", None),
            ("gloss", "inline", "if-content", None),
            ("definition", "inline", "if-content", None),
            
            # Examples and translations (order 300-390)
            ("example", "block", "if-content", None),
            ("translation", "block", "if-content", None),
            
            # Additional sense elements (order 400-490)
            ("reversal", "inline", "if-content", None),
            ("illustration", "block", "if-content", None),
            
            # Metadata and extensibility (order 500-590)
            ("note", "block", "if-content", None),
            ("field", "block", "if-content", "custom-field"),
            ("trait", "inline", "if-content", None),  # Traits included per user request
            ("etymology", "block", "if-content", None),
            ("relation", "inline", "if-content", None),
        ]
        
        elements = []
        for i, (elem_name, display_mode, visibility, css_override) in enumerate(default_elements, start=1):
            elem = self.get_element(elem_name)
            if elem:
                elements.append({
                    "lift_element": elem.name,
                    "display_order": i * 10,  # Use 10, 20, 30... to allow insertion
                    "css_class": css_override if css_override else elem.default_css,
                    "prefix": "",
                    "suffix": "",
                    "visibility": visibility,
                    "config": {"display_mode": display_mode}
                })
        
        return elements
    
    def validate_element_config(self, element_config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate an element configuration.
        
        Args:
            element_config: Element configuration dictionary
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if "lift_element" not in element_config:
            return False, "Missing required field: lift_element"
        
        # Check element exists
        elem_name = element_config["lift_element"]
        if elem_name not in self._elements:
            return False, f"Unknown LIFT element: {elem_name}"
        
        # Check visibility if provided
        if "visibility" in element_config:
            valid_visibility = {opt["value"] for opt in self._visibility_options}
            if element_config["visibility"] not in valid_visibility:
                return False, f"Invalid visibility: {element_config['visibility']}"
        
        return True, None
    
    def get_element_hierarchy(self) -> Dict[str, List[str]]:
        """Get the parent-child hierarchy of elements.
        
        Returns:
            Dictionary mapping parent element names to lists of child element names
        """
        hierarchy: Dict[str, List[str]] = {}
        
        for element in self._elements.values():
            if element.parent:
                if element.parent not in hierarchy:
                    hierarchy[element.parent] = []
                hierarchy[element.parent].append(element.name)
        
        return hierarchy
    
    def export_registry_json(self) -> str:
        """Export registry as JSON string for API responses.
        
        Returns:
            JSON string of registry data
        """
        data = {
            "elements": [elem.to_dict() for elem in self._elements.values()],
            "categories": self._categories,
            "visibility_options": self._visibility_options,
            "relation_types": self._relation_types,
            "note_types": self._note_types,
            "grammatical_categories": self._grammatical_categories
        }
        return json.dumps(data, indent=2)
