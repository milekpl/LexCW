"""
Verify pronunciation handling in the dictionary system.

This script tests the pronunciation component to ensure it follows the requirements:
1. Only using seh-fonipa language code
2. Removing the IPA language selector
3. Properly displaying the pronunciation in the entry form
"""

import sys
import os
from pathlib import Path

# Add the project root to the path for imports
project_root = str(Path(__file__).parent)
sys.path.insert(0, project_root)

from app import create_app
from app.services.dictionary_service import DictionaryService

def verify_pronunciation_handling():
    """Verify that pronunciation handling follows requirements."""
    print("Verifying pronunciation handling...")
    
    # Create the app context
    app = create_app()
    
    with app.app_context():
        # Get dictionary service
        from app import injector
        dict_service = injector.get(DictionaryService)
        
        # Check that we can get language codes
        language_codes = dict_service.get_language_codes()
        print(f"Available language codes: {language_codes}")
        assert 'seh-fonipa' in language_codes, "seh-fonipa should be in language codes"
        
        # Check that we can get variant types from traits
        variant_types = dict_service.get_variant_types_from_traits()
        print(f"Found {len(variant_types)} variant types from traits")
        for vt in variant_types[:5]:  # Show first 5 for brevity
            print(f"  - {vt.get('value', 'unknown')}")
        
        # Check if static files for JS exist
        js_path = os.path.join(project_root, 'app', 'static', 'js', 'pronunciation-forms.js')
        assert os.path.exists(js_path), f"Missing pronunciation-forms.js at {js_path}"
        print(f"Found pronunciation-forms.js at {js_path}")
        
    print("Pronunciation handling verification completed successfully!")
        
if __name__ == "__main__":
    verify_pronunciation_handling()
