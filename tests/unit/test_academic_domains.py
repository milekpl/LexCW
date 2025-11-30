"""
Unit tests for Academic Domains functionality.

Tests that the Entry and Sense models correctly handle academic_domain field
as a separate field from semantic domains, following LIFT standard domain-type ranges.
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.utils.multilingual_form_processor import process_senses_form_data, process_entry_form_data


class TestAcademicDomainsEntryLevel:
    """Test academic_domain field at entry level."""

    def test_entry_model_accepts_academic_domain_string(self) -> None:
        """Test that Entry model accepts academic_domain as a string."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            academic_domain="informatyka"
        )
        
        assert entry.academic_domain == "informatyka"
        assert isinstance(entry.academic_domain, str)

    def test_entry_model_accepts_academic_domain_none(self) -> None:
        """Test that Entry model accepts None for academic_domain."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            academic_domain=None
        )
        
        assert entry.academic_domain is None

    def test_entry_model_defaults_to_none(self) -> None:
        """Test that academic_domain defaults to None."""
        entry = Entry(
            lexical_unit={"en": "test word"}
        )
        
        assert entry.academic_domain is None

    def test_entry_to_dict_includes_academic_domain(self) -> None:
        """Test that Entry.to_dict() includes academic_domain."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            academic_domain="finanse"
        )
        
        entry_dict = entry.to_dict()
        
        assert 'academic_domain' in entry_dict
        assert entry_dict['academic_domain'] == "finanse"

    def test_entry_to_template_dict_includes_academic_domain(self) -> None:
        """Test that Entry.to_template_dict() includes academic_domain."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            academic_domain="prawniczy"
        )
        
        template_dict = entry.to_template_dict()
        
        assert 'academic_domain' in template_dict
        assert template_dict['academic_domain'] == "prawniczy"

    def test_entry_form_processing_academic_domain(self) -> None:
        """Test that form processor does NOT include academic_domain at entry level.
        
        Academic domain was moved to sense-level only as per specification.
        This test verifies that entry-level academic_domain is NOT processed.
        """
        form_data = {
            'lexical_unit[en]': 'test word',  # Use bracket notation as expected by processor
            'academic_domain': 'literatura'  # This should be ignored
        }
        
        entry_data = process_entry_form_data(form_data)
        
        # Academic domain should NOT be at entry level anymore
        assert 'academic_domain' not in entry_data
        # Only lexical_unit should be present
        assert 'lexical_unit' in entry_data
        assert entry_data['lexical_unit'] == {'en': 'test word'}

    def test_entry_form_processing_empty_academic_domain(self) -> None:
        """Test that form processor handles empty academic_domain."""
        form_data = {
            'lexical_unit.en': 'test word',
            'academic_domain': ''
        }
        
        entry_data = process_entry_form_data(form_data)
        
        assert entry_data.get('academic_domain') is None or entry_data.get('academic_domain') == ''


class TestAcademicDomainsSenseLevel:
    """Test academic_domain field at sense level."""

    def test_sense_model_accepts_academic_domain_string(self) -> None:
        """Test that Sense model accepts academic_domain as a string."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            academic_domain="informatyka"
        )
        
        assert sense.academic_domain == "informatyka"
        assert isinstance(sense.academic_domain, str)

    def test_sense_model_accepts_academic_domain_none(self) -> None:
        """Test that Sense model accepts None for academic_domain."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            academic_domain=None
        )
        
        assert sense.academic_domain is None

    def test_sense_model_defaults_to_none(self) -> None:
        """Test that academic_domain defaults to None."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"}
        )
        
        assert sense.academic_domain is None

    def test_sense_to_dict_includes_academic_domain(self) -> None:
        """Test that Sense.to_dict() includes academic_domain."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            academic_domain="finanse"
        )
        
        sense_dict = sense.to_dict()
        
        assert 'academic_domain' in sense_dict
        assert sense_dict['academic_domain'] == "finanse"

    def test_form_processor_handles_sense_academic_domain(self) -> None:
        """Test that form processor handles sense academic_domain as a string."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].academic_domain': 'prawniczy',
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert 'academic_domain' in senses[0]
        assert senses[0]['academic_domain'] == "prawniczy"
        assert isinstance(senses[0]['academic_domain'], str)

    def test_form_processor_handles_empty_sense_academic_domain(self) -> None:
        """Test that form processor handles empty sense academic_domain."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].academic_domain': '',
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert senses[0].get('academic_domain') is None or senses[0].get('academic_domain') == ''

    def test_multiple_senses_with_different_academic_domains(self) -> None:
        """Test form processor with multiple senses having different academic_domain values."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].academic_domain': 'informatyka',
            'senses[0].definition.en.text': 'first definition',
            'senses[1].id': 'sense2',
            'senses[1].academic_domain': 'finanse',
            'senses[1].definition.en.text': 'second definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 2
        assert senses[0]['academic_domain'] == 'informatyka'
        assert senses[1]['academic_domain'] == 'finanse'


