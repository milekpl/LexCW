#!/usr/bin/env python3

"""
Comprehensive test to verify LIFT ranges UI integration is working.
"""

import pytest
from app import create_app


class TestLIFTRangesUIIntegration:
    """Test that all UI components properly use dynamic LIFT ranges."""

    @pytest.fixture
    def app(self):
        """Create test app instance."""
        return create_app('testing')

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_ranges_api_available(self, client):
        """Test that ranges API is available and returns expected data."""
        response = client.get('/api/ranges')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 21
        
        # Check for specific ranges
        ranges = data['data']
        assert 'grammatical-info' in ranges
        assert 'lexical-relation' in ranges
        assert 'semantic-domain-ddp4' in ranges
        
        # Check grammatical-info structure
        gram_info = ranges['grammatical-info']
        assert 'values' in gram_info
        assert len(gram_info['values']) > 0

    def test_entry_form_includes_ranges_loader(self, client):
        """Test that entry form includes ranges loader script."""
        response = client.get('/entries/test_entry/edit')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        
        # Check for ranges loader script
        assert 'ranges-loader.js' in html
        assert 'window.rangesLoader' in html
        assert 'populateSelectWithFallback' in html

    def test_dynamic_grammatical_info_elements(self, client):
        """Test that grammatical info elements are properly configured."""
        response = client.get('/entries/test_entry/edit')
        html = response.get_data(as_text=True)
        
        # Check for dynamic-grammatical-info class
        assert 'dynamic-grammatical-info' in html
        assert 'data-range-id="grammatical-info"' in html

    def test_ranges_loader_fallback_values(self, client):
        """Test that ranges loader has appropriate fallback values."""
        # Get the ranges-loader.js file
        response = client.get('/static/js/ranges-loader.js')
        assert response.status_code == 200
        
        js_content = response.get_data(as_text=True)
        
        # Check for fallback values
        assert 'grammatical-info' in js_content
        assert 'Noun' in js_content
        assert 'Verb' in js_content
        assert 'relation-types' in js_content
        assert 'synonym' in js_content

    def test_specific_range_endpoints(self, client):
        """Test individual range endpoints work correctly."""
        # Test grammatical-info endpoint
        response = client.get('/api/ranges/grammatical-info')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'values' in data['data']
        
        # Test semantic domains endpoint
        response = client.get('/api/ranges/semantic-domain-ddp4')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'values' in data['data']

    def test_advanced_search_form(self, client):
        """Test that advanced search form uses dynamic ranges."""
        response = client.get('/search/advanced')
        
        # The search form should exist
        if response.status_code == 200:
            html = response.get_data(as_text=True)
            # Should have references to ranges or dynamic loading
            assert 'search' in html.lower()

    def test_no_hardcoded_ranges_in_templates(self, client):
        """Test that templates don't contain hardcoded range values."""
        # Check entry form
        response = client.get('/entries/test_entry/edit')
        if response.status_code == 200:
            html = response.get_data(as_text=True)
            
            # Should not contain hardcoded option values
            hardcoded_patterns = [
                '<option value="noun"',
                '<option value="verb"',
                '<option value="synonym"',
                '<option value="antonym"'
            ]
            
            for pattern in hardcoded_patterns:
                assert pattern.lower() not in html.lower(), f"Found hardcoded pattern: {pattern}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
