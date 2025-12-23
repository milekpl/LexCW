"""
Tests for the DictionaryService's CRUD, search, import, and export functionality.
"""

import os
import pytest
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError

# Test data
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_LIFT_FILE = os.path.join(TEST_DATA_DIR, "test.lift")
TEST_RANGES_FILE = os.path.join(TEST_DATA_DIR, "test-ranges.lift-ranges")

# Connection parameters
HOST = "localhost"
PORT = 1984
USERNAME = "admin"
PASSWORD = "admin"
TEST_DB_BASE = "test_dict_service"

import uuid


@pytest.fixture(scope="function")
def dict_service():
    """Create a DictionaryService with test database for each test."""
    # Generate a unique database name for this test run
    TEST_DB = f"{TEST_DB_BASE}_{uuid.uuid4().hex[:8]}"
    
    # Create an admin connector (no database specified)
    admin_connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD)
    admin_connector.connect()
    
    # Clean up any existing test database
    try:
        if TEST_DB in (admin_connector.execute_command("LIST") or ""):
            admin_connector.execute_command(f"DROP DB {TEST_DB}")
    except Exception:
        pass
    
    # Create the test database
    admin_connector.execute_command(f"CREATE DB {TEST_DB}")
    admin_connector.disconnect()
    
    # Now create a connector for the test database
    connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD, TEST_DB)
    connector.connect()
    
    # Create the service
    service = DictionaryService(connector)
    
    # Initialize with test data
    service.initialize_database(TEST_LIFT_FILE, TEST_RANGES_FILE)
    
    yield service
    
    # Clean up
    try:
        connector.disconnect()
        admin_connector.connect()
        admin_connector.execute_command(f"DROP DB {TEST_DB}")
        admin_connector.disconnect()
    except Exception:
        pass



@pytest.mark.integration
class TestDictionaryService:
    """Test the DictionaryService functionality with a live BaseX server."""
    
    @pytest.mark.integration
    def test_initialize_database(self, dict_service):
        """Test that the database is properly initialized."""
        # The initialize_database was called in the fixture
        # Check that we have the expected entries
        count = dict_service.count_entries()
        assert count == 2  # Our test.lift file has 2 entries
    
    @pytest.mark.integration
    def test_get_entry(self, dict_service):
        """Test retrieving an entry by ID."""
        # Get an entry that exists
        entry = dict_service.get_entry("test_entry_1")
        assert entry is not None
        assert entry.id == "test_entry_1"
        assert entry.lexical_unit.get('en') == "test"
        
        # Try to get an entry that doesn't exist
        with pytest.raises(NotFoundError):
            dict_service.get_entry("nonexistent_entry")
    
    @pytest.mark.integration
    def test_create_entry(self, dict_service):
        """Test creating a new entry."""
        # Create a new entry
        entry = Entry(
            id_="new_test_entry",
            lexical_unit={'en': 'new test'},
            senses=[{"id": "sense_1", "definition": {"en": "a new test entry"}}]
        )
        
        # Add it to the database
        entry_id = dict_service.create_entry(entry)
        assert entry_id == "new_test_entry"
        
        # Verify it was added
        retrieved_entry = dict_service.get_entry("new_test_entry")
        assert retrieved_entry is not None
        assert retrieved_entry.id == "new_test_entry"
        assert retrieved_entry.lexical_unit.get('en') == "new test"
        
        # Verify the count increased
        count = dict_service.count_entries()
        assert count == 3  # Original 2 plus our new one
    
    @pytest.mark.integration
    def test_update_entry(self, dict_service):
        """Test updating an existing entry."""
        # Get an existing entry
        entry = dict_service.get_entry("test_entry_1")
        
        # Modify it
        entry.lexical_unit = {'en': 'modified test'}
        
        # Update it
        dict_service.update_entry(entry)
        
        # Verify the change
        updated_entry = dict_service.get_entry("test_entry_1")
        assert updated_entry.lexical_unit.get('en') == "modified test"
    
    @pytest.mark.integration
    def test_delete_entry(self, dict_service):
        """Test deleting an entry."""
        # Delete an existing entry
        dict_service.delete_entry("test_entry_1")
        
        # Verify it's gone
        with pytest.raises(NotFoundError):
            dict_service.get_entry("test_entry_1")
        
        # Verify the count decreased
        count = dict_service.count_entries()
        assert count == 1  # Original 2 minus the deleted one
    
    @pytest.mark.integration
    def test_list_entries(self, dict_service):
        """Test listing entries."""
        # List all entries
        entries, total = dict_service.list_entries()
        assert total == 2
        assert len(entries) == 2
        
        # List with limit
        entries, total = dict_service.list_entries(limit=1)
        assert total == 2
        assert len(entries) == 1
    
    @pytest.mark.integration
    def test_search_entries(self, dict_service):
        """Test searching for entries."""
        # Search for entries containing "test"
        entries, total = dict_service.search_entries("test")
        assert total == 1
        assert len(entries) == 1
        assert entries[0].id == "test_entry_1"
        
        # Search for entries containing "example"
        entries, total = dict_service.search_entries("example")
        assert total == 1
        assert len(entries) == 1
        assert entries[0].id == "test_entry_2"
        
        # Search with no matches
        entries, total = dict_service.search_entries("nonexistent")
        assert total == 0
        assert len(entries) == 0
    
    @pytest.mark.integration
    def test_import_lift(self, dict_service):
        """Test importing a LIFT file."""
        # Count initial entries
        initial_count = dict_service.count_entries()
        assert initial_count == 2
        
        # Import the LIFT file (which will update existing entries)
        imported_count = dict_service.import_lift(TEST_LIFT_FILE)
        assert imported_count == 2
        
        # Verify count remains the same (since we imported the same file)
        count = dict_service.count_entries()
        assert count == 2
    
    @pytest.mark.integration
    def test_export_lift(self, dict_service, tmp_path):
        """Test exporting to LIFT format."""
        # Export the database to a LIFT file
        lift_content = dict_service.export_lift()
        
        # Verify the LIFT content
        assert "<lift " in lift_content
        assert "test_entry_1" in lift_content
        assert "test_entry_2" in lift_content
        
        # Export to a file
        export_path = os.path.join(tmp_path, "export.lift")
        dict_service.export_to_lift(export_path)
        
        # Verify the file exists
        assert os.path.exists(export_path)
        
        # Read the file and verify contents
        with open(export_path, "r", encoding="utf-8") as f:
            file_content = f.read()
            assert "<lift " in file_content
            assert "test_entry_1" in file_content
            assert "test_entry_2" in file_content
