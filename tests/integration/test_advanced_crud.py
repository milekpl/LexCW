"""
Additional CRUD tests for the DictionaryService focusing on edge cases.
"""

from __future__ import annotations

import pytest
from app.models.entry import Entry
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError
from app.services.dictionary_service import DictionaryService



@pytest.mark.integration
class TestAdvancedCRUD:
    """Additional CRUD tests for the DictionaryService."""
    
    @pytest.mark.integration
    def test_create_entry_duplicate_id(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with a duplicate ID."""
        # Create an entry with a unique ID (not test_entry_1 which is from fixture)
        entry = Entry(
            id_="duplicate_test_entry",
            lexical_unit={"en": "duplicate"},
            senses=[{"id": "sense_1", "definition": {"en": "a duplicate entry"}}]
        )
        # First, create the entry
        dict_service_with_db.create_entry(entry)
        # Attempt to create the entry again - should raise ValidationError
        with pytest.raises(ValidationError):
            dict_service_with_db.create_entry(entry)
    
    @pytest.mark.integration
    def test_create_entry_with_invalid_data(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with invalid data."""
        # Create an entry with no lexical unit (which is required)
        entry = Entry(id_="invalid_entry")
        
        # Attempt to create the entry - should raise ValidationError
        with pytest.raises(ValidationError):
            dict_service_with_db.create_entry(entry)
    
    @pytest.mark.integration
    def test_create_entry_with_complex_structure(self, dict_service_with_db: DictionaryService) -> None:
        """Test creating an entry with a complex structure."""
        # Create an entry with multiple senses, examples, and pronunciations
        entry = Entry(
            id_="complex_entry",
            lexical_unit={"en": "complex", "pl": "złożony"},
            senses=[
                {"id": "initial_sense", "definition": {"en": "initial definition"}, "gloss": {"en": "initial"}},
                {"id": "sense1", "grammatical_info": "noun", "gloss": {"pl": "złożony"}, "definition": {"en": "Having many interconnected parts"}},
                {"id": "sense2", "grammatical_info": "noun", "gloss": {"pl": "kompleks"}, "definition": {"en": "A group of buildings or related things"}}
            ],
            pronunciations={"seh-fonipa": "kɒmplɛks"}
        )
        dict_service_with_db.create_entry(entry)
        retrieved_entry = dict_service_with_db.get_entry("complex_entry")
        assert retrieved_entry.id == "complex_entry"
        assert retrieved_entry.lexical_unit.get("en") == "complex"
        assert retrieved_entry.lexical_unit.get("pl") == "złożony"
        assert len(retrieved_entry.senses) == 3
        sense_ids = [sense.id for sense in retrieved_entry.senses]
        assert "sense1" in sense_ids
        assert "sense2" in sense_ids
        sense1 = next((s for s in retrieved_entry.senses if s.id == "sense1"), None)
        assert sense1 is not None
        assert sense1.id == "sense1"
        # Check for grammatical info and data
        assert getattr(sense1, "grammatical_info", None) == "noun"
        # Use flat format (LIFT standard) - glosses and definitions are Dict[str, str]
        assert sense1.glosses.get("pl") == "złożony"
        assert sense1.definitions.get("en") == "Having many interconnected parts"
    
    @pytest.mark.integration
    def test_update_nonexistent_entry(self, dict_service_with_db):
        """Test updating an entry that doesn't exist."""
        # Create an entry but don't add it to the database
        entry = Entry(
            id_="nonexistent_entry", 
            lexical_unit={"en": "nonexistent"},
            senses=[{"id": "sense_1", "definition": {"en": "a nonexistent word"}}]
        )
        
        # Attempt to update the entry - should raise NotFoundError
        with pytest.raises(NotFoundError):
            dict_service_with_db.update_entry(entry)
    
    @pytest.mark.integration
    def test_delete_nonexistent_entry(self, dict_service_with_db):
        """Test deleting an entry that doesn't exist."""
        # Attempt to delete an entry that doesn't exist - should raise NotFoundError
        with pytest.raises(NotFoundError):
            dict_service_with_db.delete_entry("nonexistent_entry")
    
    @pytest.mark.integration
    def test_create_or_update_entry(self, dict_service_with_db):
        """Test the create_or_update_entry method."""
        # Create a new entry
        new_entry = Entry(
            id_="new_entry", 
            lexical_unit={"en": "new"},
            senses=[{"id": "sense_1", "definition": {"en": "a new entry"}}]
        )
        
        # Use create_or_update_entry - should create
        entry_id = dict_service_with_db.create_or_update_entry(new_entry)
        assert entry_id == "new_entry"
        
        # Verify it was created
        retrieved_entry = dict_service_with_db.get_entry("new_entry")
        assert retrieved_entry.id == "new_entry"
        assert retrieved_entry.lexical_unit.get("en") == "new"
        
        # Modify the entry
        new_entry.lexical_unit = {"en": "updated"}
        
        # Use create_or_update_entry again - should update
        entry_id = dict_service_with_db.create_or_update_entry(new_entry)
        assert entry_id == "new_entry"
        
        # Verify it was updated
        retrieved_entry = dict_service_with_db.get_entry("new_entry")
        assert retrieved_entry.id == "new_entry"
        assert retrieved_entry.lexical_unit.get("en") == "updated"
    
    @pytest.mark.integration
    def test_related_entries(self, dict_service_with_db):
        """Test creating and retrieving related entries."""
        # Create entries with relationships
        entry1 = Entry(
            id_="word1", 
            lexical_unit={"en": "word1"},
            senses=[{"id": "sense_1", "definition": {"en": "first word"}}]
        )
        entry2 = Entry(
            id_="word2", 
            lexical_unit={"en": "word2"},
            senses=[{"id": "sense_1", "definition": {"en": "second word"}}]
        )
        
        # Add relationship from entry1 to entry2
        from app.models.entry import Relation
        entry1.relations = [Relation(type="synonym", ref="word2")]
        
        # Create the entries
        dict_service_with_db.create_entry(entry1)
        dict_service_with_db.create_entry(entry2)
        
        # Get related entries for entry1
        related_entries = dict_service_with_db.get_related_entries("word1")
        
        # Verify related entries
        assert len(related_entries) == 1
        assert related_entries[0].id == "word2"
        
        # Get related entries with specific relation type
        related_entries = dict_service_with_db.get_related_entries("word1", relation_type="synonym")
        assert len(related_entries) == 1
        assert related_entries[0].id == "word2"
        
        # Try a non-existent relation type
        related_entries = dict_service_with_db.get_related_entries("word1", relation_type="antonym")
        assert len(related_entries) == 0
        
        # Add another relation
        entry1.relations.append(Relation(type="antonym", ref="word2"))
        dict_service_with_db.update_entry(entry1)
        
        # Get related entries with the new relation type
        related_entries = dict_service_with_db.get_related_entries("word1", relation_type="antonym")
        assert len(related_entries) == 1
        assert related_entries[0].id == "word2"
    
    @pytest.mark.integration
    def test_entries_by_grammatical_info(self, dict_service_with_db):
        """Test retrieving entries by grammatical information."""
        # Use create_entry to add test entries
        entries = [
            Entry(id_="noun1", lexical_unit={"en": "table"}, senses=[{"id": "s1", "grammatical_info": "noun", "gloss": {"pl": "stół"}}]),
            Entry(id_="verb1", lexical_unit={"en": "run"}, senses=[{"id": "s2", "grammatical_info": "verb", "gloss": {"pl": "biegać"}}]),
            Entry(id_="adj1", lexical_unit={"en": "red"}, senses=[{"id": "s3", "grammatical_info": "adjective", "gloss": {"pl": "czerwony"}}]),
            Entry(id_="noun2", lexical_unit={"en": "book"}, senses=[{"id": "s4", "grammatical_info": "noun", "gloss": {"pl": "książka"}}]),
        ]
        for entry in entries:
            dict_service_with_db.create_entry(entry)
        entry_count = dict_service_with_db.get_entry_count()
        print(f"DEBUG_ENTRY_COUNT: {entry_count}")
        all_entries = dict_service_with_db.list_entries(limit=100, offset=0)[0]
        print(f"DEBUG_ALL_ENTRIES_IDS: {[entry.id for entry in all_entries]}")

        noun_entries = dict_service_with_db.get_entries_by_grammatical_info("noun")
        print(f"DEBUG_NOUN_ENTRIES: {noun_entries}")
        assert len(noun_entries) == 2
        noun_ids = sorted([entry.id for entry in noun_entries])
        assert noun_ids == ["noun1", "noun2"]

        verb_entries = dict_service_with_db.get_entries_by_grammatical_info("verb")
        assert len(verb_entries) == 1
        assert verb_entries[0].id == "verb1"

        adj_entries = dict_service_with_db.get_entries_by_grammatical_info("adjective")
        assert len(adj_entries) == 1
        assert adj_entries[0].id == "adj1"

        adv_entries = dict_service_with_db.get_entries_by_grammatical_info("adverb")
        assert len(adv_entries) == 0

        # Clean up the test entries using individual delete operations
        for entry_id in ["noun1", "verb1", "adj1", "noun2"]:
            try:
                dict_service_with_db.delete_entry(entry_id)
            except Exception:
                pass  # Entry might not exist, which is fine
  