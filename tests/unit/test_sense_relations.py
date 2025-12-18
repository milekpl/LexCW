"""
Unit tests for sense-level relations in LIFT 0.13.

Tests parsing and generation of relations within sense elements,
including synonyms, antonyms, and other semantic relationships.
"""

from __future__ import annotations

import pytest

from app.models.sense import Sense
from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser


pytestmark = pytest.mark.skip_et_mock


class TestSenseRelationParsing:
    """Test parsing sense relations from LIFT XML."""
    
    def test_parse_sense_with_synonym_relation(self) -> None:
        """Test parsing a sense with a synonym relation."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test_001">
                <lexical-unit><form lang="en"><text>happy</text></form></lexical-unit>
                <sense id="sense_001">
                    <gloss lang="en"><text>feeling joy</text></gloss>
                    <relation type="synonym" ref="joyful_sense_002"/>
                </sense>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        assert len(entries[0].senses) == 1
        
        sense = entries[0].senses[0]
        assert len(sense.relations) == 1
        assert sense.relations[0]['type'] == 'synonym'
        entry = Entry(id_='test_001')
        entry.lexical_unit = {'en': 'dog'}
        entry.senses = [sense]
        
        parser = LIFTParser(validate=False)
        xml_str = parser.generate_lift_string([entry])
        
        assert 'type="synonym"' in xml_str
        assert 'type="hypernym"' in xml_str
        assert 'type="hyponym"' in xml_str
        assert xml_str.count('<lift:relation') == 3
    
    def test_parse_sense_with_synonym_relation(self) -> None:
        """Test parsing a sense with a synonym relation."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test_001">
                <lexical-unit><form lang="en"><text>happy</text></form></lexical-unit>
                <sense id="sense_001">
                    <gloss lang="en"><text>feeling joy</text></gloss>
                    <relation type="synonym" ref="joyful_sense_002"/>
                </sense>
            </entry>
        </lift>'''

        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)

        assert len(entries) == 1
        assert len(entries[0].senses) == 1

        sense = entries[0].senses[0]
        assert len(sense.relations) == 1
        assert sense.relations[0]['type'] == 'synonym'
        assert sense.relations[0]['ref'] == 'joyful_sense_002'


