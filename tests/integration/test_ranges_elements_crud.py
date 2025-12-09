"""Integration tests for range elements CRUD operations."""

from __future__ import annotations

import pytest
import json
from typing import Any
from flask import Flask
from flask.testing import FlaskClient


@pytest.mark.integration
class TestRangeElementsCRUD:
    """Test complete CRUD operations for range elements."""
    
    @pytest.fixture
    def client(self, app: Flask) -> FlaskClient:
        """Create test client."""
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def test_range_id(self, client: FlaskClient) -> str:
        """Get a test range ID that should exist in the database."""
        # Get first available range from the database
        response = client.get('/api/ranges-editor/')
        if response.status_code == 200:
            data = json.loads(response.data)
            ranges = data.get('data', {})
            if ranges:
                # Return first range ID
                return list(ranges.keys())[0]
        # Fallback to a common range
        return 'grammatical-info'
    
    def test_list_range_elements(self, client: FlaskClient, test_range_id: str) -> None:
        """Test GET /api/ranges-editor/<range_id>/elements."""
        response = client.get(f'/api/ranges-editor/{test_range_id}/elements')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    def test_create_range_element(self, client: FlaskClient, test_range_id: str) -> None:
        """Test POST /api/ranges-editor/<range_id>/elements to create element."""
        element_id = 'test-element-crud'
        
        # First, try to delete if it exists from previous test run
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
        
        payload = {
            'id': element_id,
            'abbrev': 'TEC',
            'value': 'test-value',
            'parent': '',
            'description': {
                'en': 'Test Element for CRUD',
                'pl': 'Element testowy dla CRUD'
            }
        }
        
        response = client.post(
            f'/api/ranges-editor/{test_range_id}/elements',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should succeed now
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert 'guid' in data['data']
        
        # Cleanup
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
    
    def test_get_specific_element(self, client: FlaskClient, test_range_id: str) -> None:
        """Test GET /api/ranges-editor/<range_id>/elements/<element_id>."""
        # First get list of elements
        list_response = client.get(f'/api/ranges-editor/{test_range_id}/elements')
        
        if list_response.status_code != 200:
            pytest.skip("Cannot list elements")
        
        list_data = json.loads(list_response.data)
        elements = list_data['data']
        
        if not elements:
            pytest.skip("No elements in test range")
        
        # Get first element
        first_element = elements[0]
        element_id = first_element['id']
        
        response = client.get(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert data['data']['id'] == element_id
        
        # Verify all fields are present
        element = data['data']
        assert 'id' in element
        assert 'description' in element or 'descriptions' in element
        # abbrev might be present
        if 'abbrev' in element:
            assert isinstance(element['abbrev'], str)
    
    def test_get_nonexistent_element(self, client: FlaskClient, test_range_id: str) -> None:
        """Test GET for element that doesn't exist."""
        response = client.get(
            f'/api/ranges-editor/{test_range_id}/elements/nonexistent-element-12345'
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_update_range_element(self, client: FlaskClient, test_range_id: str) -> None:
        """Test PUT /api/ranges-editor/<range_id>/elements/<element_id>."""
        element_id = 'test-update-element'
        
        # Delete if exists from previous run
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
        
        # First create an element to update
        create_payload = {
            'id': element_id,
            'abbrev': 'TUE',
            'value': 'original-value',
            'description': {
                'en': 'Original description'
            }
        }
        
        create_response = client.post(
            f'/api/ranges-editor/{test_range_id}/elements',
            data=json.dumps(create_payload),
            content_type='application/json'
        )
        
        assert create_response.status_code == 201
        
        # Now update it
        update_payload = {
            'labels': {},
            'descriptions': {
                'en': 'Updated description',
                'pl': 'Zaktualizowany opis'
            },
            'abbrevs': {'und': 'UPD'},
            'parent': ''
        }
        
        update_response = client.put(
            f'/api/ranges-editor/{test_range_id}/elements/{element_id}',
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        if update_response.status_code == 200:
            data = json.loads(update_response.data)
            assert data['success'] is True
            
            # Verify the update by fetching the element
            get_response = client.get(
                f'/api/ranges-editor/{test_range_id}/elements/{element_id}'
            )
            
            if get_response.status_code == 200:
                get_data = json.loads(get_response.data)
                element = get_data['data']
                
                # Check if description was updated
                if 'description' in element:
                    assert 'en' in element['description']
        
        # Cleanup
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{element_id}')
    
    def test_delete_range_element(self, client: FlaskClient, test_range_id: str) -> None:
        """Test DELETE /api/ranges-editor/<range_id>/elements/<element_id>."""
        # First create an element to delete
        create_payload = {
            'id': 'test-delete-element',
            'abbrev': 'TDE',
            'description': {
                'en': 'Element to be deleted'
            }
        }
        
        create_response = client.post(
            f'/api/ranges-editor/{test_range_id}/elements',
            data=json.dumps(create_payload),
            content_type='application/json'
        )
        
        if create_response.status_code != 201:
            pytest.skip("Cannot create element for delete test")
        
        # Delete it
        delete_response = client.delete(
            f'/api/ranges-editor/{test_range_id}/elements/test-delete-element'
        )
        
        if delete_response.status_code == 200:
            data = json.loads(delete_response.data)
            assert data['success'] is True
            
            # Verify deletion by trying to get the element
            get_response = client.get(
                f'/api/ranges-editor/{test_range_id}/elements/test-delete-element'
            )
            assert get_response.status_code == 404
    
    def test_complete_element_workflow(self, client: FlaskClient, test_range_id: str) -> None:
        """Test complete CRUD workflow: Create -> Read -> Update -> Delete."""
        element_id = 'test-workflow-element'
        
        # Step 1: CREATE
        create_payload = {
            'id': element_id,
            'abbrev': 'TWE',
            'value': 'workflow-test',
            'parent': '',
            'description': {
                'en': 'Workflow Test Element',
                'pl': 'Element testowy przepływu'
            }
        }
        
        create_response = client.post(
            f'/api/ranges-editor/{test_range_id}/elements',
            data=json.dumps(create_payload),
            content_type='application/json'
        )
        
        if create_response.status_code != 201:
            pytest.skip("Cannot create element - database might be read-only")
        
        create_data = json.loads(create_response.data)
        assert create_data['success'] is True
        assert 'guid' in create_data['data']
        
        # Step 2: READ
        read_response = client.get(
            f'/api/ranges-editor/{test_range_id}/elements/{element_id}'
        )
        
        assert read_response.status_code == 200
        read_data = json.loads(read_response.data)
        assert read_data['success'] is True
        assert read_data['data']['id'] == element_id
        
        # Step 3: UPDATE
        update_payload = {
            'labels': {},
            'descriptions': {
                'en': 'Updated Workflow Test Element',
                'pl': 'Zaktualizowany element testowy',
                'pt': 'Elemento de teste de fluxo de trabalho'
            },
            'abbrevs': {'und': 'UWE'},
            'parent': ''
        }
        
        update_response = client.put(
            f'/api/ranges-editor/{test_range_id}/elements/{element_id}',
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        if update_response.status_code == 200:
            update_data = json.loads(update_response.data)
            assert update_data['success'] is True
        
        # Step 4: DELETE
        delete_response = client.delete(
            f'/api/ranges-editor/{test_range_id}/elements/{element_id}'
        )
        
        if delete_response.status_code == 200:
            delete_data = json.loads(delete_response.data)
            assert delete_data['success'] is True
            
            # Verify deletion
            verify_response = client.get(
                f'/api/ranges-editor/{test_range_id}/elements/{element_id}'
            )
            assert verify_response.status_code == 404
    
    def test_create_element_validation(self, client: FlaskClient, test_range_id: str) -> None:
        """Test validation when creating elements."""
        # Missing required field: id
        payload = {
            'abbrev': 'TST',
            'description': {'en': 'Test'}
        }
        
        response = client.post(
            f'/api/ranges-editor/{test_range_id}/elements',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'id' in data['error'].lower()
    
    def test_element_with_hierarchical_parent(self, client: FlaskClient, test_range_id: str) -> None:
        """Test creating element with parent reference."""
        parent_id = 'test-parent-element'
        child_id = 'test-child-element'
        
        # Cleanup any existing elements
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{child_id}')
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{parent_id}')
        
        # First create parent
        parent_payload = {
            'id': parent_id,
            'abbrev': 'TPE',
            'description': {'en': 'Parent Element'}
        }
        
        parent_response = client.post(
            f'/api/ranges-editor/{test_range_id}/elements',
            data=json.dumps(parent_payload),
            content_type='application/json'
        )
        
        assert parent_response.status_code == 201
        
        # Create child with parent reference
        child_payload = {
            'id': child_id,
            'abbrev': 'TCE',
            'parent': parent_id,
            'description': {'en': 'Child Element'}
        }
        
        child_response = client.post(
            f'/api/ranges-editor/{test_range_id}/elements',
            data=json.dumps(child_payload),
            content_type='application/json'
        )
        
        if child_response.status_code == 201:
            child_data = json.loads(child_response.data)
            assert child_data['success'] is True
            
            # Verify parent relationship
            get_response = client.get(
                f'/api/ranges-editor/{test_range_id}/elements/{child_id}'
            )
            
            if get_response.status_code == 200:
                get_data = json.loads(get_response.data)
                element = get_data['data']
                if 'parent' in element:
                    assert element['parent'] == parent_id
        
        # Cleanup
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{child_id}')
        client.delete(f'/api/ranges-editor/{test_range_id}/elements/{parent_id}')
