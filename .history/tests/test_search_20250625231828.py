"""
Tests for the search functionality in the DictionaryService.
"""

import os
import pytest
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
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
TEST_DB = "test_dict_search"


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
    
    # Add more test entries for search testing
    create_test_entries(service)
    
    yield service
    
    # Clean up
    try:
        if TEST_DB in (connector.execute_query("LIST") or ""):
            connector.execute_update(f"DROP DB {TEST_DB}")
    except Exception:
        pass
    
    connector.disconnect()


def create_test_entries(service):
    """Create additional test entries for search testing."""
    # Entry with multiple senses
    entry1 = Entry(
        id_="multiple_senses",
        lexical_unit={"en": "bank"},
        grammatical_info="noun"
    )
    entry1.senses = [
        {
            "id": "bank_sense1",
            "gloss": {"pl": "bank (instytucja finansowa)"},
            "definition": {"en": "A financial institution"},
            "examples": [
                {
                    "id": "bank_example1",
                    "form": {"en": "I need to go to the bank."},
                    "translation": {"pl": "Muszę iść do banku."}
                }
            ]
        },
        {
            "id": "bank_sense2",
            "gloss": {"pl": "brzeg (rzeki)"},
            "definition": {"en": "The land alongside a river or lake"},
            "examples": [
                {
                    "id": "bank_example2",
                    "form": {"en": "We sat on the river bank."},
                    "translation": {"pl": "Siedzieliśmy na brzegu rzeki."}
                }
            ]
        }
    ]
    
    # Entry with similar words
    entry2 = Entry(
        id_="similar_word_1",
        lexical_unit={"en": "testing"},
        grammatical_info="verb"
    )
    entry2.senses = [
        {
            "id": "testing_sense",
            "gloss": {"pl": "testowanie"},
            "definition": {"en": "The action of testing something"}
        }
    ]
    
    # Entry with similar words
    entry3 = Entry(
        id_="similar_word_2",
        lexical_unit={"en": "tester"},
        grammatical_info="noun"
    )
    entry3.senses = [
        {
            "id": "tester_sense",
            "gloss": {"pl": "tester"},
            "definition": {"en": "A person who tests something"}
        }
    ]
    
    # Entry with special characters
    entry4 = Entry(
        id_="special_chars",
        lexical_unit={"en": "café"},
        grammatical_info="noun"
    )
    entry4.senses = [
        {
            "id": "cafe_sense",
            "gloss": {"pl": "kawiarnia"},
            "definition": {"en": "A small restaurant selling light meals and drinks"}
        }
    ]
    
    # Create all entries
    service.create_entry(entry1)
    service.create_entry(entry2)
    service.create_entry(entry3)
    service.create_entry(entry4)


class TestSearch:
    """Test the search functionality of the DictionaryService."""
    
    def test_basic_search(self, dict_service):
        """Test basic search functionality."""
        # Search for entries containing "test"
        entries, total = dict_service.search_entries("test")
        assert total == 3  # test_entry_1 + similar_word_1 (testing) + similar_word_2 (tester)
        assert len(entries) == 3
        
        # Verify entry IDs
        entry_ids = [entry.id for entry in entries]
        assert "test_entry_1" in entry_ids
        assert "similar_word_1" in entry_ids
        assert "similar_word_2" in entry_ids
    
    def test_search_exact_match(self, dict_service):
        """Test searching for exact matches."""
        # Search for entries exactly matching "test"
        entries, total = dict_service.search_entries("test")
        assert "test_entry_1" in [entry.id for entry in entries]
        
        # Search for "example" which is in test_entry_2
        entries, total = dict_service.search_entries("example")
        assert total == 1
        assert entries[0].id == "test_entry_2"
    
    def test_search_by_field(self, dict_service):
        """Test searching in specific fields."""
        # Search only in lexical_unit field
        entries, total = dict_service.search_entries("test", fields=["lexical_unit"])
        assert total == 1  # Only test_entry_1 has "test" in lexical_unit
        assert entries[0].id == "test_entry_1"
        
        # Search only in glosses field
        entries, total = dict_service.search_entries("instytucja", fields=["glosses"])
        assert total == 1  # Only multiple_senses (bank) has "instytucja" in glosses
        assert entries[0].id == "multiple_senses"
        
        # Search only in definitions field
        entries, total = dict_service.search_entries("financial", fields=["definitions"])
        assert total == 1  # Only multiple_senses (bank) has "financial" in definitions
        assert entries[0].id == "multiple_senses"
        
        # Search in both glosses and definitions
        entries, total = dict_service.search_entries("river", fields=["glosses", "definitions"])
        assert total == 1  # Only multiple_senses (bank) has "river" in definitions
        assert entries[0].id == "multiple_senses"
    
    def test_search_special_characters(self, dict_service):
        """Test searching with special characters."""
        # Search for entries containing "café"
        entries, total = dict_service.search_entries("café")
        assert total == 1
        assert entries[0].id == "special_chars"
        
        # Search with lowercase, should still find it
        entries, total = dict_service.search_entries("cafe")
        assert total == 1
        assert entries[0].id == "special_chars"
    
    def test_search_pagination(self, dict_service):
        """Test search pagination."""
        # Search with a small limit
        entries, total = dict_service.search_entries("test", limit=1)
        assert total == 3  # Total count should still be 3
        assert len(entries) == 1  # But only 1 entry returned
        
        # Search with offset
        entries_page1, _ = dict_service.search_entries("test", limit=2, offset=0)
        entries_page2, _ = dict_service.search_entries("test", limit=2, offset=2)
        
        # Ensure we get different entries on different pages
        page1_ids = {entry.id for entry in entries_page1}
        page2_ids = {entry.id for entry in entries_page2}
        assert page1_ids != page2_ids
        assert len(page1_ids.intersection(page2_ids)) == 0  # No overlap
    
    def test_search_no_results(self, dict_service):
        """Test search with no matching results."""
        # Search for a term that doesn't exist
        entries, total = dict_service.search_entries("nonexistent")
        assert total == 0
        assert len(entries) == 0
    
    def test_search_after_update(self, dict_service):
        """Test that search results update after modifying entries."""
        # Initial search for "update"
        entries, total = dict_service.search_entries("update")
        assert total == 0  # Should not find anything
        
        # Create a new entry with "update" in lexical_unit
        entry = Entry(id_="update_test", lexical_unit={"en": "update test"})
        dict_service.create_entry(entry)
        
        # Search again
        entries, total = dict_service.search_entries("update")
        assert total == 1
        assert entries[0].id == "update_test"
        
        # Update the entry to remove "update"
        entry.lexical_unit = {"en": "changed"}
        dict_service.update_entry(entry)
        
        # Search again
        entries, total = dict_service.search_entries("update")
        assert total == 0  # Should no longer find anything
        
        # But should find with the new text
        entries, total = dict_service.search_entries("changed")
        assert total == 1
        assert entries[0].id == "update_test"
