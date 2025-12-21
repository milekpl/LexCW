"""Integration tests for multilingual LIFT range element API."""

from __future__ import annotations

import pytest
from flask import Flask

from app import create_app
from app.services.ranges_service import RangesService


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
        service = client.application.injector.get(RangesService)
        service.create_range(range_data)
        
        # Create element with multilingual properties
        element_data = {
            'id': 'test-element',
            'labels': {
                'en': 'English Label',
                'pl': 'Etykieta Polska',
                'pt': 'Rótulo Português'
            },
            'description': {
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
        
        # Execute via service
        service.create_range_element('test-range', element_data)
    
    def test_get_element_returns_multilingual_properties(self, client) -> None:
        """Should return element with all multilingual properties."""
        # Create range and element
        range_data = {
            'id': 'ml-range',
            'labels': {'en': 'ML Range'}
        }
        service = client.application.injector.get(RangesService)
        service.create_range(range_data)
        
        element_data = {
            'id': 'ml-element',
            'labels': {'en': 'English', 'pl': 'Polski'},
            'description': {'en': 'Desc EN', 'pl': 'Opis PL'},
            'abbrevs': {'en': 'EN', 'pl': 'PL'}
        }
        service.create_range_element('ml-range', element_data)
        
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
        assert 'description' in element
        assert element['description'].get('en') == 'Desc EN'
        assert element['description'].get('pl') == 'Opis PL'
        assert 'abbrevs' in element
        assert element['abbrevs'].get('en') == 'EN'
        assert element['abbrevs'].get('pl') == 'PL'
    
    def test_update_element_multilingual_properties(self, client) -> None:
        """Should update element with new multilingual properties."""
        # Create range and element
        range_data = {'id': 'update-range', 'labels': {'en': 'Update Range'}}
        service = client.application.injector.get(RangesService)
        service.create_range(range_data)
        
        element_data = {
            'id': 'update-element',
            'labels': {'en': 'Old EN'},
            'description': {},
            'abbrevs': {}
        }
        service.create_range_element('update-range', element_data)
        
        # Update element with new multilingual content
        updated_data = {
            'labels': {
                'en': 'New English',
                'pl': 'Nowy Polski',
                'fr': 'Nouveau Français'
            },
            'description': {
                'en': 'Updated description',
                'pl': 'Zaktualizowany opis'
            },
            'abbrevs': {
                'en': 'NEW',
                'pl': 'NWY'
            }
        }
        
        # Execute via service
        service.update_range_element('update-range', 'update-element', updated_data)

    def test_create_range_json_rejected(self, client) -> None:
        """JSON POST to create range should be rejected (data-rich JSON removed)."""
        range_data = {
            'id': 'json-reject-range',
            'labels': {'en': 'JSON Reject Range'}
        }
        response = client.post(
            '/api/ranges-editor/',
            json=range_data,
            content_type='application/json'
        )
        # Expect 415 Unsupported Media Type or 400 depending on implementation
        assert response.status_code in (400, 415)
    
    def test_list_elements_shows_all_properties(self, client) -> None:
        """Should list all elements with their multilingual properties."""
        # Create range
        range_data = {'id': 'list-range', 'labels': {'en': 'List Range'}}
        service = client.application.injector.get(RangesService)
        service.create_range(range_data)
        
        # Create multiple elements
        elements = [
            {
                'id': 'elem-1',
                'labels': {'en': 'First', 'pl': 'Pierwszy'},
                'description': {'en': 'First desc'},
                'abbrevs': {'en': 'F1'}
            },
            {
                'id': 'elem-2',
                'labels': {'en': 'Second', 'pl': 'Drugi'},
                'description': {'en': 'Second desc'},
                'abbrevs': {'en': 'F2'}
            }
        ]
        
        for elem in elements:
            service.create_range_element('list-range', elem)
        
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
                assert 'description' in elem
                assert 'abbrevs' in elem
                assert elem['labels'].get('en') == 'First'
                assert elem['labels'].get('pl') == 'Pierwszy'


class TestMultilingualElementValidation:
    """Test API validation for multilingual elements."""
    
    def test_create_element_without_id_fails(self, client) -> None:
        """Should reject element creation without ID."""
        # Create range first
        range_data = {'id': 'val-range', 'labels': {'en': 'Val Range'}}
        service = client.application.injector.get(RangesService)
        service.create_range(range_data)
        
        # Try to create without ID
        element_data = {
            'labels': {'en': 'No ID'},
            'description': {},
            'abbrevs': {}
        }
        
        # Validate service raises for missing id when creating element
        with pytest.raises(Exception):
            service.create_range_element('val-range', element_data)
    
    def test_update_nonexistent_element_fails(self, client) -> None:
        """Should reject update of non-existent element."""
        # Create range via service
        range_data = {'id': 'ne-range', 'labels': {'en': 'NE Range'}}
        service = client.application.injector.get(RangesService)
        service.create_range(range_data)
        
        # Try to update non-existent element
        element_data = {
            'labels': {'en': 'Test'},
            'description': {},
            'abbrevs': {}
        }
        
        with pytest.raises(Exception):
            service.update_range_element('ne-range', 'nonexistent', element_data)


class TestMultilingualElementCRUD:
    """Test complete CRUD cycle for multilingual elements."""
    
    def test_full_crud_cycle(self, client) -> None:
        """Should handle create, read, update, delete cycle."""
        # 1. Create range
        range_data = {'id': 'crud-range', 'labels': {'en': 'CRUD Range'}}
        service = client.application.injector.get(RangesService)
        service.create_range(range_data)
        
        # 2. Create element with multilingual properties
        element_data = {
            'id': 'crud-element',
            'labels': {'en': 'Original', 'pl': 'Oryginał'},
            'description': {'en': 'Original desc'},
            'abbrevs': {'en': 'ORG'}
        }
        service.create_range_element('crud-range', element_data)
        
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
            'description': {'en': 'Updated desc', 'pt': 'Descrição atualizada'},
            'abbrevs': {'en': 'UPD', 'pt': 'ATU'}
        }
        service.update_range_element('crud-range', 'crud-element', updated_data)
        
        # 5. Read updated element
        response = client.get('/api/ranges-editor/crud-range/elements/crud-element')
        assert response.status_code == 200
        result = response.get_json()
        element = result['data']
        assert element['labels']['en'] == 'Updated'
        assert element['labels']['pt'] == 'Atualizado'
        assert element['description']['pt'] == 'Descrição atualizada'
        assert element['abbrevs']['pt'] == 'ATU'
        
        # 6. Delete element
        response = client.delete('/api/ranges-editor/crud-range/elements/crud-element')
        assert response.status_code == 200
        
        # 7. Verify deletion
        response = client.get('/api/ranges-editor/crud-range/elements/crud-element')
        assert response.status_code == 404
