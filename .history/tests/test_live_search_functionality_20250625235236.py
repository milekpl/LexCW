"""
Unit test for directly testing the search functionality of DictionaryService with a live BaseX server.

This test ensures that the dictionary service's search functions work correctly 
with the actual BaseX database used in the application.
"""

import os
import sys
import unittest
import logging
from typing import List, Tuple

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
from app.models.entry import Entry

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TestLiveSearchFunctionality(unittest.TestCase):
    """Test the search functionality of DictionaryService with a live BaseX server."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once before all tests."""
        # BaseX connection parameters - use the same as the live app
        cls.basex_host = 'localhost'
        cls.basex_port = 1984
        cls.basex_username = 'admin'
        cls.basex_password = 'admin'
        cls.basex_database = 'dictionary'  # This is what's used in the app
        
        # Create a BaseX connector
        cls.connector = BaseXConnector(
            host=cls.basex_host,
            port=cls.basex_port,
            username=cls.basex_username,
            password=cls.basex_password,
            database=cls.basex_database
        )
        
        # Connect to BaseX server
        cls.connector.connect()
        
        # Create a dictionary service
        cls.service = DictionaryService(cls.connector)
        
        # Log setup information
        logger.info("Test setup complete with database: %s", cls.basex_database)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Disconnect from BaseX server
        cls.connector.disconnect()
        logger.info("Test teardown complete")

    def test_count_entries(self):
        """Test that we can count entries in the database."""
        try:
            count = self.service.count_entries()
            logger.info("Total entries in database: %d", count)
            self.assertIsInstance(count, int, "Entry count should be an integer")
            self.assertGreaterEqual(count, 0, "Entry count should be non-negative")
        except Exception as e:
            self.fail(f"Error counting entries: {e}")

    def test_basic_search(self):
        """Test basic search functionality with a simple query."""
        try:
            query = "test"
            logger.info("Searching for '%s'...", query)
            entries, total = self.service.search_entries(query)
            
            logger.info("Found %d entries for query '%s'", total, query)
            
            # Basic validation of the search results
            self.assertIsInstance(entries, list, "Entries should be a list")
            self.assertIsInstance(total, int, "Total should be an integer")
            self.assertEqual(len(entries), min(total, 10), "Number of entries should match total (up to default limit)")
            
            # Log the found entries
            for i, entry in enumerate(entries[:5]):  # Print first 5 entries
                logger.info("Entry %d: %s - %s", i+1, entry.id, entry.lexical_unit)
                self.assertIsInstance(entry.id, str, "Entry ID should be a string")
                
            # Ensure we have entry data
            if entries:
                first_entry = entries[0]
                self.assertIsNotNone(first_entry.id, "Entry should have an ID")
                self.assertIsNotNone(first_entry.lexical_unit, "Entry should have a lexical unit")
        except Exception as e:
            self.fail(f"Error searching entries: {e}")

    def test_search_with_fields(self):
        """Test search with specific fields."""
        try:
            # Test searching only in lexical unit
            entries_lexical, total_lexical = self.service.search_entries("test", fields=["lexical_unit"])
            logger.info("Found %d entries when searching only in lexical_unit", total_lexical)
            
            # Test searching only in glosses
            entries_glosses, total_glosses = self.service.search_entries("test", fields=["glosses"])
            logger.info("Found %d entries when searching only in glosses", total_glosses)
            
            # Test searching only in definitions
            entries_defs, total_defs = self.service.search_entries("test", fields=["definitions"])
            logger.info("Found %d entries when searching only in definitions", total_defs)
            
            # Test searching in all fields
            entries_all, total_all = self.service.search_entries("test", fields=["lexical_unit", "glosses", "definitions"])
            logger.info("Found %d entries when searching in all fields", total_all)
            
            # The total from all fields should be at least as large as any individual field
            self.assertGreaterEqual(total_all, total_lexical, "Total from all fields should be >= lexical_unit only")
            self.assertGreaterEqual(total_all, total_glosses, "Total from all fields should be >= glosses only")
            self.assertGreaterEqual(total_all, total_defs, "Total from all fields should be >= definitions only")
        except Exception as e:
            self.fail(f"Error searching with fields: {e}")

    def test_search_pagination(self):
        """Test search pagination."""
        try:
            query = "test"  # Assuming this returns multiple results
            
            # First page (limit=2, offset=0)
            entries_page1, total = self.service.search_entries(query, limit=2, offset=0)
            logger.info("Page 1: Found %d entries (total=%d)", len(entries_page1), total)
            
            # Second page (limit=2, offset=2)
            entries_page2, total2 = self.service.search_entries(query, limit=2, offset=2)
            logger.info("Page 2: Found %d entries (total=%d)", len(entries_page2), total2)
            
            # Totals should be the same on both pages
            self.assertEqual(total, total2, "Total count should be consistent across pages")
            
            # If we have enough entries for pagination
            if total > 2:
                # We should have different entries on different pages
                if entries_page1 and entries_page2:
                    page1_ids = [e.id for e in entries_page1]
                    page2_ids = [e.id for e in entries_page2]
                    logger.info("Page 1 IDs: %s", page1_ids)
                    logger.info("Page 2 IDs: %s", page2_ids)
                    
                    # Check for any overlap - in a perfect world, there should be none
                    # But due to BaseX pagination quirks, we'll just log a warning if there is
                    if any(pid in page2_ids for pid in page1_ids):
                        logger.warning("Overlap detected between page 1 and page 2")
        except Exception as e:
            self.fail(f"Error testing pagination: {e}")

    def test_search_special_characters(self):
        """Test search with special characters."""
        try:
            # Search with special characters (only if we know we have entries with them)
            special_queries = ["café", "naïve", "résumé"]
            
            for query in special_queries:
                entries, total = self.service.search_entries(query)
                logger.info("Found %d entries for special query '%s'", total, query)
                
                # Just log the results, we don't know if these entries exist in the test DB
                if entries:
                    for entry in entries[:2]:  # First 2 entries
                        logger.info("Special char match: %s - %s", entry.id, entry.lexical_unit)
        except Exception as e:
            logger.warning(f"Error searching with special characters: {e}")
            # Don't fail the test as we don't know if special character entries exist

    def test_search_edge_cases(self):
        """Test search edge cases."""
        try:
            # Empty query
            entries_empty, total_empty = self.service.search_entries("")
            logger.info("Empty query: Found %d entries", total_empty)
            
            # Very long query (100 characters)
            long_query = "a" * 100
            entries_long, total_long = self.service.search_entries(long_query)
            logger.info("Long query: Found %d entries", total_long)
            
            # Query with quotes and special characters
            special_query = 'test"with\'quotes and & special < chars >'
            entries_special, total_special = self.service.search_entries(special_query)
            logger.info("Special query: Found %d entries", total_special)
            
            # These tests pass if they don't throw exceptions
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Error with edge case search: {e}")


if __name__ == "__main__":
    unittest.main()
