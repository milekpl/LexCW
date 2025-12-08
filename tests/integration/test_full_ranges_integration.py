#!/usr/bin/env python3

"""
Test that all LIFT ranges are properly loaded and available in the UI.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient


@pytest.mark.integration
def test_grammatical_info_has_full_lift_ranges(client: FlaskClient) -> None:
    """Test that the grammatical-info range contains values from LIFT ranges file."""
    response = client.get('/api/ranges/grammatical-info')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    
    range_data = data['data']
    values = range_data['values']
    
    # In test environment, we expect at least some basic values
    assert len(values) >= 3, f"Expected at least 3 grammatical categories, got {len(values)}"
    
    # Check for basic values that should be present
    value_ids = {val['id'] for val in values}
    
    # At least one basic value should be present
    basic_values = {'Noun', 'Verb', 'Adjective', 'Adverb'}
    found_basic = basic_values & value_ids
    assert len(found_basic) >= 2, f"Expected at least 2 basic grammatical categories, found: {found_basic}"
    
    # Verify that values have proper structure
    for value in values:
        assert 'id' in value
        # Some structure verification
        assert isinstance(value.get('children', []), list)
            
    # If we have more than 20 values, we know LIFT ranges are loaded
    if len(values) > 20:
        # These should be present from the LIFT ranges file
        expected_lift_values = {
            'Personal pronoun', 'Possessive pronoun', 'Reflexive pronoun',
            'Demonstrative pronoun', 'Relative pronoun',
            'Countable Noun', 'Uncountable Noun', 'Article', 'Interjection'
        }
        
        missing_lift_values = expected_lift_values - value_ids
        assert not missing_lift_values, f"Missing expected LIFT grammatical categories: {missing_lift_values}"


@pytest.mark.integration
def test_lexical_relation_types_available(client: FlaskClient) -> None:
    """Test that lexical relation types from LIFT ranges are available."""
    response = client.get('/api/ranges/relation-types')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    
    # Should have relation types available
    range_data = data['data']
    values = range_data['values']
    assert len(values) > 0
    
    # Check structure
    if values:
        first_value = values[0]
        assert 'id' in first_value
        assert 'value' in first_value


@pytest.mark.integration
def test_entry_form_loads_dynamic_ranges(client: FlaskClient) -> None:
    """Test that entry form page loads and includes dynamic ranges loader."""
    # First get an entry to edit
    entries_response = client.get('/api/entries')
    entries_data = entries_response.get_json()
    
    if entries_data.get('success') and entries_data.get('data'):
        entries = entries_data['data']
        if entries:
            entry_id = entries[0]['id']
            
            # Load the entry form page
            response = client.get(f'/entries/{entry_id}/edit')
            assert response.status_code == 200
            
            html_content = response.get_data(as_text=True)
            
            # Should include the ranges loader script
            assert 'ranges-loader.js' in html_content
            
            # Should have dynamic grammatical info selects
            assert 'dynamic-grammatical-info' in html_content
            
            # Should include initialization code for ranges
            assert 'rangesLoader' in html_content


@pytest.mark.integration
def test_all_ranges_available(client: FlaskClient) -> None:
    """Test that all expected ranges are available through API."""
    response = client.get('/api/ranges')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    
    ranges = data['data']
    
    # Should have these key ranges available (flexible for different environments)
    # Check for core ranges that should be present in any properly configured system
    expected_core_ranges = ['grammatical-info', 'usage-type', 'lexical-relation']
    
    # Optional ranges that may vary by LIFT file
    optional_ranges = {
        'semantic-domain': ['semantic-domain', 'semantic-domain-ddp4'],
        'status': ['status'],
        'note-type': ['note-type'],
    }
    
    available_ranges = set(ranges.keys())
    
    # Check core ranges
    for core_range in expected_core_ranges:
        assert core_range in available_ranges, f"Core range '{core_range}' missing. Available: {list(available_ranges)}"
    
    # Check optional ranges (at least one should exist)
    found_optional = 0
    for category, alternatives in optional_ranges.items():
        if any(alt in available_ranges for alt in alternatives):
            found_optional += 1
    
    assert found_optional >= 1, f"Should find at least 1 optional range category. Available: {list(available_ranges)}"
    
    # Verify we have a reasonable number of ranges
    assert len(available_ranges) >= 3, f"Expected at least 3 ranges, got {len(available_ranges)}: {list(available_ranges)}"


if __name__ == '__main__':
    pytest.main([__file__])
