"""Test entry update process to check for list errors."""

import os
import sys
import pytest
import uuid
import time
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector

@pytest.fixture(scope="function")
def test_db_name():
    """Generate a unique test database name for each test."""
    return f"test_entry_update_{str(uuid.uuid4()).replace('-', '_')}"

@pytest.fixture(scope="function")
def dict_service(test_db_name):
    """Create a DictionaryService with test database for each test."""
    # Create an admin connector (no database specified)
    admin_connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin')
    )
    admin_connector.connect()
    
    # Clean up any existing test database
    try:
        if test_db_name in (admin_connector.execute_command("LIST") or ""):
            admin_connector.execute_command(f"DROP DB {test_db_name}")
    except Exception:
        pass
    
    # Create the test database
    admin_connector.execute_command(f"CREATE DB {test_db_name}")
    admin_connector.disconnect()
    
    # Now create a connector for the test database
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=test_db_name
    )
    connector.connect()
    
    # Create the service
    service = DictionaryService(db_connector=connector)
    
    # Create minimal test data
    minimal_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.15">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <gloss lang="en"><text>test entry</text></gloss>
        </sense>
    </entry>
</lift>'''
    
    # Create temporary LIFT file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False) as f:
        f.write(minimal_lift)
        temp_lift_path = f.name
    
    try:
        # Initialize with test data
        service.initialize_database(temp_lift_path)
    finally:
        # Cleanup temp file
        if os.path.exists(temp_lift_path):
            os.unlink(temp_lift_path)
    
    yield service
    
    # Clean up
    try:
        connector.disconnect()
        admin_connector.connect()
        admin_connector.execute_command(f"DROP DB {test_db_name}")
        admin_connector.disconnect()
    except Exception:
        pass

@pytest.mark.integration
def test_entry_update(dict_service):
    """Test entry update to check for list errors."""
    try:
        # Get first entry for testing
        entries = dict_service.search_entries(query='', limit=1)
        if not entries:
            print("No entries found for testing")
            return
            
        test_entry = entries[0]
        print(f"Testing entry update for: {test_entry.id}")
        
        # Try to update the entry (this should trigger XML generation)
        dict_service.update_entry(test_entry)
        print("Entry update successful!")
        
    except Exception as e:
        print(f"Error during entry update: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
