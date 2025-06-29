"""
Unit test for API entries endpoint error handling.
"""
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app.api.entries import entries_bp, get_entry
from app.utils.exceptions import NotFoundError


def test_get_entry_handles_none_result():
    """Test that get_entry properly handles when service returns None."""
    app = Flask(__name__)
    app.register_blueprint(entries_bp, url_prefix='/api/entries')
    
    with app.test_client() as client:
        with patch('app.api.entries.get_dictionary_service') as mock_service_func:
            mock_service = MagicMock()
            mock_service.get_entry.return_value = None  # Service returns None instead of raising NotFoundError
            mock_service_func.return_value = mock_service
            
            with app.test_request_context():
                response = client.get('/api/entries/nonexistent')
                
                assert response.status_code == 404
                data = response.get_json()
                assert 'error' in data
                assert 'not found' in data['error'].lower()


def test_get_entry_handles_not_found_error():
    """Test that get_entry properly handles NotFoundError."""
    app = Flask(__name__)
    app.register_blueprint(entries_bp, url_prefix='/api/entries')
    
    with app.test_client() as client:
        with patch('app.api.entries.get_dictionary_service') as mock_service_func:
            mock_service = MagicMock()
            mock_service.get_entry.side_effect = NotFoundError("Entry not found")
            mock_service_func.return_value = mock_service
            
            with app.test_request_context():
                response = client.get('/api/entries/nonexistent')
                
                assert response.status_code == 404
                data = response.get_json()
                assert 'error' in data
                assert 'Entry not found' in data['error']


if __name__ == '__main__':
    test_get_entry_handles_none_result()
    test_get_entry_handles_not_found_error()
    print("Tests passed!")
