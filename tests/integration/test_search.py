"""
Tests for the search functionality in the DictionaryService.
Uses real BaseX backend via shared fixtures.
"""

import os
import pytest
import logging
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.services.dictionary_service import DictionaryService

logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestSearch:
    """Test the search functionality of the DictionaryService."""

    @pytest.fixture(autouse=True)
    def setup_search_data(self, dict_service_with_db: DictionaryService):
        """Initialize service and seed data for each test."""
        self.service = dict_service_with_db
        # Seed additional entries for search testing
        self._create_test_entries()

    def _create_test_entries(self) -> None:
        """Create test entries for search testing."""
        # Note: basex_test_connector already adds 'test_entry_1'
        
        # Entry test_entry_2 (matching the legacy file content)
        entry2 = Entry(
            id_="test_entry_2",
            lexical_unit={"en": "example"},
            senses=[
                Sense(
                    id_="2234",
                    gloss={"pl": "przykład"},
                    definition={"en": "A representative instance"}
                )
            ]
        )
        
        # Entry with multiple senses
        entry_bank = Entry(
            id_="multiple_senses",
            lexical_unit={"en": "bank"},
            grammatical_info="noun",
            senses=[
                Sense(
                    id_="bank_sense1",
                    gloss={"pl": "bank (instytucja finansowa)"},
                    definition={"en": "A financial institution"},
                    examples=[
                        Example(
                            id_="bank_example1",
                            form={"en": "I need to go to the bank."},
                            translation={"pl": "Muszę iść do banku."},
                        )
                    ],
                ),
                Sense(
                    id_="bank_sense2",
                    gloss={"pl": "brzeg (rzeki)"},
                    definition={"en": "The land alongside a river or lake"},
                    examples=[
                        Example(
                            id_="bank_example2",
                            form={"en": "We sat on the river bank."},
                            translation={"pl": "Siedzieliśmy na brzegu rzeki."},
                        )
                    ],
                ),
            ],
        )
        
        # Entry with similar words
        entry_testing = Entry(
            id_="similar_word_1",
            lexical_unit={"en": "testing"},
            grammatical_info="verb",
            senses=[
                Sense(
                    id_="testing_sense",
                    gloss={"pl": "testowanie"},
                    definition={"en": "The action of testing something"},
                )
            ],
        )
        
        entry_tester = Entry(
            id_="similar_word_2",
            lexical_unit={"en": "tester"},
            grammatical_info="noun",
            senses=[
                Sense(
                    id_="tester_sense",
                    gloss={"pl": "tester"},
                    definition={"en": "A person who tests something"},
                )
            ],
        )
        
        entry_cafe = Entry(
            id_="special_chars",
            lexical_unit={"en": "café"},
            grammatical_info="noun",
            senses=[
                Sense(
                    id_="cafe_sense",
                    gloss={"pl": "kawiarnia"},
                    definition={"en": "A small restaurant selling light meals and drinks"},
                )
            ],
        )
        
        for e in [entry2, entry_bank, entry_testing, entry_tester, entry_cafe]:
            try:
                # Use create_entry which is safe if it doesn't exist
                if not self.service.entry_exists(e.id):
                    self.service.create_entry(e)
            except Exception as ex:
                logger.warning(f"Error seeding search data for {e.id}: {ex}")

    def test_basic_search(self):
        """Test basic search functionality."""
        # Search for entries containing "test"
        entries, total = self.service.search_entries("test")
        
        # Should find: 
        # 1. test_entry_1 (from connector)
        # 2. similar_word_1 (testing)
        # 3. similar_word_2 (tester)
        assert total >= 3
        
        entry_ids = [entry.id for entry in entries]
        assert "test_entry_1" in entry_ids
        assert "similar_word_1" in entry_ids
        assert "similar_word_2" in entry_ids

    def test_search_exact_match(self):
        """Test searching for exact matches."""
        # Search for entries exactly matching "test"
        entries, total = self.service.search_entries("test")
        assert "test_entry_1" in [entry.id for entry in entries]

        # Search for "example" which is in test_entry_2
        entries, total = self.service.search_entries("example")
        assert total >= 1
        assert any(e.id == "test_entry_2" for e in entries)

    def test_search_by_field(self):
        """Test searching in specific fields."""
        # Search only in lexical_unit field
        entries, total = self.service.search_entries("test", fields=["lexical_unit"])
        assert total > 0
        assert any(e.id == "test_entry_1" for e in entries)

        # Search only in glosses field
        # test_entry_1 has "test" in gloss (from conftest.py's sample LIFT)
        # Actually conftest.py adds: <gloss lang="pl"><text>test</text></gloss>
        entries, total = self.service.search_entries("test", fields=["glosses"])
        assert total > 0

        # Search in both glosses and definitions
        # test_entry_1 has "A test entry" in definition
        entries, total = self.service.search_entries(
            "test", fields=["glosses", "definitions"]
        )
        assert total > 0
        assert any(entry.id == "test_entry_1" for entry in entries)

    def test_search_special_characters(self):
        """Test searching with special characters."""
        # Search for "café"
        entries, total = self.service.search_entries("café")
        assert total > 0
        assert any(e.id == "special_chars" for e in entries)

    def test_search_pagination(self):
        """Test search pagination."""
        # Search for entries with at least 2 results for pagination testing
        query = "test"

        # Get all matching entries first to ensure we have enough
        all_matching, total = self.service.search_entries(query)
        assert total >= 2, f"Expected at least 2 matching entries for pagination test, got {total}"

        # Test pagination by getting entries with different offsets
        entries_page1, _ = self.service.search_entries(query, limit=1, offset=0)
        entries_page2, _ = self.service.search_entries(query, limit=1, offset=1)

        assert len(entries_page1) == 1, f"Page 1 should return 1 entry, got {len(entries_page1)}"
        assert len(entries_page2) == 1, f"Page 2 should return 1 entry, got {len(entries_page2)}"

        # Different offsets should return different entries
        # (Note: if there's only 1 unique entry matching, this may fail)
        page1_ids = {e.id for e in entries_page1}
        page2_ids = {e.id for e in entries_page2}
        assert page1_ids != page2_ids, f"Different pages should return different entries: page1={page1_ids}, page2={page2_ids}"

    def test_search_no_results(self):
        """Test search with no matching results."""
        entries, total = self.service.search_entries("nonexistent_word_xyz_123")
        assert total == 0
        assert len(entries) == 0

    def test_search_after_update(self):
        """Test that search results update after modifying entries."""
        unique_id = "search_update_test"
        
        # Ensure it doesn't exist
        if self.service.entry_exists(unique_id):
            self.service.delete_entry(unique_id)
            
        # Create new entry
        entry = Entry(
            id_=unique_id,
            lexical_unit={"en": "uniqueword"},
            senses=[{"id": "s1", "definition": {"en": "desc"}}]
        )
        self.service.create_entry(entry)

        # Search for unique word
        entries, total = self.service.search_entries("uniqueword")
        # Database may contain other entries; ensure the created entry is present
        assert total >= 1
        assert any(e.id == unique_id for e in entries)

        # Update entry
        entry.lexical_unit = {"en": "changedword"}
        self.service.update_entry(entry)

        # Old word should not find anything
        _, total_old = self.service.search_entries("uniqueword")
        assert total_old == 0

        # New word should find it
        entries, total_new = self.service.search_entries("changedword")
        assert total_new >= 1
        assert any(e.id == unique_id for e in entries)
        
    def test_search_via_api(self, client):
        """Test search via the API endpoint (ensures client fixture works)."""
        # Search for 'test' via the API
        response = client.get('/api/test-search?query=test')
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'entries' in data
        assert data['total'] >= 3
        entry_ids = [e['id'] for e in data['entries']]
        assert "test_entry_1" in entry_ids