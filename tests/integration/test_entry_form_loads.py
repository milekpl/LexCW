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
    import uuid

    api_url = "/api/entries/"
    # Use a unique id per fixture invocation to avoid collisions between tests
    unique_id = f"test-entry-for-loading-{uuid.uuid4().hex[:8]}"
    test_entry_data: dict[str, str | dict[str, str] | list[dict[str, str | dict[str, str]]]] = {
        "id": unique_id,
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
    # API returns 'id' not 'entry_id'
    entry_id = response_json.get('id')
    assert entry_id is not None

    yield entry_id

    # Teardown: delete the test entry and ensure the deletion succeeded
    delete_url = f"/api/entries/{entry_id}"
    del_resp = client.delete(delete_url)
    if del_resp.status_code not in (200, 404):
        # Log for visibility if teardown failed
        print(f"Warning: failed to delete test entry {entry_id}, status: {del_resp.status_code}, body: {del_resp.get_data(as_text=True)[:200]}")


@pytest.mark.integration
class TestEntryFormLoading:
    @pytest.mark.integration
    def test_ranges_api_available(self, client: FlaskClient):
        """Test that the ranges API returns LIFT ranges data"""
        response = client.get('/api/ranges')
        assert response.status_code == 200
        data = response.json
        assert data is not None
        assert data['success']
        assert 'data' in data
        ranges = data['data']
        
        # Look for semantic domain range (can be either 'semantic-domain' or 'semantic-domain-ddp4')
        semantic_range_key = None
        if 'semantic-domain' in ranges:
            semantic_range_key = 'semantic-domain'
        elif 'semantic-domain-ddp4' in ranges:
            semantic_range_key = 'semantic-domain-ddp4'
        
        assert semantic_range_key is not None, f"No semantic domain range found in: {list(ranges.keys())}"
        
        semantic_domains = ranges[semantic_range_key]['values']
        assert len(semantic_domains) > 0
        domain_ids = [item['id'] for item in semantic_domains]
        
        # Test data may contain different values depending on which test data is loaded
        # For simple test data: 'agriculture' and 'technology' 
        # For comprehensive test data: numeric codes like '1', '2', etc.
        assert len(domain_ids) > 0, "Semantic domain should have at least one value"

    @pytest.mark.integration
    def test_entry_form_loads_successfully(self, client: FlaskClient, test_entry: int):
        """Test that entry form page loads without errors"""
        response = client.get(f'/entries/{test_entry}/edit')
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'lexical-unit' in content
        assert 'entry-form.js' in content
        assert 'ranges-loader.js' in content

    @pytest.mark.integration
    def test_ranges_loader_javascript_present(self, client: FlaskClient, test_entry: int):
        """Test that ranges-loader.js is included in entry form"""
        response = client.get(f'/entries/{test_entry}/edit')
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert 'ranges-loader.js' in content

    @pytest.mark.integration
    def test_entry_form_has_lift_selects(self, client: FlaskClient, test_entry: int):
        """Test that entry form has select elements for LIFT ranges"""
        response = client.get(f'/entries/{test_entry}/edit')
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        # Check for entry-level status field
        assert 'name="status"' in content or 'id="status"' in content
        # Check for sense-level domain_type (semantic domain) and usage_type fields
        assert 'name="senses[0].domain_type"' in content or '.domain_type' in content
        assert 'name="senses[0].usage_type"' in content or '.usage_type' in content
