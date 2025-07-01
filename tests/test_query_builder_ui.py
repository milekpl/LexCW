#!/usr/bin/env python3

"""
Test-driven implementation of dynamic query builder UI.
Following TDD cycle: Red -> Green -> Refactor

Per specification section 3.1.1: "Dynamic Query Builder: TDD-validated interface for creating complex entry filters"
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient
from unittest.mock import patch, Mock


class TestQueryBuilderUI:
    """Test query builder user interface components."""

    def test_query_builder_page_renders(self, client: FlaskClient) -> None:
        """Test GET /workbench/query-builder - renders query builder interface."""
        # RED: Test for workbench query builder page
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should contain query builder components
        assert 'query-builder-container' in html
        assert 'add-filter-btn' in html
        assert 'filter-conditions' in html
        assert 'query-preview' in html

    def test_query_builder_has_field_options(self, client: FlaskClient) -> None:
        """Test query builder contains all expected field options."""
        # RED: Test for available filter fields
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should have field selection options
        expected_fields = [
            'lexical_unit', 'pos', 'sense.semantic_domain', 
            'etymology.source', 'pronunciation', 'sense.definition'
        ]
        
        for field in expected_fields:
            assert f'data-field="{field}"' in html or f'value="{field}"' in html

    def test_query_builder_has_operator_options(self, client: FlaskClient) -> None:
        """Test query builder contains operator selection."""
        # RED: Test for filter operators
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should have operator options
        expected_operators = [
            'equals', 'contains', 'starts_with', 'ends_with', 
            'greater_than', 'less_than', 'in', 'not_in'
        ]
        
        for operator in expected_operators:
            assert f'value="{operator}"' in html

    def test_query_builder_dynamic_filter_management(self, client: FlaskClient) -> None:
        """Test dynamic addition and removal of filter conditions."""
        # RED: Test for JavaScript-driven filter management
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should contain JavaScript for dynamic filter management
        assert 'addFilterCondition' in html
        assert 'removeFilterCondition' in html
        assert 'updateQueryPreview' in html

    def test_query_builder_has_sorting_options(self, client: FlaskClient) -> None:
        """Test query builder includes sorting configuration."""
        # RED: Test for sort options
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should have sorting controls
        assert 'sort-by-select' in html
        assert 'sort-order-select' in html
        assert 'value="asc"' in html
        assert 'value="desc"' in html

    def test_query_builder_preview_functionality(self, client: FlaskClient) -> None:
        """Test query preview shows generated query."""
        # RED: Test for real-time query preview
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should have preview area and JavaScript
        assert 'query-preview-json' in html
        assert 'estimated-results' in html
        assert 'performance-indicator' in html

    def test_query_builder_save_functionality(self, client: FlaskClient) -> None:
        """Test query builder allows saving queries."""
        # RED: Test for query save functionality
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should have save controls
        assert 'save-query-btn' in html
        assert 'query-name-input' in html
        assert 'saved-queries-list' in html


class TestQueryBuilderAPI:
    """Test query builder AJAX API endpoints."""

    def test_validate_query_endpoint(self, client: FlaskClient) -> None:
        """Test POST /api/query-builder/validate - real-time validation."""
        # RED: Test for query validation endpoint
        query_data = {
            "filters": [
                {"field": "lexical_unit", "operator": "starts_with", "value": "a"},
                {"field": "pos", "operator": "equals", "value": "noun"}
            ],
            "sort_by": "lexical_unit",
            "sort_order": "asc"
        }
        
        response = client.post(
            '/api/query-builder/validate',
            json=query_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'valid' in data
        assert 'estimated_count' in data
        assert 'performance_score' in data
        assert 'validation_errors' in data

    def test_preview_query_endpoint(self, client: FlaskClient) -> None:
        """Test POST /api/query-builder/preview - get sample results."""
        # RED: Test for query preview endpoint
        query_data = {
            "filters": [
                {"field": "pos", "operator": "equals", "value": "verb"}
            ],
            "limit": 5
        }
        
        response = client.post(
            '/api/query-builder/preview',
            json=query_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'preview_entries' in data
        assert 'total_count' in data
        assert len(data['preview_entries']) <= 5

    def test_save_query_endpoint(self, client: FlaskClient) -> None:
        """Test POST /api/query-builder/save - save named queries."""
        # RED: Test for save query endpoint
        save_data = {
            "name": "All Verbs Starting with A",
            "description": "Query for verb entries beginning with letter A",
            "query": {
                "filters": [
                    {"field": "lexical_unit", "operator": "starts_with", "value": "a"},
                    {"field": "pos", "operator": "equals", "value": "verb"}
                ],
                "sort_by": "lexical_unit",
                "sort_order": "asc"
            }
        }
        
        response = client.post(
            '/api/query-builder/save',
            json=save_data,
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert data['success'] is True
        assert 'query_id' in data
        assert data['name'] == "All Verbs Starting with A"

    def test_load_saved_queries_endpoint(self, client: FlaskClient) -> None:
        """Test GET /api/query-builder/saved - list saved queries."""
        # RED: Test for loading saved queries
        response = client.get('/api/query-builder/saved')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'queries' in data
        assert isinstance(data['queries'], list)

    def test_execute_query_and_create_workset(self, client: FlaskClient) -> None:
        """Test POST /api/query-builder/execute - create workset from query."""
        # RED: Test for query execution that creates workset
        execute_data = {
            "workset_name": "My Query Results",
            "query": {
                "filters": [
                    {"field": "pos", "operator": "in", "value": ["noun", "verb"]}
                ],
                "sort_by": "lexical_unit",
                "sort_order": "asc"
            }
        }
        
        response = client.post(
            '/api/query-builder/execute',
            json=execute_data,
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert data['success'] is True
        assert 'workset_id' in data
        assert 'entry_count' in data
        assert data['workset_name'] == "My Query Results"


class TestQueryBuilderPerformance:
    """Test query builder performance requirements."""

    def test_query_validation_response_time(self, client: FlaskClient) -> None:
        """Test query validation completes within 1 second."""
        # RED: Test for performance requirements from spec
        import time
        
        query_data = {
            "filters": [
                {"field": "lexical_unit", "operator": "contains", "value": "test"},
                {"field": "pos", "operator": "equals", "value": "noun"},
                {"field": "semantic_domain", "operator": "starts_with", "value": "1."}
            ]
        }
        
        start_time = time.time()
        
        response = client.post(
            '/api/query-builder/validate',
            json=query_data,
            content_type='application/json'
        )
        
        validation_time = time.time() - start_time
        
        assert response.status_code == 200
        assert validation_time < 1.0  # Must complete within 1 second
        
        data = response.get_json()
        assert data['valid'] is not None

    def test_query_preview_handles_large_results(self, client: FlaskClient) -> None:
        """Test query preview works efficiently with large result sets."""
        # RED: Test for handling queries that would return many results
        large_query = {
            "filters": [
                {"field": "pos", "operator": "in", "value": ["noun", "verb", "adjective"]}
            ],
            "limit": 10  # Preview should be limited
        }
        
        response = client.post(
            '/api/query-builder/preview',
            json=large_query,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Preview should be limited regardless of total results
        assert len(data['preview_entries']) <= 10
        # Should still report actual total count
        assert 'total_count' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
