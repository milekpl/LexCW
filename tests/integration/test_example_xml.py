"""
Integration tests for Day 47-48: Example Enhancements

Tests XML parsing and generation for:
- Example source attribute
- Example note field
- Example custom fields
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.parsers.lift_parser import LIFTParser


@pytest.mark.integration
class TestExampleSourceXML:
    """Test example source attribute in LIFT XML."""
    
    def test_parse_example_source(self):
        """LIFTParser parses example source attribute."""
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
            <example source="corpus-ref-123">
                <form lang="en"><text>This is an example</text></form>
            </example>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert len(sense.examples) == 1
        example = sense.examples[0]
        assert example.source == 'corpus-ref-123'
    
    def test_generate_example_source(self):
        """LIFTParser generates example source in XML."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            source='corpus-ref-123'
        )
        
        sense = Sense(
            id_='sense1',
            definition={'en': 'A test sense'},
            examples=[example]
        )
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=[sense]
        )
        
        parser = LIFTParser(validate=False)
        xml_output = parser.generate_lift_string([entry])
        
        assert 'source="corpus-ref-123"' in xml_output
        assert 'id="ex1"' in xml_output


@pytest.mark.integration
class TestExampleNoteXML:
    """Test example note field in LIFT XML."""
    
    def test_parse_example_note(self):
        """LIFTParser parses example note field."""
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
            <example>
                <form lang="en"><text>This is an example</text></form>
                <field type="note">
                    <form lang="en"><text>This is an editorial note</text></form>
                    <form lang="fr"><text>Ceci est une note éditoriale</text></form>
                </field>
            </example>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert len(sense.examples) == 1
        example = sense.examples[0]
        assert example.note is not None
        assert example.note['en'] == 'This is an editorial note'
        assert example.note['fr'] == 'Ceci est une note éditoriale'
    
    def test_generate_example_note(self):
        """LIFTParser generates example note in XML."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            note={'en': 'This is an editorial note'}
        )
        
        sense = Sense(
            id_='sense1',
            definition={'en': 'A test sense'},
            examples=[example]
        )
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=[sense]
        )
        
        parser = LIFTParser(validate=False)
        xml_output = parser.generate_lift_string([entry])
        
        assert 'type="note"' in xml_output
        assert 'This is an editorial note' in xml_output


@pytest.mark.integration
class TestExampleCustomFieldsXML:
    """Test example custom fields in LIFT XML."""
    
    def test_parse_example_custom_fields(self):
        """LIFTParser parses example custom fields."""
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
            <example>
                <form lang="en"><text>This is an example</text></form>
                <field type="certainty">
                    <form lang="en"><text>high</text></form>
                </field>
                <field type="register">
                    <form lang="en"><text>formal</text></form>
                </field>
            </example>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        sense = entry.senses[0]
        example = sense.examples[0]
        assert 'certainty' in example.custom_fields
        assert example.custom_fields['certainty']['en'] == 'high'
        assert 'register' in example.custom_fields
        assert example.custom_fields['register']['en'] == 'formal'
    
    def test_generate_example_custom_fields(self):
        """LIFTParser generates example custom fields in XML."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            custom_fields={
                'certainty': {'en': 'high'},
                'register': {'en': 'formal'}
            }
        )
        
        sense = Sense(
            id_='sense1',
            definition={'en': 'A test sense'},
            examples=[example]
        )
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=[sense]
        )
        
        parser = LIFTParser(validate=False)
        xml_output = parser.generate_lift_string([entry])
        
        assert 'type="certainty"' in xml_output
        assert 'type="register"' in xml_output
        assert 'high' in xml_output
        assert 'formal' in xml_output


@pytest.mark.integration
class TestExampleBackwardCompatibility:
    """Test that examples without enhancements still work."""
    
    def test_parse_simple_example(self):
        """LIFTParser parses simple examples without enhancements."""
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
            <example>
                <form lang="en"><text>This is an example</text></form>
            </example>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        sense = entry.senses[0]
        example = sense.examples[0]
        assert example.source is None
        assert example.note is None
        assert example.custom_fields == {}


@pytest.mark.integration
class TestExampleRoundTrip:
    """Test round-trip preservation of example enhancements."""
    
    def test_round_trip_all_enhancements(self):
        """Example enhancements survive round-trip parsing."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example', 'fr': 'Ceci est un exemple'},
            translations={'pl': 'To jest przykład'},
            source='corpus-ref-123',
            note={'en': 'Editorial note', 'fr': 'Note éditoriale'},
            custom_fields={
                'certainty': {'en': 'high'},
                'register': {'en': 'formal', 'fr': 'formel'}
            }
        )
        
        sense = Sense(
            id_='sense1',
            definition={'en': 'A test sense'},
            examples=[example]
        )
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=[sense]
        )
        
        parser = LIFTParser(validate=False)
        xml_output = parser.generate_lift_string([entry])
        
        # Parse the generated XML
        entries = parser.parse_string(xml_output)
        
        assert len(entries) == 1
        parsed_entry = entries[0]
        parsed_sense = parsed_entry.senses[0]
        parsed_example = parsed_sense.examples[0]
        
        # Verify all attributes preserved
        assert parsed_example.source == 'corpus-ref-123'
        assert parsed_example.note == {'en': 'Editorial note', 'fr': 'Note éditoriale'}
        assert 'certainty' in parsed_example.custom_fields
        assert parsed_example.custom_fields['certainty']['en'] == 'high'
        assert 'register' in parsed_example.custom_fields
        assert parsed_example.custom_fields['register']['en'] == 'formal'
        assert parsed_example.custom_fields['register']['fr'] == 'formel'
