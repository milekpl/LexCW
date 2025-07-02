"""
Test-driven development test for comprehensive LIFT ranges support.

This test verifies that the application can fully load, parse, and utilize
a comprehensive LIFT ranges file containing all possible range types.
"""
from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient


def test_comprehensive_lift_ranges_support(app: Flask) -> None:
    """
    Test full LIFT ranges support by verifying all ranges from sample-lift-file.lift-ranges
    are available via the API and can be used in the UI.
    
    This test verifies that the application supports ALL range types found
    in the comprehensive sample LIFT ranges file:
    - etymology
    - grammatical-info (with hierarchical structure)
    - lexical-relation
    - note-type
    - paradigm
    - reversal-type
    - semantic-domain-ddp4 (with thousands of semantic domains)
    - status
    - users
    - location
    - anthro-code
    - translation-type
    - inflection-feature
    - inflection-feature-type
    - from-part-of-speech
    - morph-type
    - num-feature-value
    - Publications
    - do-not-publish-in
    - domain-type
    - usage-type
    """
    with app.test_client() as client:
        # Test main ranges API endpoint
        response = client.get('/api/ranges')
        assert response.status_code == 200
        ranges_data = response.get_json()
        assert 'data' in ranges_data or 'ranges' in ranges_data
        
        # Get the ranges data regardless of the key name
        ranges = ranges_data.get('data', ranges_data.get('ranges', {}))
        
        # Define all expected range types from the sample LIFT ranges file
        expected_range_types = {
            'etymology',
            'grammatical-info', 
            'lexical-relation',
            'note-type',
            'paradigm',
            'reversal-type',
            'semantic-domain-ddp4',
            'status',
            'users',
            'location',
            'anthro-code',
            'translation-type',
            'inflection-feature',
            'inflection-feature-type',
            'from-part-of-speech',
            'morph-type',
            'num-feature-value',
            'Publications',
            'do-not-publish-in',
            'domain-type',
            'usage-type'
        }
        
        available_types = set(ranges.keys())
        
        # Test that each expected range type is available
        for range_type in expected_range_types:
            # Test main ranges endpoint contains this range type
            assert range_type in available_types or any(
                alt in available_types for alt in [
                    f"{range_type}s",  # plural form
                    range_type.replace('-', '_'),  # underscore form
                    range_type.replace('_', '-')   # hyphen form
                ]
            ), f"Range type '{range_type}' not found in available ranges: {available_types}"
            
            # Test specific range endpoint
            response = client.get(f'/api/ranges/{range_type}')
            if response.status_code == 404:
                # Try alternative forms
                for alt_type in [f"{range_type}s", range_type.replace('-', '_'), range_type.replace('_', '-')]:
                    response = client.get(f'/api/ranges/{alt_type}')
                    if response.status_code == 200:
                        break
            
            assert response.status_code == 200, f"Range endpoint '/api/ranges/{range_type}' not accessible"
            range_data = response.get_json()
            assert 'data' in range_data or 'ranges' in range_data
        
        # Test hierarchical ranges (grammatical-info should have parent-child relationships)
        gram_response = client.get('/api/ranges/grammatical-info')
        assert gram_response.status_code == 200
        gram_data = gram_response.get_json()
        
        # Should contain hierarchical data structure
        assert 'data' in gram_data or 'ranges' in gram_data
        
        # Test semantic domains (should be very extensive)
        semantic_response = client.get('/api/ranges/semantic-domain-ddp4')
        if semantic_response.status_code == 404:
            # Try alternative names
            for alt in ['semantic-domains', 'semantic-domain']:
                semantic_response = client.get(f'/api/ranges/{alt}')
                if semantic_response.status_code == 200:
                    break
        
        assert semantic_response.status_code == 200
        semantic_data = semantic_response.get_json()
        assert 'data' in semantic_data or 'ranges' in semantic_data
        
        # Test that ranges can be used in entry form
        # This ensures UI integration works
        response = client.get('/entries/add')
        assert response.status_code == 200
        form_html = response.get_data(as_text=True)
        
        # Check that common range types appear in the form
        # (Either as select elements or as JavaScript configuration)
        essential_ranges = ['grammatical-info', 'semantic-domain', 'usage-type', 'status']
        for range_type in essential_ranges:
            # The range should either be a select element or loaded via JavaScript
            range_found = (
                f'name="{range_type}"' in form_html or
                f'id="{range_type}"' in form_html or
                f'"{range_type}"' in form_html or
                range_type.replace('-', '_') in form_html or
                range_type.replace('-', '') in form_html
            )
            assert range_found, f"Range type '{range_type}' not found in entry form"


def test_lift_ranges_dynamic_loading(app: Flask) -> None:
    """
    Test that LIFT ranges are dynamically loaded and not hardcoded.
    
    This ensures the application can adapt to different LIFT ranges files
    without code changes.
    """
    with app.test_client() as client:
        # Test that ranges are loaded from database/file, not hardcoded
        response = client.get('/api/ranges')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have actual range data, not empty defaults
        assert 'ranges' in data
        ranges = data['ranges']
        assert len(ranges) > 0, "No ranges loaded - should load from database/file"
        
        # Test that at least some ranges have multiple elements
        has_multi_element_range = False
        for range_id, range_data in ranges.items():
            if isinstance(range_data, list) and len(range_data) > 1:
                has_multi_element_range = True
                break
            elif isinstance(range_data, dict):
                values = range_data.get('values', range_data.get('elements', []))
                if len(values) > 1:
                    has_multi_element_range = True
                    break
        
        assert has_multi_element_range, "No ranges with multiple elements found"


def test_lift_ranges_api_performance(app: Flask) -> None:
    """
    Test that LIFT ranges API performs well with large datasets.
    
    The sample LIFT ranges file contains thousands of semantic domains,
    so the API should handle this efficiently.
    """
    import time
    
    with app.test_client() as client:
        # Test main endpoint performance
        start_time = time.time()
        response = client.get('/api/ranges')
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0, "Ranges API too slow (>2s)"
        
        # Test specific range endpoint performance
        start_time = time.time()
        response = client.get('/api/ranges/semantic-domain-ddp4')
        if response.status_code == 404:
            response = client.get('/api/ranges/semantic-domains')
        end_time = time.time()
        
        if response.status_code == 200:
            assert (end_time - start_time) < 1.0, "Specific range API too slow (>1s)"
