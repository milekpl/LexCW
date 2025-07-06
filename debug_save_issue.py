#!/usr/bin/env python3
"""
Debug the save issue by testing form data processing and validation.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data, process_senses_form_data
from app.services.validation_engine import ValidationEngine
import json

def test_sense_data_parsing():
    """Test if sense data is being parsed correctly from form data."""
    print("=== Testing Sense Data Parsing ===")
    
    # Simulate form data with dot notation (as it comes from the HTML form)
    form_data_dot_notation = {
        'senses[0].definition': 'Test definition',
        'senses[0].gloss': 'Test gloss',
        'senses[0].grammatical_info': 'noun',
        'senses[0].note': 'Test note'
    }
    
    print(f"Input form data (dot notation): {form_data_dot_notation}")
    
    # Test the current sense processor
    senses_result = process_senses_form_data(form_data_dot_notation)
    print(f"Parsed senses: {senses_result}")
    
    # Test with bracket notation (what the backend expects)
    form_data_bracket_notation = {
        'senses[0][definition]': 'Test definition',
        'senses[0][gloss]': 'Test gloss', 
        'senses[0][grammatical_info]': 'noun',
        'senses[0][note]': 'Test note'
    }
    
    print(f"\nInput form data (bracket notation): {form_data_bracket_notation}")
    senses_result_brackets = process_senses_form_data(form_data_bracket_notation)
    print(f"Parsed senses (brackets): {senses_result_brackets}")

def test_pos_validation():
    """Test part of speech validation rules."""
    print("\n=== Testing PoS Validation ===")
    
    # Test entry without PoS
    entry_data_no_pos = {
        'lexical_unit': {'en': 'testword'},
        'senses': [
            {
                'definition': 'Test definition',
                'gloss': 'Test gloss'
            }
        ]
    }
    
    print(f"Entry without PoS: {json.dumps(entry_data_no_pos, indent=2)}")
    
    # Test validation
    app = create_app()
    with app.app_context():
        validator = ValidationEngine()
        result = validator.validate_json(entry_data_no_pos)
        
        print(f"Validation result: {result}")
        print(f"Errors: {[str(e) for e in result.errors]}")
        print(f"Warnings: {[str(e) for e in result.warnings]}")
        
        # Check specifically for PoS requirements
        pos_errors = [e for e in result.errors if 'part_of_speech' in str(e).lower() or 'grammatical' in str(e).lower()]
        print(f"PoS-related errors: {pos_errors}")

def test_complete_form_processing():
    """Test complete form data processing like the real endpoint."""
    print("\n=== Testing Complete Form Processing ===")
    
    # Simulate a complete form submission
    form_data = {
        'lexical_unit': 'testword',
        'senses[0].definition': 'Test definition',
        'senses[0].gloss': 'Test gloss',
        'morph_type': 'stem'  # Adding morph_type as it might be required
    }
    
    print(f"Complete form data: {form_data}")
    
    # Process like the endpoint does
    empty_entry_data = {}
    merged_data = merge_form_data_with_entry_data(form_data, empty_entry_data)
    print(f"Merged data: {json.dumps(merged_data, indent=2)}")
    
    # Test validation
    app = create_app()
    with app.app_context():
        validator = ValidationEngine()
        result = validator.validate_json(merged_data)
        
        print(f"Final validation result: {result}")
        print(f"Errors: {[str(e) for e in result.errors]}")
        print(f"Critical errors: {[e for e in result.errors if e.priority == 'critical']}")

if __name__ == '__main__':
    test_sense_data_parsing()
    test_pos_validation() 
    test_complete_form_processing()
