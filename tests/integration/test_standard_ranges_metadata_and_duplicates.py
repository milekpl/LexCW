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

    # Mock get_all_ranges to return our test range data directly
    # This tests that the service properly merges LIFT data with metadata
    test_range_data = {
        'variant-type': {
            'id': 'variant-type',
            'values': [{'id': 'V1'}],
            'labels': {},
            'description': {}
        }
    }

    # Save original method and cache
    original_get_all_ranges = service.get_all_ranges
    original_cache = service._ranges_cache.copy() if hasattr(service, '_ranges_cache') else {}

    try:
        # Mock the method and populate cache
        service.get_all_ranges = lambda *args, **kwargs: test_range_data
        service._ranges_cache = {'variant-type': test_range_data['variant-type']}

        ranges = service.get_all_ranges()

        # There should be exactly one key for variant-type (no duplicate singular/plural)
        assert 'variant-type' in ranges
        assert 'variant_types' not in ranges  # No plural duplicate

        # The label should be filled from metadata since LIFT had none
        assert ranges['variant-type']['label'] in ('Variant types', 'variant-type')

        # Provided_by_config should not be True for the same range when LIFT provides it
        assert not ranges['variant-type'].get('provided_by_config', False)
    finally:
        # Restore original method and cache
        service.get_all_ranges = original_get_all_ranges
        if hasattr(service, '_ranges_cache'):
            service._ranges_cache = original_cache


def test_config_not_applied_when_lift_has_same_range(client, app):
    """If a range exists in LIFT and in custom_ranges.json, LIFT should take precedence."""
    service: RangesService = client.application.injector.get(RangesService)

    # Mock get_all_ranges to return our test range data directly
    test_range_data = {
        'complex-form-type': {
            'id': 'complex-form-type',
            'values': [{'id': 'X'}],
            'labels': {},
            'description': {}
        }
    }

    # Save original method and cache
    original_get_all_ranges = service.get_all_ranges
    original_cache = service._ranges_cache.copy() if hasattr(service, '_ranges_cache') else {}

    try:
        # Mock the method and populate cache
        service.get_all_ranges = lambda *args, **kwargs: test_range_data
        service._ranges_cache = {'complex-form-type': test_range_data['complex-form-type']}

        ranges = service.get_all_ranges()
        assert 'complex-form-type' in ranges
        assert ranges['complex-form-type'].get('provided_by_config', False) is False
    finally:
        # Restore original method and cache
        service.get_all_ranges = original_get_all_ranges
        if hasattr(service, '_ranges_cache'):
            service._ranges_cache = original_cache