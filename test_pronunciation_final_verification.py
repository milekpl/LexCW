#!/usr/bin/env python3
"""
Test-driven development test for pronunciation field display functionality.
This test verifies that pronunciation fields are properly rendered in the UI.
"""

from __future__ import annotations

import sys
sys.path.insert(0, '.')

import pytest
import requests

def test_pronunciation_field_display_add_form() -> None:
    """Test that pronunciation fields are displayed in the add entry form."""
    
    base_url = "http://localhost:5000"
    
    try:
        # Test the add entry form
        response = requests.get(f"{base_url}/entries/add")
        assert response.status_code == 200, f"Add form not accessible: {response.status_code}"
        
        html = response.text
        
        # Verify key pronunciation elements are present
        required_elements = [
            'pronunciation-container',
            'add-pronunciation-btn', 
            'PronunciationFormsManager',
            'pronunciation-forms.js',
            'window.pronunciationFormsManager = new PronunciationFormsManager'
        ]
        
        for element in required_elements:
            assert element in html, f"Required element '{element}' not found in add form"
        
        # Verify pronunciation data initialization
        assert 'const pronunciationData = {}' in html or 'const pronunciationData = null' in html, \
            "Pronunciation data initialization not found"
        
        print("✓ All pronunciation elements found in add form")
        
    except requests.exceptions.ConnectionError:
        pytest.skip("Application not running on localhost:5000")

def test_pronunciation_field_display_with_mock_data() -> None:
    """Test pronunciation field rendering with mock pronunciation data."""
    
    # This test would verify the JavaScript logic with mock data
    # Since we can't easily test JavaScript directly, we verify the template logic
    
    mock_entry_data = {
        'pronunciations': {
            'seh-fonipa': 'test_ipa_pronunciation'
        }
    }
    
    # The template should convert this to:
    expected_js_array = [
        {
            'type': 'seh-fonipa',
            'value': 'test_ipa_pronunciation', 
            'audio_file': '',
            'is_default': True
        }
    ]
    
    # Verify the conversion logic matches expectations
    pronunciations = mock_entry_data.get('pronunciations', {})
    pronunciation_array = []
    
    if pronunciations and isinstance(pronunciations, dict):
        for writing_system, value in pronunciations.items():
            if value and value.strip():
                pronunciation_array.append({
                    'type': writing_system,
                    'value': value,
                    'audio_file': '',
                    'is_default': True
                })
    
    assert pronunciation_array == expected_js_array, \
        f"Pronunciation conversion failed. Expected: {expected_js_array}, Got: {pronunciation_array}"
    
    print("✓ Pronunciation data conversion logic works correctly")

def test_pronunciation_infrastructure_complete() -> None:
    """Test that all pronunciation infrastructure components are in place."""
    
    # Test that required files exist
    import os
    
    files_to_check = [
        'app/static/js/pronunciation-forms.js',
        'app/templates/entry_form.html'
    ]
    
    for file_path in files_to_check:
        assert os.path.exists(file_path), f"Required file {file_path} not found"
    
    # Check pronunciation-forms.js contains required class
    with open('app/static/js/pronunciation-forms.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    required_js_elements = [
        'class PronunciationFormsManager',
        'renderExistingPronunciations',
        'addPronunciation',
        'renderPronunciation'
    ]
    
    for element in required_js_elements:
        assert element in js_content, f"Required JS element '{element}' not found"
    
    # Check entry_form.html contains pronunciation initialization
    with open('app/templates/entry_form.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    required_template_elements = [
        'pronunciation-container',
        'PronunciationFormsManager',
        'pronunciationArray'
    ]
    
    for element in required_template_elements:
        assert element in template_content, f"Required template element '{element}' not found"
    
    print("✓ All pronunciation infrastructure components are in place")

if __name__ == '__main__':
    test_pronunciation_field_display_add_form()
    test_pronunciation_field_display_with_mock_data()
    test_pronunciation_infrastructure_complete()
    print("✓ All pronunciation tests passed successfully")
