#!/usr/bin/env python3

"""
Test-driven implementation of date fields in the query builder UI.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient

@pytest.mark.integration
class TestDatesUI:
    """Test date fields in the query builder user interface components."""

    @pytest.mark.integration
    def test_query_builder_has_date_sorting_options(self, client: FlaskClient) -> None:
        """Test query builder includes date sorting options."""
        response = client.get('/workbench/query-builder')
        
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should have date sorting controls
        assert 'sort-by-select' in html
        assert 'value="date_created"' in html
        assert 'value="date_modified"' in html

    @pytest.mark.integration
    def test_date_sorting_functionality(self, client: FlaskClient) -> None:
        """Test that date sorting works through the query builder API."""
        # Test ascending sort by date_created
        query_data: dict[str, str | int] = {
            "sort_by": "date_created",
            "sort_order": "asc",
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
        assert len(data['preview_entries']) > 0

        # Test descending sort by date_modified
        query_data: dict[str, str | int] = {
            "sort_by": "date_modified",
            "sort_order": "desc",
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
        assert len(data['preview_entries']) > 0