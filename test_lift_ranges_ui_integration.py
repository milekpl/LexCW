#!/usr/bin/env python3
"""
TDD Test: LIFT Ranges UI Integration
Tests that all UI components load dynamic LIFT ranges from the API.
"""

import pytest
from flask import url_for
from app import create_app
from app.services.dictionary_service import DictionaryService


class TestLiftRangesUIIntegration:
    """Test that all UI components use dynamic LIFT ranges from the API."""
    
    @pytest.fixture
    def app(self):
        """Create test app."""
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def app_context(self, app):
        """Create app context."""
        with app.app_context():
            yield app
    
    def test_ranges_api_returns_all_ranges(self, client, app_context):
        """Test that /api/ranges returns all 21 LIFT range types."""
        response = client.get('/api/ranges')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        
        ranges = data['data']
        # Should have all 21 LIFT range types
        assert len(ranges) >= 21
        
        # Check key range types exist
        expected_ranges = [
            'grammatical-info', 'semantic-domain-ddp4', 'lexical-relation',
            'etymology', 'domain-type', 'anthro-code',
            'location', 'status', 'usage-type'
        ]
        
        for range_type in expected_ranges:
            assert range_type in ranges
            assert 'values' in ranges[range_type]
            assert len(ranges[range_type]['values']) > 0
    
    def test_entry_form_includes_ranges_loader(self, client, app_context):
        """Test that entry form includes ranges-loader.js."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        assert 'ranges-loader.js' in html
        # Note: window.rangesLoader is created by the JS file, not in HTML template
    
    def test_entry_form_has_dynamic_range_selects(self, client, app_context):
        """Test that entry form has selects marked for dynamic loading."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        
        # Should have selects with data-range-id attributes
        assert 'data-range-id="grammatical-info"' in html
        assert 'data-range-id="semantic-domain-ddp4"' in html
        assert 'dynamic-lift-range' in html or 'dynamic-grammatical-info' in html
    
    def test_query_builder_includes_ranges_loader(self, client, app_context):
        """Test that query builder includes ranges-loader.js."""
        response = client.get('/workbench/query-builder')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        # Should include ranges loader
        assert 'ranges-loader.js' in html
    
    def test_all_ui_components_load_ranges_dynamically(self, client, app_context):
        """Test that UI components are set up to load ranges dynamically."""
        # Test entry form
        response = client.get('/entries/add')
        html = response.get_data(as_text=True)
        assert 'populateAllRangeSelects' in html or 'data-range-id' in html
        
        # Test query builder
        response = client.get('/workbench/query-builder')
        html = response.get_data(as_text=True)
        # Should have some mechanism to load ranges
        assert 'ranges' in html.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
