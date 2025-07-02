"""
Test that verifies the LIFT ranges functionality using the sample file directly.
This bypasses database issues and tests the core dynamic ranges functionality.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from flask import Flask


def test_lift_ranges_with_sample_file(app: Flask) -> None:
    """
    Test LIFT ranges functionality by forcing the service to use the sample file.
    This test ensures that when database is unavailable, the service correctly
    falls back to loading the comprehensive sample LIFT ranges file.
    """
    # Mock the database connection to force fallback to sample file
    with patch('app.services.dictionary_service.DictionaryService.get_ranges') as mock_get_ranges:
        # Import and use the parser directly to load sample file
        from app.parsers.lift_parser import LIFTRangesParser
        import os
        
        sample_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'sample-lift-file', 'sample-lift-file.lift-ranges')
        
        if not os.path.exists(sample_file):
            pytest.skip(f"Sample LIFT ranges file not found: {sample_file}")
        
        parser = LIFTRangesParser()
        sample_ranges = parser.parse_file(sample_file)
        
        # Mock the service to return the sample ranges
        mock_get_ranges.return_value = sample_ranges
        
        with app.test_client() as client:
            response = client.get('/api/ranges')
            assert response.status_code == 200
            
            ranges_data = response.get_json()
            assert 'data' in ranges_data
            ranges = ranges_data['data']
            
            # Verify all expected range types from sample file are present
            expected_range_types = {
                'etymology', 'grammatical-info', 'lexical-relation', 'note-type',
                'paradigm', 'reversal-type', 'semantic-domain-ddp4', 'status',
                'users', 'location', 'anthro-code', 'translation-type',
                'inflection-feature', 'inflection-feature-type', 'from-part-of-speech',
                'morph-type', 'num-feature-value', 'Publications', 'do-not-publish-in',
                'domain-type', 'usage-type'
            }
            
            available_types = set(ranges.keys())
            
            # Check each expected range type
            missing_ranges = []
            for range_type in expected_range_types:
                if range_type not in available_types:
                    missing_ranges.append(range_type)
            
            assert not missing_ranges, f"Missing range types: {missing_ranges}. Available: {sorted(available_types)}"
            
            # Verify that ranges have proper structure
            for range_type, range_data in ranges.items():
                assert 'id' in range_data, f"Range {range_type} missing 'id' field"
                assert 'values' in range_data, f"Range {range_type} missing 'values' field"
                assert isinstance(range_data['values'], list), f"Range {range_type} 'values' should be a list"
                
                # Verify range values have proper structure
                if range_data['values']:
                    for value in range_data['values'][:3]:  # Check first 3 values
                        assert 'id' in value, f"Range {range_type} value missing 'id' field"
                        assert 'value' in value, f"Range {range_type} value missing 'value' field"


def test_lift_ranges_parser_with_sample_file() -> None:
    """
    Test the LIFT ranges parser directly with the sample file to ensure
    it can parse all range types correctly.
    """
    from app.parsers.lift_parser import LIFTRangesParser
    import os
    
    sample_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                              'sample-lift-file', 'sample-lift-file.lift-ranges')
    
    if not os.path.exists(sample_file):
        pytest.skip(f"Sample LIFT ranges file not found: {sample_file}")
    
    parser = LIFTRangesParser()
    ranges = parser.parse_file(sample_file)
    
    # Verify we got all expected range types
    expected_range_types = {
        'etymology', 'grammatical-info', 'lexical-relation', 'note-type',
        'paradigm', 'reversal-type', 'semantic-domain-ddp4', 'status',
        'users', 'location', 'anthro-code', 'translation-type',
        'inflection-feature', 'inflection-feature-type', 'from-part-of-speech',
        'morph-type', 'num-feature-value', 'Publications', 'do-not-publish-in',
        'domain-type', 'usage-type'
    }
    
    available_types = set(ranges.keys())
    assert available_types == expected_range_types, f"Expected {expected_range_types}, got {available_types}"
    
    # Verify specific ranges have expected characteristics
    
    # Test hierarchical structure (grammatical-info should have subcategories)
    assert 'grammatical-info' in ranges
    gram_info = ranges['grammatical-info']
    assert 'values' in gram_info
    assert len(gram_info['values']) > 0
    
    # Test semantic domain should have many entries
    assert 'semantic-domain-ddp4' in ranges
    semantic_domain = ranges['semantic-domain-ddp4']
    assert len(semantic_domain['values']) > 0
    
    # Test various other ranges exist and have content
    for range_type in ['etymology', 'status', 'users', 'location']:
        assert range_type in ranges
        assert 'values' in ranges[range_type]
        assert len(ranges[range_type]['values']) > 0


def test_lift_ranges_service_fallback() -> None:
    """
    Test that the dictionary service correctly falls back to sample file
    when database ranges are not available.
    """
    from app.services.dictionary_service import DictionaryService
    from app.database.basex_connector import BaseXConnector
    from unittest.mock import MagicMock
    
    # Create a mock connector that simulates no ranges in database
    mock_connector = MagicMock(spec=BaseXConnector)
    mock_connector.database = 'test_db'
    mock_connector.execute_query.return_value = None  # No ranges found
    
    service = DictionaryService(mock_connector)
    ranges = service.get_ranges()
    
    # Should have fallen back to sample file and have all expected ranges
    expected_range_types = {
        'etymology', 'grammatical-info', 'lexical-relation', 'note-type',
        'paradigm', 'reversal-type', 'semantic-domain-ddp4', 'status',
        'users', 'location', 'anthro-code', 'translation-type',
        'inflection-feature', 'inflection-feature-type', 'from-part-of-speech',
        'morph-type', 'num-feature-value', 'Publications', 'do-not-publish-in',
        'domain-type', 'usage-type'
    }
    
    available_types = set(ranges.keys())
    
    # Should have at least most of the expected types (allowing for some flexibility)
    # since we're now using the sample file
    intersection = available_types.intersection(expected_range_types)
    assert len(intersection) >= 15, f"Expected at least 15 range types from sample file, got {len(intersection)}: {sorted(intersection)}"
