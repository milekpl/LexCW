"""
Unit tests for sense-level relations in LIFT 0.13.

Tests parsing and generation of relations within sense elements,
including synonyms, antonyms, and other semantic relationships.
"""

from __future__ import annotations

import pytest

from app.models.sense import Sense
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
        assert sense.relations[0]['ref'] == 'joyful_sense_002'
    
    def test_parse_sense_with_antonym_relation(self) -> None:
        """Test parsing a sense with an antonym relation."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test_001">
                <lexical-unit><form lang="en"><text>happy</text></form></lexical-unit>
                <sense id="sense_001">
                    <gloss lang="en"><text>feeling joy</text></gloss>
                    <relation type="antonym" ref="sad_sense_003"/>
                </sense>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        sense = entries[0].senses[0]
        assert len(sense.relations) == 1
        assert sense.relations[0]['type'] == 'antonym'
        assert sense.relations[0]['ref'] == 'sad_sense_003'
    
    def test_parse_sense_with_multiple_relations(self) -> None:
        """Test parsing a sense with multiple relations."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test_001">
                <lexical-unit><form lang="en"><text>dog</text></form></lexical-unit>
                <sense id="sense_001">
                    <gloss lang="en"><text>canine animal</text></gloss>
                    <relation type="synonym" ref="canine_sense_002"/>
                    <relation type="hypernym" ref="animal_sense_003"/>
                    <relation type="hyponym" ref="poodle_sense_004"/>
                </sense>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        sense = entries[0].senses[0]
        assert len(sense.relations) == 3
        assert sense.relations[0]['type'] == 'synonym'
        assert sense.relations[1]['type'] == 'hypernym'
        assert sense.relations[2]['type'] == 'hyponym'
    
    def test_parse_sense_without_relations(self) -> None:
        """Test parsing a sense without any relations."""
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test_001">
                <lexical-unit><form lang="en"><text>unique</text></form></lexical-unit>
                <sense id="sense_001">
                    <gloss lang="en"><text>one of a kind</text></gloss>
                </sense>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        sense = entries[0].senses[0]
        assert len(sense.relations) == 0


class TestSenseRelationGeneration:
    """Test generating LIFT XML with sense relations."""
    
    def test_generate_sense_with_synonym_relation(self) -> None:
        """Test generating XML for a sense with a synonym relation."""
        from app.models.entry import Entry
        
        sense = Sense(id_='sense_001')
        sense.glosses = {'en': 'feeling joy'}
        sense.add_relation('synonym', 'joyful_sense_002')
        
        entry = Entry(id_='test_001')
        entry.lexical_unit = {'en': 'happy'}
        entry.senses = [sense]
        
        parser = LIFTParser(validate=False)
        xml_str = parser.generate_lift_string([entry])
        
        assert 'id="sense_001"' in xml_str
        assert 'type="synonym"' in xml_str
        assert 'ref="joyful_sense_002"' in xml_str
    
    def test_generate_sense_with_antonym_relation(self) -> None:
        """Test generating XML for a sense with an antonym relation."""
        from app.models.entry import Entry
        
        sense = Sense(id_='sense_001')
        sense.glosses = {'en': 'feeling joy'}
        sense.add_relation('antonym', 'sad_sense_003')
        
        entry = Entry(id_='test_001')
        entry.lexical_unit = {'en': 'happy'}
        entry.senses = [sense]
        
        parser = LIFTParser(validate=False)
        xml_str = parser.generate_lift_string([entry])
        
        assert 'type="antonym"' in xml_str
        assert 'ref="sad_sense_003"' in xml_str
    
    def test_generate_sense_with_multiple_relations(self) -> None:
        """Test generating XML for a sense with multiple relations."""
        from app.models.entry import Entry
        
        sense = Sense(id_='sense_001')
        sense.glosses = {'en': 'canine animal'}
        sense.add_relation('synonym', 'canine_sense_002')
        sense.add_relation('hypernym', 'animal_sense_003')
        sense.add_relation('hyponym', 'poodle_sense_004')
        
        entry = Entry(id_='test_001')
        entry.lexical_unit = {'en': 'dog'}
        entry.senses = [sense]
        
        parser = LIFTParser(validate=False)
        xml_str = parser.generate_lift_string([entry])
        
        assert 'type="synonym"' in xml_str
        assert 'type="hypernym"' in xml_str
        assert 'type="hyponym"' in xml_str
        assert xml_str.count('<lift:relation') == 3
    
    def test_generate_sense_without_relations(self) -> None:
        """Test generating XML for a sense without relations."""
        from app.models.entry import Entry
        
        sense = Sense(id_='sense_001')
        sense.glosses = {'en': 'one of a kind'}
        
        entry = Entry(id_='test_001')
        entry.lexical_unit = {'en': 'unique'}
        entry.senses = [sense]
        
        parser = LIFTParser(validate=False)
        xml_str = parser.generate_lift_string([entry])
        
        assert '<lift:relation' not in xml_str


class TestSenseRelationRoundTrip:
    """Test round-trip preservation of sense relations."""
    
    def test_round_trip_sense_relations(self) -> None:
        """Test that sense relations survive parse-generate-parse cycle."""
        original_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test_001">
                <lexical-unit><form lang="en"><text>big</text></form></lexical-unit>
                <sense id="sense_001">
                    <gloss lang="en"><text>large in size</text></gloss>
                    <relation type="synonym" ref="large_sense_002"/>
                    <relation type="antonym" ref="small_sense_003"/>
                </sense>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries[0].senses[0].relations) == 2
        
        # Generate XML
        generated_xml = parser.generate_lift_string(entries)
        
        # Parse generated XML
        re_parsed_entries = parser.parse_string(generated_xml)
        
        # Verify relations preserved
        original_sense = entries[0].senses[0]
        reparsed_sense = re_parsed_entries[0].senses[0]
        
        assert len(reparsed_sense.relations) == len(original_sense.relations)
        assert reparsed_sense.relations[0]['type'] == original_sense.relations[0]['type']
        assert reparsed_sense.relations[0]['ref'] == original_sense.relations[0]['ref']
        assert reparsed_sense.relations[1]['type'] == original_sense.relations[1]['type']
        assert reparsed_sense.relations[1]['ref'] == original_sense.relations[1]['ref']
