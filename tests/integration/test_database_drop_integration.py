"""
Integration tests for database drop functionality.
"""

import pytest
import tempfile
import os
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector


@pytest.fixture(scope="function")
def test_db_name():
    """Generate a unique test database name for each test."""
    import uuid
    return f"test_drop_{str(uuid.uuid4()).replace('-', '_')}"


@pytest.fixture(scope="function")
def dict_service_with_data(test_db_name):
    """Create a DictionaryService with test database and sample data for each test."""
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
    
    # Create the service with testing mode to avoid auto-connect
    import sys
    sys.modules['pytest'] = True  # Fake pytest module to avoid auto-connect
    service = DictionaryService(db_connector=connector)
    del sys.modules['pytest']  # Clean up
    
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
    <entry id="test_entry_2">
        <lexical-unit>
            <form lang="en"><text>example</text></form>
        </lexical-unit>
        <sense id="test_sense_2">
            <gloss lang="en"><text>example entry</text></gloss>
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
        yield service
    finally:
        # Cleanup temp file
        if os.path.exists(temp_lift_path):
            os.unlink(temp_lift_path)
        
        # Clean up test database
        try:
            admin_connector.connect()
            if test_db_name in (admin_connector.execute_command("LIST") or ""):
                admin_connector.execute_command(f"DROP DB {test_db_name}")
            admin_connector.disconnect()
        except Exception:
            pass


@pytest.mark.integration
class TestDatabaseDrop:
    """Test the database drop functionality."""

    @pytest.mark.integration
    def test_drop_database_content(self, dict_service_with_data):
        """Test that drop_database_content properly empties the database."""
        # Verify we have entries before dropping
        initial_count = dict_service_with_data.count_entries()
        assert initial_count == 2, f"Expected 2 entries, got {initial_count}"
        
        # Drop the database content
        dict_service_with_data.drop_database_content()
        
        # Verify database is now empty
        final_count = dict_service_with_data.count_entries()
        assert final_count == 0, f"Expected 0 entries after drop, got {final_count}"
        
    @pytest.mark.integration
    def test_drop_and_reinitialize(self, dict_service_with_data):
        """Test that we can drop and reinitialize the database."""
        # Get initial count
        initial_count = dict_service_with_data.count_entries()
        assert initial_count == 2
        
        # Drop the database content
        dict_service_with_data.drop_database_content()
        
        # Verify it's empty
        empty_count = dict_service_with_data.count_entries()
        assert empty_count == 0
        
        # Create new test data
        new_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.15">
    <entry id="new_entry_1">
        <lexical-unit>
            <form lang="en"><text>new</text></form>
        </lexical-unit>
        <sense id="new_sense_1">
            <gloss lang="en"><text>new entry</text></gloss>
        </sense>
    </entry>
</lift>'''
        
        # Create temporary LIFT file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False) as f:
            f.write(new_lift)
            new_lift_path = f.name
        
        try:
            # Reinitialize with new data
            dict_service_with_data.initialize_database(new_lift_path)
            
            # Verify new data is loaded
            final_count = dict_service_with_data.count_entries()
            assert final_count == 1, f"Expected 1 entry after reinitialize, got {final_count}"
            
            # Verify the new entry is there
            entries, total = dict_service_with_data.list_entries()
            assert len(entries) == 1
            assert entries[0].id == "new_entry_1"
            
        finally:
            # Cleanup temp file
            if os.path.exists(new_lift_path):
                os.unlink(new_lift_path)

    @pytest.mark.integration
    def test_drop_database_content_multiple_times(self, dict_service_with_data):
        """Test that dropping database content multiple times works correctly."""
        # Drop multiple times
        for i in range(3):
            dict_service_with_data.drop_database_content()
            count = dict_service_with_data.count_entries()
            assert count == 0, f"Expected 0 entries after drop {i+1}, got {count}"
        
        # Should still be able to use the database after multiple drops
        assert dict_service_with_data.count_entries() == 0