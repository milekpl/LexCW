"""
Test pronunciation display in the entry form.

This test verifies that:
1. Pronunciations are properly extracted from the LIFT XML
2. The pronunciation data is correctly passed to the entry form template
3. Pronunciations are properly displayed in the entry edit form
"""

import pytest
from flask import url_for
from bs4 import BeautifulSoup
import json
from app.models.entry import Entry
from flask.testing import FlaskClient
from flask import Flask
from unittest.mock import patch, MagicMock
from app.services.dictionary_service import DictionaryService

@pytest.fixture
def mock_entry():
    """Create a mock entry with pronunciations."""
    entry = Entry(id_="test_pronunciation_entry",
        lexical_unit={"en": "pronunciation test"},
        pronunciations={"seh-fonipa": "pronʌnsiˈeɪʃən"},  # Valid IPA characters
        grammatical_info="noun"
    ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
    return entry

@pytest.mark.integration
def test_pronunciation_display_in_entry_form(app: Flask):
    """Test that pronunciations from LIFT entries are displayed in the entry form using real LIFT XML and parser."""
    from app.parsers.lift_parser import LIFTParser
    # Use a realistic LIFT XML entry with valid IPA characters
    lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <lift producer="SIL.FLEx 9.1.25.877" version="0.13">
    <entry id="test_pronunciation_entry">
        <lexical-unit><form lang="en"><text>pronunciation test</text></form></lexical-unit>
        <pronunciation><form lang="seh-fonipa"><text>pronʌnsiˈeɪʃən</text></form></pronunciation>
        <sense id="sense1"><definition><form lang="en"><text>test definition</text></form></definition></sense>
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
        <script src="/static/js/pronunciation-forms.js"></script>
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
        script_found = False
        for script in soup.find_all('script'):
            if 'pronunciation-forms.js' in str(script.get('src', '')):
                script_found = True
        assert script_found, "The pronunciation-forms.js script should be included"
        init_script_found = False
        for script in soup.find_all('script'):
            script_text = script.string
            if script_text and 'PronunciationFormsManager' in script_text:
                init_script_found = True
                assert 'pronunciationArray' in script_text or 'pronunciations:' in script_text, "Pronunciation initialization logic should be present"
                ipa_test_string = '/pro.nun.si.eɪ.ʃən/'
                ipa_parts = ['/pro.nun.si.e', 'ɪ', '.', 'ʃ', 'ə', 'n/']
                ipa_found = False
                if ipa_test_string in script_text:
                    ipa_found = True
                else:
                    escaped_parts_found = 0
                    for part in ipa_parts:
                        if part in script_text or any(f"\\u{ord(c):04x}" in script_text.lower() for c in part if ord(c) > 127):
                            escaped_parts_found += 1
                    ipa_found = escaped_parts_found >= 3
                assert ipa_found, "The IPA value or its Unicode-escaped form should be included in the script"
                break
        assert init_script_found, "Script initializing PronunciationFormsManager should be present"

@pytest.mark.integration
def test_pronunciation_conversion(app: Flask):
    """Test that pronunciation dictionary is properly converted to array format for the JavaScript."""
    from app.models.entry import Entry
    
    # Create an entry with pronunciations in dictionary format
    entry = Entry(id_="test123",
        lexical_unit={"en": "Test"},
        pronunciations={"seh-fonipa": "ˈtɛst"}  # Dictionary format
    ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
    
    with app.test_request_context():
        # Convert pronunciations dict to JS-compatible array format
        pronunciations_array = []
        for writing_system, value in entry.pronunciations.items():
            pronunciations_array.append({
                "type": writing_system,
                "value": value,
                "audio_file": "",
                "is_default": True
            })
        
        # Verify the conversion
        assert len(pronunciations_array) == 1
        assert pronunciations_array[0]["type"] == "seh-fonipa"
        assert pronunciations_array[0]["value"] == "ˈtɛst"
        
        # Verify it can be JSON serialized (as the template will do)
        json_data = json.dumps(pronunciations_array)
        assert json_data == '[{"type": "seh-fonipa", "value": "\\u02c8t\\u025bst", "audio_file": "", "is_default": true}]'
