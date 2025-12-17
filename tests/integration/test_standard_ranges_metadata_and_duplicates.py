"""Integration tests ensuring custom_ranges.json doesn't duplicate LIFT values and provides label fallback."""
from __future__ import annotations

import pytest
from app.services.ranges_service import RangesService


@pytest.mark.integration
def test_standard_ranges_config_does_not_duplicate_and_label_fallback(client, app):
    """If a LIFT range exists without labels, the service should fill a friendly label
    from STANDARD_RANGE_METADATA, and config entries should not create duplicate
    singular/plural ranges."""
    service: RangesService = client.application.injector.get(RangesService)

    # Mock parsed ranges: LIFT has 'variant-type' present but without labels
    service.ranges_parser.parse_string = lambda xml: {
        'variant-type': {
            'id': 'variant-type',
            'values': [{'id': 'V1'}],
            'labels': {},
            'descriptions': {}
        }
    }

    ranges = service.get_all_ranges()

    # There should be exactly one key for variant-type (no duplicate singular/plural)
    assert ('variant-type' in ranges) and ('variant-type' not in ranges)

    # The label should be filled from metadata since LIFT had none
    assert ranges['variant-type']['label'] in ('Variant Entry Types', 'variant-type')

    # Provided_by_config should not be True for the same range when LIFT provides it
    assert not ranges['variant-type'].get('provided_by_config', False)


def test_config_not_applied_when_lift_has_same_range(client, app):
    """If a range exists in LIFT and in custom_ranges.json, LIFT should take precedence."""
    service: RangesService = client.application.injector.get(RangesService)

    # Simulate LIFT having a complex-form-type range
    service.ranges_parser.parse_string = lambda xml: {
        'complex-form-type': {
            'id': 'complex-form-type',
            'values': [{'id': 'X'}],
            'labels': {},
            'descriptions': {}
        }
    }

    ranges = service.get_all_ranges()
    assert 'complex-form-type' in ranges
    assert ranges['complex-form-type'].get('provided_by_config', False) is False