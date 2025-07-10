"""
Unit test specifically focused on testing search pagination in DictionaryService.

This test ensures that pagination works correctly in the search_entries method.
"""

import os
import sys
import unittest
import logging

import pytest

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)



@pytest.mark.integration
class TestSearchPagination(unittest.TestCase):
    """Test the search pagination functionality of DictionaryService."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once before all tests."""
        # BaseX connection parameters - use the same as the live app
        cls.basex_host = 'localhost'
        cls.basex_port = 1984
        cls.basex_username = 'admin'
        cls.basex_password = 'admin'
        cls.basex_database = 'dictionary'  # This is what's used in the app
        
        # Create a BaseX connector without connection pooling for tests
        cls.connector = BaseXConnector(
            host=cls.basex_host,
            port=cls.basex_port,
            username=cls.basex_username,
            password=cls.basex_password,
            database=cls.basex_database,
            
        )
        
        # Connect to BaseX server
        try:
            cls.connector.connect()
            # Create a dictionary service
            cls.service = DictionaryService(cls.connector)
            # Log setup information
            logger.info("Test setup complete with database: %s", cls.basex_database)
            
            # Check that the database exists and has entries
            try:
                entry_count = cls.service.count_entries()
                logger.info("Database has %d entries", entry_count)
                cls.test_enabled = entry_count > 0
            except Exception as e:
                logger.error("Error checking entry count: %s", str(e))
                cls.test_enabled = False
                
        except Exception as e:
            logger.error("Error setting up test: %s", str(e))
            cls.test_enabled = False

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Disconnect from BaseX server
        if hasattr(cls, 'connector'):
            try:
                cls.connector.disconnect()
                logger.info("Test teardown complete")
            except Exception as e:
                logger.error("Error during teardown: %s", str(e))

    def setUp(self):
        """Skip tests if database is not available."""
        if not getattr(self.__class__, 'test_enabled', False):
            self.skipTest("BaseX database not available or empty")

    @pytest.mark.integration
    def test_search_with_limit_only(self):
        """Test that search respects the limit parameter even without an offset."""
        limit = 5
        entries, total = self.service.search_entries("a", limit=limit)
        
        logger.info(f"Search with limit={limit} returned {len(entries)} entries (total: {total})")
        
        # Verify that the number of entries doesn't exceed the limit
        self.assertLessEqual(len(entries), limit, 
                             f"Expected at most {limit} entries, got {len(entries)}")
        
        # Verify we got entries if there were any matches
        if total > 0:
            self.assertTrue(len(entries) > 0, "Expected at least one entry when total > 0")
    
    @pytest.mark.integration
    def test_search_with_limit_and_offset(self):
        """Test that search respects both limit and offset parameters."""
        # Only run this test if we have enough entries
        total_entries = self.service.count_entries()
        if total_entries < 10:
            self.skipTest("Not enough entries for pagination test")
        
        # Search for a common pattern like 'a' that should match many entries
        limit = 3
        offset = 0
        
        # Get the first page
        entries_page1, total = self.service.search_entries("a", limit=limit, offset=offset)
        
        # Get the second page
        entries_page2, _ = self.service.search_entries("a", limit=limit, offset=limit)
        
        # Get the third page
        entries_page3, _ = self.service.search_entries("a", limit=limit, offset=limit*2)
        
        logger.info(f"Page 1: {len(entries_page1)} entries, Page 2: {len(entries_page2)} entries, Page 3: {len(entries_page3)} entries (total: {total})")
        
        # Check that each page has no more than the limit
        self.assertLessEqual(len(entries_page1), limit, f"Page 1 should have at most {limit} entries")
        self.assertLessEqual(len(entries_page2), limit, f"Page 2 should have at most {limit} entries")
        self.assertLessEqual(len(entries_page3), limit, f"Page 3 should have at most {limit} entries")
        
        # Check that we have no duplicate entries between pages
        page1_ids = {entry.id for entry in entries_page1}
        page2_ids = {entry.id for entry in entries_page2}
        page3_ids = {entry.id for entry in entries_page3}
        
        # No overlap between pages
        self.assertEqual(len(page1_ids.intersection(page2_ids)), 0, "Found duplicate entries between page 1 and 2")
        self.assertEqual(len(page1_ids.intersection(page3_ids)), 0, "Found duplicate entries between page 1 and 3")
        self.assertEqual(len(page2_ids.intersection(page3_ids)), 0, "Found duplicate entries between page 2 and 3")
    
    @pytest.mark.integration
    def test_pagination_consistency(self):
        """Test that pagination is consistent (same entries appear on same pages)."""
        # Only run this test if we have enough entries
        total_entries = self.service.count_entries()
        if total_entries < 10:
            self.skipTest("Not enough entries for pagination test")
        
        limit = 5
        offset = 5
        
        # Perform the same search twice
        entries1, _ = self.service.search_entries("a", limit=limit, offset=offset)
        entries2, _ = self.service.search_entries("a", limit=limit, offset=offset)
        
        # Get the IDs from both searches
        ids1 = [entry.id for entry in entries1]
        ids2 = [entry.id for entry in entries2]
        
        logger.info(f"First search: {len(ids1)} entries, Second search: {len(ids2)} entries")
        logger.info(f"First page IDs: {ids1}")
        logger.info(f"Second page IDs: {ids2}")
        
        # Both searches should return the same entries in the same order
        self.assertEqual(ids1, ids2, "Pagination should return the same entries in the same order")
    
    @pytest.mark.integration
    def test_search_with_specific_limit(self):
        """Test search with a very specific limit to ensure precision."""
        # Get total entries that match a common pattern
        _, total = self.service.search_entries("a")
        
        if total < 2:
            self.skipTest("Not enough matching entries for this test")
        
        # Try different limits and verify results
        for limit in [1, 2, total-1, total]:
            entries, _ = self.service.search_entries("a", limit=limit)
            
            logger.info(f"Search with limit={limit} returned {len(entries)} entries")
            
            # Check that the number of entries matches the limit (or total if limit > total)
            expected_count = min(limit, total)
            self.assertEqual(len(entries), expected_count, 
                            f"Expected exactly {expected_count} entries for limit={limit}, got {len(entries)}")


if __name__ == "__main__":
    unittest.main()
