"""
Unit tests for LIFT Element Registry Service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.services.lift_element_registry import ElementMetadata, LIFTElementRegistry

if TYPE_CHECKING:
    pass


@pytest.fixture
def registry() -> LIFTElementRegistry:
    """Create a LIFT element registry instance."""
    return LIFTElementRegistry()


class TestLIFTElementRegistry:
    """Test LIFT Element Registry functionality."""

    def test_registry_loads_successfully(self, registry: LIFTElementRegistry) -> None:
        """Test that the registry loads from JSON file."""
        assert registry is not None
        elements = registry.get_all_elements()
        assert len(elements) > 0

    def test_get_element_by_name(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving a specific element by name."""
        lexical_unit = registry.get_element("lexical-unit")
        
        assert lexical_unit is not None
        assert lexical_unit.name == "lexical-unit"
        assert lexical_unit.display_name == "Lexical Unit / Headword"
        assert lexical_unit.category == "entry"
        assert lexical_unit.required is True

    def test_get_nonexistent_element(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving an element that doesn't exist."""
        result = registry.get_element("nonexistent-element")
        assert result is None

    def test_get_all_elements(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving all elements."""
        elements = registry.get_all_elements()
        
        assert len(elements) > 20  # Should have many elements
        assert all(isinstance(elem, ElementMetadata) for elem in elements)
        
        # Check some key elements exist
        names = {elem.name for elem in elements}
        assert "entry" in names
        assert "lexical-unit" in names
        assert "sense" in names
        assert "pronunciation" in names

    def test_get_elements_by_category(self, registry: LIFTElementRegistry) -> None:
        """Test filtering elements by category."""
        entry_elements = registry.get_elements_by_category("entry")
        
        assert len(entry_elements) > 0
        assert all(elem.category == "entry" for elem in entry_elements)
        
        # Check expected entry-level elements
        names = {elem.name for elem in entry_elements}
        assert "lexical-unit" in names
        assert "pronunciation" in names

    def test_get_entry_level_elements(self, registry: LIFTElementRegistry) -> None:
        """Test getting elements that appear under entry."""
        entry_elements = registry.get_entry_level_elements()
        
        assert len(entry_elements) > 0
        assert all(elem.parent == "entry" for elem in entry_elements)
        
        names = {elem.name for elem in entry_elements}
        assert "lexical-unit" in names
        assert "sense" in names
        assert "pronunciation" in names

    def test_get_sense_level_elements(self, registry: LIFTElementRegistry) -> None:
        """Test getting elements that appear within sense."""
        sense_elements = registry.get_sense_level_elements()
        
        assert len(sense_elements) > 0
        assert all(elem.parent == "sense" for elem in sense_elements)
        
        names = {elem.name for elem in sense_elements}
        assert "grammatical-info" in names
        assert "definition" in names
        assert "example" in names

    def test_get_displayable_elements(self, registry: LIFTElementRegistry) -> None:
        """Test getting elements suitable for display profiles."""
        displayable = registry.get_displayable_elements()
        
        assert len(displayable) > 0
        
        names = {elem.name for elem in displayable}
        # Should include main displayable elements
        assert "lexical-unit" in names
        assert "pronunciation" in names
        assert "sense" in names
        
        # Should not include purely structural elements
        assert "form" not in names
        assert "text" not in names

    def test_get_categories(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving element categories."""
        categories = registry.get_categories()
        
        assert isinstance(categories, dict)
        assert len(categories) > 0
        
        # Check expected categories
        assert "entry" in categories
        assert "sense" in categories
        assert "basic" in categories

    def test_get_visibility_options(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving visibility options."""
        options = registry.get_visibility_options()
        
        assert isinstance(options, list)
        assert len(options) > 0
        
        values = {opt["value"] for opt in options}
        assert "always" in values
        assert "if-content" in values
        assert "never" in values

    def test_get_relation_types(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving relation types."""
        relation_types = registry.get_relation_types()
        
        assert isinstance(relation_types, list)
        assert len(relation_types) > 0
        assert "synonym" in relation_types
        assert "antonym" in relation_types

    def test_get_note_types(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving note types."""
        note_types = registry.get_note_types()
        
        assert isinstance(note_types, list)
        assert len(note_types) > 0
        assert "grammar" in note_types
        assert "encyclopedic" in note_types

    def test_get_grammatical_categories(self, registry: LIFTElementRegistry) -> None:
        """Test retrieving grammatical categories."""
        categories = registry.get_grammatical_categories()
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "Noun" in categories
        assert "Verb" in categories

    def test_create_default_profile_elements(self, registry: LIFTElementRegistry) -> None:
        """Test creating default element configuration."""
        default_elements = registry.create_default_profile_elements()
        
        assert isinstance(default_elements, list)
        assert len(default_elements) > 0
        
        # Check structure of element configs
        for elem_config in default_elements:
            assert "lift_element" in elem_config
            assert "display_order" in elem_config
            assert "css_class" in elem_config
            assert "visibility" in elem_config
        
        # Check expected default elements
        names = {elem["lift_element"] for elem in default_elements}
        assert "lexical-unit" in names
        assert "pronunciation" in names

    def test_validate_element_config_valid(self, registry: LIFTElementRegistry) -> None:
        """Test validating a valid element configuration."""
        valid_config = {
            "lift_element": "lexical-unit",
            "display_order": 1,
            "css_class": "headword",
            "visibility": "always"
        }
        
        is_valid, error = registry.validate_element_config(valid_config)
        assert is_valid is True
        assert error is None

    def test_validate_element_config_missing_element(self, registry: LIFTElementRegistry) -> None:
        """Test validating config without lift_element field."""
        invalid_config = {
            "display_order": 1,
            "css_class": "headword"
        }
        
        is_valid, error = registry.validate_element_config(invalid_config)
        assert is_valid is False
        assert "lift_element" in error  # type: ignore

    def test_validate_element_config_unknown_element(self, registry: LIFTElementRegistry) -> None:
        """Test validating config with unknown element."""
        invalid_config = {
            "lift_element": "unknown-element",
            "display_order": 1
        }
        
        is_valid, error = registry.validate_element_config(invalid_config)
        assert is_valid is False
        assert "Unknown LIFT element" in error  # type: ignore

    def test_validate_element_config_invalid_visibility(self, registry: LIFTElementRegistry) -> None:
        """Test validating config with invalid visibility."""
        invalid_config = {
            "lift_element": "lexical-unit",
            "visibility": "invalid-visibility"
        }
        
        is_valid, error = registry.validate_element_config(invalid_config)
        assert is_valid is False
        assert "Invalid visibility" in error  # type: ignore

    def test_get_element_hierarchy(self, registry: LIFTElementRegistry) -> None:
        """Test getting element hierarchy."""
        hierarchy = registry.get_element_hierarchy()
        
        assert isinstance(hierarchy, dict)
        assert "entry" in hierarchy
        assert "sense" in hierarchy
        
        # Check entry children
        entry_children = hierarchy["entry"]
        assert "lexical-unit" in entry_children
        assert "sense" in entry_children
        
        # Check sense children
        sense_children = hierarchy["sense"]
        assert "grammatical-info" in sense_children
        assert "definition" in sense_children

    def test_export_registry_json(self, registry: LIFTElementRegistry) -> None:
        """Test exporting registry as JSON."""
        json_str = registry.export_registry_json()
        
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # Check it contains expected data
        assert "elements" in json_str
        assert "categories" in json_str
        assert "lexical-unit" in json_str


class TestElementMetadata:
    """Test ElementMetadata dataclass."""

    def test_element_metadata_to_dict(self) -> None:
        """Test converting ElementMetadata to dictionary."""
        element = ElementMetadata(
            name="test-element",
            display_name="Test Element",
            category="test",
            description="A test element",
            level=1,
            parent="entry",
            allowed_children=["child1", "child2"],
            required=False,
            attributes={"attr1": "value1"},
            default_css="test-class",
            default_visibility="if-content",
            typical_order=10
        )
        
        element_dict = element.to_dict()
        
        assert element_dict["name"] == "test-element"
        assert element_dict["display_name"] == "Test Element"
        assert element_dict["category"] == "test"
        assert element_dict["level"] == 1
        assert element_dict["parent"] == "entry"
        assert element_dict["allowed_children"] == ["child1", "child2"]
        assert element_dict["required"] is False
        assert element_dict["default_css"] == "test-class"
        assert element_dict["default_visibility"] == "if-content"
        assert element_dict["typical_order"] == 10
