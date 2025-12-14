"""Integration tests for custom_ranges.json behavior and API flags."""
from __future__ import annotations

import pytest
from app.services.ranges_service import RangesService


@pytest.mark.integration
def test_custom_config_range_is_provided_and_marked(client, app):
    """Ranges defined only in custom_ranges.json should be present and marked."""
    service: RangesService = client.application.injector.get(RangesService)

    # Simulate LIFT having no ranges
    service.ranges_parser.parse_string = lambda xml: {}

    ranges = service.get_all_ranges()

    assert 'complex-form-type' in ranges
    r = ranges['complex-form-type']
    assert r.get('provided_by_config') is True
    assert r.get('fieldworks_standard') is True
    assert r.get('config_type') == 'fieldworks'
    assert r.get('label') == 'Complex form types'


@pytest.mark.integration
def test_api_returns_provided_flag_for_config_range(client, app):
    """GET endpoint should reflect provided_by_config for config-only ranges."""
    # Ensure LIFT missing
    service: RangesService = client.application.injector.get(RangesService)
    service.ranges_parser.parse_string = lambda xml: {}

    resp = client.get('/api/ranges-editor/complex-form-type')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    rd = data['data']
    assert rd.get('provided_by_config') is True
    assert rd.get('fieldworks_standard') is True