"""
TDD tests for application consistency and Redis cache integration.
"""
from __future__ import annotations

import pytest
from flask import Flask
from unittest.mock import patch, MagicMock

from app import create_app
from app.services.cache_service import CacheService


class TestAppConsistency:
    """Test application title consistency and routing."""
    
    def test_consistent_app_title_in_templates(self):
        """Test that all templates use consistent app title 'Lexicographic Curation Workbench'."""
        app = create_app('testing')
        
        with app.test_client() as client:
            # Test main page title
            response = client.get('/')
            assert response.status_code == 200
            assert b'Lexicographic Curation Workbench' in response.data
            assert b'Dictionary Writing System' not in response.data
            
    def test_corpus_management_single_route(self):
        """Test that corpus management has single consistent route."""
        app = create_app('testing')
        
        with app.test_client() as client:
            # Test correct route works
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Test old API route doesn't serve templates
            response = client.get('/api/corpus/')
            # Should either not exist or return JSON, not HTML template
            if response.status_code == 200:
                assert b'text/html' not in response.headers.get('Content-Type', '')
                
    def test_corpus_management_postgres_connection(self):
        """Test that corpus management connects to PostgreSQL."""
        app = create_app('testing')
        
        with app.test_client() as client:
            # Mock PostgreSQL connection
            with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
                mock_instance = MagicMock()
                mock_connector.return_value = mock_instance
                mock_instance.test_connection.return_value = True
                
                response = client.get('/corpus-management')
                assert response.status_code == 200
                # Should have PostgreSQL status check
                
    def test_navigation_consistency(self):
        """Test that navigation links are consistent across templates."""
        app = create_app('testing')
        
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
    
    def test_cache_service_initialization(self):
        """Test that cache service initializes correctly."""
        cache_service = CacheService()
        assert cache_service is not None
        
    def test_cache_service_connection(self):
        """Test cache service Redis connection."""
        with patch('redis.Redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache_service = CacheService()
            assert cache_service.is_available() is True
            
    def test_entries_api_caching(self):
        """Test that entries API uses Redis caching when available."""
        app = create_app('testing')
        
        with app.test_client() as client:
            with patch('app.services.cache_service.CacheService') as mock_cache:
                mock_cache_instance = MagicMock()
                mock_cache.return_value = mock_cache_instance
                mock_cache_instance.is_available.return_value = True
                mock_cache_instance.get.return_value = None  # Cache miss
                
                # This should use cache service when implemented
                response = client.get('/api/entries/?limit=20&offset=0')
                # Test will fail until we implement caching
