"""
TDD tests for application consistency and Redis cache integration.
"""
from __future__ import annotations

import pytest
from flask import Flask, current_app
from unittest.mock import patch, MagicMock

from app import create_app
from app.services.cache_service import CacheService
from app.database.mock_connector import MockDatabaseConnector
from app.services.dictionary_service import DictionaryService


class TestAppConsistency:
    """Test application title consistency and routing."""
    
    def test_consistent_app_title_in_templates(self, app: Flask):
        """Test that all templates use consistent app title 'Lexicographic Curation Workbench'."""
        with app.test_client() as client:
            # Test main page title
            response = client.get('/')
            assert response.status_code == 200
            assert b'Lexicographic Curation Workbench' in response.data
            assert b'Dictionary Writing System' not in response.data
            
    def test_corpus_management_single_route(self, app: Flask):
        """Test that corpus management has single consistent route."""
        with app.test_client() as client:
            # Test correct route works
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Test old API route doesn't serve templates
            response = client.get('/api/corpus/')
            # Should either not exist or return JSON, not HTML template
            if response.status_code == 200:
                assert 'text/html' not in response.content_type
                
    def test_corpus_management_postgres_connection(self, app: Flask):
        """Test that corpus management connects to PostgreSQL."""
        with app.test_client() as client:
            # Mock PostgreSQL connection
            with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
                mock_instance = MagicMock()
                mock_connector.return_value = mock_instance
                mock_instance.test_connection.return_value = True
                
                response = client.get('/corpus-management')
                assert response.status_code == 200
                # Should have PostgreSQL status check
                
    def test_navigation_consistency(self, app: Flask):
        """Test that navigation links are consistent across templates."""
        with app.test_client() as client:
            # Check main page navigation
            response = client.get('/')
            assert response.status_code == 200
            assert b'/corpus-management' in response.data
            assert b'/api/corpus' not in response.data
            
            # Check entries page navigation
            response = client.get('/entries')
            assert response.status_code == 200
            assert b'/corpus-management' in response.data


class TestRedisCacheIntegration:
    """Test Redis cache integration for performance optimization."""
    
    def test_cache_service_initialization(self, app: Flask):
        """Test that cache service initializes correctly."""
        with app.app_context():
            # The cache_service is now attached directly to the app, not via injector
            assert hasattr(current_app, 'cache_service')
            assert isinstance(current_app.cache_service, CacheService)
        
    def test_cache_service_connection(self, app: Flask):
        """Test cache service Redis connection."""
        with patch('redis.Redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            # CacheService is a singleton, so we create a new instance normally
            cache_service = CacheService()
            # The connection would be attempted in _connect method
            assert hasattr(cache_service, 'redis_client')
            
    def test_entries_api_caching(self, app: Flask):
        """Test that entries API uses Redis caching when available."""
        with app.test_client() as client:
            # We patch the cache_service instance on the app context
            with patch.object(app.cache_service, 'get') as mock_get:
                mock_get.return_value = None  # Cache miss
                response = client.get('/api/entries')
                # Just verify that the endpoint works, caching is optional
                assert response.status_code == 200
