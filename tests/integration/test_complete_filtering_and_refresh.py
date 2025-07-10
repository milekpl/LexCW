#!/usr/bin/env python3

"""
Integration test for complete filter and refresh functionality.
Tests the API endpoints, cache clear endpoints, and frontend integration.
"""

from __future__ import annotations

import pytest
from typing import Any
from flask.testing import FlaskClient
from unittest.mock import patch, Mock



@pytest.mark.integration
class TestCompleteFilteringAndRefresh:
    """Test complete filtering, caching, and refresh functionality."""

    def setup_method(self, method: Any) -> None:
        """Setup before each test method."""
        # Clear specific cache patterns that might interfere with tests
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            cache.clear_pattern('dashboard_stats*')

    def teardown_method(self, method: Any) -> None:
        """Cleanup after each test method."""
        # Additional cleanup if needed
        pass

    @pytest.mark.integration
    def test_entries_filtering_api_integration(self, client: FlaskClient) -> None:
        """Test that entries API filtering works end-to-end."""
        # Clear cache first
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            
            # Mock entries that would match a filter
            mock_entry1 = Mock()
            mock_entry1.to_dict.return_value = {
                "id": "apple_1", 
                "lexical_unit": {"en": "apple"},
                "pos": "noun"
            }
            mock_entry2 = Mock()
            mock_entry2.to_dict.return_value = {
                "id": "application_1", 
                "lexical_unit": {"en": "application"},
                "pos": "noun"
            }
            
            # Mock service to return filtered results
            mock_dict_service.list_entries.return_value = ([mock_entry1, mock_entry2], 2)
            mock_get_service.return_value = mock_dict_service
            
            # Test API call with filter
            response = client.get('/api/entries/?filter_text=app&limit=20&offset=0&sort_by=lexical_unit&sort_order=asc')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'entries' in data
            assert data['total_count'] == 2
            assert len(data['entries']) == 2
            
            # Verify the entries contain our filter text
            entries = data['entries']
            lexical_units = [entry['lexical_unit']['en'] for entry in entries]
            assert 'apple' in lexical_units
            assert 'application' in lexical_units
            
            # Verify service was called with correct filter
            mock_dict_service.list_entries.assert_called_once()
            call_args = mock_dict_service.list_entries.call_args
            assert call_args.kwargs['filter_text'] == 'app'
            assert call_args.kwargs['sort_by'] == 'lexical_unit'
            assert call_args.kwargs['sort_order'] == 'asc'

    @pytest.mark.integration
    def test_dashboard_cache_clear_endpoint(self, client: FlaskClient) -> None:
        """Test that dashboard cache clear endpoint works."""
        response = client.post('/api/dashboard/clear-cache')
        
        # Check if cache service is available in the test environment
        from app.services.cache_service import CacheService
        cache = CacheService()
        
        if cache.is_available():
            # If cache is available, expect success
            assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.data.decode('utf-8') if response.data else 'No data'}"
            data = response.get_json()
            assert data is not None, "Response should contain JSON data"
            assert data['success'] is True
            assert 'message' in data
        else:
            # If cache is not available, expect 500 with appropriate error message
            assert response.status_code == 500, f"Expected 500 (cache not available), got {response.status_code}"
            data = response.get_json()
            assert data is not None, "Response should contain JSON data"
            assert data['success'] is False
            assert 'Cache service not available' in data['error']

    @pytest.mark.integration
    def test_entries_cache_clear_endpoint(self, client: FlaskClient) -> None:
        """Test that entries cache clear endpoint works."""
        response = client.post('/api/entries/clear-cache')
        
        # Check if cache service is available in the test environment
        from app.services.cache_service import CacheService
        cache = CacheService()
        
        if cache.is_available():
            # If cache is available, expect success
            assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.data.decode('utf-8') if response.data else 'No data'}"
            data = response.get_json()
            assert data is not None, "Response should contain JSON data"
            assert data['success'] is True
            assert 'message' in data
        else:
            # If cache is not available, expect 500 with appropriate error message
            assert response.status_code == 500, f"Expected 500 (cache not available), got {response.status_code}"
            data = response.get_json()
            assert data is not None, "Response should contain JSON data"
            assert data['success'] is False
            assert 'Cache service not available' in data['error']

    @pytest.mark.integration
    def test_entries_cache_behavior_with_different_filters(self, client: FlaskClient) -> None:
        """Test that different filter parameters create different cache entries."""
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            mock_entry = Mock()
            mock_entry.to_dict.return_value = {"id": "test", "lexical_unit": {"en": "test"}}
            mock_dict_service.list_entries.return_value = ([mock_entry], 1)
            mock_get_service.return_value = mock_dict_service
            
            # Make requests with different filters
            response1 = client.get('/api/entries/?filter_text=apple&limit=10&offset=0')
            response2 = client.get('/api/entries/?filter_text=banana&limit=10&offset=0')
            response3 = client.get('/api/entries/?filter_text=apple&sort_order=desc&limit=10&offset=0')
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response3.status_code == 200
            
            # Each should have called the service (not cached from each other)
            assert mock_dict_service.list_entries.call_count >= 3

    @pytest.mark.integration
    def test_sort_order_functionality(self, client: FlaskClient) -> None:
        """Test that sort order parameter works correctly."""
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        
        with patch('app.api.entries.get_dictionary_service') as mock_get_service:
            mock_dict_service = Mock()
            
            # Mock sorted entries
            mock_entry1 = Mock()
            mock_entry1.to_dict.return_value = {"id": "zebra_1", "lexical_unit": {"en": "zebra"}}
            mock_entry2 = Mock()
            mock_entry2.to_dict.return_value = {"id": "apple_1", "lexical_unit": {"en": "apple"}}
            
            mock_dict_service.list_entries.return_value = ([mock_entry1, mock_entry2], 2)
            mock_get_service.return_value = mock_dict_service
            
            # Test descending sort
            response = client.get('/api/entries/?sort_order=desc&sort_by=lexical_unit&limit=10&offset=0')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['total_count'] == 2
            
            # Verify service was called with desc sort order
            mock_dict_service.list_entries.assert_called_once()
            call_args = mock_dict_service.list_entries.call_args
            assert call_args.kwargs['sort_order'] == 'desc'
            assert call_args.kwargs['sort_by'] == 'lexical_unit'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
