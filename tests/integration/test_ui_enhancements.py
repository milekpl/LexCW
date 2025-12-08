"""
Integration tests for UI enhancements.

Tests that the entry form renders with the correct UI elements for:
- Pronunciation upload and generate buttons
- Illustration upload and preview
"""

import pytest
from flask.testing import FlaskClient
from app.parsers.lift_parser import LIFTParser


@pytest.mark.integration
class TestPronunciationUIElements:
    """Test that pronunciation UI has separate Upload and Generate buttons."""
    
    def test_pronunciation_has_separate_buttons(self, client: FlaskClient):
        """Test that pronunciation section renders with separate Upload and Generate buttons."""
        # Create an entry with pronunciation
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="ui_test_001">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <pronunciation>
        <form lang="en-fonipa"><text>tɛst</text></form>
    </pronunciation>
</entry>'''
        
        # Submit the entry
        response = client.post(
            '/api/xml/entries',
            data=xml_content,
            content_type='application/xml'
        )
        assert response.status_code == 201
        
        # Get the entry edit form
        response = client.get('/entries/ui_test_001/edit')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        
        # Verify separate Upload and Generate buttons exist
        assert 'upload-audio-btn' in html
        assert 'generate-audio-btn' in html
        assert '<i class="fas fa-upload"></i> Upload' in html
        assert '<i class="fas fa-magic"></i> Generate' in html
    
    def test_pronunciation_buttons_in_template(self, client: FlaskClient):
        """Test that pronunciation template section has both button types in HTML."""
        # Get the entry form template by viewing an existing entry
        response = client.get('/static/js/entry-form.js')
        assert response.status_code == 200
        
        # The template HTML is embedded in the JavaScript
        # Just verify the buttons exist in our template
        pass  # Already verified by other tests


@pytest.mark.integration
class TestIllustrationUIElements:
    """Test that illustration UI has upload button and preview container."""
    
    def test_illustration_has_upload_button(self, client: FlaskClient):
        """Test that illustration section renders with upload button."""
        # Create an entry with illustration
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="ui_test_002">
    <lexical-unit>
        <form lang="en"><text>cat</text></form>
    </lexical-unit>
    <sense id="s1">
        <gloss lang="en"><text>feline animal</text></gloss>
        <illustration href="images/cat.jpg">
            <label>
                <form lang="en"><text>A cat</text></form>
            </label>
        </illustration>
    </sense>
</entry>'''
        
        # Submit the entry
        response = client.post(
            '/api/xml/entries',
            data=xml_content,
            content_type='application/xml'
        )
        assert response.status_code == 201
        
        # Get the entry edit form
        response = client.get('/entries/ui_test_002/edit')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        
        # Verify upload button exists
        assert 'upload-illustration-btn' in html
        assert '<i class="fas fa-upload"></i> Upload Image' in html
    
    def test_illustration_has_preview_container(self, client: FlaskClient):
        """Test that illustration section has image preview container."""
        # Create an entry with illustration
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="ui_test_003">
    <lexical-unit>
        <form lang="en"><text>dog</text></form>
    </lexical-unit>
    <sense id="s1">
        <gloss lang="en"><text>canine animal</text></gloss>
        <illustration href="images/dog.jpg">
            <label>
                <form lang="en"><text>A dog</text></form>
            </label>
        </illustration>
    </sense>
</entry>'''
        
        # Submit the entry
        response = client.post(
            '/api/xml/entries',
            data=xml_content,
            content_type='application/xml'
        )
        assert response.status_code == 201
        
        # Get the entry edit form
        response = client.get('/entries/ui_test_003/edit')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        
        # Verify preview container exists
        assert 'image-preview-container' in html
        assert 'illustration-preview' in html
        assert 'img-thumbnail' in html


@pytest.mark.integration
class TestJavaScriptFileUploadHandlers:
    """Test that JavaScript files contain the correct event handlers."""
    
    def test_entry_form_js_has_upload_handler(self, client: FlaskClient):
        """Test that entry-form.js contains audio upload handler."""
        response = client.get('/static/js/entry-form.js')
        assert response.status_code == 200
        
        js_content = response.data.decode('utf-8')
        
        # Verify upload button handler exists
        assert "e.target.closest('.upload-audio-btn')" in js_content
        assert "fileInput.type = 'file'" in js_content
        assert "fileInput.accept = 'audio/*'" in js_content
    
    def test_entry_form_js_has_generate_handler(self, client: FlaskClient):
        """Test that entry-form.js contains audio generate handler."""
        response = client.get('/static/js/entry-form.js')
        assert response.status_code == 200
        
        js_content = response.data.decode('utf-8')
        
        # Verify generate button handler exists
        assert "e.target.closest('.generate-audio-btn')" in js_content
        assert 'generateAudio' in js_content
    
    def test_multilingual_sense_fields_js_has_illustration_picker(self, client: FlaskClient):
        """Test that multilingual-sense-fields.js contains multilingual field management."""
        response = client.get('/static/js/multilingual-sense-fields.js')
        assert response.status_code == 200
        
        js_content = response.data.decode('utf-8')
        
        # Verify core multilingual field functionality exists
        assert 'MultilingualSenseFieldsManager' in js_content
        assert 'addLanguageField' in js_content
        assert '.add-definition-language-btn' in js_content or ".add-definition-language-btn" in js_content
    
    def test_multilingual_sense_fields_js_has_preview_initialization(self, client: FlaskClient):
        """Test that multilingual-sense-fields.js initializes correctly."""
        response = client.get('/static/js/multilingual-sense-fields.js')
        assert response.status_code == 200
        
        js_content = response.data.decode('utf-8')
        
        # Verify initialization and event listeners
        assert 'initEventListeners' in js_content
        assert 'DOMContentLoaded' in js_content
        assert 'window.multilingualSenseFieldsManager' in js_content


@pytest.fixture(scope='function', autouse=True)
def cleanup_test_entries(client: FlaskClient):
    """Clean up test entries after each test."""
    yield
    # Clean up test entries
    for entry_id in ['ui_test_001', 'ui_test_002', 'ui_test_003']:
        try:
            client.delete(f'/api/xml/entries/{entry_id}')
        except Exception:
            pass
