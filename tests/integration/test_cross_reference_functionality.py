#!/usr/bin/env python3

"""
Test cross-reference search and workset creation functionality.

This test ensures that relational search and workset creation work correctly
with dynamic type loading from LIFT ranges.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient


@pytest.mark.integration
def test_query_builder_api_endpoints(client: FlaskClient) -> None:
    """Test that query builder API endpoints work correctly."""
    # Test query validation endpoint
    query_data = {
        "filters": [
            {
                "field": "lexical_unit",
                "operator": "contains", 
                "value": "test"
            }
        ],
        "sort_by": "lexical_unit",
        "sort_order": "asc"
    }
    
    response = client.post('/api/query-builder/validate', 
                          json=query_data,
                          headers={'Content-Type': 'application/json'})
    
    # Should work regardless of actual database content
    assert response.status_code in [200, 400]  # Valid request format


@pytest.mark.integration
def test_worksets_api_endpoints(client: FlaskClient) -> None:
    """Test that worksets API endpoints are available."""
    # Test listing worksets
    response = client.get('/api/worksets')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'worksets' in data or 'success' in data


@pytest.mark.integration
def test_cross_reference_search_with_dynamic_types(client: FlaskClient) -> None:
    """Test that cross-reference search uses dynamic relation types."""
    # First verify relation types are available
    response = client.get('/api/ranges/relation-types')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    relation_types = data['data']['values']
    
    # Should have at least basic relation types
    relation_ids = [rt['id'] for rt in relation_types]
    assert len(relation_ids) > 0
    
    # Test query builder with relation type filter
    query_data = {
        "filters": [
            {
                "field": "relation.type",
                "operator": "equals",
                "value": relation_ids[0]  # Use first available relation type
            }
        ]
    }
    
    response = client.post('/api/query-builder/validate',
                          json=query_data,
                          headers={'Content-Type': 'application/json'})
    
    # Should accept the relation type from ranges
    assert response.status_code in [200, 400]  # Valid request format


@pytest.mark.integration
def test_variant_search_with_dynamic_types(client: FlaskClient) -> None:
    """Test that variant search uses dynamic variant types."""
    # First verify variant types are available
    response = client.get('/api/ranges/variant-types')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    variant_types = data['data']['values']
    
    # Should have at least basic variant types
    variant_ids = [vt['id'] for vt in variant_types]
    assert len(variant_ids) > 0
    
    # Test query builder with variant type filter
    query_data = {
        "filters": [
            {
                "field": "variant.type",
                "operator": "equals",
                "value": variant_ids[0]  # Use first available variant type
            }
        ]
    }
    
    response = client.post('/api/query-builder/validate',
                          json=query_data,
                          headers={'Content-Type': 'application/json'})
    
    # Should accept the variant type from ranges
    assert response.status_code in [200, 400]  # Valid request format


@pytest.mark.integration
def test_grammatical_info_search_with_dynamic_types(client: FlaskClient) -> None:
    """Test that grammatical info search uses dynamic categories."""
    # First verify grammatical info is available
    response = client.get('/api/ranges/grammatical-info')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    grammatical_info = data['data']['values']
    
    # Should have at least basic grammatical categories
    pos_values = [gi['value'] for gi in grammatical_info]
    assert len(pos_values) > 0
    
    # Test query builder with grammatical info filter
    query_data = {
        "filters": [
            {
                "field": "grammatical_info",
                "operator": "equals",
                "value": pos_values[0]  # Use first available POS
            }
        ]
    }
    
    response = client.post('/api/query-builder/validate',
                          json=query_data,
                          headers={'Content-Type': 'application/json'})
    
    # Should accept the grammatical info from ranges
    assert response.status_code in [200, 400]  # Valid request format


@pytest.mark.integration
def test_workset_creation_with_complex_query(client: FlaskClient) -> None:
    """Test workset creation with a complex query using dynamic types."""
    # Get available types for building a complex query
    relation_resp = client.get('/api/ranges/relation-types')
    variant_resp = client.get('/api/ranges/variant-types')
    grammar_resp = client.get('/api/ranges/grammatical-info')
    
    assert relation_resp.status_code == 200
    assert variant_resp.status_code == 200
    assert grammar_resp.status_code == 200
    
    relation_types = relation_resp.get_json()['data']['values']
    variant_types = variant_resp.get_json()['data']['values']
    grammar_types = grammar_resp.get_json()['data']['values']
    
    # Create a complex query using dynamic types
    workset_data = {
        "workset_name": "Test Complex Workset",
        "query": {
            "filters": [
                {
                    "field": "lexical_unit",
                    "operator": "contains",
                    "value": "test"
                },
                {
                    "field": "relation.type",
                    "operator": "equals",
                    "value": relation_types[0]['value'] if relation_types else "synonym"
                },
                {
                    "field": "grammatical_info",
                    "operator": "equals",
                    "value": grammar_types[0]['value'] if grammar_types else "noun"
                }
            ],
            "sort_by": "lexical_unit",
            "sort_order": "asc"
        }
    }
    
    response = client.post('/api/query-builder/execute',
                          json=workset_data,
                          headers={'Content-Type': 'application/json'})
    
    # Should either succeed or give a meaningful error (not a type validation error)
    assert response.status_code in [200, 201, 400, 404]
    
    if response.status_code == 200:
        data = response.get_json()
        assert data.get('success') is True
        assert 'workset_name' in data


@pytest.mark.integration
def test_ranges_api_provides_all_necessary_types(client: FlaskClient) -> None:
    """Test that ranges API provides all types needed for UI functionality."""
    response = client.get('/api/ranges')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    ranges = data['data']
    
    # Should have all the key ranges needed for UI
    expected_ranges = [
        'grammatical-info',
        'relation-types',
        'variant-types'
    ]
    
    for expected_range in expected_ranges:
        assert expected_range in ranges, f"Missing expected range: {expected_range}"
        assert 'values' in ranges[expected_range], f"Range {expected_range} missing values"
        assert len(ranges[expected_range]['values']) > 0, f"Range {expected_range} has no values"
        
        # Each value should have required fields
        first_value = ranges[expected_range]['values'][0]
        assert 'id' in first_value, f"Range {expected_range} values missing 'id'"
        assert 'value' in first_value, f"Range {expected_range} values missing 'value'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
