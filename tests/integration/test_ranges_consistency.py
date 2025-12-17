
import pytest
from app.services.dictionary_service import DictionaryService
from app.services.ranges_service import RangesService

def test_ranges_consistency(app, basex_test_connector):
    """
    Test that DictionaryService.get_ranges() includes standard ranges 
    like 'variant-type', matching RangesService.get_all_ranges().
    """
    with app.app_context():
        # Initialize services
        dict_service = DictionaryService(basex_test_connector)
        ranges_service = RangesService(basex_test_connector)
        
        # Ensure DB is initialized (mock or real)
        # For this test, we assume empty DB or minimal DB
        
        # Get ranges from both services
        dict_ranges = dict_service.get_ranges()
        ranges_ranges = ranges_service.get_all_ranges()
        
        # Check for variant-type
        assert 'variant-type' in ranges_ranges, "RangesService should include variant-type"
        
        # This assertion is expected to fail currently
        if 'variant-type' not in dict_ranges:
            print("\nFAILURE CONFIRMED: variant-type missing from DictionaryService.get_ranges()")
        else:
            print("\nvariant-type IS present in DictionaryService.get_ranges()")
            
        assert 'variant-type' in dict_ranges, "DictionaryService should include variant-type"
