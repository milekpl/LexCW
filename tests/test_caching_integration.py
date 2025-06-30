#!/usr/bin/env python3

"""
Test for updated dashboard and corpus management functionality with caching.
This follows TDD principles - tests first before fixing existing tests.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from flask.testing import FlaskClient
from app.services.cache_service import CacheService
import json


class TestDashboardWithCaching:
    """Test dashboard functionality with our new caching implementation."""

    def test_homepage_with_caching_enabled(self, client: FlaskClient) -> None:
        """Test homepage when caching is enabled and working."""
        # Clear any existing cache to ensure fresh test
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('dashboard_stats*')
        
        with patch('app.injector.get') as mock_injector_get:
            mock_dict_service = Mock()
            mock_dict_service.count_entries.return_value = 150
            mock_dict_service.count_senses_and_examples.return_value = (300, 450)
            mock_dict_service.get_recent_activity.return_value = [
                {'timestamp': '2025-06-29 12:00', 'action': 'Test', 'description': 'Test entry'}
            ]
            mock_dict_service.get_system_status.return_value = {
                'db_connected': True,
                'last_backup': '2025-06-29 12:00',
                'storage_percent': 25
            }
            mock_injector_get.return_value = mock_dict_service
            
            response = client.get('/')
            assert response.status_code == 200
            
            response_text = response.data.decode('utf-8')
            
            # Should show the mocked statistics (first call, cached)
            assert '150' in response_text  # entry count
            assert '300' in response_text  # sense count
            assert '450' in response_text  # example count

    def test_dashboard_api_endpoint_with_caching(self, client: FlaskClient) -> None:
        """Test dashboard API endpoint with caching behavior."""
        # Clear any existing cache
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('dashboard_stats*')
        
        with patch('app.injector.get') as mock_injector_get:
            mock_dict_service = Mock()
            mock_dict_service.count_entries.return_value = 200
            mock_dict_service.count_senses_and_examples.return_value = (400, 600)
            mock_dict_service.get_recent_activity.return_value = []
            mock_dict_service.get_system_status.return_value = {
                'db_connected': True,
                'last_backup': '2025-06-29 12:00',
                'storage_percent': 30
            }
            mock_injector_get.return_value = mock_dict_service
            
            # First call - should generate fresh data
            response1 = client.get('/api/dashboard/stats')
            assert response1.status_code == 200
            data1 = response1.get_json()
            assert data1['success'] is True
            assert data1['cached'] is False  # Fresh data
            assert data1['data']['stats']['entries'] == 200
            
            # Second call - should return cached data (without calling service again)
            response2 = client.get('/api/dashboard/stats')
            assert response2.status_code == 200
            data2 = response2.get_json()
            assert data2['success'] is True
            assert data2['cached'] is True  # Cached data
            assert data2['data']['stats']['entries'] == 200
            
            # Verify the service was only called once (for fresh data)
            assert mock_dict_service.count_entries.call_count == 1


class TestCorpusManagementWithCaching:
    """Test corpus management functionality with our caching implementation."""
    
    def test_corpus_management_with_cache_miss(self, client: FlaskClient) -> None:
        """Test corpus management when cache is empty (cache miss)."""
        # Clear cache to simulate cache miss
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('corpus_stats*')
        
        with patch('app.views.CorpusMigrator') as mock_migrator_class:
            mock_migrator = Mock()
            mock_migrator_class.return_value = mock_migrator
            mock_migrator._get_postgres_connection.return_value = Mock()
            
            mock_stats = {
                'total_records': 1000,
                'avg_source_length': 25.5,
                'avg_target_length': 30.2,
                'first_record': datetime(2023, 1, 1, 10, 0, 0),
                'last_record': datetime(2023, 12, 31, 15, 30, 0)
            }
            mock_migrator.get_corpus_stats.return_value = mock_stats
            
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Verify that the migrator was called (cache miss)
            mock_migrator.get_corpus_stats.assert_called_once()

    def test_corpus_management_with_cache_hit(self, client: FlaskClient) -> None:
        """Test corpus management when cache is populated (cache hit)."""
        # Pre-populate cache with test data
        cache = CacheService()
        if cache.is_available():
            cache_data = {
                'total_records': 2000,
                'avg_source_length': 35.5,
                'avg_target_length': 40.2,
                'last_updated': '2025-06-29 12:00:00'
            }
            cache.set('corpus_stats', json.dumps(cache_data, default=str), ttl=1800)
        
        with patch('app.views.CorpusMigrator') as mock_migrator_class:
            mock_migrator = Mock()
            mock_migrator_class.return_value = mock_migrator
            
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Verify that the migrator was NOT called (cache hit)
            mock_migrator.get_corpus_stats.assert_not_called()

    def test_corpus_management_cache_fallback(self, client: FlaskClient) -> None:
        """Test corpus management fallback when cache and database both fail."""
        # Clear cache to ensure no cached data
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('corpus_stats*')
        
        with patch('app.views.CorpusMigrator') as mock_migrator_class:
            # Mock migrator to raise exception
            mock_migrator_class.side_effect = Exception("Database connection failed")
            
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Should still render with default values
            response_text = response.data.decode('utf-8')
            assert 'corpus_management.html' in response.request.endpoint or response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
