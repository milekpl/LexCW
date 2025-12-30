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

        # Monkeypatch parser to return a deterministic nested range
        service.ranges_parser.parse_string = lambda xml: {
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