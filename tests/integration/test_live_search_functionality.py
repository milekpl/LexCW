"""
Integration tests for DictionaryService search functionality.
Uses real BaseX backend via shared fixtures.
"""

import pytest
import logging
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService

logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestLiveSearchFunctionality:
    """Test the search functionality of DictionaryService with a real BaseX server."""

    @pytest.fixture(autouse=True)
    def setup_method(self, dict_service_with_db: DictionaryService):
        """Initialize service for each test."""
        self.service = dict_service_with_db

    def test_count_entries(self):
        """Test that we can count entries in the database."""
        count = self.service.count_entries()
        logger.info("Total entries in database: %d", count)
        assert isinstance(count, int)
        assert count >= 0

    def test_basic_search(self):
        """Test basic search functionality with a simple query."""
        query = "test"
        logger.info("Searching for '%s'...", query)
        # basex_test_connector adds test_entry_1 with lexical unit 'test'
        entries, total = self.service.search_entries(query, limit=10)
        
        logger.info("Found %d entries for query '%s' (total=%d)", len(entries), query, total)
        
        assert isinstance(entries, list)
        assert isinstance(total, int)
        assert len(entries) <= 10
        
        if entries:
            first_entry = entries[0]
            assert first_entry.id is not None
            assert first_entry.lexical_unit is not None
            # Verify it found our sample entry
            assert any(e.id == 'test_entry_1' for e in entries)

    def test_search_with_fields(self):
        """Test search with specific fields."""
        # Test searching only in lexical unit
        _, total_lexical = self.service.search_entries("test", fields=["lexical_unit"])
        
        # Test searching only in glosses
        _, total_glosses = self.service.search_entries("test", fields=["glosses"])
        
        # Test searching only in definitions
        _, total_defs = self.service.search_entries("test", fields=["definitions"])
        
        # Test searching in all fields
        _, total_all = self.service.search_entries("test", fields=["lexical_unit", "glosses", "definitions"])
        
        # The total from all fields should be at least as large as any individual field
        assert total_all >= total_lexical
        assert total_all >= total_glosses
        assert total_all >= total_defs

    def test_search_pagination(self):
        """Test search pagination."""
        query = "test"
        
        # First page
        entries_page1, total = self.service.search_entries(query, limit=1, offset=0)
        
        # Second page
        entries_page2, total2 = self.service.search_entries(query, limit=1, offset=1)
        
        assert total == total2
        
        if total > 1 and entries_page1 and entries_page2:
            assert entries_page1[0].id != entries_page2[0].id

    def test_search_special_characters(self):
        """Test search with special characters."""
        # This test ensures no crash occurs with special chars
        special_queries = ["café", "naïve", "résumé"]
        
        for query in special_queries:
            entries, total = self.service.search_entries(query)
            assert isinstance(total, int)

    def test_search_edge_cases(self):
        """Test search edge cases."""
        # Empty query
        _, total_empty = self.service.search_entries("")
        assert isinstance(total_empty, int)
        
        # Very long query
        long_query = "a" * 100
        _, total_long = self.service.search_entries(long_query)
        assert isinstance(total_long, int)
        
        # Query with quotes
        safe_special_query = 'test with "quotes"'
        _, total_special = self.service.search_entries(safe_special_query)
        assert isinstance(total_special, int)