"""
Unit tests for sense-level fields (usage_type, domain_type).

Tests that the Sense model and form processor correctly handle
usage_type and domain_type as lists at the sense level.
"""
from __future__ import annotations

import pytest
from app.models.sense import Sense
from app.utils.multilingual_form_processor import process_senses_form_data


class TestSenseLevelFields:
    """Test usage_type and domain_type fields at sense level."""

    def test_sense_model_accepts_usage_type_list(self) -> None:
        """Test that Sense model accepts usage_type as a list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            usage_type=["formal", "written"]
        )
        
        assert sense.usage_type == ["formal", "written"]
        assert isinstance(sense.usage_type, list)

    def test_sense_model_accepts_domain_type_list(self) -> None:
        """Test that Sense model accepts domain_type as a list."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            domain_type=["1.1 Universe, creation", "1.2 World"]
        )
        
        assert sense.domain_type == ["1.1 Universe, creation", "1.2 World"]
        assert isinstance(sense.domain_type, list)

    def test_sense_model_defaults_to_empty_lists(self) -> None:
        """Test that usage_type and domain_type default to empty lists."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"}
        )
        
        assert sense.usage_type == []
        assert sense.domain_type == []

    def test_form_processor_handles_usage_type_as_list(self) -> None:
        """Test that form processor handles usage_type as a list."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].usage_type': ['formal', 'written'],
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert 'usage_type' in senses[0]
        assert senses[0]['usage_type'] == ['formal', 'written']
        assert isinstance(senses[0]['usage_type'], list)

    def test_form_processor_handles_domain_type_as_list(self) -> None:
        """Test that form processor handles domain_type as a list."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].domain_type': ['1.1', '1.2'],
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert 'domain_type' in senses[0]
        assert senses[0]['domain_type'] == ['1.1', '1.2']
        assert isinstance(senses[0]['domain_type'], list)

    def test_form_processor_handles_semicolon_separated_string(self) -> None:
        """Test that form processor handles semicolon-separated strings (LIFT format)."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].usage_type': 'formal;written;academic',
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert 'usage_type' in senses[0]
        assert senses[0]['usage_type'] == ['formal', 'written', 'academic']

    def test_form_processor_handles_empty_values(self) -> None:
        """Test that form processor handles empty usage_type and domain_type."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].usage_type': '',
            'senses[0].domain_type': '',
            'senses[0].definition.en.text': 'test definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 1
        assert senses[0].get('usage_type', []) == []
        assert senses[0].get('domain_type', []) == []

    def test_sense_to_dict_includes_usage_type_and_domain_type(self) -> None:
        """Test that Sense.to_dict() includes usage_type and domain_type."""
        sense = Sense(
            id_="test_sense",
            glosses={"en": "test"},
            usage_type=["formal"],
            domain_type=["1.1"]
        )
        
        sense_dict = sense.to_dict()
        
        assert 'usage_type' in sense_dict
        assert 'domain_type' in sense_dict
        assert sense_dict['usage_type'] == ["formal"]
        assert sense_dict['domain_type'] == ["1.1"]

    def test_multiple_senses_with_different_values(self) -> None:
        """Test form processor with multiple senses having different usage_type values."""
        form_data = {
            'senses[0].id': 'sense1',
            'senses[0].usage_type': ['formal'],
            'senses[0].definition.en.text': 'first definition',
            'senses[1].id': 'sense2',
            'senses[1].usage_type': ['informal', 'slang'],
            'senses[1].definition.en.text': 'second definition'
        }
        
        senses = process_senses_form_data(form_data)
        
        assert len(senses) == 2
        assert senses[0]['usage_type'] == ['formal']
        assert senses[1]['usage_type'] == ['informal', 'slang']
