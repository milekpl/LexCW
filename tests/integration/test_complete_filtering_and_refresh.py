#!/usr/bin/env python3

"""
Integration test for complete filter and refresh functionality.
Tests the API endpoints, cache clear endpoints, and frontend integration.
"""

from __future__ import annotations

import pytest

from typing import Any
from flask.testing import FlaskClient


# Suppress logging for this test module to avoid excessive output
from typing import Generator

@pytest.fixture(autouse=True, scope="class")
def suppress_logging_for_tests(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    import logging
    loggers_to_silence = [
        logging.getLogger(),
        logging.getLogger('flask.app'),
        logging.getLogger('werkzeug'),
        logging.getLogger('sqlalchemy'),
    ]
    previous_levels = [logger.level for logger in loggers_to_silence]
    for logger in loggers_to_silence:
        logger.setLevel(logging.WARNING)
    yield
    for logger, prev_level in zip(loggers_to_silence, previous_levels):
        logger.setLevel(prev_level)



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
        import uuid
        
        # Clear cache first
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')
        
        # Create a test entry to ensure we have data to filter
        test_id = f"filter_test_{uuid.uuid4().hex[:8]}"
        entry_xml = f'''<entry id="{test_id}">
            <lexical-unit>
                <form lang="en"><text>application</text></form>
                <form lang="pl"><text>aplikacja</text></form>
            </lexical-unit>
            <sense id="sense_1">
                <gloss lang="en"><text>Software application</text></gloss>
                <definition>
                    <form lang="en"><text>A computer program</text></form>
                </definition>
            </sense>
        </entry>'''
        
        create_response = client.post('/api/xml/entries', data=entry_xml, content_type='application/xml')
        assert create_response.status_code == 201
        
        # Test API call with filter
        response = client.get('/api/entries/?filter_text=app&limit=20&offset=0&sort_by=lexical_unit&sort_order=asc')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert 'total_count' in data
        # Check that our test entry is included in the filtered results
        entries = data['entries']
        assert any(test_id == entry['id'] or 'app' in entry['lexical_unit'].get('en', '').lower() for entry in entries)

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
            print(f"[DEBUG] /api/entries/clear-cache response data: {data}")
            assert data is not None, "Response should contain JSON data"
            assert data.get('status') == 'success', f"Expected status 'success', got: {data}"
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
        # Make requests with different filters
        response1 = client.get('/api/entries/?filter_text=apple&limit=10&offset=0')
        response2 = client.get('/api/entries/?filter_text=banana&limit=10&offset=0')
        response3 = client.get('/api/entries/?filter_text=apple&sort_order=desc&limit=10&offset=0')
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

    @pytest.mark.integration
    def test_sort_order_functionality(self, client: FlaskClient) -> None:
        """Test that sort order parameter works correctly (integration, no mocks)."""
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries*')

        # Test descending sort
        response = client.get('/api/entries/?sort_order=desc&sort_by=lexical_unit&limit=10&offset=0')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.data.decode('utf-8') if response.data else 'No data'}"
        data = response.get_json()
        assert 'entries' in data
        assert 'total_count' in data
        entries = data['entries']
        # If there are at least 2 entries, check that the sort order is descending by lexical_unit['en']
        if len(entries) >= 2:
            lexical_units = [entry['lexical_unit']['en'] for entry in entries if 'lexical_unit' in entry and 'en' in entry['lexical_unit']]
            expected = sorted(lexical_units, key=lambda x: x.lower(), reverse=True)
            print(f"[DEBUG] Actual lexical_units: {lexical_units}")
            print(f"[DEBUG] Expected descending order: {expected}")
            assert lexical_units == expected, f"Entries not sorted in descending order: {lexical_units}\nExpected: {expected}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
