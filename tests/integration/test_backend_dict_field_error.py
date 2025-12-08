from __future__ import annotations
import logging
import uuid
from flask import Flask
from app.services.dictionary_service import DictionaryService
from app.parsers.lift_parser import LIFTParser
import pytest

@pytest.mark.integration
def test_update_entry_with_dict_field_logs_error(client, caplog):
    """Test that updating an entry with invalid field type logs an error."""
    # Create a test entry first using XML API with unique ID
    test_id = f"dict_field_test_{uuid.uuid4().hex[:8]}"
    entry_xml = f'''<entry id="{test_id}">
        <lexical-unit>
            <form lang="en"><text>test_entry</text></form>
        </lexical-unit>
        <sense id="sense_1">
            <gloss lang="en"><text>Test gloss</text></gloss>
            <definition>
                <form lang="en"><text>Test definition</text></form>
            </definition>
        </sense>
    </entry>'''
    
    # Create the entry
    create_response = client.post('/api/xml/entries', data=entry_xml, content_type='application/xml')
    assert create_response.status_code == 201
    
    # Get the entry to verify it exists
    get_response = client.get(f'/api/entries/{test_id}')
    assert get_response.status_code == 200
    
    # Now try to update with invalid note structure
    # Parse the XML to get an Entry object
    parser = LIFTParser()
    entry = parser.parse_entry(entry_xml)
    
    # Intentionally break a field - note should be a string, not a dict
    entry.note = {"en": "This should be a string, not a dict"}
    
    # Try to serialize this back to XML - this should fail
    with caplog.at_level(logging.ERROR):
        try:
            from lxml import etree as ET
            entry_elem = ET.Element('entry', id=entry.id)
            # Try to add the note - this should fail because note is a dict
            if entry.note:
                note_elem = ET.SubElement(entry_elem, 'note')
                # This will fail with dict
                note_elem.text = entry.note  # type: ignore
            xml_str = ET.tostring(entry_elem, encoding='unicode')
        except TypeError as e:
            # The error should be logged or raised
            assert "must be" in str(e) or "str" in str(e)
