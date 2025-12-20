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

    # Test a range that is actually marked as fieldworks type in config
    assert 'is-primary' in ranges
    r = ranges['is-primary']
    assert r.get('provided_by_config') is True
    assert r.get('fieldworks_standard') is True
    assert r.get('config_type') == 'fieldworks'
    assert r.get('label') == 'Is primary (trait)'


@pytest.mark.integration
def test_api_returns_provided_flag_for_config_range(client, app):
    """GET endpoint should reflect provided_by_config for config-only ranges."""
    # Ensure LIFT missing
    service: RangesService = client.application.injector.get(RangesService)
    service.ranges_parser.parse_string = lambda xml: {}

    # Test a range that is actually marked as fieldworks type in config
    resp = client.get('/api/ranges-editor/is-primary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    rd = data['data']
    assert rd.get('provided_by_config') is True
    assert rd.get('fieldworks_standard') is True