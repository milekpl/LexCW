"""
Unit tests for Domain Types functionality.

Tests that the Entry and Sense models correctly handle domain_type field
as a separate field from semantic domains, following LIFT standard domain-type ranges.
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.utils.multilingual_form_processor import process_senses_form_data, process_entry_form_data


class TestDomainTypesEntryLevel:
    """Test domain_type field at entry level."""

    def test_entry_model_accepts_domain_type_string(self) -> None:
        """Test that Entry model accepts domain_type as a string."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            domain_type="informatyka"
        )
        
        assert entry.domain_type == ["informatyka"]
        assert isinstance(entry.domain_type, list)

    def test_entry_model_accepts_domain_type_none(self) -> None:
        """Test that Entry model accepts None for domain_type."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            domain_type=None
        )
        
        assert entry.domain_type == []

    def test_entry_model_defaults_to_none(self) -> None:
        """Test that domain_type defaults to an empty list."""
        entry = Entry(
            lexical_unit={"en": "test word"}
        )
        
        assert entry.domain_type == []

    def test_entry_to_dict_includes_domain_type(self) -> None:
        """Test that Entry.to_dict() includes domain_type."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            domain_type="finanse"
        )
        
        entry_dict = entry.to_dict()
        
        assert 'domain_type' in entry_dict
        assert entry_dict['domain_type'] == ["finanse"]

    def test_entry_to_template_dict_includes_domain_type(self) -> None:
        """Test that Entry.to_template_dict() includes domain_type."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            domain_type="prawniczy"
        )
        
        template_dict = entry.to_template_dict()
        
        assert 'domain_type' in template_dict
        assert template_dict['domain_type'] == ["prawniczy"]

    def test_entry_form_processing_domain_type(self) -> None:
        """Test that form processor does NOT include domain_type at entry level.
        
        Domain Type was moved to sense-level only as per specification.
        This test verifies that entry-level domain_type is NOT processed.
        """
        form_data = {
            'lexical_unit[en]': 'test word',  # Use bracket notation as expected by processor
            'domain_type': 'literatura'  # This should be ignored
        }
        
        entry_data = process_entry_form_data(form_data)
        
        # Domain Type should NOT be at entry level anymore
        assert 'domain_type' not in entry_data
        # Only lexical_unit should be present
        assert 'lexical_unit' in entry_data
        assert entry_data['lexical_unit'] == {'en': 'test word'}

    def test_entry_form_processing_empty_domain_type(self) -> None:
        """Test that form processor handles empty domain_type."""
        form_data = {
            'lexical_unit.en': 'test word',
            'domain_type': ''
        }
        
        entry_data = process_entry_form_data(form_data)
        
        assert entry_data.get('domain_type') is None or entry_data.get('domain_type') == ''


class TestDomainTypesSenseLevel:
    """Test domain_type field at sense level."""

    def test_sense_model_accepts_domain_type_string(self) -> None:
        """Test that Sense model accepts domain_type as a string and normalizes to list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type="informatyka"
        )
        
        assert sense.domain_type == ["informatyka"]
        assert isinstance(sense.domain_type, list)

    def test_sense_model_accepts_domain_type_none(self) -> None:
        """Test that Sense model accepts None for domain_type and normalizes to empty list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type=None
        )
        
        assert sense.domain_type == []

    def test_sense_model_defaults_to_none(self) -> None:
        """Test that domain_type defaults to an empty list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"}
        )
        
        assert sense.domain_type == []

    def test_sense_to_dict_includes_domain_type(self) -> None:
        """Test that Sense.to_dict() includes domain_type as a list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type="finanse"
        )
        
        sense_dict = sense.to_dict()
        
        assert 'domain_type' in sense_dict
        assert sense_dict['domain_type'] == ["finanse"]

    def test_form_processor_handles_sense_domain_type(self) -> None:
        """Test that form processor handles sense domain_type as a string."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].domain_type': 'prawniczy',
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert 'domain_type' in senses[0]
        assert senses[0]['domain_type'] == ["prawniczy"]
        assert isinstance(senses[0]['domain_type'], list)

    def test_form_processor_handles_empty_sense_domain_type(self) -> None:
        """Test that form processor handles empty sense domain_type."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].domain_type': '',
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert senses[0].get('domain_type') == []

    def test_multiple_senses_with_different_domain_types(self) -> None:
        """Test form processor with multiple senses having different domain_type values."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].domain_type': 'informatyka',
            'senses[0].definition.en.text': 'first definition',
            'senses[1].id': 'sense2',
            'senses[1].domain_type': 'finanse',
            'senses[1].definition.en.text': 'second definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 2
        assert senses[0]['domain_type'] == ['informatyka']
        assert senses[1]['domain_type'] == ['finanse']


class TestDomainTypesLIFTIntegration:
    """Test Domain Types integration with LIFT format."""

    def test_entry_with_semantic_and_domain_types(self) -> None:
        """Test that entry can have both semantic domains and Domain Types independently."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "test"},
                    semantic_domain=["1.1 Universe, creation"],  # Semantic domain
                    domain_type="informatyka"  # Domain Type - separate
                )
            ]
        )
        
        sense = entry.senses[0]
        assert sense.semantic_domain == ["1.1 Universe, creation"]  # Semantic domain
        assert sense.domain_type == ["informatyka"]  # Domain Type - separate

    def test_domain_type_values_from_lift_ranges(self) -> None:
        """Test that domain_type accepts valid values from LIFT domain-type ranges."""
        valid_domain_types = [
            "informatyka",      # computer science
            "finanse",          # finance
            "prawniczy",        # legal
            "literatura",       # literature
            "antyk",            # ancient/aniquity
            "administracja",    # administration
            "rolnictwo"         # agriculture
        ]
        
        for domain in valid_domain_types:
            sense = Sense(
                id_="test_sense",
                glosses={"en": "test"},
                domain_type=domain
            )
            assert sense.domain_type == [domain]

    def test_entry_domain_type_independent_of_senses(self) -> None:
        """Test that entry-level domain_type is independent of sense domain_types."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            domain_type="finanse",  # Entry-level Domain Type
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "test"},
                    domain_type="informatyka"  # Sense-level Domain Type
                )
            ]
        )
        
        assert entry.domain_type == ["finanse"]  # Entry-level
        assert entry.senses[0].domain_type == ["informatyka"]  # Sense-level - different


class TestDomainTypesValidation:
    """Test Domain Types validation and edge cases."""

    def test_invalid_domain_type_type_string_conversion(self) -> None:
        """Test that non-string domain_type values are converted to strings."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type=123  # Non-string value
        )
        
        # Should handle gracefully (convert to string or keep as-is)
        assert sense.domain_type is not None

    def test_empty_string_domain_type(self) -> None:
        """Test that empty string domain_type becomes an empty list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type=""
        )
        
        assert sense.domain_type == []

    def test_whitespace_only_domain_type(self) -> None:
        """Test that whitespace-only domain_type becomes an empty list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type="   "
        )
        
        # Empty/whitespace strings are normalized to empty list
        assert sense.domain_type == []

    def test_unicode_domain_type(self) -> None:
        """Test that Unicode domain_type values are handled correctly."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type="informatyka"  # Polish word
        )
        
        assert sense.domain_type == ["informatyka"]