"""Tests for FieldWorks flagging behavior when ranges come from LIFT vs config."""
from __future__ import annotations

import pytest
from app.services.ranges_service import RangesService


@pytest.mark.integration
def test_fieldworks_flags_for_lift_provided_range(client, app):
    """A range present in LIFT should not be marked provided_by_config but may be fieldworks_standard if declared in config."""
    service: RangesService = client.application.injector.get(RangesService)

    # Simulate LIFT containing 'infl-class' (no labels)
    service.ranges_parser.parse_string = lambda xml: {
        'infl-class': {'id': 'infl-class', 'labels': {}, 'descriptions': {}, 'values': []}
    }

    ranges = service.get_all_ranges()
    r = ranges['infl-class']
    assert r.get('provided_by_config') is False
    # fieldworks_standard depends on whether the key is in custom_ranges.json
    assert isinstance(r.get('fieldworks_standard'), bool)


@pytest.mark.integration
def test_fieldworks_flags_for_config_only_range(client, app):
    """A range only present in custom_ranges.json should be marked provided_by_config and fieldworks_standard True."""
    service: RangesService = client.application.injector.get(RangesService)

    # Ensure LIFT missing
    service.ranges_parser.parse_string = lambda xml: {}

    ranges = service.get_all_ranges()
    assert 'complex-form-type' in ranges
    rc = ranges['complex-form-type']
    assert rc.get('provided_by_config') is True
    assert rc.get('fieldworks_standard') is True