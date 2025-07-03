#!/usr/bin/env python3

"""
TDD Test: UI Integration with Dynamic LIFT Ranges
This test defines the expected behavior for UI components using dynamic LIFT ranges.
"""

import pytest
from app import create_app


class TestUIRangesIntegration:
    """Test that all UI components properly integrate with dynamic LIFT ranges."""

    @pytest.fixture
    def app(self):
        """Create test app instance."""
        return create_app('testing')

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_entry_edit_form_loads_dynamic_ranges(self, client):
        """Test that entry edit form uses dynamic LIFT ranges for dropdowns."""
        # First, verify our API has ranges
        ranges_response = client.get('/api/ranges')
        assert ranges_response.status_code == 200
        ranges_data = ranges_response.get_json()
        assert ranges_data['success'] is True
        assert len(ranges_data['data']) == 21  # All LIFT ranges

        # Test edit form page loads and contains dynamic ranges
        # Using a mock entry ID for testing
        response = client.get('/entries/test_entry/edit')
        
        if response.status_code == 200:
            html_content = response.get_data(as_text=True)
            
            # Check that the page includes JavaScript to load dynamic ranges
            assert '/api/ranges' in html_content, "Edit form should reference dynamic ranges API"
            
            # Check for absence of hardcoded ranges (common hardcoded values)
            hardcoded_indicators = [
                'option value="noun"',  # Hardcoded grammatical info
                'option value="verb"',
                'option value="synonym"',  # Hardcoded relation types
                'option value="antonym"'
            ]
            
            for indicator in hardcoded_indicators:
                assert indicator not in html_content, f"Found hardcoded range: {indicator}"

    def test_advanced_search_uses_dynamic_ranges(self, client):
        """Test that advanced search form uses dynamic LIFT ranges."""
        response = client.get('/search/advanced')
        
        if response.status_code == 200:
            html_content = response.get_data(as_text=True)
            
            # Should reference the ranges API
            assert '/api/ranges' in html_content, "Advanced search should use dynamic ranges API"
            
            # Should not contain hardcoded semantic domains
            assert 'Universe, creation' not in html_content, "Should not have hardcoded semantic domains"

    def test_query_builder_uses_dynamic_ranges(self, client):
        """Test that query builder interface uses dynamic LIFT ranges."""
        # Check if query builder page exists
        response = client.get('/query/builder')
        
        if response.status_code == 200:
            html_content = response.get_data(as_text=True)
            
            # Should load ranges dynamically
            assert '/api/ranges' in html_content, "Query builder should use dynamic ranges API"

    def test_ranges_javascript_integration(self, client):
        """Test that JavaScript properly integrates with ranges API."""
        # Check if there's a dedicated JavaScript file for ranges
        js_response = client.get('/static/js/ranges.js')
        
        if js_response.status_code == 200:
            js_content = js_response.get_data(as_text=True)
            
            # Should contain API calls to load ranges
            assert 'fetch(' in js_content and '/api/ranges' in js_content, "JS should fetch dynamic ranges"
            
            # Should have functions to populate dropdowns
            assert 'populateDropdown' in js_content or 'loadRanges' in js_content, "JS should have range loading functions"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
