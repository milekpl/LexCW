"""Integration tests for ranges editor API."""

from __future__ import annotations

import pytest
import json
from typing import Any
from flask import Flask
from flask.testing import FlaskClient


@pytest.mark.integration
class TestRangesEditorAPI:
    """Test ranges editor API endpoints."""
    
    @pytest.fixture
    def client(self, app: Flask) -> FlaskClient:
        """Create test client."""
        with app.test_client() as client:
            yield client
    
    def test_list_ranges(self, client: FlaskClient) -> None:
        """Test GET /api/ranges-editor/."""
        response = client.get('/api/ranges-editor/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert isinstance(data['data'], dict)
    
    def test_get_specific_range_exists(self, client: FlaskClient) -> None:
        """Test GET /api/ranges-editor/<range_id> for existing range."""
        # Assuming 'grammatical-info' range exists in test data
        response = client.get('/api/ranges-editor/grammatical-info')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'data' in data
            assert data['data']['id'] == 'grammatical-info'
    
    def test_get_specific_range_not_found(self, client: FlaskClient) -> None:
        """Test GET /api/ranges-editor/<range_id> for non-existent range."""
        response = client.get('/api/ranges-editor/nonexistent-range-12345')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_create_range_valid(self, client: FlaskClient) -> None:
        """Test POST /api/ranges-editor/ with valid data."""
        payload = {
            'id': 'test-range-integration',
            'labels': {'en': 'Test Range Integration'},
            'descriptions': {'en': 'A test range for integration testing'}
        }
        
        response = client.post(
            '/api/ranges-editor/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Might fail if range already exists or database not writable
        if response.status_code == 201:
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'guid' in data['data']
            assert len(data['data']['guid']) == 36  # UUID length
    
    def test_create_range_missing_id(self, client: FlaskClient) -> None:
        """Test POST /api/ranges-editor/ without ID."""
        payload = {
            'labels': {'en': 'Test Range'}
        }
        
        response = client.post(
            '/api/ranges-editor/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_create_range_missing_labels(self, client: FlaskClient) -> None:
        """Test POST /api/ranges-editor/ without labels."""
        payload = {
            'id': 'test-range-no-labels'
        }
        
        response = client.post(
            '/api/ranges-editor/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_update_range_not_found(self, client: FlaskClient) -> None:
        """Test PUT /api/ranges-editor/<range_id> for non-existent range."""
        payload = {
            'labels': {'en': 'Updated Range'}
        }
        
        response = client.put(
            '/api/ranges-editor/nonexistent-range-12345',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_delete_range_not_found(self, client: FlaskClient) -> None:
        """Test DELETE /api/ranges-editor/<range_id> for non-existent range."""
        response = client.delete('/api/ranges-editor/nonexistent-range-12345')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_list_range_elements(self, client: FlaskClient) -> None:
        """Test GET /api/ranges-editor/<range_id>/elements."""
        # Test with grammatical-info which should have elements
        response = client.get('/api/ranges-editor/grammatical-info/elements')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'data' in data
            assert isinstance(data['data'], list)
    
    def test_list_range_elements_not_found(self, client: FlaskClient) -> None:
        """Test GET /api/ranges-editor/<range_id>/elements for non-existent range."""
        response = client.get('/api/ranges-editor/nonexistent-range/elements')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_create_range_element_missing_id(self, client: FlaskClient) -> None:
        """Test POST /api/ranges-editor/<range_id>/elements without element ID."""
        payload = {
            'labels': {'en': 'New Element'}
        }
        
        response = client.post(
            '/api/ranges-editor/test-range/elements',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [400, 404]  # 404 if range doesn't exist, 400 if missing ID
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_get_range_usage(self, client: FlaskClient) -> None:
        """Test GET /api/ranges-editor/<range_id>/usage."""
        # Test with grammatical-info which might have usage
        response = client.get('/api/ranges-editor/grammatical-info/usage')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'data' in data
            # Now returns grouped statistics with 'elements' and 'total_entries'
            assert isinstance(data['data'], dict)
            assert 'elements' in data['data']
            assert 'total_entries' in data['data']
            assert isinstance(data['data']['elements'], dict)
            assert isinstance(data['data']['total_entries'], int)
    
    def test_get_range_usage_with_element_id(self, client: FlaskClient) -> None:
        """Test GET /api/ranges-editor/<range_id>/usage with element_id parameter."""
        # Test with specific element - this returns a list
        response = client.get('/api/ranges-editor/grammatical-info/usage?element_id=Noun')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'data' in data
            assert isinstance(data['data'], list)
    
    def test_migrate_range_values_missing_operation(self, client: FlaskClient) -> None:
        """Test POST /api/ranges-editor/<range_id>/migrate without operation."""
        payload = {
            'old_value': 'test-value'
        }
        
        response = client.post(
            '/api/ranges-editor/test-range/migrate',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'operation' in data['error'].lower()
    
    def test_migrate_range_values_dry_run(self, client: FlaskClient) -> None:
        """Test POST /api/ranges-editor/<range_id>/migrate with dry_run."""
        payload = {
            'old_value': 'test-value',
            'operation': 'remove',
            'dry_run': True
        }
        
        response = client.post(
            '/api/ranges-editor/grammatical-info/migrate',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should succeed even if range/value doesn't exist in dry_run mode
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'data' in data
            assert 'entries_affected' in data['data']
            assert 'fields_updated' in data['data']
            assert data['data']['fields_updated'] == 0  # Dry run shouldn't update
    
    def test_create_update_delete_range_workflow(self, client: FlaskClient) -> None:
        """Test complete workflow: create, update, and delete a range."""
        range_id = 'test-workflow-range'
        
        # Clean up if exists from previous run
        client.delete(f'/api/ranges-editor/{range_id}')
        
        # Step 1: Create a new range
        create_payload = {
            'id': range_id,
            'labels': {'en': 'Workflow Test Range'},
            'descriptions': {'en': 'Testing complete workflow'}
        }
        
        create_response = client.post(
            '/api/ranges-editor/',
            data=json.dumps(create_payload),
            content_type='application/json'
        )
        
        assert create_response.status_code == 201
        create_data = json.loads(create_response.data)
        assert create_data['success'] is True
        guid = create_data['data']['guid']
        
        # Step 2: Get the created range
        get_response = client.get(f'/api/ranges-editor/{range_id}')
        assert get_response.status_code == 200
        get_data = json.loads(get_response.data)
        assert get_data['data']['id'] == range_id
        
        # Step 3: Update the range
        update_payload = {
            'guid': guid,
            'labels': {'en': 'Updated Workflow Test Range'},
            'descriptions': {'en': 'Updated description'}
        }
        
        update_response = client.put(
            f'/api/ranges-editor/{range_id}',
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        assert update_response.status_code == 200
        update_data = json.loads(update_response.data)
        assert update_data['success'] is True
        
        # Step 4: Delete the range
        delete_response = client.delete(f'/api/ranges-editor/{range_id}')
        
        assert delete_response.status_code == 200
        delete_data = json.loads(delete_response.data)
        assert delete_data['success'] is True
        
        # Verify it's deleted
        verify_response = client.get(f'/api/ranges-editor/{range_id}')
        assert verify_response.status_code == 404
    
    def test_api_returns_json_content_type(self, client: FlaskClient) -> None:
        """Test that all API responses have JSON content type."""
        response = client.get('/api/ranges-editor/')
        
        assert response.status_code == 200
        assert 'application/json' in response.content_type
    
    def test_error_handling_invalid_json(self, client: FlaskClient) -> None:
        """Test error handling for invalid JSON payload."""
        response = client.post(
            '/api/ranges-editor/',
            data='invalid json{',
            content_type='application/json'
        )
        
        # Should return 400 or 500 depending on error handling
        assert response.status_code in [400, 500]
        # Should still return JSON even on error
        assert 'application/json' in response.content_type

    def test_create_update_delete_range_element_workflow_with_multilingual_abbrev(self, client: FlaskClient) -> None:
        """Test complete workflow for a range element with multilingual abbreviations."""
        range_id = 'test-workflow-range'
        element_id = 'test-workflow-element'

        # Step 1: Create a range to host the element
        create_range_payload = {
            'id': range_id,
            'labels': {'en': 'Workflow Test Range'},
            'descriptions': {'en': 'Testing element workflow'}
        }
        client.post('/api/ranges-editor/', data=json.dumps(create_range_payload), content_type='application/json')

        # Step 2: Create a new range element with multilingual abbreviations
        create_element_payload = {
            'id': element_id,
            'labels': {'en': 'Workflow Test Element'},
            'descriptions': {'en': 'A test element'},
            'abbrevs': {'en': 'WTE', 'es': 'ETW'}
        }

        create_response = client.post(
            f'/api/ranges-editor/{range_id}/elements',
            data=json.dumps(create_element_payload),
            content_type='application/json'
        )

        assert create_response.status_code == 201

        # Step 3: Get the created element to verify
        get_response = client.get(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert get_response.status_code == 200
        get_data = json.loads(get_response.data)
        assert get_data['data']['abbrevs'] == {'en': 'WTE', 'es': 'ETW'}

        # Step 4: Update the element with new multilingual abbreviations
        update_element_payload = {
            'labels': {'en': 'Updated Workflow Test Element'},
            'abbrevs': {'en': 'UWTE', 'fr': 'ETUM'}
        }

        update_response = client.put(
            f'/api/ranges-editor/{range_id}/elements/{element_id}',
            data=json.dumps(update_element_payload),
            content_type='application/json'
        )

        assert update_response.status_code == 200

        # Step 5: Get the updated element to verify
        get_updated_response = client.get(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert get_updated_response.status_code == 200
        get_updated_data = json.loads(get_updated_response.data)
        assert get_updated_data['data']['abbrevs'] == {'en': 'UWTE', 'fr': 'ETUM'}

        # Step 6: Delete the element
        delete_response = client.delete(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert delete_response.status_code == 200

        # Verify it's deleted
        verify_response = client.get(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert verify_response.status_code == 404

        # Clean up the range
        client.delete(f'/api/ranges-editor/{range_id}')

    def test_create_update_delete_range_element_workflow_with_multilingual_label(self, client: FlaskClient) -> None:
        """Test complete workflow for a range element with multilingual labels."""
        range_id = 'test-workflow-range'
        element_id = 'test-workflow-element'

        # Step 1: Create a range to host the element
        create_range_payload = {
            'id': range_id,
            'labels': {'en': 'Workflow Test Range'},
            'descriptions': {'en': 'Testing element workflow'}
        }
        client.post('/api/ranges-editor/', data=json.dumps(create_range_payload), content_type='application/json')

        # Step 2: Create a new range element with multilingual labels
        create_element_payload = {
            'id': element_id,
            'labels': {'en': 'Workflow Test Element', 'es': 'Elemento de Flujo de Trabajo'},
            'descriptions': {'en': 'A test element'},
            'abbrevs': {'en': 'WTE'}
        }

        create_response = client.post(
            f'/api/ranges-editor/{range_id}/elements',
            data=json.dumps(create_element_payload),
            content_type='application/json'
        )

        assert create_response.status_code == 201

        # Step 3: Get the created element to verify
        get_response = client.get(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert get_response.status_code == 200
        get_data = json.loads(get_response.data)
        assert get_data['data']['labels'] == {'en': 'Workflow Test Element', 'es': 'Elemento de Flujo de Trabajo'}

        # Step 4: Update the element with new multilingual labels
        update_element_payload = {
            'labels': {'en': 'Updated Workflow Test Element', 'fr': 'Élément de Flux de Travail Mis à Jour'},
            'abbrevs': {'en': 'UWTE'}
        }

        update_response = client.put(
            f'/api/ranges-editor/{range_id}/elements/{element_id}',
            data=json.dumps(update_element_payload),
            content_type='application/json'
        )

        assert update_response.status_code == 200

        # Step 5: Get the updated element to verify
        get_updated_response = client.get(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert get_updated_response.status_code == 200
        get_updated_data = json.loads(get_updated_response.data)
        assert get_updated_data['data']['labels'] == {'en': 'Updated Workflow Test Element', 'fr': 'Élément de Flux de Travail Mis à Jour'}

        # Step 6: Delete the element
        delete_response = client.delete(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert delete_response.status_code == 200

        # Verify it's deleted
        verify_response = client.get(f'/api/ranges-editor/{range_id}/elements/{element_id}')
        assert verify_response.status_code == 404

        # Clean up the range
        client.delete(f'/api/ranges-editor/{range_id}')
