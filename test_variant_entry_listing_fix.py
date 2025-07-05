#!/usr/bin/env python3
"""
Test to verify that variant entries can be listed without validation errors.

This test ensures that the fix for variant entry validation during listing operations works correctly.
"""

import pytest
from app.services.dictionary_service import DictionaryService
from app.database.mock_connector import MockDatabaseConnector
from app.parsers.lift_parser import LIFTParser


def test_variant_entry_listing_without_validation_errors():
    """Test that variant entries can be listed without triggering validation errors."""
    
    # Create mock database connector
    mock_db = MockDatabaseConnector()
    dict_service = DictionaryService(mock_db)
    
    # Test listing entries with mock data - this should NOT raise validation errors
    try:
        entries, count = dict_service.list_entries(limit=10)
        
        # Should succeed without validation errors
        assert isinstance(entries, list), "Should return a list of entries"
        assert isinstance(count, int), "Should return an integer count"
        
        print(f"✅ Successfully listed {len(entries)} entries out of {count} total!")
        print("✅ No validation errors during listing operation!")
        
    except Exception as e:
        pytest.fail(f"Listing entries should not raise validation errors: {e}")


def test_validation_still_works_for_create_operations():
    """Test that validation is still enforced during create/update operations."""
    
    # Create a parser with validation enabled (default for create operations)
    validating_parser = LIFTParser(validate=True)
    
    # This should fail validation (invalid entry)
    invalid_entry_xml = """
    <lift>
        <entry id="invalid_entry">
            <lexical-unit>
                <form lang="en">
                    <text>invalid entry</text>
                </form>
            </lexical-unit>
            <sense id="sense_1">
                <!-- No definition, gloss, or variant reference - should fail validation -->
            </sense>
        </entry>
    </lift>
    """
    
    # This should raise a validation error
    with pytest.raises(Exception) as exc_info:
        validating_parser.parse_string(invalid_entry_xml)
    
    assert "validation" in str(exc_info.value).lower(), "Should raise validation error"
    print("✅ Validation still works for create operations!")


def test_non_validating_parser_accepts_variant_entries():
    """Test that non-validating parser accepts variant entries."""
    
    # Create a parser with validation disabled (used for listing operations)
    non_validating_parser = LIFTParser(validate=False)
    
    # This variant entry would normally fail validation but should be accepted
    variant_entry_xml = """
    <lift>
        <entry id="variant_entry">
            <lexical-unit>
                <form lang="en">
                    <text>variant form</text>
                </form>
            </lexical-unit>
            <relation type="_component-lexeme" ref="main_entry">
                <trait name="variant-type" value="Unspecified Variant"/>
            </relation>
            <sense id="sense_1">
                <!-- No definition or gloss - OK for variants when validation is disabled -->
            </sense>
        </entry>
    </lift>
    """
    
    # This should NOT raise a validation error
    try:
        entries = non_validating_parser.parse_string(variant_entry_xml)
        assert len(entries) == 1
        assert entries[0].id == "variant_entry"
        print("✅ Non-validating parser accepts variant entries!")
        
    except Exception as e:
        pytest.fail(f"Non-validating parser should accept variant entries: {e}")


if __name__ == "__main__":
    print("Testing variant entry listing fix...")
    
    test_variant_entry_listing_without_validation_errors()
    test_validation_still_works_for_create_operations()
    test_non_validating_parser_accepts_variant_entries()
    
    print("\n🎉 All tests passed! Variant entry listing fix is working correctly.")
