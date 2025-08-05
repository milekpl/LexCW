#!/usr/bin/env python3
"""
Test script to verify the current behavior of reordering buttons and source language validation.
"""

import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.validation_engine import ValidationEngine


class TestTODOIssues:
    """Test class for TODO issues #1 and #2."""

    def test_issue_1_reordering_buttons(self):
        """Test that reordering buttons are present in the HTML template."""
        # This is a UI test - we'll verify the HTML has the right structure
        # and the JavaScript can find the buttons
        pass  # Will be implemented with actual browser testing

    def test_issue_2_source_language_validation(self):
        """Test source language definition validation behavior."""
        validation_engine = ValidationEngine()
        
        # Test case 1: Source language with empty definition should be allowed to be removed
        # This simulates the case where user leaves source language definition empty
        # and it should not cause validation errors
        entry_data_no_source_def = {
            "id": "test_entry_no_source",
            "lexical_unit": {"en": "test"},
            "senses": [
                {
                    "id": "sense1",
                    "definition": {
                        "pl": "proper polish definition"
                        # No source language (en) definition at all
                    }
                }
            ]
        }
        
        result = validation_engine.validate_json(entry_data_no_source_def)
        print(f"No source definition validation - Valid: {result.is_valid}")
        if not result.is_valid:
            for error in result.errors:
                print(f"  Error: {error.message}")
        
        # Test case 2: Source language present but empty - this is the problematic case
        entry_data_empty_source_def = {
            "id": "test_entry_empty_source",
            "lexical_unit": {"en": "test"},
            "senses": [
                {
                    "id": "sense1",
                    "definition": {
                        "en": {"text": ""},  # Empty source language definition
                        "pl": {"text": "proper polish definition"}
                    }
                }
            ]
        }
        
        result2 = validation_engine.validate_json(entry_data_empty_source_def)
        print(f"Empty source definition validation - Valid: {result2.is_valid}")
        if not result2.is_valid:
            for error in result2.errors:
                print(f"  Error: {error.message}")
        
        # Test case 3: Both languages have content - should pass
        entry_data_both_content = {
            "id": "test_entry_both_content",
            "lexical_unit": {"en": "test"},
            "senses": [
                {
                    "id": "sense1",
                    "definition": {
                        "en": {"text": "english definition"},
                        "pl": {"text": "polish definition"}
                    }
                }
            ]
        }
        
        result3 = validation_engine.validate_json(entry_data_both_content)
        print(f"Both languages with content validation - Valid: {result3.is_valid}")
        if not result3.is_valid:
            for error in result3.errors:
                print(f"  Error: {error.message}")
        
        return result.is_valid, result2.is_valid, result3.is_valid


if __name__ == '__main__':
    test = TestTODOIssues()
    empty_valid, whitespace_valid, all_empty_valid = test.test_issue_2_source_language_validation()
    
    print("\n" + "=" * 60)
    print("TODO ISSUE #2 ANALYSIS:")
    print("=" * 60)
    print(f"Empty source definition allowed: {'✓' if empty_valid else '✗'}")
    print(f"Whitespace source definition allowed: {'✓' if whitespace_valid else '✗'}")
    print(f"All empty definitions rejected: {'✓' if not all_empty_valid else '✗'}")
    print("=" * 60)
