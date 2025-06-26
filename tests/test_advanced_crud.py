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
            pronunciations={"seh-fonipa": "kɒmplɛks"}
        )
        
        # Add the entry directly with a simpler structure first
        dict_service.create_entry(entry)
        
        # Retrieve the entry
        retrieved_entry = dict_service.get_entry("complex_entry")
        assert retrieved_entry.id == "complex_entry"
        assert retrieved_entry.lexical_unit.get("en") == "complex"
        assert retrieved_entry.lexical_unit.get("pl") == "złożony"
        
        # Now update it with senses via BaseX direct update
        db_name = dict_service.db_connector.database
        
        # Add senses and examples via direct BaseX update
        update_query = f"""
        xquery 
        let $entry := collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id="complex_entry"]
        return (
            insert node 
            <sense id="sense1">
                <grammatical-info value="noun"/>
                <gloss lang="pl">
                    <text>złożony</text>
                </gloss>
                <definition>
                    <form lang="en">
                        <text>Having many interconnected parts</text>
                    </form>
                </definition>
                <example>
                    <form lang="en">
                        <text>This is a complex problem.</text>
                    </form>
                    <translation>
                        <form lang="pl">
                            <text>To jest złożony problem.</text>
                        </form>
                    </translation>
                </example>
            </sense>
            into $entry,
            
            insert node
            <sense id="sense2">
                <grammatical-info value="noun"/>
                <gloss lang="pl">
                    <text>kompleks</text>
                </gloss>
                <definition>
                    <form lang="en">
                        <text>A group of buildings or related things</text>
                    </form>
                </definition>
                <example>
                    <form lang="en">
                        <text>The shopping complex.</text>
                    </form>
                    <translation>
                        <form lang="pl">
                            <text>Kompleks handlowy.</text>
                        </form>
                    </translation>
                </example>
            </sense>
            into $entry
        )
        """
        
        dict_service.db_connector.execute_update(update_query)
        
        # Re-retrieve the entry to verify the changes
        retrieved_entry = dict_service.get_entry("complex_entry")
        assert retrieved_entry.id == "complex_entry"
        
        # Check for the senses
        assert len(retrieved_entry.senses) == 2
        
        # Check the sense IDs
        sense_ids = [sense.id for sense in retrieved_entry.senses]
        assert "sense1" in sense_ids
        assert "sense2" in sense_ids
        
        # Find sense1 and verify it has the correct data
        sense1 = next((s for s in retrieved_entry.senses if s.id == "sense1"), None)
        assert sense1 is not None
        
        # Check that it has grammatical info
        # In some XML parsers, the grammatical-info might be parsed differently
        # Let's check if there's any grammatical info or hint in the sense
        assert sense1 is not None
        
        # Print the sense to help debug
        print(f"Sense1: {sense1}")
        
        # Instead of checking a specific format which might vary, just check if the sense data is valid
        assert sense1.id == "sense1"
        assert sense1.glosses.get("pl") == "złożony"
        assert sense1.definitions.get("en") == "Having many interconnected parts"
        
        # Try to check for grammatical info - this is what we're testing
        grammatical_info = sense1.grammatical_info
        if grammatical_info is not None:
            assert grammatical_info == "noun"
            print(f"SUCCESS: Grammatical info correctly parsed as: {grammatical_info}")
        else:
            # If not found in the standard field, it might be in a custom field or we're parsing it wrong
            # For now, let's just print a warning and make the test pass
            import warnings
            warnings.warn(f"Grammatical info not found in expected format. Sense data: {sense1}")
            print(f"FAILED: Grammatical info is None. Sense object: {sense1}")
            # Test fails because we're specifically testing grammatical info
            assert False, f"Grammatical info should be 'noun' but got: {grammatical_info}"
    
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
        # Add entries with grammatical info directly with BaseX
        db_name = dict_service.db_connector.database
        
        # Insert test entries with grammatical info
        insert_query = f"""
        xquery
        insert node 
        <entry id="noun1">
            <lexical-unit>
                <form lang="en">
                    <text>table</text>
                </form>
            </lexical-unit>
            <sense id="s1">
                <grammatical-info value="noun"/>
                <gloss lang="pl">
                    <text>stół</text>
                </gloss>
            </sense>
        </entry>
        into collection('{db_name}')/*[local-name()='lift'],
        
        insert node 
        <entry id="verb1">
            <lexical-unit>
                <form lang="en">
                    <text>run</text>
                </form>
            </lexical-unit>
            <sense id="s2">
                <grammatical-info value="verb"/>
                <gloss lang="pl">
                    <text>biegać</text>
                </gloss>
            </sense>
        </entry>
        into collection('{db_name}')/*[local-name()='lift'],
        
        insert node 
        <entry id="adj1">
            <lexical-unit>
                <form lang="en">
                    <text>red</text>
                </form>
            </lexical-unit>
            <sense id="s3">
                <grammatical-info value="adjective"/>
                <gloss lang="pl">
                    <text>czerwony</text>
                </gloss>
            </sense>
        </entry>
        into collection('{db_name}')/*[local-name()='lift'],
        
        insert node 
        <entry id="noun2">
            <lexical-unit>
                <form lang="en">
                    <text>book</text>
                </form>
            </lexical-unit>
            <sense id="s4">
                <grammatical-info value="noun"/>
                <gloss lang="pl">
                    <text>książka</text>
                </gloss>
            </sense>
        </entry>
        into collection('{db_name}')/*[local-name()='lift']
        """
        
        dict_service.db_connector.execute_update(insert_query)
        
        # Get entries by grammatical info
        noun_entries = dict_service.get_entries_by_grammatical_info("noun")
        assert len(noun_entries) == 2
        noun_ids = sorted([entry.id for entry in noun_entries])
        assert noun_ids == ["noun1", "noun2"]
        
        verb_entries = dict_service.get_entries_by_grammatical_info("verb")
        assert len(verb_entries) == 1
        assert verb_entries[0].id == "verb1"
        
        adj_entries = dict_service.get_entries_by_grammatical_info("adjective")
        assert len(adj_entries) == 1
        assert adj_entries[0].id == "adj1"
        
        # Test with non-existent grammatical info
        adv_entries = dict_service.get_entries_by_grammatical_info("adverb")
        assert len(adv_entries) == 0
        
        # Clean up the test entries
        cleanup_query = f"""
        xquery
        for $id in ("noun1", "verb1", "adj1", "noun2")
        return delete node collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry'][@id=$id]
        """
        dict_service.db_connector.execute_update(cleanup_query)
