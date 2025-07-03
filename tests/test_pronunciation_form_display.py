import pytest
from flask import current_app
from app.services.dictionary_service import DictionaryService


def test_pronunciation_field_displays_in_form(client):
    """Test that pronunciation fields are displayed in the entry form."""
    # Use a test entry with known pronunciation data
    response = client.get('/entries/test_pronunciation_entry/edit')
    assert response.status_code == 200
    
    response_text = response.get_data(as_text=True)
    
    # Check that pronunciation container exists
    assert 'pronunciation-container' in response_text
    
    # Check that the PronunciationFormsManager is initialized with data
    assert 'new PronunciationFormsManager' in response_text
    
    # Check that pronunciation data is passed to JavaScript
    # Should contain the IPA transcription (may be Unicode escaped)
    assert '/pro.nun.si.eɪ.ʃən/' in response_text or 'pro.nun.si.eɪ.ʃən' in response_text or '/pro.nun.si.e\\u026a.\\u0283\\u0259n/' in response_text
    
    print("✓ Test passed: Pronunciation form displays correctly")


def test_pronunciation_form_renders_input_fields(client):
    """Test that the pronunciation form renders input fields for existing data."""
    # This test ensures the UI shows pronunciation input fields
    response = client.get('/entries/test_pronunciation_entry/edit')
    assert response.status_code == 200
    
    response_text = response.get_data(as_text=True)
    
    # Should contain the base structure for pronunciations
    assert 'Add Pronunciation' in response_text
    assert 'pronunciation-container' in response_text
    
    # The form should be ready to display pronunciations
    assert 'pronunciation-forms.js' in response_text
    
    print("✓ Test passed: Pronunciation form structure is correct")
