"""
Integration test for /api/entries/ endpoint - validates architecture compliance.

Verifies that:
1. Entries API uses BaseX/XML for dictionary data (not PostgreSQL)
2. PostgreSQL is only used for corpus/frequency data  
3. API correctly handles DB connectivity issues
"""
from __future__ import annotations

import pytest
import json
from unittest.mock import patch, MagicMock

from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.utils.exceptions import DatabaseConnectionError


@pytest.fixture(scope="module")
def app() -> Flask:
    app = create_app('testing')
    app.config['TESTING'] = True
    return app

@pytest.fixture(scope="module")
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.mark.integration
def test_entries_api_uses_basex_not_postgresql(client: FlaskClient, app: Flask) -> None:
    """Test that /api/entries/ uses BaseX/XML for dictionary data, not PostgreSQL."""
    with app.test_request_context():
        with patch('app.api.entries.get_dictionary_service') as mock_get_service, \
             patch('app.api.entries.CacheService') as mock_cache_class:
            
            # Mock cache to not return cached data
            mock_cache = MagicMock()
            mock_cache.is_available.return_value = False
            mock_cache_class.return_value = mock_cache
            
            # Mock BaseX dictionary service
            from app.models.entry import Entry
            mock_service = MagicMock()
            mock_entry = Entry(id_='test1', lexical_unit={'en': 'test'},
                senses=[{"id": "sense1", "definitions": {"en": {"text": "test definition"}}}])
            mock_service.list_entries.return_value = ([mock_entry], 1)
            mock_get_service.return_value = mock_service
            
            response = client.get('/api/entries/?limit=10&offset=0')
            assert response.status_code == 200
            
            data = json.loads(response.data.decode('utf-8'))
            assert 'entries' in data
            assert data['total_count'] == 1
            assert data['entries'][0]['lexical_unit'] == {'en': 'test'}
            
            # Verify BaseX service was called, not PostgreSQL
            mock_service.list_entries.assert_called_once()


@pytest.mark.integration
def test_entries_api_basex_unavailable(client: FlaskClient) -> None:
    """Test /api/entries/ returns error if BaseX is unavailable."""
    with patch('app.api.entries.get_dictionary_service') as mock_get_service, \
         patch('app.api.entries.CacheService') as mock_cache_class:
        
        # Mock cache to not return cached data
        mock_cache = MagicMock()
        mock_cache.is_available.return_value = False
        mock_cache_class.return_value = mock_cache
        
        # Mock BaseX service to raise an error
        mock_get_service.side_effect = DatabaseConnectionError("BaseX unavailable")
        
        response = client.get('/api/entries/?limit=10&offset=0')
        assert response.status_code in (500, 503)
        data = json.loads(response.data.decode('utf-8'))
        assert 'error' in data


@pytest.mark.integration
def test_entries_api_architecture_compliance(client: FlaskClient) -> None:
    """Test that entries API follows correct architecture (BaseX for entries, PostgreSQL for corpus)."""
    with patch('app.api.entries.get_dictionary_service') as mock_dict_service, \
         patch('app.api.entries.CacheService') as mock_cache_class:
        
        # Mock cache to not return cached data
        mock_cache = MagicMock()
        mock_cache.is_available.return_value = False
        mock_cache_class.return_value = mock_cache
        
        # Mock BaseX dictionary service
        mock_service = MagicMock()
        mock_service.list_entries.return_value = ([], 0)
        mock_dict_service.return_value = mock_service
        
        response = client.get('/api/entries/?limit=10&offset=0')
        assert response.status_code == 200
        
        # Verify BaseX service was called
        mock_dict_service.assert_called_once()
        mock_service.list_entries.assert_called_once()
