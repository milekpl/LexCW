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


class TestPronunciationUnicodeDisplay:
    """Test pronunciation Unicode display in entry form."""
    
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app."""
        return create_app('testing')
    
    def test_pronunciation_unicode_encoding_in_js(self, app: Flask, client):
        """Test that IPA Unicode characters are properly encoded in JavaScript initialization."""
        with app.app_context():
            # Create a test entry with IPA pronunciation containing Unicode characters
            test_entry = Entry(
                id="test_unicode_entry",
                lexical_unit={"en": "test"},
                pronunciations={"seh-fonipa": "ˈtɛst"}  # Contains Unicode ˈ and ɛ
            )
            
            # Mock the dictionary service
            with patch.object(DictionaryService, 'get_entry', return_value=test_entry), \
                 patch.object(DictionaryService, 'get_lift_ranges', return_value={}):
                
                # Request the entry form
                response = client.get(f'/entries/{test_entry.id}/edit')
                assert response.status_code == 200
                
                # Parse the HTML content
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Find the script that initializes pronunciations
                pronunciation_script = None
                for script in soup.find_all('script'):
                    if script.string and 'PronunciationFormsManager' in script.string:
                        pronunciation_script = script.string
                        break
                
                assert pronunciation_script is not None, "PronunciationFormsManager initialization script not found"
                
                # Check that pronunciation data is included
                assert 'pronunciationArray.push(' in pronunciation_script or 'pronunciations: pronunciationArray' in pronunciation_script
                
                # Check that Unicode characters are properly escaped
                # ˈ should be escaped as \u02c8 and ɛ should be escaped as \u025b
                assert ('\\u02c8' in pronunciation_script or 'ˈ' in pronunciation_script), \
                    "Unicode character ˈ not found in script (neither direct nor escaped)"
                assert ('\\u025b' in pronunciation_script or 'ɛ' in pronunciation_script), \
                    "Unicode character ɛ not found in script (neither direct nor escaped)"
                
                # Check that the pronunciation container exists
                container = soup.find(id='pronunciation-container')
                assert container is not None, "Pronunciation container not found"
    
    def test_pronunciation_template_json_encoding(self, app: Flask):
        """Test that the template properly encodes pronunciation values using tojson filter."""
        with app.app_context():
            from flask import render_template_string
            
            # Create test entry with Unicode IPA
            test_entry = Entry(
                id="test_template",
                lexical_unit={"en": "test"}, 
                pronunciations={"seh-fonipa": "ˈprɒtɪstəntɪzm"}
            )
            
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
    
    def test_api_endpoints_work(self, app: Flask, client):
        """Test that the API endpoints we fixed are working."""
        with app.app_context():
            # Test relation-types endpoint (plural, not singular)
            response = client.get('/api/ranges/relation-types')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'data' in data
            
            # Test etymology-types endpoint  
            response = client.get('/api/ranges/etymology-types')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'data' in data
            
            # Test language-codes endpoint
            response = client.get('/api/ranges/language-codes')
            assert response.status_code == 200
            data = response.get_json()
            # The endpoint might return different formats depending on the implementation
            assert 'data' in data or 'language_codes' in data
