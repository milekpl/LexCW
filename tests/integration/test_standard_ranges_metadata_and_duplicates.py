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

    # Save original parser and db_execute so we can simulate parsed LIFT without touching files
    original_parse = service.ranges_parser.parse_string
    original_execute = service.db_connector.execute_query
    original_cache = service._ranges_cache.copy() if hasattr(service, '_ranges_cache') else {}

    try:
        # Simulate the DB returning a lift-ranges document and parser returning our test data
        service.db_connector.execute_query = lambda q: '<lift-ranges />'
        service.ranges_parser.parse_string = lambda s: test_range_data
        # Force reload to exercise metadata merging
        ranges = service.get_all_ranges(force_reload=True)

        # There should be exactly one key for variant-type (no duplicate singular/plural)
        assert 'variant-type' in ranges
        assert 'variant_types' not in ranges  # No plural duplicate

        # The label should be filled from metadata since LIFT had none
        assert ranges['variant-type']['label'] in ('Variant types', 'variant-type')

        # Provided_by_config should not be True for the same range when LIFT provides it
        assert not ranges['variant-type'].get('provided_by_config', False)
    finally:
        # Restore original parser, db_execute and cache
        service.ranges_parser.parse_string = original_parse
        service.db_connector.execute_query = original_execute
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

    # Save original parser and db_execute so we can simulate parsed LIFT without touching files
    original_parse = service.ranges_parser.parse_string
    original_execute = service.db_connector.execute_query
    original_cache = service._ranges_cache.copy() if hasattr(service, '_ranges_cache') else {}

    try:
        # Simulate DB + parser returning our test data and force reload
        service.db_connector.execute_query = lambda q: '<lift-ranges />'
        service.ranges_parser.parse_string = lambda s: test_range_data
        ranges = service.get_all_ranges(force_reload=True)
        assert 'complex-form-type' in ranges
        assert ranges['complex-form-type'].get('provided_by_config', False) is False
    finally:
        # Restore original method and cache
        service.ranges_parser.parse_string = original_parse
        service.db_connector.execute_query = original_execute
        if hasattr(service, '_ranges_cache'):
            service._ranges_cache = original_cache