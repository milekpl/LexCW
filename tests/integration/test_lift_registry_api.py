"""Integration tests for LIFT element registry API endpoints.

Tests all REST API endpoints for querying LIFT element metadata.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient


@pytest.mark.integration
class TestLIFTRegistryAPI:
    """Test LIFT element registry API endpoints."""

    def test_get_all_elements(self, client: FlaskClient) -> None:
        """Test getting all LIFT elements."""
        response = client.get('/api/lift/elements')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'elements' in data
        assert 'count' in data
        assert data['count'] > 0
        
        # Verify structure of first element
        element = data['elements'][0]
        assert 'name' in element
        assert 'display_name' in element
        assert 'category' in element
        assert 'description' in element

    def test_get_element_by_name(self, client: FlaskClient) -> None:
        """Test getting a specific LIFT element by name."""
        response = client.get('/api/lift/elements/entry')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['name'] == 'entry'
        assert data['display_name'] == 'Entry'
        assert data['category'] == 'root'
        assert 'description' in data
        assert 'level' in data
        assert 'attributes' in data

    def test_get_nonexistent_element(self, client: FlaskClient) -> None:
        """Test getting a nonexistent element returns 404."""
        response = client.get('/api/lift/elements/nonexistent-element')
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_displayable_elements(self, client: FlaskClient) -> None:
        """Test getting displayable elements only."""
        response = client.get('/api/lift/elements/displayable')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'elements' in data
        assert 'count' in data
        
        # Verify all elements have display_name
        for element in data['elements']:
            assert 'display_name' in element
            assert element['display_name'] != ''

    def test_get_elements_by_category(self, client: FlaskClient) -> None:
        """Test getting elements by category."""
        response = client.get('/api/lift/elements/category/entry')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'elements' in data
        assert 'count' in data
        assert 'category' in data
        assert data['category'] == 'entry'
        
        # Verify all returned elements are in entry category
        for element in data['elements']:
            assert element['category'] == 'entry'

    def test_get_elements_invalid_category(self, client: FlaskClient) -> None:
        """Test getting elements with invalid category returns 400."""
        response = client.get('/api/lift/elements/category/invalid-category')
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'error' in data
        assert 'invalid category' in data['error'].lower()

    def test_get_categories(self, client: FlaskClient) -> None:
        """Test getting all available categories."""
        response = client.get('/api/lift/categories')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'categories' in data
        assert len(data['categories']) > 0
        
        # Verify expected categories are present
        # Note: 'name' field contains the category key (root, entry, etc.)
        category_keys = [cat['name'] for cat in data['categories']]
        assert 'root' in category_keys
        assert 'entry' in category_keys
        assert 'sense' in category_keys

    def test_get_visibility_options(self, client: FlaskClient) -> None:
        """Test getting visibility options."""
        response = client.get('/api/lift/visibility-options')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'options' in data
        assert len(data['options']) > 0
        
        # Verify expected options
        option_values = [opt['value'] for opt in data['options']]
        assert 'always' in option_values
        assert 'if-content' in option_values
        assert 'never' in option_values

    def test_get_hierarchy(self, client: FlaskClient) -> None:
        """Test getting element hierarchy."""
        response = client.get('/api/lift/hierarchy')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'hierarchy' in data
        
        # Verify entry is in hierarchy and has children
        assert 'entry' in data['hierarchy']
        assert len(data['hierarchy']['entry']) > 0

    def test_get_metadata(self, client: FlaskClient) -> None:
        """Test getting metadata (relation types, note types, grammatical categories)."""
        response = client.get('/api/lift/metadata')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'relation_types' in data
        assert 'note_types' in data
        assert 'grammatical_categories' in data
        
        # Verify each has items
        assert len(data['relation_types']) > 0
        assert len(data['note_types']) > 0
        assert len(data['grammatical_categories']) > 0

    def test_get_default_profile(self, client: FlaskClient) -> None:
        """Test getting default display profile."""
        response = client.get('/api/lift/default-profile')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'profile' in data
        assert 'name' in data
        assert 'description' in data
        assert data['name'] == 'default'
        
        # Verify profile structure
        profile = data['profile']
        assert len(profile) > 0
        
        # Verify each element has required fields
        for element in profile:
            assert 'lift_element' in element
            assert 'visibility' in element
            assert 'display_order' in element
            assert 'css_class' in element

    def test_api_returns_json_content_type(self, client: FlaskClient) -> None:
        """Test that all endpoints return JSON content type."""
        endpoints = [
            '/api/lift/elements',
            '/api/lift/elements/entry',
            '/api/lift/elements/displayable',
            '/api/lift/elements/category/entry',
            '/api/lift/categories',
            '/api/lift/visibility-options',
            '/api/lift/hierarchy',
            '/api/lift/metadata',
            '/api/lift/default-profile',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert 'application/json' in response.content_type
