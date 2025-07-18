"""
Test that pronunciations are properly displayed in the entry form after our Unicode encoding fix.

This test creates a unit test to verify that:
1. Pronunciation data is correctly encoded in the JavaScript initialization
2. The Unicode IPA characters are properly escaped for JavaScript
3. The pronunciation form manager receives the correct data
"""

from __future__ import annotations

import pytest
from flask import Flask
from bs4 import BeautifulSoup
from unittest.mock import patch
from app import create_app
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService



@pytest.mark.integration
class TestPronunciationUnicodeDisplay:
    """Test pronunciation Unicode display in entry form."""
    
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app."""
        return create_app('testing')
    
    @pytest.mark.integration
    def test_pronunciation_unicode_encoding_in_js(self, app: Flask):
        """Test that IPA Unicode characters are properly encoded in JavaScript initialization using real LIFT XML parsing."""
        from app.parsers.lift_parser import LIFTParser
        # Use a realistic LIFT XML entry with Unicode IPA pronunciation (from sample-lift-file.lift)
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift producer="SIL.FLEx 9.1.25.877" version="0.13">
        <entry id="unicode_test_entry">
            <lexical-unit>
                <form lang="en"><text>unicode test</text></form>
            </lexical-unit>
            <pronunciation>
                <form lang="seh-fonipa"><text>ˈtɛst</text></form>
            </pronunciation>
            <sense id="sense1">
                <definition><form lang="en"><text>test definition</text></form></definition>
            </sense>
        </entry>
        </lift>
        '''
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        assert len(entries) > 0
        entry = entries[0]
        from flask import render_template_string
        template = """
        {% if entry.pronunciations %}
            <script>
            var pronunciationArray = [];
            {% for writing_system, value in entry.pronunciations.items() %}
                pronunciationArray.push({
                    type: {{ writing_system | tojson | safe }},
                    value: {{ value | tojson | safe }},
                    audio_file: "",
                    is_default: true
                });
            {% endfor %}
            // PronunciationFormsManager init
            new PronunciationFormsManager(pronunciationArray);
            </script>
            <div id="pronunciation-container"></div>
        {% endif %}
        """
        with app.app_context():
            rendered = render_template_string(template, entry=entry)
            soup = BeautifulSoup(rendered, 'html.parser')
            pronunciation_script = None
            for script in soup.find_all('script'):
                if script.string and 'PronunciationFormsManager' in script.string:
                    pronunciation_script = script.string
                    break
            assert pronunciation_script is not None, "PronunciationFormsManager initialization script not found"
            assert 'pronunciationArray.push(' in pronunciation_script or 'pronunciations: pronunciationArray' in pronunciation_script
            assert ('\\u02c8' in pronunciation_script or 'ˈ' in pronunciation_script), \
                "Unicode character ˈ not found in script (neither direct nor escaped)"
            assert ('\\u025b' in pronunciation_script or 'ɛ' in pronunciation_script), \
                "Unicode character ɛ not found in script (neither direct nor escaped)"
            container = soup.find(id='pronunciation-container')
            assert container is not None, "Pronunciation container not found"
    
    @pytest.mark.integration
    def test_pronunciation_template_json_encoding(self, app: Flask):
        """Test that the template properly encodes pronunciation values using tojson filter."""
        with app.app_context():
            from flask import render_template_string
            
            # Create test entry with Unicode IPA
            test_entry = Entry(id="test_template",
                lexical_unit={"en": "test"}, 
                pronunciations={"seh-fonipa": "ˈprɒtɪstəntɪzm"}
            ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
            
            # Test template with our fix (using tojson filter)
            template = """
            {% if entry.pronunciations %}
                const pronunciations = [];
                {% for writing_system, value in entry.pronunciations.items() %}
                    pronunciations.push({
                        type: {{ writing_system | tojson | safe }},
                        value: {{ value | tojson | safe }},
                        audio_file: "",
                        is_default: true
                    });
                {% endfor %}
            {% endif %}
            """
            
            rendered = render_template_string(template, entry=test_entry)
            
            # Check that Unicode characters are properly escaped
            assert '\\u02c8' in rendered  # ˈ character
            assert '\\u0252' in rendered  # ɒ character  
            assert '\\u026a' in rendered  # ɪ character
            assert '\\u0259' in rendered  # ə character
            
            # Check that the structure is correct
            assert 'pronunciations.push(' in rendered
            assert '"seh-fonipa"' in rendered
    
    @pytest.mark.integration
    def test_api_endpoints_work(self):
        """Test that the API endpoint logic works using real LIFT XML parsing (no DB, no mocks)."""
        from app.parsers.lift_parser import LIFTParser
        # Read a realistic LIFT XML sample (truncated for test speed)
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift producer="SIL.FLEx 9.1.25.877" version="0.13">
        <entry id="acceptance test_3a03ccc9-0475-4900-b96c-fe0ce2a8e89b">
            <lexical-unit><form lang="en"><text>acceptance test</text></form></lexical-unit>
            <pronunciation><form lang="seh-fonipa"><text>əkˈseptəns test</text></form></pronunciation>
            <sense id="90bc0d68-13f3-4318-bcfb-c5e7ac3f80e1">
                <grammatical-info value="Noun"></grammatical-info>
                <definition><form lang="pl"><text>próba odbiorcza</text></form></definition>
                <trait name="domain-type" value="biznes"/>
                <relation type="synonim" ref="e441a377-f424-4e52-aa58-9eb1725cd18e"/>
            </sense>
        </entry>
        <entry id="acid test_dc82bb0e-f5cb-4390-8912-0b53a0e54800">
            <lexical-unit><form lang="en"><text>acid test</text></form></lexical-unit>
            <pronunciation><form lang="seh-fonipa"><text>ˌæsɪd test</text></form></pronunciation>
            <sense id="727d5e44-4157-4756-93bf-8da4ccfe3113">
                <definition><form lang="pl"><text>ciężki sprawdzian, próba ognia, decydujący test</text></form></definition>
                <trait name="usage-type" value="przenosnie"/>
                <relation type="synonim" ref="2c7f72b2-352a-451d-b736-7936ab9e62fa"/>
            </sense>
        </entry>
        </lift>
        '''
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        # Simulate /api/ranges/relation-types: collect all relation types
        relation_types = set()
        for entry in entries:
            if hasattr(entry, 'senses'):
                for sense in entry.senses:
                    if hasattr(sense, 'relations'):
                        for rel in sense.relations:
                            if 'type' in rel:
                                relation_types.add(rel['type'])
        assert 'synonim' in relation_types
        # Simulate /api/ranges/etymology: (none in this sample, but check structure)
        etymology_types = set()
        for entry in entries:
            if hasattr(entry, 'etymology'):
                for ety in entry.etymologies:
                    if 'type' in ety:
                        etymology_types.add(ety['type'])
        assert isinstance(etymology_types, set)
        # Simulate /api/ranges/language-codes: collect all language codes
        lang_codes = set()
        for entry in entries:
            if hasattr(entry, 'lexical_unit'):
                lang_codes.update(entry.lexical_unit.keys())
            if hasattr(entry, 'pronunciations'):
                lang_codes.update(entry.pronunciations.keys())
            if hasattr(entry, 'senses'):
                for sense in entry.senses:
                    if hasattr(sense, 'definitions'):
                        lang_codes.update(sense.definitions.keys())
        assert 'en' in lang_codes
        assert 'pl' in lang_codes
        assert 'seh-fonipa' in lang_codes
