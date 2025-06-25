"""
Additional CRUD tests for the DictionaryService focusing on edge cases.
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
TEST_DB = "test_dict_crud"


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


class TestAdvancedCRUD:
    """Additional CRUD tests for the DictionaryService."""
    
    def test_create_entry_duplicate_id(self, dict_service):
        """Test creating an entry with a duplicate ID."""
        # Create an entry with an ID that already exists
        entry = Entry(id_="test_entry_1", lexical_unit={"en": "duplicate"})
        
        # Attempt to create the entry - should raise ValidationError
        with pytest.raises(ValidationError):
            dict_service.create_entry(entry)
    
    def test_create_entry_with_invalid_data(self, dict_service):
        """Test creating an entry with invalid data."""
        # Create an entry with no lexical unit (which is required)
        entry = Entry(id_="invalid_entry")
        
        # Attempt to create the entry - should raise ValidationError
        with pytest.raises(ValidationError):
            dict_service.create_entry(entry)
    
    def test_create_entry_with_complex_structure(self, dict_service):
        """Test creating an entry with a complex structure."""
        # Create an entry with multiple senses, examples, and pronunciations
        entry = Entry(
            id_="complex_entry",
            lexical_unit={"en": "complex", "pl": "złożony"},
            pronunciations={"seh-fonipa": "kɒmplɛks"},
            grammatical_info="noun"
        )
        
        # Add senses and examples
        entry.senses = [
            {
                "id": "sense1",
                "gloss": {"pl": "złożony"},
                "definition": {"en": "Having many interconnected parts"},
                "examples": [
                    {
                        "id": "example1",
                        "form": {"en": "This is a complex problem."},
                        "translation": {"pl": "To jest złożony problem."}
                    }
                ]
            },
            {
                "id": "sense2",
                "gloss": {"pl": "kompleks"},
                "definition": {"en": "A group of buildings or related things"},
                "examples": [
                    {
                        "id": "example2",
                        "form": {"en": "The shopping complex."},
                        "translation": {"pl": "Kompleks handlowy."}
                    }
                ]
            }
        ]
        
        # Create the entry
        entry_id = dict_service.create_entry(entry)
        assert entry_id == "complex_entry"
        
        # Retrieve the entry to verify it was created correctly
        retrieved_entry = dict_service.get_entry("complex_entry")
        assert retrieved_entry.id == "complex_entry"
        assert retrieved_entry.lexical_unit.get("en") == "complex"
        assert retrieved_entry.lexical_unit.get("pl") == "złożony"
        assert len(retrieved_entry.senses) == 2
        
        # Check the senses
        sense_ids = [sense.get("id") for sense in retrieved_entry.senses]
        assert "sense1" in sense_ids
        assert "sense2" in sense_ids
        
        # Check the examples
        # Find the first sense
        sense1 = next((sense for sense in retrieved_entry.senses if sense.get("id") == "sense1"), None)
        assert sense1 is not None
        
        # Check that it has an example
        examples = sense1.get("examples", [])
        assert len(examples) > 0
        assert examples[0].get("form", {}).get("en") == "This is a complex problem."
    
    def test_update_nonexistent_entry(self, dict_service):
        """Test updating an entry that doesn't exist."""
        # Create an entry but don't add it to the database
        entry = Entry(id_="nonexistent_entry", lexical_unit={"en": "nonexistent"})
        
        # Attempt to update the entry - should raise NotFoundError
        with pytest.raises(NotFoundError):
            dict_service.update_entry(entry)
    
    def test_delete_nonexistent_entry(self, dict_service):
        """Test deleting an entry that doesn't exist."""
        # Attempt to delete an entry that doesn't exist - should raise NotFoundError
        with pytest.raises(NotFoundError):
            dict_service.delete_entry("nonexistent_entry")
    
    def test_create_or_update_entry(self, dict_service):
        """Test the create_or_update_entry method."""
        # Create a new entry
        new_entry = Entry(id_="new_entry", lexical_unit={"en": "new"})
        
        # Use create_or_update_entry - should create
        entry_id = dict_service.create_or_update_entry(new_entry)
        assert entry_id == "new_entry"
        
        # Verify it was created
        retrieved_entry = dict_service.get_entry("new_entry")
        assert retrieved_entry.id == "new_entry"
        assert retrieved_entry.lexical_unit.get("en") == "new"
        
        # Modify the entry
        new_entry.lexical_unit = {"en": "updated"}
        
        # Use create_or_update_entry again - should update
        entry_id = dict_service.create_or_update_entry(new_entry)
        assert entry_id == "new_entry"
        
        # Verify it was updated
        retrieved_entry = dict_service.get_entry("new_entry")
        assert retrieved_entry.id == "new_entry"
        assert retrieved_entry.lexical_unit.get("en") == "updated"
    
    def test_related_entries(self, dict_service):
        """Test creating and retrieving related entries."""
        # Create entries with relationships
        entry1 = Entry(id_="word1", lexical_unit={"en": "word1"})
        entry2 = Entry(id_="word2", lexical_unit={"en": "word2"})
        
        # Add relationship from entry1 to entry2
        entry1.relations = [{"type": "synonym", "ref": "word2"}]
        
        # Create the entries
        dict_service.create_entry(entry1)
        dict_service.create_entry(entry2)
        
        # Get related entries for entry1
        related_entries = dict_service.get_related_entries("word1")
        
        # Verify related entries
        assert len(related_entries) == 1
        assert related_entries[0].id == "word2"
        
        # Get related entries with specific relation type
        related_entries = dict_service.get_related_entries("word1", relation_type="synonym")
        assert len(related_entries) == 1
        assert related_entries[0].id == "word2"
        
        # Try a non-existent relation type
        related_entries = dict_service.get_related_entries("word1", relation_type="antonym")
        assert len(related_entries) == 0
        
        # Add another relation
        entry1.relations.append({"type": "antonym", "ref": "word2"})
        dict_service.update_entry(entry1)
        
        # Get related entries with the new relation type
        related_entries = dict_service.get_related_entries("word1", relation_type="antonym")
        assert len(related_entries) == 1
        assert related_entries[0].id == "word2"
    
    def test_entries_by_grammatical_info(self, dict_service):
        """Test retrieving entries by grammatical information."""
        # Create entries with different grammatical info
        entries = [
            Entry(id_="noun1", lexical_unit={"en": "table"}, grammatical_info="noun"),
            Entry(id_="verb1", lexical_unit={"en": "run"}, grammatical_info="verb"),
            Entry(id_="adj1", lexical_unit={"en": "red"}, grammatical_info="adjective"),
            Entry(id_="noun2", lexical_unit={"en": "book"}, grammatical_info="noun")
        ]
        
        # Create the entries
        for entry in entries:
            dict_service.create_entry(entry)
        
        # Get entries by grammatical info
        noun_entries = dict_service.get_entries_by_grammatical_info("noun")
        assert len(noun_entries) == 2
        noun_ids = [entry.id for entry in noun_entries]
        assert "noun1" in noun_ids
        assert "noun2" in noun_ids
        
        verb_entries = dict_service.get_entries_by_grammatical_info("verb")
        assert len(verb_entries) == 1
        assert verb_entries[0].id == "verb1"
        
        adj_entries = dict_service.get_entries_by_grammatical_info("adjective")
        assert len(adj_entries) == 1
        assert adj_entries[0].id == "adj1"
        
        # Test with non-existent grammatical info
        adv_entries = dict_service.get_entries_by_grammatical_info("adverb")
        assert len(adv_entries) == 0
