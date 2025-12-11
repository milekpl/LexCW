"""Integration tests for multilingual LIFT range element API."""

from __future__ import annotations

import pytest
from flask import Flask

from app import create_app


@pytest.fixture
def app() -> Flask:
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app: Flask):
    """Create test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def cleanup_ranges(app):
    """Clean up test ranges before and after tests."""
    from app.services.ranges_service import RangesService
    from app.utils.exceptions import NotFoundError
    
    range_ids = [
        'test-range', 'ml-range', 'update-range', 'list-range', 
        'val-range', 'ne-range', 'crud-range'
    ]
    
    service = app.injector.get(RangesService)
    
    def _clean():
        for rid in range_ids:
            try:
                service.delete_range(rid)
            except (NotFoundError, Exception):
                pass

    _clean()
    yield
    _clean()


class TestMultilingualElementAPI:
    """Test multilingual element CRUD via API."""
    
    def test_create_element_with_multilingual_properties(self, client) -> None:
        """Should create element with multilingual labels, descriptions, and abbreviations."""
        # Create a range first
        range_data = {
            'id': 'test-range',
            'labels': {'en': 'Test Range'}
        }
        create_response = client.post(
            '/api/ranges-editor/',
            json=range_data,
            content_type='application/json'
        )
        assert create_response.status_code in [201, 200]
        
        # Create element with multilingual properties
        element_data = {
            'id': 'test-element',
            'labels': {
                'en': 'English Label',
                'pl': 'Etykieta Polska',
                'pt': 'Rótulo Português'
            },
            'descriptions': {
                'en': 'English description',
                'pl': 'Polski opis',
                'pt': 'Descrição em português'
            },
            'abbrevs': {
                'en': 'ENG',
                'pl': 'POL',
                'pt': 'PRT'
            }
        }
        
        # Execute
        response = client.post(
            '/api/ranges-editor/test-range/elements',
            json=element_data,
            content_type='application/json'
        )
        
        # Verify response
        assert response.status_code in [201, 200]
        result = response.get_json()
        assert result['success'] is True
        assert 'data' in result
        assert 'guid' in result['data']
    
    def test_get_element_returns_multilingual_properties(self, client) -> None:
        """Should return element with all multilingual properties."""
        # Create range and element
        range_data = {
            'id': 'ml-range',
            'labels': {'en': 'ML Range'}
        }
        client.post('/api/ranges-editor/', json=range_data, content_type='application/json')
        
        element_data = {
            'id': 'ml-element',
            'labels': {'en': 'English', 'pl': 'Polski'},
            'descriptions': {'en': 'Desc EN', 'pl': 'Opis PL'},
            'abbrevs': {'en': 'EN', 'pl': 'PL'}
        }
        client.post(
            '/api/ranges-editor/ml-range/elements',
            json=element_data,
            content_type='application/json'
        )
        
        # Get element
        response = client.get('/api/ranges-editor/ml-range/elements/ml-element')
        
        # Verify
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        element = result['data']
        assert element['id'] == 'ml-element'
        assert 'labels' in element
        assert element['labels'].get('en') == 'English'
        assert element['labels'].get('pl') == 'Polski'
        assert 'descriptions' in element
        assert element['descriptions'].get('en') == 'Desc EN'
        assert element['descriptions'].get('pl') == 'Opis PL'
        assert 'abbrevs' in element
        assert element['abbrevs'].get('en') == 'EN'
        assert element['abbrevs'].get('pl') == 'PL'
    
    def test_update_element_multilingual_properties(self, client) -> None:
        """Should update element with new multilingual properties."""
        # Create range and element
        range_data = {'id': 'update-range', 'labels': {'en': 'Update Range'}}
        client.post('/api/ranges-editor/', json=range_data, content_type='application/json')
        
        element_data = {
            'id': 'update-element',
            'labels': {'en': 'Old EN'},
            'descriptions': {},
            'abbrevs': {}
        }
        client.post(
            '/api/ranges-editor/update-range/elements',
            json=element_data,
            content_type='application/json'
        )
        
        # Update element with new multilingual content
        updated_data = {
            'labels': {
                'en': 'New English',
                'pl': 'Nowy Polski',
                'fr': 'Nouveau Français'
            },
            'descriptions': {
                'en': 'Updated description',
                'pl': 'Zaktualizowany opis'
            },
            'abbrevs': {
                'en': 'NEW',
                'pl': 'NWY'
            }
        }
        
        # Execute
        response = client.put(
            '/api/ranges-editor/update-range/elements/update-element',
            json=updated_data,
            content_type='application/json'
        )
        
        # Verify update succeeded
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
    
    def test_list_elements_shows_all_properties(self, client) -> None:
        """Should list all elements with their multilingual properties."""
        # Create range
        range_data = {'id': 'list-range', 'labels': {'en': 'List Range'}}
        client.post('/api/ranges-editor/', json=range_data, content_type='application/json')
        
        # Create multiple elements
        elements = [
            {
                'id': 'elem-1',
                'labels': {'en': 'First', 'pl': 'Pierwszy'},
                'descriptions': {'en': 'First desc'},
                'abbrevs': {'en': 'F1'}
            },
            {
                'id': 'elem-2',
                'labels': {'en': 'Second', 'pl': 'Drugi'},
                'descriptions': {'en': 'Second desc'},
                'abbrevs': {'en': 'F2'}
            }
        ]
        
        for elem in elements:
            client.post(
                '/api/ranges-editor/list-range/elements',
                json=elem,
                content_type='application/json'
            )
        
        # List elements
        response = client.get('/api/ranges-editor/list-range/elements')
        
        # Verify
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        data = result['data']
        
        # Check that we have both elements
        elem_ids = [e['id'] for e in data]
        assert 'elem-1' in elem_ids
        assert 'elem-2' in elem_ids
        
        # Verify multilingual properties are present
        for elem in data:
            if elem['id'] == 'elem-1':
                assert 'labels' in elem
                assert 'descriptions' in elem
                assert 'abbrevs' in elem
                assert elem['labels'].get('en') == 'First'
                assert elem['labels'].get('pl') == 'Pierwszy'


class TestMultilingualElementValidation:
    """Test API validation for multilingual elements."""
    
    def test_create_element_without_id_fails(self, client) -> None:
        """Should reject element creation without ID."""
        # Create range first
        range_data = {'id': 'val-range', 'labels': {'en': 'Val Range'}}
        client.post('/api/ranges-editor/', json=range_data, content_type='application/json')
        
        # Try to create without ID
        element_data = {
            'labels': {'en': 'No ID'},
            'descriptions': {},
            'abbrevs': {}
        }
        
        response = client.post(
            '/api/ranges-editor/val-range/elements',
            json=element_data,
            content_type='application/json'
        )
        
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
    
    def test_update_nonexistent_element_fails(self, client) -> None:
        """Should reject update of non-existent element."""
        # Create range
        range_data = {'id': 'ne-range', 'labels': {'en': 'NE Range'}}
        client.post('/api/ranges-editor/', json=range_data, content_type='application/json')
        
        # Try to update non-existent element
        element_data = {
            'labels': {'en': 'Test'},
            'descriptions': {},
            'abbrevs': {}
        }
        
        response = client.put(
            '/api/ranges-editor/ne-range/elements/nonexistent',
            json=element_data,
            content_type='application/json'
        )
        
        assert response.status_code == 404


class TestMultilingualElementCRUD:
    """Test complete CRUD cycle for multilingual elements."""
    
    def test_full_crud_cycle(self, client) -> None:
        """Should handle create, read, update, delete cycle."""
        # 1. Create range
        range_data = {'id': 'crud-range', 'labels': {'en': 'CRUD Range'}}
        response = client.post(
            '/api/ranges-editor/',
            json=range_data,
            content_type='application/json'
        )
        assert response.status_code in [200, 201]
        
        # 2. Create element with multilingual properties
        element_data = {
            'id': 'crud-element',
            'labels': {'en': 'Original', 'pl': 'Oryginał'},
            'descriptions': {'en': 'Original desc'},
            'abbrevs': {'en': 'ORG'}
        }
        response = client.post(
            '/api/ranges-editor/crud-range/elements',
            json=element_data,
            content_type='application/json'
        )
        assert response.status_code in [200, 201]
        
        # 3. Read element
        response = client.get('/api/ranges-editor/crud-range/elements/crud-element')
        assert response.status_code == 200
        result = response.get_json()
        element = result['data']
        assert element['labels']['en'] == 'Original'
        assert element['labels']['pl'] == 'Oryginał'
        
        # 4. Update element
        updated_data = {
            'labels': {
                'en': 'Updated',
                'pl': 'Zaktualizowany',
                'pt': 'Atualizado'
            },
            'descriptions': {'en': 'Updated desc', 'pt': 'Descrição atualizada'},
            'abbrevs': {'en': 'UPD', 'pt': 'ATU'}
        }
        response = client.put(
            '/api/ranges-editor/crud-range/elements/crud-element',
            json=updated_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # 5. Read updated element
        response = client.get('/api/ranges-editor/crud-range/elements/crud-element')
        assert response.status_code == 200
        result = response.get_json()
        element = result['data']
        assert element['labels']['en'] == 'Updated'
        assert element['labels']['pt'] == 'Atualizado'
        assert element['descriptions']['pt'] == 'Descrição atualizada'
        assert element['abbrevs']['pt'] == 'ATU'
        
        # 6. Delete element
        response = client.delete('/api/ranges-editor/crud-range/elements/crud-element')
        assert response.status_code == 200
        
        # 7. Verify deletion
        response = client.get('/api/ranges-editor/crud-range/elements/crud-element')
        assert response.status_code == 404
