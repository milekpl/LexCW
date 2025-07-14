#!/usr/bin/env python3

"""
Integration test for entries filtering and sorting functionality.
Tests the actual API endpoints to verify filter and sort_order parameters work correctly.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient



@pytest.mark.integration
class TestEntriesFilteringIntegration:
    """Test entries filtering and sorting through the API."""

    @pytest.mark.integration
    def test_entries_api_supports_filter_parameter(self, client: FlaskClient) -> None:
        """Test that entries API accepts and uses filter_text parameter (integration, no mocks)."""
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        response = client.get('/api/entries/?filter_text=app&limit=10&offset=0')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert 'total_count' in data
        # Optionally, check that at least one entry matches the filter
        entries = data['entries']
        assert any('app' in entry['lexical_unit']['en'] for entry in entries)

    @pytest.mark.integration
    def test_entries_api_supports_sort_order_parameter(self, client: FlaskClient) -> None:
        """Test that entries API accepts and uses sort_order parameter (integration, no mocks)."""
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        response = client.get('/api/entries/?sort_order=desc&limit=10&offset=0')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert 'total_count' in data
        entries = data['entries']
        # If there are at least 2 entries, check that the sort order is descending by lexical_unit['en']
        if len(entries) >= 2:
            lexical_units = [entry['lexical_unit']['en'] for entry in entries if 'lexical_unit' in entry and 'en' in entry['lexical_unit']]
            expected = sorted(lexical_units, key=lambda x: x.lower(), reverse=True)
            assert lexical_units == expected, f"Entries not sorted in descending order: {lexical_units}\nExpected: {expected}"

    @pytest.mark.integration
    def test_entries_api_supports_combined_filter_and_sort(self, client: FlaskClient) -> None:
        """Test that entries API supports both filtering and sorting together (integration, no mocks)."""
        response = client.get('/api/entries/?filter_text=app&sort_order=desc&sort_by=lexical_unit&limit=10&offset=0')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert 'total_count' in data
        entries = data['entries']
        # Optionally, check that at least one entry matches the filter
        assert any('app' in entry['lexical_unit']['en'] for entry in entries)
        # If there are at least 2 entries, check descending order
        if len(entries) >= 2:
            lexical_units = [entry['lexical_unit']['en'] for entry in entries if 'lexical_unit' in entry and 'en' in entry['lexical_unit']]
            expected = sorted(lexical_units, key=lambda x: x.lower(), reverse=True)
            assert lexical_units == expected, f"Entries not sorted in descending order: {lexical_units}\nExpected: {expected}"

    @pytest.mark.integration
    def test_entries_api_maintains_backward_compatibility(self, client: FlaskClient) -> None:
        """Test that entries API works without new filter/sort parameters (integration, no mocks)."""
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        response = client.get('/api/entries/?limit=10&offset=0')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert len(data['entries']) >= 1

    @pytest.mark.integration
    def test_entries_api_cache_key_includes_filter_parameters(self, client: FlaskClient) -> None:
        """Test that cache keys include filter and sort parameters (integration, no mocks)."""
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        # Make two different requests that should have different cache keys
        response1 = client.get('/api/entries/?filter_text=apple&sort_order=asc&limit=10&offset=0')
        response2 = client.get('/api/entries/?filter_text=banana&sort_order=desc&limit=10&offset=0')
        assert response1.status_code == 200
        assert response2.status_code == 200
        data1 = response1.get_json()
        data2 = response2.get_json()
        assert 'entries' in data1
        assert 'entries' in data2
        # Optionally, check that the entries are different for different filters
        ids1 = {entry['id'] for entry in data1['entries']}
        ids2 = {entry['id'] for entry in data2['entries']}
        assert ids1 != ids2 or not ids1 or not ids2, f"Expected different entries for different filters, got: {ids1} and {ids2}"


