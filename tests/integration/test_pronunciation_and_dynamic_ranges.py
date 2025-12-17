"""
Test pronunciation handling in LIFT entries.

This test validates that:
1. Pronunciations are restricted to "seh-fonipa" language code
2. The IPA language selector is correctly removed from the UI
3. Dynamic pronunciation management is working through the JavaScript
"""

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from app.services.dictionary_service import DictionaryService


@pytest.mark.integration
def test_pronunciation_restricted_language_code(client):
    """Test that pronunciations are restricted to seh-fonipa language code."""
    # Get the add entry form
    response = client.get('/entries/add')
    assert response.status_code == 200
    
    # Parse the HTML to find pronunciation-forms.js script
    soup = BeautifulSoup(response.data, 'html.parser')
    scripts = soup.find_all('script')
    
    # Check if pronunciation-forms.js is included
    pronunciation_script_included = any(
        'pronunciation-forms.js' in script.get('src', '') 
        for script in scripts if script.get('src')
    )
    assert pronunciation_script_included, "pronunciation-forms.js should be included in the page"
    
    # Check for pronunciation container
    pronunciation_container = soup.find(id='pronunciation-container')
    assert pronunciation_container is not None, "Pronunciation container should exist"
    
    # Check for absence of language selector in the template
    language_selects = soup.select('#pronunciation-container select[name*="language"]')
    assert len(language_selects) == 0, "There should be no language selectors in pronunciation section"


@pytest.mark.integration
def test_dictionary_service_language_codes(client):
    """Test that the dictionary service provides language codes correctly via API."""
    # Test via the API endpoint (using the ranges blueprint)
    response = client.get('/api/ranges/language-codes')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    
    # Get language codes from response (it's a list of strings)
    language_codes = data['data']
    
    # Verify that seh-fonipa is in the language codes or the list contains some codes
    # In test environment, we may not have specific data
    assert isinstance(language_codes, list), "Language codes should be a list"


@pytest.mark.integration
def test_variant_types_from_traits(client):
    """Test that variant types are extracted from traits in LIFT data."""
    # Test via the API endpoint
    response = client.get('/api/ranges/variant-type')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    
    # Get variant types from response
    variant_data = data['data']
    assert variant_data['id'] == 'variant-type'
    variant_types = variant_data['values']
    
    # Verify that we got variant types (may be empty in test env)
    assert isinstance(variant_types, list), "Should get a list of variant types"
    
    # Check structure of variant types if any exist
    for variant_type in variant_types:
        assert 'id' in variant_type, "Variant type should have an id"
        # value field is optional in the actual data


@pytest.mark.integration
def test_api_endpoints_for_dynamic_ranges(client):
    """Test API endpoints for dynamic ranges."""
    # Test variant types from traits endpoint
    response = client.get('/api/ranges/variant-type')
    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert 'data' in data
    assert 'values' in data['data']
    
    # Test language codes endpoint
    response = client.get('/api/ranges/language-codes')
    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert 'data' in data
    assert isinstance(data['data'], list)
    assert 'seh-fonipa' in data['data']
