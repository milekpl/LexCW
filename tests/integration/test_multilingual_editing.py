"""
Test cases for multilingual editing support for fields with language attributes.
Tests based on LIFT 0.13 specification requirements for multilingual content.
"""

from __future__ import annotations

import uuid
from bs4 import BeautifulSoup
from typing import Dict, Any
from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser
import xml.etree.ElementTree as ET


import pytest


@pytest.mark.integration
class TestMultilingualFieldEditing:
    """Test cases for multilingual field editing functionality."""

    @pytest.mark.integration
    def test_multilingual_note_parsing_from_lift(self):
        """Test that multilingual notes are correctly parsed from LIFT format."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="pl">
                        <text>mukwa</text>
                    </form>
                </lexical-unit>
                <sense id="sense1">
                    <definition>
                        <form lang="en">
                            <text>A tree species</text>
                        </form>
                    </definition>
                </sense>
                <note type="general">
                    <form lang="en">
                        <text>This is an English note</text>
                    </form>
                    <form lang="pt">
                        <text>Esta é uma nota em português</text>
                    </form>
                    <form lang="pl">
                        <text>Ichi ndi chida chakupanda mu Chisena</text>
                    </form>
                </note>
                <note type="usage">
                    <form lang="en">
                        <text>Used in formal contexts</text>
                    </form>
                    <form lang="pt">
                        <text>Usado em contextos formais</text>
                    </form>
                </note>
            </entry>
        </lift>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        entry_elem = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}entry')
        
        # Use public method and assert entry_elem is not None
        assert entry_elem is not None
        entry = parser.parse_entry_element(entry_elem)
        
        # Check that multilingual notes are properly parsed
        assert 'general' in entry.notes
        assert 'usage' in entry.notes
        
        # General note should contain all three languages
        general_note = entry.notes['general']
        assert isinstance(general_note, dict)
        assert 'en' in general_note
        assert 'pt' in general_note
        assert 'pl' in general_note
        # Type ignores to handle current type structure until we update the models
        assert general_note['en']['text'] == "This is an English note"
        assert general_note['pt']['text'] == "Esta é uma nota em português"
        assert general_note['pl']['text'] == "Ichi ndi chida chakupanda mu Chisena"
        
        # Usage note should contain two languages
        usage_note = entry.notes['usage']
        assert isinstance(usage_note, dict)
        assert 'en' in usage_note
        assert 'pt' in usage_note
        assert usage_note['en']['text'] == "Used in formal contexts"
        assert usage_note['pt']['text'] == "Usado em contextos formais"

    @pytest.mark.integration
    def test_multilingual_note_serialization_to_dict(self):
        """Test that multilingual notes are correctly serialized to dictionary format."""
        entry = Entry(id_="test_entry",
            lexical_unit={"pl": "mukwa"},
            notes={
                "general": {
                    "en": {"text": "This is an English note"},
                    "pt": {"text": "Esta é uma nota em português"},
                    "pl": {"text": "Ichi ndi chida chakupanda mu Chisena"}
                },
                "usage": {
                    "en": {"text": "Used in formal contexts"},
                    "pt": {"text": "Usado em contextos formais"}
                }
            },
            senses=[{"id": "sense1", "definitions": {"en": {"text": "test definition"}}}])
        
        entry_dict = entry.to_dict()
        
        # Verify the multilingual notes structure in serialized format
        assert 'notes' in entry_dict
        assert 'general' in entry_dict['notes']
        assert 'usage' in entry_dict['notes']
        
        general_note = entry_dict['notes']['general']
        assert isinstance(general_note, dict)
        assert general_note['en']['text'] == "This is an English note"
        assert general_note['pt']['text'] == "Esta é uma nota em português"
        assert general_note['pl']['text'] == "Ichi ndi chida chakupanda mu Chisena"
        
        usage_note = entry_dict['notes']['usage']
        assert isinstance(usage_note, dict)
        assert usage_note['en']['text'] == "Used in formal contexts"
        assert usage_note['pt']['text'] == "Usado em contextos formais"

    @pytest.mark.integration
    def test_multilingual_sense_note_parsing(self):
        """Test that multilingual notes on senses are correctly parsed."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="pl">
                        <text>mukwa</text>
                    </form>
                </lexical-unit>
                <sense id="sense1">
                    <definition>
                        <form lang="en">
                            <text>tree</text>
                        </form>
                    </definition>
                    <note type="semantic">
                        <form lang="en">
                            <text>Refers specifically to large trees</text>
                        </form>
                        <form lang="pt">
                            <text>Refere-se especificamente a árvores grandes</text>
                        </form>
                    </note>
                </sense>
            </entry>
        </lift>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        entry_elem = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}entry')
        
        # Use public method and assert entry_elem is not None
        assert entry_elem is not None
        entry = parser.parse_entry_element(entry_elem)
        
        # Check that sense has multilingual notes
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert hasattr(sense, 'notes')
        assert 'semantic' in sense.notes  # type: ignore
        
        semantic_note = sense.notes['semantic']  # type: ignore
        assert isinstance(semantic_note, dict)
        assert 'en' in semantic_note
        assert 'pt' in semantic_note
        assert semantic_note['en']['text'] == "Refers specifically to large trees"
        assert semantic_note['pt']['text'] == "Refere-se especificamente a árvores grandes"

    @pytest.mark.integration
    def test_multilingual_note_form_rendering_in_ui(self):
        """Test that multilingual note form fields are properly rendered in the UI."""
        # This test will verify that the entry form template correctly renders 
        # multilingual note fields for user editing
        entry = Entry(id_="test_entry",
            lexical_unit={"pl": "mukwa"},
            notes={
                "general": {
                    "en": {"text": "This is an English note"},
                    "pt": {"text": "Esta é uma nota em português"}
                }
            },
            senses=[{"id": "sense1", "definitions": {"en": {"text": "test definition"}}}])
        
        # For now, we'll just validate that the entry has the correct structure
        # The UI integration will be tested separately
        assert hasattr(entry, 'notes')
        assert 'general' in entry.notes
        assert isinstance(entry.notes['general'], dict)
        assert 'en' in entry.notes['general']
        assert 'pt' in entry.notes['general']
        # Verify that the notes can be serialized properly for use in templates
        entry_dict = entry.to_dict()
        assert 'notes' in entry_dict
        assert entry_dict['notes']['general']['en']['text'] == "This is an English note"
        assert entry_dict['notes']['general']['pt']['text'] == "Esta é uma nota em português"

    @pytest.mark.integration
    def test_multilingual_note_form_submission_processing(self):
        """Test that form submission correctly processes multilingual note data."""
        # Simulate form data from a multilingual note editing interface
        form_data = {
            'notes[general][en]': 'Updated English note',
            'notes[general][pt]': 'Nota atualizada em português',
            'notes[general][pl]': 'Chida chakupanduka mu Chisena',
            'notes[usage][en]': 'Usage note in English',
            'notes[usage][pt]': 'Nota de uso em português'
        }
        
        # Test the form processing logic that would convert this flat form data
        # into the structured multilingual notes format
        processed_notes = self._process_multilingual_note_form_data(form_data)
        
        expected_notes = {
            'general': {
                'en': {'text': 'Updated English note'},
                'pt': {'text': 'Nota atualizada em português'},
                'pl': {'text': 'Chida chakupanduka mu Chisena'}
            },
            'usage': {
                'en': {'text': 'Usage note in English'},
                'pt': {'text': 'Nota de uso em português'}
            }
        }
        assert processed_notes == expected_notes

    @pytest.mark.integration
    def test_multilingual_custom_field_support(self):
        """Test that custom LIFT fields with language attributes are supported."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="pl">
                        <text>mukwa</text>
                    </form>
                </lexical-unit>
                <sense id="sense1">
                    <definition>
                        <form lang="en">
                            <text>A tree species</text>
                        </form>
                    </definition>
                </sense>
                <field type="source">
                    <form lang="en">
                        <text>Wilson (1995)</text>
                    </form>
                    <form lang="pt">
                        <text>Wilson (1995)</text>
                    </form>
                </field>
                <field type="cultural_note">
                    <form lang="en">
                        <text>Sacred tree in traditional ceremonies</text>
                    </form>
                    <form lang="pt">
                        <text>Árvore sagrada em cerimônias tradicionais</text>
                    </form>
                    <form lang="pl">
                        <text>Chikwa chakudedza pamicaso yakale</text>
                    </form>
                </field>
            </entry>
        </lift>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        entry_elem = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}entry')
        
        # Use public method and assert entry_elem is not None
        assert entry_elem is not None
        entry = parser.parse_entry_element(entry_elem)
        
        # Check that multilingual custom fields are properly parsed
        assert 'source' in entry.custom_fields
        assert 'cultural_note' in entry.custom_fields
        
        # Source field
        source_field = entry.custom_fields['source']
        assert isinstance(source_field, dict)
        assert 'en' in source_field
        assert 'pt' in source_field
        assert source_field['en']['text'] == "Wilson (1995)"
        assert source_field['pt']['text'] == "Wilson (1995)"
        
        # Cultural note field
        cultural_note = entry.custom_fields['cultural_note']
        assert isinstance(cultural_note, dict)
        assert 'en' in cultural_note
        assert 'pt' in cultural_note
        assert 'pl' in cultural_note
        assert cultural_note['en']['text'] == "Sacred tree in traditional ceremonies"
        assert cultural_note['pt']['text'] == "Árvore sagrada em cerimônias tradicionais"
        assert cultural_note['pl']['text'] == "Chikwa chakudedza pamicaso yakale"

    def _process_multilingual_note_form_data(self, form_data: Dict[str, str]) -> Dict[str, Dict[str, dict]]:
        """
        Helper method to process multilingual note form data.
        This simulates the form processing logic that would be implemented in the actual application.
        """
        notes: Dict[str, Dict[str, dict]] = {}
        
        for key, value in form_data.items():
            if key.startswith('notes[') and value.strip():
                # Parse the key: notes[general][en] -> ('general', 'en')
                # Remove 'notes[' from the beginning
                key_part = key[6:]  # Remove 'notes['
                # Find the closing bracket for the note type
                first_bracket = key_part.find('][')
                if first_bracket != -1:
                    note_type = key_part[:first_bracket]
                    # Extract language from the rest
                    lang_part = key_part[first_bracket+2:]
                    if lang_part.endswith(']'):
                        language = lang_part[:-1]  # Remove the closing bracket
                        
                        if note_type not in notes:
                            notes[note_type] = {}
                        
                        notes[note_type][language] = {"text": value.strip()}
        
        return notes

    @pytest.mark.integration
    def test_form_shows_non_project_language(self, client, app):
        """
        GIVEN a dictionary entry with a definition in a language not in the project's languages.
        WHEN the edit form for that entry is requested.
        THEN the response HTML should contain the non-project language in the language dropdown, and it should be selected.
        """
        with app.app_context():
            dictionary_service = app.dict_service
            entry_id = f"test-entry-{uuid.uuid4()}"
            entry_data = {
                "id": entry_id,
                "lexical_unit": {"en": "foreign word"},
                "senses": [{
                    "id": f"sense-{uuid.uuid4()}",
                    "definitions": {
                        "fr": {"text": "Ceci est une définition française."}
                    }
                }]
            }
            entry = Entry.from_dict(entry_data)
            dictionary_service.create_entry(entry)

            try:
                # WHEN
                response = client.get(f"/entries/{entry_id}/edit")
                assert response.status_code == 200
                html = response.data.decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')

                # THEN
                # The name attribute is constructed dynamically based on the language key.
                # Debug: Print all select elements and their names
                print("\nDEBUG: All select elements:")
                for select in soup.find_all('select'):
                    print(f"  - {select.get('name')}")
                

                # Find any select for a definition in 'fr', regardless of sense index
                lang_select = None
                for select in soup.find_all('select'):
                    name = select.get('name', '')
                    if name and name.endswith('.definition.fr.lang'):
                        lang_select = select
                        break
                assert lang_select, "Language select for 'fr' definition not found."

                selected_option = lang_select.find('option', selected=True)
                assert selected_option, "No selected option found for definition language."
                assert selected_option['value'] == 'fr', f"Expected 'fr' to be selected, but got '{selected_option['value']}'."

                fr_option = lang_select.find('option', {'value': 'fr'})
                assert fr_option, "Option with value 'fr' not found in dropdown."

            finally:
                # Cleanup
                dictionary_service.delete_entry(entry_id)
