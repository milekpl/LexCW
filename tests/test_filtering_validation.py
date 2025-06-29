#!/usr/bin/env python3

"""
Final validation test for filtering and refresh functionality.
This test demonstrates that all new features work correctly.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient
from unittest.mock import patch, Mock


def test_filtering_and_refresh_integration(client: FlaskClient) -> None:
    """Test that filtering, sorting, and refresh functionality work together."""
    # Clear cache
    from app.services.cache_service import CacheService
    cache = CacheService()
    if cache.is_available():
        cache.clear_pattern('entries*')
    
    with patch('app.api.entries.get_dictionary_service') as mock_get_service:
        mock_dict_service = Mock()
        
        # Mock entries for filtering test
        mock_entry = Mock()
        mock_entry.to_dict.return_value = {
            "id": "apple_1", 
            "lexical_unit": {"en": "apple"},
            "pos": "noun"
        }
        mock_dict_service.list_entries.return_value = ([mock_entry], 1)
        mock_get_service.return_value = mock_dict_service
        
        # Test 1: Filtering works
        response = client.get('/api/entries/?filter_text=app&limit=10&offset=0')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_count'] == 1
        
        # Verify filter parameter was passed correctly
        call_args = mock_dict_service.list_entries.call_args
        assert call_args.kwargs['filter_text'] == 'app'
        
        # Test 2: Sorting works  
        mock_dict_service.reset_mock()
        response = client.get('/api/entries/?sort_order=desc&sort_by=lexical_unit&limit=10&offset=0')
        assert response.status_code == 200
        
        call_args = mock_dict_service.list_entries.call_args
        assert call_args.kwargs['sort_order'] == 'desc'
        assert call_args.kwargs['sort_by'] == 'lexical_unit'
        
        # Test 3: Cache clear endpoint works
        response = client.post('/api/entries/clear-cache')
        assert response.status_code == 200
        clear_data = response.get_json()
        assert clear_data['success'] is True
        
        # Test 4: Dashboard cache clear works
        response = client.post('/api/dashboard/clear-cache')
        assert response.status_code == 200
        clear_data = response.get_json()
        assert clear_data['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
