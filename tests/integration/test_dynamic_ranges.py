#!/usr/bin/env python3

"""
Test dynamic ranges loading functionality.

This test verifies that the query builder, search page, and entry form
correctly load type/category options from LIFT ranges rather than using
hardcoded values.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient


@pytest.mark.integration
def test_ranges_api_endpoint(client: FlaskClient) -> None:
    """Test that ranges API endpoints work correctly."""
    # Test getting all ranges
    response = client.get('/api/ranges')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'data' in data
    
    # Should have default ranges at minimum
    ranges = data['data']
    assert 'grammatical-info' in ranges
    assert 'lexical-relation' in ranges    
    
    # Test getting specific range
    response = client.get('/api/ranges/grammatical-info')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['id'] == 'grammatical-info'
    assert 'values' in data['data']
    assert len(data['data']['values']) > 0
    
    # Verify structure of range values
    first_value = data['data']['values'][0]
    assert 'id' in first_value
    assert 'value' in first_value
    assert 'abbrev' in first_value


@pytest.mark.integration
def test_lexical_relation_range(client: FlaskClient) -> None:
    """Test lexical relation range specifically."""
    response = client.get('/api/ranges/lexical-relation')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    
    relation_types = data['data']['values']
    relation_ids = [rt['id'] for rt in relation_types]
    
    # Should have at least some relation types defined
    assert len(relation_ids) > 0
    # The test environment may have different relation types than production
    # Just verify we have valid data structure
    assert all('id' in rt and 'value' in rt for rt in relation_types)


@pytest.mark.integration
def test_search_page_loads_without_hardcoded_pos(client: FlaskClient) -> None:
    """Test that search page doesn't contain hardcoded part of speech options."""
    response = client.get('/search')
    assert response.status_code == 200
    
    # Should not contain hardcoded options
    content = response.data.decode('utf-8')
    assert '<option value="noun">Noun</option>' not in content
    assert '<option value="verb">Verb</option>' not in content
    
    # Should contain placeholder comments for dynamic loading
    assert '<!-- Options will be dynamically loaded from LIFT ranges -->' in content
    
    # Should load ranges-loader.js
    assert 'ranges-loader.js' in content


@pytest.mark.integration
def test_entry_form_loads_without_hardcoded_pos(client: FlaskClient) -> None:
    """Test that entry form doesn't contain hardcoded grammatical info."""
    response = client.get('/entries/add')
    assert response.status_code == 200
    
    content = response.data.decode('utf-8')
    
    # Should not contain hardcoded options
    assert '<option value="noun"' not in content
    assert '<option value="verb"' not in content
    
    # Should contain dynamic loading classes and placeholders
    assert 'dynamic-grammatical-info' in content
    assert '<!-- Options will be dynamically loaded from LIFT ranges -->' in content
    
    # Should load ranges-loader.js
    assert 'ranges-loader.js' in content


@pytest.mark.integration
def test_query_builder_workset_functionality(client: FlaskClient) -> None:
    """Test that query builder's create workset functionality works."""
    response = client.get('/workbench/query-builder')
    assert response.status_code == 200
    
    content = response.data.decode('utf-8')
    
    # Should have create workset button and modal
    assert 'Create Workset' in content
    assert 'createWorksetModal' in content
    assert 'execute-query-btn' in content
    assert 'confirm-create-workset' in content


@pytest.mark.integration
def test_ranges_fallback_functionality() -> None:
    """Test that ranges loader provides dynamic loading from API."""
    # The new implementation loads ranges dynamically from API
    # instead of using hardcoded fallbacks
    import os
    
    ranges_js_path = os.path.join(
        os.path.dirname(__file__), 
        '..', '..', 'app', 'static', 'js', 'ranges-loader.js'
    )
    
    with open(ranges_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Should have RangesLoader class
    assert 'class RangesLoader' in content
    assert 'loadRange' in content
    assert '/api/ranges' in content
    
    # Should have cache mechanism
    assert 'cache' in content
    
    # Should have populateAllRangeSelects method
    assert 'populateAllRangeSelects' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
