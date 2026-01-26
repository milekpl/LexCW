"""Integration tests for resolved ranges API behavior."""

from __future__ import annotations

import pytest
import json
from app.services.ranges_service import RangesService
from flask.testing import FlaskClient


@pytest.mark.integration
class TestRangesResolvedAPI:
    """Tests that the ranges API returns resolved view when requested."""

    def test_get_range_resolved_query_param_returns_effective_fields(self, client: FlaskClient) -> None:
        """GET /api/ranges-editor/<id>?resolved=true should return effective_* on values."""
        service: RangesService = client.application.injector.get(RangesService)

        # Mock get_all_ranges to return our test range data directly
        # This is the proper way to test since get_range() calls get_all_ranges() first
        test_range_data = {
            'res-range': {
                'id': 'res-range',
                'labels': {'en': 'Resolved Range'},
                'description': {},
                'values': [
                    {
                        'id': 'parent',
                        'value': 'parent',
                        'labels': {'en': 'ParentLabel'},
                        'abbrev': 'P1',
                        'abbrevs': {},
                        'children': [
                            {
                                'id': 'child',
                                'value': 'child',
                                'labels': {},
                                'abbrev': '',
                                'abbrevs': {}
                            }
                        ]
                    }
                ]
            }
        }

        # Save original method and cache
        original_get_all_ranges = service.get_all_ranges
        original_cache = service._ranges_cache.copy() if hasattr(service, '_ranges_cache') else {}

        try:
            # Mock the method and populate cache
            service.get_all_ranges = lambda *args, **kwargs: test_range_data
            service._ranges_cache = {'res-range': test_range_data['res-range']}

            resp = client.get('/api/ranges-editor/res-range?resolved=true')
            assert resp.status_code == 200
            data = resp.get_json()
            assert data['success'] is True
            rd = data['data']
            vals = rd.get('values', [])
            assert len(vals) == 1
            parent = vals[0]
            child = parent.get('children', [])[0]

            # effective fields should be present on resolved output
            assert 'effective_label' in child
            assert child['effective_label'] == 'ParentLabel'
            assert 'effective_abbrev' in child
            assert child['effective_abbrev'] == 'P1'
        finally:
            # Restore original method and cache
            service.get_all_ranges = original_get_all_ranges
            if hasattr(service, '_ranges_cache'):
                service._ranges_cache = original_cache