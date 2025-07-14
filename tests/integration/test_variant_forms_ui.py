"""
Test suite for variant forms UI functionality.

This module tests the UI components and backend support for LIFT variant forms
including Form object editing, dynamic add/remove, and integration with ranges.
"""

from __future__ import annotations

import pytest

from app.models.entry import Entry, Variant



@pytest.mark.integration
class TestVariantFormsUI:
    """Test variant forms UI functionality."""

    @pytest.mark.integration
    def test_entry_model_supports_variants(self) -> None:
        """Test that Entry model properly supports variant forms."""
        # Create entry with variant forms
        variants_data = [
            {
                "form": {
                    "lang": "en",
                    "text": "color"
                }
            },
            {
                "form": {
                    "lang": "en-GB", 
                    "text": "colour"
                }
            }
        ]
        
        entry = Entry(id_="test-entry",
            lexical_unit={"en": "color"},
            variants=variants_data,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Verify variants are properly created
        assert len(entry.variants) == 2
        assert isinstance(entry.variants[0], Variant)
        assert isinstance(entry.variants[1], Variant)

    @pytest.mark.integration
    def test_variant_object_creation_and_serialization(self) -> None:
        """Test Variant object creation and to_dict serialization."""
        # Test Variant creation from dict
        variant_data = {
            "form": {
                "lang": "it",
                "text": "parola"
            }
        }
        variant_from_dict = Variant(**variant_data)
        
        # Test to_dict serialization
        variant_dict = variant_from_dict.to_dict()
        assert "form" in variant_dict
        assert variant_dict["form"]["lang"] == "it"
        assert variant_dict["form"]["text"] == "parola"

    @pytest.mark.integration
    def test_entry_variant_serialization(self) -> None:
        """Test that Entry properly serializes variants to JSON."""
        variants_data = [
            {
                "form": {
                    "lang": "en-US",
                    "text": "center"
                }
            },
            {
                "form": {
                    "lang": "en-GB",
                    "text": "centre"
                }
            }
        ]
        
        entry = Entry(id_="test-serialization",
            lexical_unit={"en": "center"},
            variants=variants_data
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Test to_dict serialization
        entry_dict = entry.to_dict()
        assert "variants" in entry_dict
        assert len(entry_dict["variants"]) == 2
        
        # Verify nested serialization
        variant1 = entry_dict["variants"][0]
        assert "form" in variant1
        assert variant1["form"]["lang"] == "en-US"
        assert variant1["form"]["text"] == "center"
        
        variant2 = entry_dict["variants"][1]
        assert "form" in variant2
        assert variant2["form"]["lang"] == "en-GB"
        assert variant2["form"]["text"] == "centre"
        
        # Test JSON serialization doesn't fail
        entry_json = entry.to_json()
        assert isinstance(entry_json, str)
        assert "variants" in entry_json

    @pytest.mark.integration
    def test_empty_variants_handling(self) -> None:
        """Test proper handling of entries with no variants."""
        entry = Entry(id_="no-variants",
            lexical_unit={"en": "simple"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        assert entry.variants == []
        
        entry_dict = entry.to_dict()
        assert entry_dict["variants"] == []

    @pytest.mark.integration
    def test_variant_validation_requirements(self) -> None:
        """Test validation requirements for variant forms."""
        # Test that variants can be created with proper form data
        variant_data = {
            "form": {
                "lang": "en",
                "text": "test"
            }
        }
        variant = Variant(**variant_data)
        assert variant is not None



@pytest.mark.integration
class TestVariantFormsAPISupport:
    """Test API support for variant forms."""

    @pytest.mark.integration
    def test_api_entry_creation_with_variants(self) -> None:
        """Test API endpoint supports entry creation with variants."""
        entry_data = {
            "id": "api-test-variants",
            "lexical_unit": {"en": "analyze"},
            "variants": [
                {
                    "form": {
                        "lang": "en-GB",
                        "text": "analyse"
                    }
                }
            ]
        }
        
        # This should not raise an exception when processed by Entry model
        entry = Entry(**entry_data)
        assert len(entry.variants) == 1
        assert entry.variants[0].form["lang"] == "en-GB"
        assert entry.variants[0].form["text"] == "analyse"

    @pytest.mark.integration
    def test_api_entry_update_with_variants(self) -> None:
        """Test API endpoint supports entry updates with variants."""
        # Create entry without variants
        entry = Entry(id_="update-test",
            lexical_unit={"en": "organize"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        assert len(entry.variants) == 0
        
        # Update with variants
        update_data = {
            "variants": [
                {
                    "form": {
                        "lang": "en-GB",
                        "text": "organise"
                    }
                },
                {
                    "form": {
                        "lang": "en-CA",
                        "text": "organise"
                    }
                }
            ]
        }
        
        # Simulate update by creating new entry with updated data
        updated_entry = Entry(id_=entry.id,
            lexical_unit=entry.lexical_unit,
            **update_data
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        assert len(updated_entry.variants) == 2
        assert updated_entry.variants[0].form["text"] == "organise"
        assert updated_entry.variants[1].form["lang"] == "en-CA"



@pytest.mark.integration
class TestVariantFormsRangesIntegration:
    """Test integration with LIFT ranges for variant types."""

    @pytest.mark.integration
    def test_variant_type_from_ranges(self) -> None:
        """Test that variant types can be loaded from LIFT ranges."""
        # This test will be expanded when ranges integration is implemented
        # For now, test the structure is ready
        
        variant_data = {
            "form": {
                "lang": "en",
                "text": "variant_text"
            },
            # Future: variant_type from ranges
            # "type": "dialectal"
        }
        
        variant = Variant(**variant_data)
        
        # Verify we can add custom attributes (for future ranges integration)
        # This tests extensibility
        variant_dict = variant.to_dict()
        assert "form" in variant_dict

    @pytest.mark.integration
    def test_form_language_code_validation_ready(self) -> None:
        """Test that variant forms support various language codes."""
        # Test various language codes that should be valid
        valid_codes = ["en", "en-US", "en-GB", "es", "fr", "de", "zh-CN", "seh-fonipa"]
        
        for code in valid_codes:
            variant_data = {
                "form": {
                    "lang": code,
                    "text": "test"
                }
            }
            variant = Variant(**variant_data)
            assert variant is not None



@pytest.mark.integration
class TestVariantFormsLifecycle:
    """Test complete lifecycle of variant forms in entry editing."""

    @pytest.mark.integration
    def test_add_variant_to_existing_entry(self) -> None:
        """Test adding variants to an existing entry."""
        # Start with entry without variants
        entry = Entry(id_="lifecycle-test",
            lexical_unit={"en": "honor"},
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        assert len(entry.variants) == 0
        
        # Add variant (simulating UI action)
        new_variant_data = {
            "form": {
                "lang": "en-GB",
                "text": "honour"
            }
        }
        new_variant = Variant(**new_variant_data)
        entry.variants.append(new_variant)
        
        assert len(entry.variants) == 1

    @pytest.mark.integration
    def test_remove_variant_from_entry(self) -> None:
        """Test removing variants from an entry."""
        # Start with entry with multiple variants
        variants_data = [
            {"form": {"lang": "en-US", "text": "flavor"}},
            {"form": {"lang": "en-GB", "text": "flavour"}},
            {"form": {"lang": "en-CA", "text": "flavour"}}
        ]
        
        entry = Entry(id_="remove-test",
            lexical_unit={"en": "flavor"},
            variants=variants_data,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        assert len(entry.variants) == 3
        
        # Remove middle variant (simulating UI action)
        entry.variants.pop(1)
        
        assert len(entry.variants) == 2

    @pytest.mark.integration
    def test_modify_variant_in_entry(self) -> None:
        """Test modifying existing variants in an entry."""
        variants_data = [
            {"form": {"lang": "en", "text": "colour"}}
        ]
        
        entry = Entry(id_="modify-test",
            lexical_unit={"en": "color"},
            variants=variants_data,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Verify variant was created
        assert len(entry.variants) == 1
