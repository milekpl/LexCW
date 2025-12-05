"""
Unit tests for LIFT 0.13 FieldWorks Standard Custom Fields (Day 28).

Tests the implementation of:
- exemplar field (sense-level)
- scientific-name field (sense-level)
- literal-meaning field (entry-level)

Following TDD approach.
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense


class TestExemplarField:
    """Tests for exemplar custom field on senses."""
    
    def test_sense_has_exemplar_attribute(self) -> None:
        """Test that Sense model has exemplar attribute."""
        sense = Sense()
        assert hasattr(sense, 'exemplar')
    
    def test_sense_exemplar_is_dict(self) -> None:
        """Test that exemplar is stored as a dictionary (multitext)."""
        sense = Sense()
        sense.exemplar = {'en': 'example form', 'fr': 'forme exemplaire'}
        assert isinstance(sense.exemplar, dict)
        assert sense.exemplar['en'] == 'example form'
        assert sense.exemplar['fr'] == 'forme exemplaire'
    
    def test_sense_exemplar_defaults_to_none(self) -> None:
        """Test that exemplar defaults to None when not set."""
        sense = Sense()
        assert sense.exemplar is None or sense.exemplar == {}
    
    def test_sense_exemplar_multiple_languages(self) -> None:
        """Test that exemplar can store multiple language variants."""
        sense = Sense()
        sense.exemplar = {
            'en': 'good man',
            'fr': 'homme bon',
            'es': 'hombre bueno',
            'de': 'guter Mann'
        }
        assert len(sense.exemplar) == 4
        assert sense.exemplar['de'] == 'guter Mann'


class TestScientificNameField:
    """Tests for scientific-name custom field on senses."""
    
    def test_sense_has_scientific_name_attribute(self) -> None:
        """Test that Sense model has scientific_name attribute."""
        sense = Sense()
        assert hasattr(sense, 'scientific_name')
    
    def test_sense_scientific_name_is_dict(self) -> None:
        """Test that scientific_name is stored as a dictionary (multitext)."""
        sense = Sense()
        sense.scientific_name = {'la': 'Felis catus'}
        assert isinstance(sense.scientific_name, dict)
        assert sense.scientific_name['la'] == 'Felis catus'
    
    def test_sense_scientific_name_defaults_to_none(self) -> None:
        """Test that scientific_name defaults to None when not set."""
        sense = Sense()
        assert sense.scientific_name is None or sense.scientific_name == {}
    
    def test_sense_scientific_name_with_common_name(self) -> None:
        """Test scientific name with accompanying common name translation."""
        sense = Sense()
        sense.scientific_name = {
            'la': 'Homo sapiens',
            'en': 'human being (scientific: Homo sapiens)'
        }
        assert 'Homo sapiens' in sense.scientific_name['la']
        assert 'human being' in sense.scientific_name['en']


class TestLiteralMeaningField:
    """Tests for literal-meaning custom field on senses (MOVED FROM ENTRY LEVEL - Day 28)."""
    
    def test_sense_has_literal_meaning_attribute(self) -> None:
        """Test that Sense model has literal_meaning attribute."""
        sense = Sense()
        assert hasattr(sense, 'literal_meaning')
    
    def test_sense_literal_meaning_is_dict(self) -> None:
        """Test that literal_meaning is stored as a dictionary (multitext)."""
        sense = Sense()
        sense.literal_meaning = {'en': 'foot to ground', 'fr': 'pied à terre'}
        assert isinstance(sense.literal_meaning, dict)
        assert sense.literal_meaning['en'] == 'foot to ground'
        assert sense.literal_meaning['fr'] == 'pied à terre'
    
    def test_sense_literal_meaning_defaults_to_none(self) -> None:
        """Test that literal_meaning defaults to None when not set."""
        sense = Sense()
        assert sense.literal_meaning is None or sense.literal_meaning == {}
    
    def test_sense_literal_meaning_for_idiom(self) -> None:
        """Test literal meaning for an idiomatic expression."""
        sense = Sense()
        sense.glosses = {'en': 'to die'}
        sense.literal_meaning = {
            'en': 'strike the pail with foot',
            'es': 'patear el cubo'
        }
        assert 'strike the pail' in sense.literal_meaning['en']
        assert sense.literal_meaning['es'] == 'patear el cubo'
    
    def test_sense_literal_meaning_for_compound(self) -> None:
        """Test literal meaning for a compound word."""
        sense = Sense()
        sense.glosses = {'en': 'glove'}
        sense.literal_meaning = {
            'en': 'hand-shoe',
            'de': 'Hand-Schuh'
        }
        assert sense.literal_meaning['en'] == 'hand-shoe'
        assert 'Hand' in sense.literal_meaning['de']


class TestCustomFieldsIntegration:
    """Integration tests for all three custom fields together."""
    
    def test_entry_and_sense_with_all_custom_fields(self) -> None:
        """Test entry with literal_meaning and sense with exemplar and scientific_name."""
        entry = Entry()
        entry.lexical_unit = {'en': 'domestic cat'}
        entry.literal_meaning = {'en': 'house cat', 'la': 'catus domesticus'}
        
        sense = Sense()
        sense.definition = {'en': 'A small domesticated carnivorous mammal'}
        sense.exemplar = {'en': 'tabby cat', 'fr': 'chat tigré'}
        sense.scientific_name = {'la': 'Felis catus'}
        
        entry.senses = [sense]
        
        assert entry.literal_meaning['en'] == 'house cat'
        assert entry.senses[0].exemplar['en'] == 'tabby cat'
        assert entry.senses[0].scientific_name['la'] == 'Felis catus'
    
    def test_multiple_senses_with_different_scientific_names(self) -> None:
        """Test entry with multiple senses having different scientific names."""
        entry = Entry()
        entry.lexical_unit = {'en': 'oak'}
        
        sense1 = Sense()
        sense1.definition = {'en': 'White oak'}
        sense1.scientific_name = {'la': 'Quercus alba'}
        
        sense2 = Sense()
        sense2.definition = {'en': 'Red oak'}
        sense2.scientific_name = {'la': 'Quercus rubra'}
        
        entry.senses = [sense1, sense2]
        
        assert entry.senses[0].scientific_name['la'] == 'Quercus alba'
        assert entry.senses[1].scientific_name['la'] == 'Quercus rubra'
