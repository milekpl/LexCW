"""
Unit test for API entries endpoint error handling.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from flask.testing import FlaskClient
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import NotFoundError


@pytest.fixture
def mock_service() -> MagicMock:
    """Create a mock dictionary service for unit tests."""
    service = MagicMock(spec=DictionaryService)
    service.get_entry.return_value = None
    service.create_entry.return_value = True
    service.list_entries.return_value = ([], 0)
    service.search_entries.return_value = ([], 0)
    service.count_entries.return_value = 0
    
    return service


@pytest.mark.integration
def test_get_entry_handles_none_result(client: FlaskClient, mock_service: MagicMock) -> None:
    """Test that get_entry properly handles when service returns None."""
    mock_service.get_entry.return_value = None
    
    # Patch the injector to return our mock service
    with patch('app.routes.api_routes.current_app') as mock_current_app:
        mock_current_app.injector.get.return_value = mock_service
        response = client.get('/api/entries/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'not found' in data['error'].lower()


@pytest.mark.integration
def test_get_entry_handles_not_found_error(client: FlaskClient, mock_service: MagicMock) -> None:
    """Test that get_entry properly handles NotFoundError."""
    mock_service.get_entry.side_effect = NotFoundError("Entry not found")
    
    # Patch the injector to return our mock service
    with patch('app.routes.api_routes.current_app') as mock_current_app:
        mock_current_app.injector.get.return_value = mock_service
        response = client.get('/api/entries/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'not found' in data['error'].lower()


if __name__ == '__main__':
    print("This test file should be run with pytest, not directly")
