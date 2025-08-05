#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.validation_engine import ValidationEngine

def test_validation_method():
    """Test if the validation method exists and can be called."""
    ve = ValidationEngine('validation_rules.json')
    
    # Check if method exists
    method_exists = hasattr(ve, '_validate_definition_content_source_lang_exception')
    print(f"Method exists: {method_exists}")
    
    if method_exists:
        # Test data
        test_data = {
            'lexical-unit': {'lang': 'gd'},
            'senses': [
                {
                    'definition': {
                        'gd': '',  # Empty source language - should be allowed
                        'en': 'English definition'  # Non-empty target language
                    }
                }
            ]
        }
        
        # Mock rule config
        rule_config = {
            'name': 'Test Rule',
            'error_message': 'Test error',
            'priority': 'critical',
            'category': 'sense_level'
        }
        
        # Mock matches (simplified)
        class MockMatch:
            def __init__(self, value, path):
                self.value = value
                self.full_path = path
        
        matches = [MockMatch(test_data['senses'][0], '$.senses[0]')]
        
        try:
            # Call the method directly
            result = ve._validate_definition_content_source_lang_exception(
                'R2.2.1', rule_config, test_data, matches
            )
            print(f"Method call successful. Errors: {len(result)}")
            for error in result:
                print(f"  - {error.message} at {error.path}")
        except Exception as e:
            print(f"Method call failed: {e}")

if __name__ == '__main__':
    test_validation_method()
