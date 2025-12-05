"""
Integration tests for pronunciation media elements (Day 35).

Tests XML parsing and generation of media elements within pronunciation.
"""

import pytest
from app.parsers.lift_parser import LIFTParser


@pytest.mark.integration
class TestPronunciationMediaXMLParsing:
    """Test parsing of media elements from LIFT XML."""
    
    def test_parse_single_media_without_label(self):
        """Test parsing a single media element without label."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <pronunciation>
        <media href="audio/test.mp3"/>
    </pronunciation>
    <sense>
        <gloss lang="en"><text>a test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert len(entries) == 1
        entry = entries[0]
        
        assert len(entry.pronunciation_media) == 1
        assert entry.pronunciation_media[0]['href'] == 'audio/test.mp3'
        assert 'label' not in entry.pronunciation_media[0]
    
    def test_parse_single_media_with_label(self):
        """Test parsing media element with multilingual label."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test2">
    <lexical-unit>
        <form lang="en"><text>hello</text></form>
    </lexical-unit>
    <pronunciation>
        <media href="audio/hello.mp3">
            <label>
                <form lang="en"><text>Audio pronunciation</text></form>
                <form lang="fr"><text>Prononciation audio</text></form>
            </label>
        </media>
    </pronunciation>
    <sense>
        <gloss lang="en"><text>greeting</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert len(entries) == 1
        entry = entries[0]
        
        assert len(entry.pronunciation_media) == 1
        media = entry.pronunciation_media[0]
        assert media['href'] == 'audio/hello.mp3'
        assert media['label']['en'] == 'Audio pronunciation'
        assert media['label']['fr'] == 'Prononciation audio'
    
    def test_parse_multiple_media_elements(self):
        """Test parsing multiple media elements."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test3">
    <lexical-unit>
        <form lang="en"><text>word</text></form>
    </lexical-unit>
    <pronunciation>
        <media href="audio/word1.mp3">
            <label>
                <form lang="en"><text>First audio</text></form>
            </label>
        </media>
        <media href="audio/word2.wav">
            <label>
                <form lang="en"><text>Second audio</text></form>
            </label>
        </media>
    </pronunciation>
    <sense>
        <gloss lang="en"><text>a word</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert len(entries) == 1
        entry = entries[0]
        
        assert len(entry.pronunciation_media) == 2
        assert entry.pronunciation_media[0]['href'] == 'audio/word1.mp3'
        assert entry.pronunciation_media[0]['label']['en'] == 'First audio'
        assert entry.pronunciation_media[1]['href'] == 'audio/word2.wav'
        assert entry.pronunciation_media[1]['label']['en'] == 'Second audio'
    
    def test_parse_media_with_url(self):
        """Test parsing media with absolute URL."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test4">
    <lexical-unit>
        <form lang="en"><text>remote</text></form>
    </lexical-unit>
    <pronunciation>
        <media href="https://example.com/audio/remote.mp3">
            <label>
                <form lang="en"><text>Remote audio file</text></form>
            </label>
        </media>
    </pronunciation>
    <sense>
        <gloss lang="en"><text>distant</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert len(entries) == 1
        entry = entries[0]
        
        assert len(entry.pronunciation_media) == 1
        assert entry.pronunciation_media[0]['href'] == 'https://example.com/audio/remote.mp3'
        assert entry.pronunciation_media[0]['label']['en'] == 'Remote audio file'


