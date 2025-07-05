"""Test entry update process to check for list errors."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector

def test_entry_update():
    """Test entry update to check for list errors."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create service
            db_connector = BaseXConnector()
            service = DictionaryService(db_connector=db_connector)
            
            # Get first entry for testing
            entries = service.search_entries(query='', limit=1)
            if not entries:
                print("No entries found for testing")
                return
                
            test_entry = entries[0]
            print(f"Testing entry update for: {test_entry.id}")
            
            # Try to update the entry (this should trigger XML generation)
            service.update_entry(test_entry)
            print("Entry update successful!")
            
        except Exception as e:
            print(f"Error during entry update: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_entry_update()
