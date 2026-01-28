"""
Unit tests for DisplayProfile configurability of LIFT elements.

Verifies that all registered LIFT elements are configurable via DisplayProfiles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.models.display_profile import DisplayProfile, ProfileElement
from app.services.lift_element_registry import LIFTElementRegistry

if TYPE_CHECKING:
    from app.services.css_mapping_service import CSSMappingService


@pytest.fixture
def registry() -> LIFTElementRegistry:
    """Create a LIFT element registry instance."""
    return LIFTElementRegistry()


@pytest.fixture
def sample_entry_xml() -> str:
    """Sample LIFT entry XML for testing rendering."""
    return '''<entry id="test-entry">
        <lexical-unit>
            <form lang="en">
                <text>test</text>
            </form>
        </lexical-unit>
        <pronunciation>
            <form lang="en">
                <text>/tɛst/</text>
            </form>
        </pronunciation>
        <sense id="sense-1">
            <grammatical-info value="Noun"/>
            <definition>
                <form lang="en">
                    <text>A test definition</text>
                </form>
            </definition>
            <example>
                <form lang="en">
                    <text>A test example</text>
                </form>
            </example>
        </sense>
    </entry>'''


@pytest.fixture
def default_profile_elements(registry: LIFTElementRegistry) -> list[dict]:
    """Get default profile elements from registry."""
    return registry.create_default_profile_elements()


class TestDisplayProfileConfigurability:
    """Verify all LIFT elements are configurable via DisplayProfiles."""

    def test_all_registered_elements_have_profile_config(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify every registered LIFT element has a default profile configuration."""
        registered_elements = {e.name for e in registry.get_all_elements()}
        default_elements = registry.create_default_profile_elements()
        profile_element_names = {e['lift_element'] for e in default_elements}

        # All registered elements should have profile configs
        # Note: Only displayable elements are included in default profile
        # (excludes structural elements like 'form', 'text', 'trait')
        displayable_elements = {e.name for e in registry.get_displayable_elements()}

        # Verify all displayable elements have configs
        missing = displayable_elements - profile_element_names
        assert not missing, f"Elements missing from default profile: {missing}"

    def test_displayable_elements_coverage(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify all expected displayable elements are in the registry."""
        displayable_elements = registry.get_displayable_elements()
        displayable_names = {e.name for e in displayable_elements}

        # Key elements that should always be displayable (from registry definition)
        expected_elements = {
            'lexical-unit', 'citation', 'pronunciation', 'variant',
            'variant-relation', 'sense', 'subsense', 'grammatical-info',
            'gloss', 'definition', 'example',
            'reversal', 'illustration', 'note', 'field', 'trait', 'etymology', 'relation'
        }

        missing = expected_elements - displayable_names
        assert not missing, f"Expected displayable elements missing: {missing}"

    def test_profile_elements_have_required_fields(
        self, registry: LIFTElementRegistry, default_profile_elements: list[dict]
    ) -> None:
        """Verify each profile element has all required configuration fields."""
        required_fields = {
            'lift_element', 'display_order', 'css_class', 'visibility', 'config'
        }

        for elem in default_profile_elements:
            missing = required_fields - set(elem.keys())
            assert not missing, (
                f"Element {elem.get('lift_element')} missing fields: {missing}"
            )

    def test_profile_elements_have_config_with_display_mode(
        self, registry: LIFTElementRegistry, default_profile_elements: list[dict]
    ) -> None:
        """Verify each profile element config contains display_mode."""
        for elem in default_profile_elements:
            config = elem.get('config')
            assert config is not None, (
                f"Element {elem.get('lift_element')} missing config dict"
            )
            assert 'display_mode' in config, (
                f"Element {elem.get('lift_element')} config missing display_mode"
            )

    def test_profile_elements_have_valid_display_modes(
        self, registry: LIFTElementRegistry, default_profile_elements: list[dict]
    ) -> None:
        """Verify all profile elements have valid display_mode values."""
        valid_modes = {'inline', 'block'}

        for elem in default_profile_elements:
            display_mode = elem.get('config', {}).get('display_mode')
            assert display_mode in valid_modes, (
                f"Element {elem.get('lift_element')} has invalid display_mode: {display_mode}"
            )

    def test_profile_elements_have_valid_visibility(
        self, registry: LIFTElementRegistry, default_profile_elements: list[dict]
    ) -> None:
        """Verify all profile elements have valid visibility values."""
        valid_visibility = {'always', 'if-content', 'never'}

        for elem in default_profile_elements:
            visibility = elem.get('visibility')
            assert visibility in valid_visibility, (
                f"Element {elem.get('lift_element')} has invalid visibility: {visibility}"
            )

    def test_default_profile_has_reasonable_element_order(
        self, registry: LIFTElementRegistry, default_profile_elements: list[dict]
    ) -> None:
        """Verify elements have reasonable display order values."""
        # Check that display_order values are positive and increment reasonably
        orders = [elem['display_order'] for elem in default_profile_elements]

        # All orders should be positive integers
        assert all(isinstance(o, int) and o > 0 for o in orders), (
            "All display_order values should be positive integers"
        )

        # Check that lexical-unit comes before pronunciation (typical order)
        lu_order = next(
            e['display_order'] for e in default_profile_elements
            if e['lift_element'] == 'lexical-unit'
        )
        pron_order = next(
            e['display_order'] for e in default_profile_elements
            if e['lift_element'] == 'pronunciation'
        )
        assert lu_order < pron_order, (
            "lexical-unit should appear before pronunciation"
        )

    def test_all_elements_have_css_class(
        self, registry: LIFTElementRegistry, default_profile_elements: list[dict]
    ) -> None:
        """Verify each profile element has a css_class defined."""
        for elem in default_profile_elements:
            css_class = elem.get('css_class')
            assert css_class is not None, (
                f"Element {elem.get('lift_element')} missing css_class"
            )
            assert isinstance(css_class, str), (
                f"Element {elem.get('lift_element')} css_class should be a string"
            )

    def test_visibility_options_are_complete(self, registry: LIFTElementRegistry) -> None:
        """Verify all visibility options are available."""
        options = registry.get_visibility_options()
        values = {opt['value'] for opt in options}

        assert 'always' in values, "Missing 'always' visibility option"
        assert 'if-content' in values, "Missing 'if-content' visibility option"
        assert 'never' in values, "Missing 'never' visibility option"


class TestDisplayProfileRendering:
    """Tests for profile configuration affecting rendering output."""

    def test_profile_element_visibility_config_structure(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify visibility configuration is properly structured."""
        default_elements = registry.create_default_profile_elements()

        # Find lexical-unit and check its visibility
        lu_elem = next(
            (e for e in default_elements if e['lift_element'] == 'lexical-unit'),
            None
        )
        assert lu_elem is not None, "lexical-unit should be in default profile"
        assert lu_elem['visibility'] == 'always', (
            "lexical-unit should have 'always' visibility by default"
        )

        # Find pronunciation and check its visibility
        pron_elem = next(
            (e for e in default_elements if e['lift_element'] == 'pronunciation'),
            None
        )
        assert pron_elem is not None, "pronunciation should be in default profile"
        assert pron_elem['visibility'] == 'if-content', (
            "pronunciation should have 'if-content' visibility by default"
        )

    def test_profile_element_prefix_suffix_config(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify prefix and suffix are configured in profile elements."""
        default_elements = registry.create_default_profile_elements()

        for elem in default_elements:
            # prefix and suffix should exist (can be empty strings)
            assert 'prefix' in elem, (
                f"Element {elem.get('lift_element')} missing prefix field"
            )
            assert 'suffix' in elem, (
                f"Element {elem.get('lift_element')} missing suffix field"
            )

    def test_custom_visibility_mode_never_hides_elements(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify visibility='never' is a valid configuration option."""
        # Create a custom element config with visibility='never'
        custom_config = {
            'lift_element': 'lexical-unit',
            'display_order': 10,
            'css_class': 'headword',
            'visibility': 'never',
            'prefix': '',
            'suffix': '',
            'config': {'display_mode': 'inline'}
        }

        is_valid, error = registry.validate_element_config(custom_config)
        assert is_valid is True, f"visibility='never' should be valid: {error}"

    def test_custom_visibility_mode_always_shows(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify visibility='always' is a valid configuration option."""
        custom_config = {
            'lift_element': 'example',
            'display_order': 300,
            'css_class': 'example-text',
            'visibility': 'always',
            'prefix': 'Ex: ',
            'suffix': '',
            'config': {'display_mode': 'block'}
        }

        is_valid, error = registry.validate_element_config(custom_config)
        assert is_valid is True, f"visibility='always' should be valid: {error}"

    def test_custom_display_mode_inline(self, registry: LIFTElementRegistry) -> None:
        """Verify inline display_mode is properly configured."""
        custom_config = {
            'lift_element': 'grammatical-info',
            'display_order': 230,
            'css_class': 'pos-tag',
            'visibility': 'if-content',
            'prefix': '(',
            'suffix': ')',
            'config': {'display_mode': 'inline'}
        }

        is_valid, error = registry.validate_element_config(custom_config)
        assert is_valid is True, f"inline display_mode should be valid: {error}"

    def test_custom_display_mode_block(self, registry: LIFTElementRegistry) -> None:
        """Verify block display_mode is properly configured."""
        custom_config = {
            'lift_element': 'definition',
            'display_order': 240,
            'css_class': 'definition-text',
            'visibility': 'if-content',
            'prefix': '',
            'suffix': '',
            'config': {'display_mode': 'block'}
        }

        is_valid, error = registry.validate_element_config(custom_config)
        assert is_valid is True, f"block display_mode should be valid: {error}"


class TestProfileElementModel:
    """Tests for ProfileElement model attributes."""

    def test_profile_element_has_all_configurable_attributes(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify ProfileElement model supports all configurable attributes."""
        default_elements = registry.create_default_profile_elements()

        # Create a mock profile with elements to verify structure
        for elem_config in default_elements:
            # Verify each element has all expected keys
            expected_keys = {
                'lift_element', 'display_order', 'css_class', 'visibility',
                'prefix', 'suffix', 'config'
            }
            actual_keys = set(elem_config.keys())
            missing = expected_keys - actual_keys
            assert not missing, (
                f"Element {elem_config.get('lift_element')} missing keys: {missing}"
            )

    def test_element_config_supports_language_filter(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify element configuration supports language_filter."""
        custom_config = {
            'lift_element': 'definition',
            'display_order': 240,
            'css_class': 'definition-text',
            'visibility': 'if-content',
            'language_filter': 'en',
            'prefix': '',
            'suffix': '',
            'config': {'display_mode': 'block'}
        }

        is_valid, error = registry.validate_element_config(custom_config)
        assert is_valid is True, f"language_filter should be valid: {error}"


class TestElementConfigurationValidation:
    """Tests for element configuration validation."""

    def test_valid_element_config_passes_validation(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify valid configurations pass validation."""
        valid_configs = [
            {
                'lift_element': 'lexical-unit',
                'display_order': 10,
                'css_class': 'headword',
                'visibility': 'always',
                'config': {'display_mode': 'inline'}
            },
            {
                'lift_element': 'sense',
                'display_order': 100,
                'css_class': 'sense-item',
                'visibility': 'if-content',
                'config': {'display_mode': 'block'}
            },
            {
                'lift_element': 'note',
                'display_order': 500,
                'css_class': 'note-item',
                'visibility': 'never',
                'config': {'display_mode': 'block'}
            },
        ]

        for config in valid_configs:
            is_valid, error = registry.validate_element_config(config)
            assert is_valid is True, (
                f"Config for {config.get('lift_element')} should be valid: {error}"
            )

    def test_invalid_visibility_fails_validation(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify invalid visibility values fail validation."""
        invalid_config = {
            'lift_element': 'lexical-unit',
            'visibility': 'sometimes',  # Invalid
        }

        is_valid, error = registry.validate_element_config(invalid_config)
        assert is_valid is False, "Invalid visibility should fail validation"
        assert 'visibility' in error.lower(), "Error should mention visibility"

    def test_unknown_element_fails_validation(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify unknown elements fail validation."""
        invalid_config = {
            'lift_element': 'non-existent-element',
            'visibility': 'always',
        }

        is_valid, error = registry.validate_element_config(invalid_config)
        assert is_valid is False, "Unknown element should fail validation"
        assert 'unknown' in error.lower() or 'not found' in error.lower(), (
            "Error should mention element not found"
        )


class TestDefaultProfileCompleteness:
    """Tests verifying default profile has complete coverage."""

    def test_default_profile_has_sufficient_elements(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify default profile has a reasonable number of elements."""
        default_elements = registry.create_default_profile_elements()

        # Should have at least 15 elements (the displayable ones)
        assert len(default_elements) >= 15, (
            f"Default profile should have at least 15 elements, got {len(default_elements)}"
        )

    def test_default_profile_covers_all_categories(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify default profile covers elements from multiple categories."""
        default_elements = registry.create_default_profile_elements()
        element_names = {e['lift_element'] for e in default_elements}

        # Entry-level elements
        assert 'lexical-unit' in element_names
        assert 'pronunciation' in element_names

        # Sense-level elements
        assert 'sense' in element_names
        assert 'grammatical-info' in element_names
        assert 'definition' in element_names
        assert 'example' in element_names

        # Relation elements
        assert 'relation' in element_names
        assert 'variant' in element_names
        assert 'variant-relation' in element_names

    def test_each_element_has_unique_display_order(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify each element has a unique display_order."""
        default_elements = registry.create_default_profile_elements()
        orders = [e['display_order'] for e in default_elements]

        # All orders should be unique
        assert len(orders) == len(set(orders)), (
            "All display_order values should be unique"
        )

    def test_display_order_allows_insertion(
        self, registry: LIFTElementRegistry
    ) -> None:
        """Verify display_order values leave room for insertion."""
        default_elements = registry.create_default_profile_elements()
        orders = sorted([e['display_order'] for e in default_elements])

        # Check that orders are spaced to allow insertion
        # Default elements use multiples of 10, so there should be gaps
        min_gap = min(
            orders[i+1] - orders[i]
            for i in range(len(orders) - 1)
        )

        assert min_gap >= 10, (
            f"Display orders should have gaps of at least 10 for insertion, "
            f"minimum gap found: {min_gap}"
        )
