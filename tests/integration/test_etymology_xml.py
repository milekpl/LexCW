"""
Integration tests for Etymology XML parsing/generation (Day 45-46).

Tests LIFT 0.13 XML round-trip for:
- Etymology comment field
- Etymology custom fields
- Backward compatibility with existing gloss
"""

import pytest
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry, Etymology


@pytest.mark.integration
class TestEtymologyCommentXML:
    """Test etymology comment field in LIFT XML."""
    
    def test_parse_etymology_with_comment(self):
        """LIFTParser can parse etymology with comment field."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="cat">
                <lexical-unit>
                    <form lang="en"><text>cat</text></form>
                </lexical-unit>
                <etymology type="inheritance" source="Latin">
                    <form lang="la"><text>cattus</text></form>
                    <gloss lang="en"><text>cat</text></gloss>
                    <field type="comment">
                        <form lang="en"><text>Borrowed via Old French</text></form>
                    </field>
                </etymology>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(xml)
        
        assert len(entries) == 1
        assert len(entries[0].etymologies) == 1
        
        etym = entries[0].etymologies[0]
        assert etym.comment == {'en': 'Borrowed via Old French'}
        assert etym.form == {'la': 'cattus'}
        assert etym.gloss == {'en': 'cat'}
    
    def test_generate_etymology_with_comment(self):
        """LIFTParser generates etymology comment field in XML."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'},
            comment={'en': 'Borrowed via Old French'}
        )
        
        entry = Entry(
            id_='cat',
            lexical_unit={'en': 'cat'},
            etymologies=[etym]
        )
        
        parser = LIFTParser(validate=False)
        xml_output = parser.generate_lift_string([entry])
        
        assert 'type="comment"' in xml_output
        assert 'Borrowed via Old French' in xml_output


@pytest.mark.integration
class TestEtymologyCustomFieldsXML:
    """Test etymology custom fields in LIFT XML."""
    
    def test_parse_etymology_with_custom_fields(self):
        """LIFTParser can parse etymology with multiple custom fields."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="cat">
                <lexical-unit>
                    <form lang="en"><text>cat</text></form>
                </lexical-unit>
                <etymology type="inheritance" source="Latin">
                    <form lang="la"><text>cattus</text></form>
                    <gloss lang="en"><text>cat</text></gloss>
                    <field type="certainty">
                        <form lang="en"><text>high</text></form>
                    </field>
                    <field type="note">
                        <form lang="en"><text>Well-documented</text></form>
                    </field>
                </etymology>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(xml)
        
        assert len(entries) == 1
        etym = entries[0].etymologies[0]
        
        assert etym.custom_fields == {
            'certainty': {'en': 'high'},
            'note': {'en': 'Well-documented'}
        }
    
    def test_generate_etymology_with_custom_fields(self):
        """LIFTParser generates etymology custom fields in XML."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'},
            custom_fields={
                'certainty': {'en': 'high'},
                'note': {'en': 'Well-documented'}
            }
        )
        
        entry = Entry(
            id_='cat',
            lexical_unit={'en': 'cat'},
            etymologies=[etym]
        )
        
        parser = LIFTParser(validate=False)
        xml_output = parser.generate_lift_string([entry])
        
        assert 'type="certainty"' in xml_output
        assert 'type="note"' in xml_output
        assert 'Well-documented' in xml_output


@pytest.mark.integration
class TestEtymologyBackwardCompatibility:
    """Test backward compatibility with existing etymology parsing."""
    
    def test_parse_etymology_without_custom_fields(self):
        """Etymology without custom fields parses correctly."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="cat">
                <lexical-unit>
                    <form lang="en"><text>cat</text></form>
                </lexical-unit>
                <etymology type="inheritance" source="Latin">
                    <form lang="la"><text>cattus</text></form>
                    <gloss lang="en"><text>cat</text></gloss>
                </etymology>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(xml)
        
        assert len(entries) == 1
        etym = entries[0].etymologies[0]
        
        assert etym.comment is None
        assert etym.custom_fields == {}
        assert etym.form == {'la': 'cattus'}
        assert etym.gloss == {'en': 'cat'}


@pytest.mark.integration
class TestEtymologyRoundTrip:
    """Test round-trip preservation of etymology enhancements."""
    
    def test_round_trip_with_comment_and_custom_fields(self):
        """Etymology with comment and custom fields survives XML round-trip."""
        original_etym = Etymology(
            type='borrowing',
            source='French',
            form={'fr': 'rendezvous'},
            gloss={'en': 'appointment'},
            comment={'en': 'Military term originally'},
            custom_fields={
                'date': {'en': '18th century'},
                'certainty': {'en': 'high'}
            }
        )
        
        original_entry = Entry(
            id_='rendezvous',
            lexical_unit={'en': 'rendezvous'},
            etymologies=[original_etym]
        )
        
        parser = LIFTParser(validate=False)
        
        # Generate XML
        xml_output = parser.generate_lift_string([original_entry])
        
        # Parse it back
        parsed_entries = parser.parse_string(xml_output)
        
        assert len(parsed_entries) == 1
        parsed_etym = parsed_entries[0].etymologies[0]
        
        assert parsed_etym.type == 'borrowing'
        assert parsed_etym.source == 'French'
        assert parsed_etym.form == {'fr': 'rendezvous'}
        assert parsed_etym.gloss == {'en': 'appointment'}
        assert parsed_etym.comment == {'en': 'Military term originally'}
        assert parsed_etym.custom_fields == {
            'date': {'en': '18th century'},
            'certainty': {'en': 'high'}
        }
