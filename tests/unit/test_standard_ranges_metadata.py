"""Unit tests for standard ranges metadata handling."""

from app.services.ranges_service import STANDARD_RANGE_METADATA


def test_standard_metadata_has_complex_form_type_and_traits():
    assert 'complex-form-type' in STANDARD_RANGE_METADATA
    assert STANDARD_RANGE_METADATA['complex-form-type']['label'] == 'Complex form types'
    assert 'is-primary' in STANDARD_RANGE_METADATA
    assert 'hide-minor-entry' in STANDARD_RANGE_METADATA


def test_variant_type_label_resolution():
    # Ensure configuration contains 'variant-type' entry
    from app.services.ranges_service import STANDARD_RANGE_METADATA
    assert 'variant-type' in STANDARD_RANGE_METADATA
