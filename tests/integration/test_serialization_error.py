#!/usr/bin/env python3
"""
Test to reproduce the exact error scenario
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app import create_app, injector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry

@pytest.mark.integration
def test_entry_serialization_issue():
    """Test what happens when we try to update entry with complex data"""
    
    app = create_app()
    
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    logger = logging.getLogger("test_serialization_error")

    with app.app_context():
        # Use the app's injector, which should be properly configured
        dict_service = app.injector.get(DictionaryService)

        # Get the problematic entry
        try:
            entry = dict_service.get_entry("Protestantism_b97495fb-d52f-4755-94bf-a7a762339605")
            logger.info(f"✅ Successfully retrieved entry: {entry.id}")
            logger.info(f"Entry type: {type(entry)}")
            logger.info(f"Lexical unit: {entry.lexical_unit} (type: {type(entry.lexical_unit)})")
            logger.info(f"Grammatical info: {entry.grammatical_info} (type: {type(entry.grammatical_info)})")

            # Check for any dict values that shouldn't be dicts
            entry_dict = entry.to_dict()
            logger.info(f"\nEntry dict keys: {list(entry_dict.keys())}")

            for key, value in entry_dict.items():
                if isinstance(value, dict) and key not in ['lexical_unit', 'notes', 'pronunciations', 'custom_fields']:
                    logger.warning(f"⚠️ WARNING: {key} is unexpectedly a dict: {value}")

            # Log the full entry dict for inspection (may be large)
            logger.debug(f"Full entry dict: {entry_dict}")

            # Try to validate the entry
            try:
                is_valid = entry.validate()
                logger.info(f"✅ Entry validation: {is_valid}")
            except Exception as e:
                logger.error(f"❌ Entry validation failed: {e}")

            # Try to update the entry (this should trigger the error)
            try:
                dict_service.update_entry(entry)
                logger.info("✅ Entry update successful")
            except Exception as e:
                logger.error(f"❌ Entry update failed: {e}")
                import traceback
                logger.error(traceback.format_exc())

        except Exception as e:
            logger.error(f"❌ Failed to retrieve entry: {e}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_entry_serialization_issue()
