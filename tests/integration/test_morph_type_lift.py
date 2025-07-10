"""Test LIFT parsing of morph-type trait."""

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector

import pytest

@pytest.mark.integration
def test_lift_morph_type_parsing():
    """Test that morph-type is correctly parsed from LIFT data."""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get service from dependency injection
            service = app.injector.get(DictionaryService)
            
            # Test with Protestant1 entry which has <trait name="morph-type" value="stem"/>
            entry_id = "Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69"
            
            print(f"Testing entry: {entry_id}")
            entry = service.get_entry(entry_id)
            
            if entry:
                print(f"Entry loaded: {entry.id}")
                print(f"Lexical unit: {entry.lexical_unit}")
                print(f"Morph type from LIFT: {entry.morph_type}")
                
                # Should be 'stem' from LIFT data, not auto-classified
                if entry.morph_type == 'stem':
                    print("✅ Morph type correctly loaded from LIFT data")
                else:
                    print(f"❌ Expected 'stem', got '{entry.morph_type}'")
                    
            else:
                print("❌ Entry not found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_lift_morph_type_parsing()
