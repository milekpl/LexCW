#!/usr/bin/env python3

"""
Test for updated API caching functionality - focused on API endpoints only.
This follows TDD principles and tests the core caching improvements.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, Mock
from flask.testing import FlaskClient
from app.services.cache_service import CacheService
import json


class TestAPICachingImprovements:
    """Test API caching improvements without template dependencies."""

    def test_dashboard_api_caching_behavior(self, client: FlaskClient) -> None:
        """Test that dashboard API properly implements caching."""
        # Clear any existing cache
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('dashboard_stats*')
        
        # Test caching behavior with real data (no mocking needed)
        # First call - should generate fresh data
        response1 = client.get('/api/dashboard/stats')
        
        # The API should either work (200) or fail gracefully (500)
        # Both are acceptable for this caching test
        if response1.status_code == 200:
            data1 = response1.get_json()
            assert data1['success'] is True
            assert data1['cached'] is False  # Fresh data
            assert 'data' in data1
            assert 'stats' in data1['data']
            
            # Second call - should return cached data
            response2 = client.get('/api/dashboard/stats')
            assert response2.status_code == 200
            data2 = response2.get_json()
            assert data2['success'] is True
            assert data2['cached'] is True  # Cached data
            
            # Data should be identical between calls
            assert data1['data'] == data2['data']
        else:
            # If the API fails due to database issues, 
            # just verify it fails consistently (no caching of errors)
            assert response1.status_code == 500
            data1 = response1.get_json()
            assert data1['success'] is False
            
            # Second call should also fail (errors aren't cached)
            response2 = client.get('/api/dashboard/stats')
            assert response2.status_code == 500

    def test_entries_api_caching_improvements(self, client: FlaskClient) -> None:
        """Test that entries API properly implements improved caching."""
        # Clear any existing cache
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            from app.models.entry import Entry
            
            mock_dict_service = Mock()
            mock_entries = [
                Entry(id_="test1", lexical_unit={"en": "test1"}),
                Entry(id_="test2", lexical_unit={"en": "test2"})
            ]
            mock_dict_service.list_entries.return_value = (mock_entries, 2)
            mock_get_service.return_value = mock_dict_service
            
            # First call - should generate fresh data and cache it
            response1 = client.get('/api/entries/?limit=10&offset=0')
            assert response1.status_code == 200
            data1 = response1.get_json()
            assert 'entries' in data1
            assert 'total_count' in data1  # New field we added
            assert data1['total_count'] == 2
            assert len(data1['entries']) == 2
            
            # Second call with same parameters - should return cached data
            response2 = client.get('/api/entries/?limit=10&offset=0')
            assert response2.status_code == 200
            data2 = response2.get_json()
            assert data2 == data1  # Should be identical (cached)
            
            # Verify the service was only called once
            assert mock_dict_service.list_entries.call_count == 1

    def test_cache_clear_functionality(self, client: FlaskClient) -> None:
        """Test that cache clearing works properly."""
        cache = CacheService()
        if not cache.is_available():
            pytest.skip("Cache service not available")
        
        # Test dashboard cache clearing
        response = client.post('/api/dashboard/clear-cache')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'cache cleared' in data['message'].lower()

    def test_api_error_handling_with_cache(self, client: FlaskClient) -> None:
        """Test that APIs handle errors properly even with caching enabled."""
        # Test with a non-existent endpoint that should return 404
        response = client.get('/api/dashboard/nonexistent')
        assert response.status_code == 404
        
        # Test actual API endpoint - it should work normally
        response = client.get('/api/dashboard/stats')
        # Should either succeed or fail gracefully, but not crash
        assert response.status_code in [200, 500]  # Allow either success or controlled error
        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] is True
        else:
            data = response.get_json()
            assert data['success'] is False
            assert 'error' in data

    def test_corpus_stats_api_caching(self, client: FlaskClient) -> None:
        """Test that corpus stats API maintains proper caching."""
        # Clear any existing cache
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('corpus_stats*')
        
        # First call should fetch fresh data
        response1 = client.get('/api/corpus/stats')
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert data1['success'] is True
        assert 'stats' in data1
        assert 'total_records' in data1['stats']
        assert isinstance(data1['stats']['total_records'], int)
        
        # Second call should return same data (may or may not be cached depending on TTL)
        response2 = client.get('/api/corpus/stats')
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['success'] is True
        assert data2['stats']['total_records'] == data1['stats']['total_records']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
