"""
Integration tests for LIFT 0.13 FieldWorks Standard Custom Fields (Day 28).

Tests the complete round-trip (form → XML → database → retrieval) for:
- exemplar field (sense-level)
- scientific-name field (sense-level)
- literal-meaning field (entry-level)

Following TDD approach.
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.parsers.lift_parser import LIFTParser


@pytest.mark.integration
class TestCustomFieldsXMLSerialization:
    """Integration tests for custom fields XML serialization and parsing."""
    
    def test_exemplar_field_xml_generation(self) -> None:
        """Test that exemplar field generates correct LIFT XML."""
        sense = Sense()
        sense.id = 'sense1'
        sense.definition = {'en': 'A good example'}
        sense.exemplar = {'en': 'model citizen', 'fr': 'citoyen modèle'}
        
        entry = Entry()
        entry.id = 'entry1'
        entry.lexical_unit = {'en': 'exemplary'}
        entry.senses = [sense]
        
        parser = LIFTParser()
        xml_str = parser.generate_lift_string([entry])
        
        # Verify XML structure - check for key content
        assert 'id="sense1"' in xml_str
        assert 'type="exemplar"' in xml_str
        assert 'model citizen' in xml_str
        assert 'citoyen modèle' in xml_str
        assert 'lang="en"' in xml_str
        assert 'lang="fr"' in xml_str
    
    def test_scientific_name_field_xml_generation(self) -> None:
        """Test that scientific-name field generates correct LIFT XML."""
        sense = Sense()
        sense.id = 'sense1'
        sense.definition = {'en': 'domestic cat'}
        sense.scientific_name = {'la': 'Felis catus', 'en': 'Latin: Felis catus'}
        
        entry = Entry()
        entry.id = 'entry1'
        entry.lexical_unit = {'en': 'cat'}
        entry.senses = [sense]
        
        parser = LIFTParser()
        xml_str = parser.generate_lift_string([entry])
        
        # Verify XML structure
        assert 'id="sense1"' in xml_str
        assert 'type="scientific-name"' in xml_str
        assert 'Felis catus' in xml_str
        assert 'Latin: Felis catus' in xml_str
    
    def test_literal_meaning_field_xml_generation(self) -> None:
        """Test that literal-meaning field generates correct LIFT XML (SENSE LEVEL - Day 28)."""
        entry = Entry()
        entry.id = 'entry1'
        entry.lexical_unit = {'fr': 'pied-à-terre'}
        
        sense = Sense()
        sense.id = 'sense1'
        sense.definition = {'en': 'temporary residence'}
        sense.literal_meaning = {'en': 'foot to ground', 'fr': 'pied à terre'}
        print(f"DEBUG: After setting literal_meaning on sense: {sense.literal_meaning}")
        print(f"DEBUG: hasattr check: {hasattr(sense, 'literal_meaning')}")
        entry.senses = [sense]
        print(f"DEBUG: After assignment, entry.senses[0].literal_meaning: {entry.senses[0].literal_meaning}")
        
        parser = LIFTParser()
        xml_str = parser.generate_lift_string([entry])
        print(f"DEBUG: Generated XML:\n{xml_str}")
        
        # Verify XML structure
        assert 'id="entry1"' in xml_str
        assert 'type="literal-meaning"' in xml_str
        assert 'foot to ground' in xml_str
        assert 'pied à terre' in xml_str
    
    def test_all_custom_fields_together(self) -> None:
        """Test entry with all custom fields (literal_meaning on sense - Day 28)."""
        entry = Entry()
        entry.id = 'entry1'
        entry.lexical_unit = {'en': 'oak tree', 'la': 'quercus'}
        
        sense1 = Sense()
        sense1.id = 'sense1'
        sense1.definition = {'en': 'White oak'}
        sense1.exemplar = {'en': 'large white oak', 'la': 'quercus alba magna'}
        sense1.scientific_name = {'la': 'Quercus alba'}
        sense1.literal_meaning = {'en': 'strong wood tree'}
        
        sense2 = Sense()
        sense2.id = 'sense2'
        sense2.definition = {'en': 'Red oak'}
        sense2.exemplar = {'en': 'red oak sapling'}
        sense2.scientific_name = {'la': 'Quercus rubra'}
        
        entry.senses = [sense1, sense2]
        
        parser = LIFTParser()
        xml_str = parser.generate_lift_string([entry])
        
        # Verify entry-level literal-meaning
        assert 'type="literal-meaning"' in xml_str
        assert 'strong wood tree' in xml_str
        
        # Verify sense1 fields
        assert 'id="sense1"' in xml_str
        assert 'type="exemplar"' in xml_str
        assert 'large white oak' in xml_str
        assert 'type="scientific-name"' in xml_str
        assert 'Quercus alba' in xml_str
        
        # Verify sense2 fields
        assert 'id="sense2"' in xml_str
        assert 'red oak sapling' in xml_str
        assert 'Quercus rubra' in xml_str


@pytest.mark.integration
class TestCustomFieldsXMLParsing:
    """Integration tests for parsing custom fields from LIFT XML."""
    
    def test_parse_exemplar_field(self) -> None:
        """Test parsing exemplar field from LIFT XML."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="sense1">
            <definition>
                <form lang="en"><text>A test sense</text></form>
            </definition>
            <field type="exemplar">
                <form lang="en"><text>perfect example</text></form>
                <form lang="es"><text>ejemplo perfecto</text></form>
            </field>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        
        assert hasattr(sense, 'exemplar')
        assert sense.exemplar is not None
        assert sense.exemplar['en'] == 'perfect example'
        assert sense.exemplar['es'] == 'ejemplo perfecto'
    
    def test_parse_scientific_name_field(self) -> None:
        """Test parsing scientific-name field from LIFT XML."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry">
        <lexical-unit>
            <form lang="en"><text>human</text></form>
        </lexical-unit>
        <sense id="sense1">
            <definition>
                <form lang="en"><text>Homo sapiens</text></form>
            </definition>
            <field type="scientific-name">
                <form lang="la"><text>Homo sapiens</text></form>
                <form lang="en"><text>scientific: Homo sapiens</text></form>
            </field>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        sense = entry.senses[0]
        
        assert hasattr(sense, 'scientific_name')
        assert sense.scientific_name is not None
        assert sense.scientific_name['la'] == 'Homo sapiens'
        assert 'scientific: Homo sapiens' in sense.scientific_name['en']
    
    def test_parse_literal_meaning_field(self) -> None:
        """Test parsing literal-meaning field from LIFT XML (SENSE LEVEL - Day 28)."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry">
        <lexical-unit>
            <form lang="en"><text>butterfly</text></form>
        </lexical-unit>
        <sense id="sense1">
            <definition>
                <form lang="en"><text>An insect</text></form>
            </definition>
            <field type="literal-meaning">
                <form lang="en"><text>butter-fly</text></form>
                <form lang="de"><text>Butter-Fliege</text></form>
            </field>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert hasattr(sense, 'literal_meaning')
        assert sense.literal_meaning is not None
        assert sense.literal_meaning['en'] == 'butter-fly'
        assert sense.literal_meaning['de'] == 'Butter-Fliege'
    
    def test_roundtrip_all_custom_fields(self) -> None:
        """Test complete roundtrip: create → serialize → parse → verify (literal_meaning on sense - Day 28)."""
        # Create entry with all custom fields
        original_entry = Entry()
        original_entry.id = 'botanical_entry'
        original_entry.lexical_unit = {'en': 'sunflower', 'la': 'helianthus'}
        
        sense = Sense()
        sense.id = 'sense1'
        sense.definition = {'en': 'A tall plant with large yellow flowers'}
        sense.exemplar = {'en': 'giant sunflower', 'la': 'helianthus giganteus'}
        sense.scientific_name = {'la': 'Helianthus annuus'}
        sense.literal_meaning = {'en': 'sun-flower', 'fr': 'fleur de soleil'}
        
        original_entry.senses = [sense]
        
        # Serialize to XML
        parser = LIFTParser()
        xml_str = parser.generate_lift_string([original_entry])
        
        # Parse back from XML
        parsed_entries = parser.parse_lift_content(xml_str)
        
        # Verify roundtrip
        assert len(parsed_entries) == 1
        parsed_entry = parsed_entries[0]
        
        # Verify sense custom fields
        assert len(parsed_entry.senses) == 1
        parsed_sense = parsed_entry.senses[0]
        
        # Verify sense literal_meaning (sense-level field)
        assert parsed_sense.literal_meaning is not None
        assert parsed_sense.literal_meaning['en'] == 'sun-flower'
        assert parsed_sense.literal_meaning['fr'] == 'fleur de soleil'
        
        assert parsed_sense.exemplar is not None
        assert parsed_sense.exemplar['en'] == 'giant sunflower'
        assert parsed_sense.exemplar['la'] == 'helianthus giganteus'
        
        assert parsed_sense.scientific_name is not None
        assert parsed_sense.scientific_name['la'] == 'Helianthus annuus'
    
    def test_empty_custom_fields_not_serialized(self) -> None:
        """Test that None/empty custom fields don't appear in XML."""
        entry = Entry()
        entry.id = 'simple_entry'
        entry.lexical_unit = {'en': 'word'}
        
        sense = Sense()
        sense.id = 'sense1'
        sense.definition = {'en': 'definition'}
        sense.literal_meaning = None  # Should not appear in XML
        sense.exemplar = None  # Should not appear
        sense.scientific_name = None  # Should not appear
        
        entry.senses = [sense]
        
        parser = LIFTParser()
        xml_str = parser.generate_lift_string([entry])
        
        # Verify custom fields are not in XML
        assert '<field type="exemplar">' not in xml_str
        assert '<field type="scientific-name">' not in xml_str
        assert '<field type="literal-meaning">' not in xml_str