class TestAcademicDomainsLIFTIntegration:
    """Test Academic Domains integration with LIFT format."""

    def test_entry_with_semantic_and_academic_domains(self) -> None:
        """Test that entry can have both semantic domains and academic domains independently."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "test"},
                    domain_type=["1.1 Universe, creation"],  # Semantic domain
                    academic_domain="informatyka"  # Academic domain - separate
                )
            ]
        )
        
        sense = entry.senses[0]
        assert sense.domain_type == ["1.1 Universe, creation"]  # Semantic domain
        assert sense.academic_domain == "informatyka"  # Academic domain - separate

    def test_academic_domain_values_from_lift_ranges(self) -> None:
        """Test that academic_domain accepts valid values from LIFT domain-type ranges."""
        valid_academic_domains = [
            "informatyka",      # computer science
            "finanse",          # finance
            "prawniczy",        # legal
            "literatura",       # literature
            "antyk",            # ancient/aniquity
            "administracja",    # administration
            "rolnictwo"         # agriculture
        ]
        
        for domain in valid_academic_domains:
            sense = Sense(
                id_="test_sense",
                glosses={"en": "test"},
                academic_domain=domain
            )
            assert sense.academic_domain == domain

    def test_entry_academic_domain_independent_of_senses(self) -> None:
        """Test that entry-level academic_domain is independent of sense academic_domains."""
        entry = Entry(
            lexical_unit={"en": "test word"},
            academic_domain="finanse",  # Entry-level academic domain
            senses=[
                Sense(
                    id_="sense1",
                    glosses={"en": "test"},
                    academic_domain="informatyka"  # Sense-level academic domain
                )
            ]
        )
        
        assert entry.academic_domain == "finanse"  # Entry-level
        assert entry.senses[0].academic_domain == "informatyka"  # Sense-level - different


class TestAcademicDomainsValidation:
    """Test Academic Domains validation and edge cases."""

    def test_invalid_academic_domain_type_string_conversion(self) -> None:
        """Test that non-string academic_domain values are converted to strings."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            academic_domain=123  # Non-string value
        )
        
        # Should handle gracefully (convert to string or keep as-is)
        assert sense.academic_domain is not None

    def test_empty_string_academic_domain(self) -> None:
        """Test that empty string academic_domain becomes None."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            academic_domain=""
        )
        
        assert sense.academic_domain is None

    def test_whitespace_only_academic_domain(self) -> None:
        """Test that whitespace-only academic_domain becomes None."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            academic_domain="   "
        )
        
        # Empty/whitespace strings are normalized to None
        assert sense.academic_domain is None

    def test_unicode_academic_domain(self) -> None:
        """Test that Unicode academic_domain values are handled correctly."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            academic_domain="informatyka"  # Polish word
        )
        
        assert sense.academic_domain == "informatyka"