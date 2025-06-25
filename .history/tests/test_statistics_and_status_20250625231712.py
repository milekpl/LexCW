"""
Tests for the statistics and system status functionality in the DictionaryService.
"""

import os
import pytest
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import DatabaseError

# Test data
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_LIFT_FILE = os.path.join(TEST_DATA_DIR, "test.lift")
TEST_RANGES_FILE = os.path.join(TEST_DATA_DIR, "test-ranges.lift-ranges")

# Connection parameters
HOST = "localhost"
PORT = 1984
USERNAME = "admin"
PASSWORD = "admin"
TEST_DB = "test_dict_stats"


@pytest.fixture(scope="function")
def dict_service():
    """Create a DictionaryService with test database for each test."""
    # Create the connector
    connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD, TEST_DB)
    connector.connect()
    
    # Clean up any existing test database
    if TEST_DB in (connector.execute_query("LIST") or ""):
        connector.execute_update(f"DROP DB {TEST_DB}")
    
    # Create the service
    service = DictionaryService(connector)
    
    # Initialize with test data
    service.initialize_database(TEST_LIFT_FILE, TEST_RANGES_FILE)
    
    yield service
    
    # Clean up
    try:
        if TEST_DB in (connector.execute_query("LIST") or ""):
            connector.execute_update(f"DROP DB {TEST_DB}")
    except Exception:
        pass
    
    connector.disconnect()


class TestDictionaryStatistics:
    """Test the statistics functionality of the DictionaryService."""
    
    def test_count_entries(self, dict_service):
        """Test that the entry count is correct."""
        # Our test.lift file contains 2 entries
        count = dict_service.count_entries()
        assert count == 2
        
        # Add a new entry
        entry = dict_service.lift_parser.parse_string("""
        <lift>
            <entry id="new_test_entry">
                <lexical-unit>
                    <form lang="en">
                        <text>new test</text>
                    </form>
                </lexical-unit>
            </entry>
        </lift>
        """)[0]
        
        dict_service.create_entry(entry)
        
        # Check that the count increased
        count = dict_service.count_entries()
        assert count == 3
        
        # Delete the entry
        dict_service.delete_entry("new_test_entry")
        
        # Check that the count decreased
        count = dict_service.count_entries()
        assert count == 2
    
    def test_count_senses_and_examples(self, dict_service):
        """Test that the sense and example counts are correct."""
        # In our test data, there are 2 entries, each with 1 sense and 1 example
        sense_count, example_count = dict_service.count_senses_and_examples()
        assert sense_count == 2
        assert example_count == 2
        
        # Add a new entry with multiple senses and examples
        entry = dict_service.lift_parser.parse_string("""
        <lift>
            <entry id="multi_sense_entry">
                <lexical-unit>
                    <form lang="en">
                        <text>multi sense</text>
                    </form>
                </lexical-unit>
                <sense id="sense1">
                    <gloss lang="pl">
                        <text>wieloznaczny 1</text>
                    </gloss>
                    <example>
                        <form lang="en">
                            <text>Example 1</text>
                        </form>
                    </example>
                </sense>
                <sense id="sense2">
                    <gloss lang="pl">
                        <text>wieloznaczny 2</text>
                    </gloss>
                    <example>
                        <form lang="en">
                            <text>Example 2</text>
                        </form>
                    </example>
                    <example>
                        <form lang="en">
                            <text>Example 3</text>
                        </form>
                    </example>
                </sense>
            </entry>
        </lift>
        """)[0]
        
        dict_service.create_entry(entry)
        
        # Check that the counts increased appropriately:
        # - 2 original senses + 2 new senses = 4 senses
        # - 2 original examples + 3 new examples = 5 examples
        sense_count, example_count = dict_service.count_senses_and_examples()
        assert sense_count == 4
        assert example_count == 5
        
        # Delete the entry
        dict_service.delete_entry("multi_sense_entry")
        
        # Check that the counts return to original values
        sense_count, example_count = dict_service.count_senses_and_examples()
        assert sense_count == 2
        assert example_count == 2
    
    def test_statistics_after_import(self, dict_service):
        """Test that statistics are correctly updated after importing a LIFT file."""
        # Initially we have 2 entries, each with 1 sense and 1 example
        initial_count = dict_service.count_entries()
        initial_sense_count, initial_example_count = dict_service.count_senses_and_examples()
        
        assert initial_count == 2
        assert initial_sense_count == 2
        assert initial_example_count == 2
        
        # Create a temporary LIFT file with additional entries
        import tempfile
        
        temp_lift_content = """<?xml version="1.0" encoding="utf-8"?>
        <lift version="0.13" producer="dictionary-writing-system">
          <entry id="new_entry_1">
            <lexical-unit>
              <form lang="en">
                <text>additional</text>
              </form>
            </lexical-unit>
            <sense id="s1">
              <gloss lang="pl">
                <text>dodatkowy</text>
              </gloss>
              <example>
                <form lang="en">
                  <text>This is an additional example</text>
                </form>
              </example>
            </sense>
          </entry>
          <entry id="new_entry_2">
            <lexical-unit>
              <form lang="en">
                <text>extra</text>
              </form>
            </lexical-unit>
            <sense id="s2">
              <gloss lang="pl">
                <text>ekstra</text>
              </gloss>
              <example>
                <form lang="en">
                  <text>This is an extra example</text>
                </form>
              </example>
            </sense>
            <sense id="s3">
              <gloss lang="pl">
                <text>dodatkowy</text>
              </gloss>
            </sense>
          </entry>
        </lift>
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', encoding='utf-8', delete=False) as temp_file:
            temp_file.write(temp_lift_content)
            temp_lift_path = temp_file.name
        
        try:
            # Import the temporary LIFT file
            dict_service.import_lift(temp_lift_path)
            
            # Check that the statistics were updated
            # - 2 original entries + 2 new entries = 4 entries
            # - 2 original senses + 3 new senses = 5 senses
            # - 2 original examples + 2 new examples = 4 examples
            count = dict_service.count_entries()
            sense_count, example_count = dict_service.count_senses_and_examples()
            
            assert count == 4
            assert sense_count == 5
            assert example_count == 4
            
            # Check that searching works for the new entries
            entries, total = dict_service.search_entries("additional")
            assert total == 1
            assert entries[0].id == "new_entry_1"
            
            entries, total = dict_service.search_entries("extra")
            assert total == 1
            assert entries[0].id == "new_entry_2"
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_lift_path):
                os.unlink(temp_lift_path)


class TestSystemStatus:
    """Test the system status functionality of the DictionaryService."""
    
    def test_get_system_status(self, dict_service):
        """Test that the system status is returned correctly."""
        status = dict_service.get_system_status()
        
        # Verify that the system status has the expected structure
        assert 'db_connected' in status
        assert status['db_connected'] is True  # The database should be connected for this test
        
        assert 'last_backup' in status  # Could be None or a timestamp
        assert 'storage_percent' in status  # Should be a number
        
    def test_system_status_disconnected(self):
        """Test system status when database is disconnected."""
        # Create a connector but don't connect it
        connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD, "nonexistent_db")
        service = DictionaryService(connector)
        
        # Get the system status
        status = service.get_system_status()
        
        # Verify that the database is shown as disconnected
        assert status['db_connected'] is False
