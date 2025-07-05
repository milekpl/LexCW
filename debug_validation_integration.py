#!/usr/bin/env python3
"""
Debug the validation integration to understand why missing ID validation is not working.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from app.models.entry import Entry
from app.services.validation_engine import ValidationEngine
from app.utils.exceptions import ValidationError


def debug_missing_id_validation():
    """Debug why missing ID validation is not working."""
    print("Debugging missing ID validation...")
    
    # Create entry without ID
    try:
        entry = Entry(
            lexical_unit={'seh': 'mutu'},
            senses=[{
                'id': 'sense_1',
                'definition': 'A person'
            }]
        )
        
        print(f"Entry created without explicit ID. Entry.id = '{entry.id}'")
        print(f"Entry.id is None: {entry.id is None}")
        print(f"Entry.id is empty string: {entry.id == ''}")
        
        # Convert to dict and check what gets validated
        entry_dict = {
            'id': entry.id,
            'lexical_unit': entry.lexical_unit,
            'senses': [sense.to_dict() if hasattr(sense, 'to_dict') else sense for sense in entry.senses]
        }
        print(f"Entry dict for validation: {entry_dict}")
        
        # Test direct engine validation
        engine = ValidationEngine()
        result = engine.validate_json(entry_dict)
        
        print(f"Engine validation result: {result.is_valid}")
        print(f"Errors: {[error.message for error in result.errors]}")
        print(f"Warnings: {[warning.message for warning in result.warnings]}")
        
        # Test model validation
        try:
            model_result = entry.validate()
            print(f"Model validation result: {model_result}")
        except ValidationError as e:
            print(f"Model validation error: {e}")
            print(f"Error details: {e.details}")
            
    except Exception as e:
        print(f"Error creating entry: {e}")


def debug_sense_missing_id_validation():
    """Debug why missing sense ID validation is not working."""
    print("\nDebugging missing sense ID validation...")
    
    from app.models.sense import Sense
    
    # Create sense without ID
    try:
        sense = Sense(
            definition='A person'
        )
        
        print(f"Sense created without explicit ID. Sense.id = '{sense.id}'")
        print(f"Sense.id is None: {sense.id is None}")
        print(f"Sense.id is empty string: {sense.id == ''}")
        
        # Convert to dict and check what gets validated
        sense_dict = sense.to_dict()
        print(f"Sense dict: {sense_dict}")
        
        # Test validation
        try:
            result = sense.validate()
            print(f"Sense validation result: {result}")
        except ValidationError as e:
            print(f"Sense validation error: {e}")
            print(f"Error details: {e.details}")
            
    except Exception as e:
        print(f"Error creating sense: {e}")


def main():
    """Run debug tests."""
    print("=" * 60)
    print("DEBUGGING VALIDATION INTEGRATION")
    print("=" * 60)
    
    debug_missing_id_validation()
    debug_sense_missing_id_validation()
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
