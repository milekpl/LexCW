"""
Unit tests for autosave API endpoint.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, ANY
from datetime import datetime, timezone


def test_autosave_persists_entry(app):
    """Autosave should call DictionaryService.update_entry()"""
    from app.api.entry_autosave_working import autosave_bp

    # Register the autosave blueprint
    app.register_blueprint(autosave_bp)

    mock_dictionary_service = Mock()
    mock_dictionary_service.update_entry.return_value = {'id': 'test', 'version': '1.0'}

    mock_event_bus = Mock()

    # Configure injector to return our mocks
    def get_mock_service(cls):
        if cls.__name__ == 'DictionaryService':
            return mock_dictionary_service
        elif cls.__name__ == 'EventBus':
            return mock_event_bus
        return Mock()

    app.injector.get = get_mock_service

    with app.test_client() as client:
        # Use valid entry data that will pass validation
        entry_data = {
            'id': 'test-entry-123',
            'lexical_unit': {'en': 'test'},
            'senses': [{'id': 'sense1', 'definition': {'en': 'A test definition'}}]
        }
        response = client.post('/api/entry/autosave',
            json={'entryData': entry_data},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        mock_dictionary_service.update_entry.assert_called_once()
        mock_event_bus.emit.assert_called_once()


def test_autosave_emits_event_with_correct_payload(app):
    """Autosave should emit entry_updated event with correct payload"""
    from app.api.entry_autosave_working import autosave_bp

    app.register_blueprint(autosave_bp)

    mock_dictionary_service = Mock()
    mock_dictionary_service.update_entry.return_value = {'id': 'test-entry'}

    mock_event_bus = Mock()

    def get_mock_service(cls):
        if cls.__name__ == 'DictionaryService':
            return mock_dictionary_service
        elif cls.__name__ == 'EventBus':
            return mock_event_bus
        return Mock()

    app.injector.get = get_mock_service

    with app.test_client() as client:
        entry_data = {
            'id': 'test-entry-456',
            'lexical_unit': {'en': 'hello'},
            'senses': [{'id': 'sense1', 'definition': {'en': 'A greeting'}}]
        }
        response = client.post('/api/entry/autosave',
            json={'entryData': entry_data},
            content_type='application/json'
        )

        assert response.status_code == 200
        # Verify event was emitted with correct event name
        mock_event_bus.emit.assert_called_once_with('entry_updated', ANY)


def test_autosave_keeps_existing_validation(app):
    """Autosave should still validate and return errors for missing entryData"""
    from app.api.entry_autosave_working import autosave_bp

    app.register_blueprint(autosave_bp)

    mock_dictionary_service = Mock()
    mock_event_bus = Mock()

    def get_mock_service(cls):
        if cls.__name__ == 'DictionaryService':
            return mock_dictionary_service
        elif cls.__name__ == 'EventBus':
            return mock_event_bus
        return Mock()

    app.injector.get = get_mock_service

    with app.test_client() as client:
        # Send request with missing entryData
        response = client.post('/api/entry/autosave',
            json={},
            content_type='application/json'
        )

        # Should fail with invalid_request, not call update_entry
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        assert data['error'] == 'invalid_request'
        mock_dictionary_service.update_entry.assert_not_called()
        mock_event_bus.emit.assert_not_called()


def test_autosave_validation_error_blocks_save(app):
    """Autosave should not persist when validation has critical errors"""
    from app.api.entry_autosave_working import autosave_bp

    app.register_blueprint(autosave_bp)

    mock_dictionary_service = Mock()
    mock_event_bus = Mock()

    def get_mock_service(cls):
        if cls.__name__ == 'DictionaryService':
            return mock_dictionary_service
        elif cls.__name__ == 'EventBus':
            return mock_event_bus
        return Mock()

    app.injector.get = get_mock_service

    with app.test_client() as client:
        # Send entry data that will fail validation (empty dict will fail)
        response = client.post('/api/entry/autosave',
            json={'entryData': {}},
            content_type='application/json'
        )

        # Should fail validation
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        # Should not call update_entry or emit event
        mock_dictionary_service.update_entry.assert_not_called()
        mock_event_bus.emit.assert_not_called()
