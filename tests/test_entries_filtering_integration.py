#!/usr/bin/env python3

"""
Integration test for entries filtering and sorting functionality.
Tests the actual API endpoints to verify filter and sort_order parameters work correctly.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient
from unittest.mock import patch, Mock


class TestEntriesFilteringIntegration:
    """Test entries filtering and sorting through the API."""

    def test_entries_api_supports_filter_parameter(self, client: FlaskClient) -> None:
        """Test that entries API accepts and uses filter_text parameter."""
        # Clear cache to ensure fresh requests
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            # Create mock entry with proper to_dict method
            mock_entry = Mock()
            mock_entry.to_dict.return_value = {"id": "entry1", "lexical_unit": {"en": "apple"}}
            
            # Mock filtered results
            mock_dict_service.list_entries.return_value = ([mock_entry], 1)
            mock_get_service.return_value = mock_dict_service
            
            # Test API call with filter
            response = client.get('/api/entries/?filter_text=app&limit=10&offset=0')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'entries' in data
            assert data['total_count'] == 1
            assert len(data['entries']) == 1
            assert data['entries'][0]['id'] == 'entry1'
            
            # Verify service was called with correct parameters
            mock_dict_service.list_entries.assert_called_once()
            call_args = mock_dict_service.list_entries.call_args
            assert 'filter_text' in call_args.kwargs
            assert call_args.kwargs['filter_text'] == 'app'

    def test_entries_api_supports_sort_order_parameter(self, client: FlaskClient) -> None:
        """Test that entries API accepts and uses sort_order parameter."""
        # Clear cache to ensure fresh requests
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            # Create mock entries with proper to_dict methods
            mock_entry1 = Mock()
            mock_entry1.to_dict.return_value = {"id": "entry2", "lexical_unit": {"en": "zebra"}}
            mock_entry2 = Mock()
            mock_entry2.to_dict.return_value = {"id": "entry1", "lexical_unit": {"en": "apple"}}
            
            # Mock sorted results
            mock_dict_service.list_entries.return_value = ([mock_entry1, mock_entry2], 2)
            mock_get_service.return_value = mock_dict_service
            
            # Test API call with descending sort
            response = client.get('/api/entries/?sort_order=desc&limit=10&offset=0')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['total_count'] == 2
            assert len(data['entries']) == 2
            
            # Verify service was called with correct parameters
            mock_dict_service.list_entries.assert_called_once()
            call_args = mock_dict_service.list_entries.call_args
            assert 'sort_order' in call_args.kwargs
            assert call_args.kwargs['sort_order'] == 'desc'

    def test_entries_api_supports_combined_filter_and_sort(self, client: FlaskClient) -> None:
        """Test that entries API supports both filtering and sorting together."""
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            # Create mock entries with proper to_dict methods
            mock_entry1 = Mock()
            mock_entry1.to_dict.return_value = {"id": "entry3", "lexical_unit": {"en": "application"}}
            mock_entry2 = Mock()
            mock_entry2.to_dict.return_value = {"id": "entry1", "lexical_unit": {"en": "apple"}}
            
            # Mock combined filter and sort results
            mock_dict_service.list_entries.return_value = ([mock_entry1, mock_entry2], 2)
            mock_get_service.return_value = mock_dict_service
            
            # Test API call with both filter and sort
            response = client.get('/api/entries/?filter_text=app&sort_order=desc&sort_by=lexical_unit&limit=10&offset=0')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['total_count'] == 2
            assert len(data['entries']) == 2
            
            # Verify service was called with all correct parameters
            mock_dict_service.list_entries.assert_called_once()
            call_args = mock_dict_service.list_entries.call_args
            assert call_args.kwargs['filter_text'] == 'app'
            assert call_args.kwargs['sort_order'] == 'desc'
            assert call_args.kwargs['sort_by'] == 'lexical_unit'

    def test_entries_api_maintains_backward_compatibility(self, client: FlaskClient) -> None:
        """Test that entries API works without new filter/sort parameters."""
        # Clear cache to ensure fresh requests
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            # Create mock entry with proper to_dict method
            mock_entry = Mock()
            mock_entry.to_dict.return_value = {"id": "entry1", "lexical_unit": {"en": "test"}}
            
            # Mock normal results
            mock_dict_service.list_entries.return_value = ([mock_entry], 1)
            mock_get_service.return_value = mock_dict_service
            
            # Test API call without new parameters
            response = client.get('/api/entries/?limit=10&offset=0')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'entries' in data
            assert len(data['entries']) == 1
            
            # Verify service was called with default parameters
            mock_dict_service.list_entries.assert_called_once()
            call_args = mock_dict_service.list_entries.call_args
            # Should have default values for new parameters
            assert call_args.kwargs.get('filter_text', '') == ''
            assert call_args.kwargs.get('sort_order', 'asc') == 'asc'

    def test_entries_api_cache_key_includes_filter_parameters(self, client: FlaskClient) -> None:
        """Test that cache keys include filter and sort parameters."""
        from app.services.cache_service import CacheService
        
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries_*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            # Create mock entry with proper to_dict method
            mock_entry = Mock()
            mock_entry.to_dict.return_value = {"id": "entry1", "lexical_unit": {"en": "test"}}
            
            mock_dict_service.list_entries.return_value = ([mock_entry], 1)
            mock_get_service.return_value = mock_dict_service
            
            # Make two different requests that should have different cache keys
            response1 = client.get('/api/entries/?filter_text=apple&sort_order=asc&limit=10&offset=0')
            response2 = client.get('/api/entries/?filter_text=banana&sort_order=desc&limit=10&offset=0')
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Both should be fresh (not cached from each other)
            data1 = response1.get_json()
            data2 = response2.get_json()
            
            # If caching is working correctly, these should be separate cache entries
            # This test verifies the cache key logic includes the new parameters
            assert 'entries' in data1
            assert 'entries' in data2
            
            # Verify that both requests called the service (not cached from each other)
            assert mock_dict_service.list_entries.call_count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
