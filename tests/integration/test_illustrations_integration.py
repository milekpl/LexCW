"""
Integration tests for LIFT illustrations feature.

Tests XML parsing and generation of illustration elements with href and multilingual labels.
"""

import pytest
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry


@pytest.mark.integration
class TestIllustrationsXMLParsing:
    """Test parsing of illustration elements from LIFT XML."""
    
    def test_parse_single_illustration_with_label(self):
        """Test parsing a single illustration with multilingual label."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>a test word</text></gloss>
            <illustration href="images/test.jpg">
                <label>
                    <form lang="en"><text>Test Image</text></form>
                    <form lang="fr"><text>Image de test</text></form>
                </label>
            </illustration>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert len(entries) == 1
        entry = entries[0]
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        
        # Check illustrations
        assert len(sense.illustrations) == 1
        illustration = sense.illustrations[0]
        assert illustration['href'] == 'images/test.jpg'
        assert 'label' in illustration
        assert illustration['label']['en'] == 'Test Image'
        assert illustration['label']['fr'] == 'Image de test'
    
    def test_parse_multiple_illustrations(self):
        """Test parsing multiple illustrations on a single sense."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>desert</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>arid region</text></gloss>
            <illustration href="Desert.jpg">
                <label>
                    <form lang="fr"><text>Desert</text></form>
                </label>
            </illustration>
            <illustration href="subfolder/MyPic.jpg">
                <label>
                    <form lang="fr"><text>My picture</text></form>
                </label>
            </illustration>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert len(entries) == 1
        sense = entries[0].senses[0]
        
        # Check two illustrations
        assert len(sense.illustrations) == 2
        assert sense.illustrations[0]['href'] == 'Desert.jpg'
        assert sense.illustrations[0]['label']['fr'] == 'Desert'
        assert sense.illustrations[1]['href'] == 'subfolder/MyPic.jpg'
        assert sense.illustrations[1]['label']['fr'] == 'My picture'
    
    def test_parse_illustration_without_label(self):
        """Test parsing an illustration with href only (no label)."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>test</text></gloss>
            <illustration href="simple.png"/>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        sense = entries[0].senses[0]
        assert len(sense.illustrations) == 1
        illustration = sense.illustrations[0]
        assert illustration['href'] == 'simple.png'
        assert 'label' not in illustration or illustration.get('label') == {}
    
    def test_parse_illustration_with_url(self):
        """Test parsing illustration with absolute URL."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>test</text></gloss>
            <illustration href="https://example.com/image.jpg">
                <label>
                    <form lang="en"><text>Remote Image</text></form>
                </label>
            </illustration>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        sense = entries[0].senses[0]
        assert len(sense.illustrations) == 1
        assert sense.illustrations[0]['href'] == 'https://example.com/image.jpg'
        assert sense.illustrations[0]['label']['en'] == 'Remote Image'


@pytest.mark.integration
class TestIllustrationsXMLGeneration:
    """Test generation of illustration elements to LIFT XML."""
    
    def test_generate_single_illustration_with_label(self):
        """Test generating XML for a single illustration with multilingual label."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'},
            senses=[{
                'id': 's1',
                'glosses': {'en': 'test word'},
                'illustrations': [
                    {
                        'href': 'images/test.jpg',
                        'label': {
                            'en': 'Test Image',
                            'fr': 'Image de test'
                        }
                    }
                ]
            }]
        )
        
        parser = LIFTParser()
        xml_output = parser.generate_lift_string([entry])
        
        # Check XML contains illustration element with namespace prefix
        assert '<lift:illustration href="images/test.jpg">' in xml_output
        assert '<lift:label>' in xml_output
        assert '<lift:form lang="en">' in xml_output and '<lift:text>Test Image</lift:text>' in xml_output
        assert '<lift:form lang="fr">' in xml_output and '<lift:text>Image de test</lift:text>' in xml_output
        assert '</lift:illustration>' in xml_output
    
    def test_generate_multiple_illustrations(self):
        """Test generating XML for multiple illustrations."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'desert'},
            senses=[{
                'id': 's1',
                'glosses': {'en': 'arid region'},
                'illustrations': [
                    {
                        'href': 'Desert.jpg',
                        'label': {'fr': 'Desert'}
                    },
                    {
                        'href': 'subfolder/MyPic.jpg',
                        'label': {'fr': 'My picture'}
                    }
                ]
            }]
        )
        
        parser = LIFTParser()
        xml_output = parser.generate_lift_string([entry])
        
        # Check both illustrations are present
        assert '<lift:illustration href="Desert.jpg">' in xml_output
        assert '<lift:illustration href="subfolder/MyPic.jpg">' in xml_output
        assert xml_output.count('<lift:illustration') == 2
        assert xml_output.count('</lift:illustration>') == 2
    
    def test_generate_illustration_without_label(self):
        """Test generating XML for illustration with href only."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'},
            senses=[{
                'id': 's1',
                'glosses': {'en': 'test'},
                'illustrations': [
                    {'href': 'simple.png'}
                ]
            }]
        )
        
        parser = LIFTParser()
        xml_output = parser.generate_lift_string([entry])
        
        # Check illustration with href only (self-closing or empty)
        assert 'href="simple.png"' in xml_output
        # Should not have label element
        assert '<lift:label>' not in xml_output
    
    def test_round_trip_preservation(self):
        """Test that illustrations are preserved through parse then generate cycle."""
        xml_input = '''<?xml version="1.0" encoding="utf-8"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>test word</text></gloss>
            <illustration href="images/photo.jpg">
                <label>
                    <form lang="en"><text>Photo</text></form>
                    <form lang="es"><text>Foto</text></form>
                </label>
            </illustration>
        </sense>
    </entry>
</lift>'''
        
        parser = LIFTParser()
        
        # Parse
        entries = parser.parse(xml_input)
        assert len(entries) == 1
        
        # Check parsed data
        sense = entries[0].senses[0]
        assert len(sense.illustrations) == 1
        assert sense.illustrations[0]['href'] == 'images/photo.jpg'
        assert sense.illustrations[0]['label']['en'] == 'Photo'
        assert sense.illustrations[0]['label']['es'] == 'Foto'
        
        # Generate
        xml_output = parser.generate_lift_string(entries)
        
        # Check generated XML (with namespace prefix)
        assert '<lift:illustration href="images/photo.jpg">' in xml_output
        assert '<lift:form lang="en">' in xml_output and '<lift:text>Photo</lift:text>' in xml_output
        assert '<lift:form lang="es">' in xml_output and '<lift:text>Foto</lift:text>' in xml_output
        
        # Parse again to verify round-trip
        entries_round_trip = parser.parse(xml_output)
        sense_round_trip = entries_round_trip[0].senses[0]
        
        # Verify data matches
        assert len(sense_round_trip.illustrations) == 1
        assert sense_round_trip.illustrations[0]['href'] == 'images/photo.jpg'
        assert sense_round_trip.illustrations[0]['label']['en'] == 'Photo'
        assert sense_round_trip.illustrations[0]['label']['es'] == 'Foto'