@pytest.mark.integration
class TestPronunciationMediaXMLGeneration:
    """Test generation of media elements to LIFT XML."""
    
    def test_generate_media_without_label(self):
        """Test generating media element without label."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test5">
    <lexical-unit>
        <form lang="en"><text>simple</text></form>
    </lexical-unit>
    <sense>
        <gloss lang="en"><text>easy</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        entry = entries[0]
        
        # Add simple media
        entry.pronunciation_media = [{'href': 'audio/hello.mp3'}]
        
        # Generate XML
        generated_xml = parser.generate_lift_string([entry])
        
        # Parse back
        reparsed_entries = parser.parse(generated_xml)
        assert len(reparsed_entries) == 1
        reparsed_entry = reparsed_entries[0]
        
        assert len(reparsed_entry.pronunciation_media) == 1
        assert reparsed_entry.pronunciation_media[0]['href'] == 'audio/hello.mp3'
    
    def test_generate_media_with_label(self):
        """Test generating media element with multilingual label."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test6">
    <lexical-unit>
        <form lang="en"><text>complex</text></form>
    </lexical-unit>
    <sense>
        <gloss lang="en"><text>complicated</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        entry = entries[0]
        
        # Add media with label
        entry.pronunciation_media = [{
            'href': 'audio/complex.mp3',
            'label': {
                'en': 'English pronunciation',
                'es': 'Pronunciación en español'
            }
        }]
        
        # Generate XML
        generated_xml = parser.generate_lift_string([entry])
        
        # Verify XML contains media and label
        assert 'href="audio/complex.mp3"' in generated_xml
        assert '<lift:label>' in generated_xml or '<label>' in generated_xml
        assert 'English pronunciation' in generated_xml
        assert 'Pronunciación en español' in generated_xml
        
        # Parse back
        reparsed_entries = parser.parse(generated_xml)
        reparsed_entry = reparsed_entries[0]
        
        assert len(reparsed_entry.pronunciation_media) == 1
        media = reparsed_entry.pronunciation_media[0]
        assert media['href'] == 'audio/complex.mp3'
        assert media['label']['en'] == 'English pronunciation'
        assert media['label']['es'] == 'Pronunciación en español'
    
    def test_generate_multiple_media(self):
        """Test generating multiple media elements."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test7">
    <lexical-unit>
        <form lang="en"><text>multiple</text></form>
    </lexical-unit>
    <sense>
        <gloss lang="en"><text>many</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        entry = entries[0]
        
        # Add multiple media
        entry.pronunciation_media = [
            {'href': 'audio/m1.mp3', 'label': {'en': 'First'}},
            {'href': 'audio/m2.wav', 'label': {'en': 'Second'}},
            {'href': 'audio/m3.ogg'}
        ]
        
        # Generate and reparse
        generated_xml = parser.generate_lift_string([entry])
        reparsed_entries = parser.parse(generated_xml)
        reparsed_entry = reparsed_entries[0]
        
        assert len(reparsed_entry.pronunciation_media) == 3
        assert reparsed_entry.pronunciation_media[0]['href'] == 'audio/m1.mp3'
        assert reparsed_entry.pronunciation_media[1]['href'] == 'audio/m2.wav'
        assert reparsed_entry.pronunciation_media[2]['href'] == 'audio/m3.ogg'
    
    def test_round_trip_preservation(self):
        """Test that media elements are preserved through parse-generate-parse cycle."""
        original_xml = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="roundtrip1">
    <lexical-unit>
        <form lang="en"><text>roundtrip</text></form>
    </lexical-unit>
    <pronunciation>
        <media href="audio/rt.mp3">
            <label>
                <form lang="en"><text>Round trip audio</text></form>
                <form lang="de"><text>Rundreise-Audio</text></form>
            </label>
        </media>
    </pronunciation>
    <sense>
        <gloss lang="en"><text>circular journey</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        
        # First parse
        entries1 = parser.parse(original_xml)
        
        # Generate
        generated_xml = parser.generate_lift_string(entries1)
        
        # Second parse
        entries2 = parser.parse(generated_xml)
        
        # Verify data preserved
        assert len(entries2) == 1
        entry = entries2[0]
        assert len(entry.pronunciation_media) == 1
        media = entry.pronunciation_media[0]
        assert media['href'] == 'audio/rt.mp3'
        assert media['label']['en'] == 'Round trip audio'
        assert media['label']['de'] == 'Rundreise-Audio'
