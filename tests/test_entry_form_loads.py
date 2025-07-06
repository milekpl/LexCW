#!/usr/bin/env python3


import os
os.environ['TESTING'] = 'true'

from flask.testing import FlaskClient
import pytest
from typing import Generator

# The app and client fixtures are now sourced from tests/conftest.py to ensure
# proper test isolation and database management. The original, module-scoped
# fixtures in this file caused database lock errors due to conflicts.

@pytest.fixture(scope="function")
def test_entry(client: FlaskClient) -> Generator[int, None, None]:
    """Fixture to create a test entry and clean it up afterwards."""
    api_url = "/api/entries/"
    test_entry_data: dict[str, str | dict[str, str] | list[dict[str, str | dict[str, str]]]] = {
        "id": "test-entry-for-loading-123",
        "lexical_unit": {"en": "test-entry-for-loading"},
        "grammatical_info": "Noun",
        "senses": [
            {
                "id": "sense-1",
                "gloss": {"en": "test entry for loading forms"}
            }
        ]
    }
    response = client.post(api_url, json=test_entry_data)
    assert response.status_code in [200, 201]
    response_json = response.json
    assert response_json is not None
    entry_id = response_json.get('entry_id')
    assert entry_id is not None

    yield entry_id

    # Teardown: delete the test entry
    delete_url = f"/api/entries/{entry_id}"
    client.delete(delete_url)

class TestEntryFormLoading:
    def test_ranges_api_available(self, client: FlaskClient):
        """Test that the ranges API returns LIFT ranges data"""
        response = client.get('/api/ranges')
        assert response.status_code == 200
        data = response.json
        assert data is not None
        assert data['success']
        assert 'data' in data
        ranges = data['data']
        
        # Look for semantic domain range (test data uses 'semantic-domain')
        assert 'semantic-domain' in ranges
        semantic_domains = ranges['semantic-domain']['values']
        assert len(semantic_domains) > 0
        domain_ids = [item['id'] for item in semantic_domains]
        # Test data contains 'agriculture' and 'technology' 
        assert 'agriculture' in domain_ids

    def test_entry_form_loads_successfully(self, client: FlaskClient, test_entry: int):
        """Test that entry form page loads without errors"""
        response = client.get(f'/entries/{test_entry}/edit')
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'lexical-unit' in content
        assert 'entry-form.js' in content
        assert 'ranges-loader.js' in content

    def test_ranges_loader_javascript_present(self, client: FlaskClient, test_entry: int):
        """Test that ranges-loader.js is included in entry form"""
        response = client.get(f'/entries/{test_entry}/edit')
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'ranges-loader.js' in content

    def test_entry_form_has_lift_selects(self, client: FlaskClient, test_entry: int):
        """Test that entry form has select elements for LIFT ranges"""
        response = client.get(f'/entries/{test_entry}/edit')
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        expected_selects = [
            'semantic_domain',
            'usage_type',
            'status'
        ]
        for select_name in expected_selects:
            assert f'name="{select_name}"' in content or f'id="{select_name}"' in content
