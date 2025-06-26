import os
import sys
import unittest
import logging

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

def add_pagination_fix():
    """Add a fix for the pagination issue."""
    
    # Store the original search_entries method
    original_search_entries = DictionaryService.search_entries
    
    # Define a wrapper function that ensures no duplicates and enforces limits
    def search_entries_wrapper(self, query, fields=None, limit=None, offset=None):
        # Call the original method
        entries, total = original_search_entries(self, query, fields, limit, offset)
        
        # Ensure unique entries by using a dictionary keyed by ID
        entry_map = {entry.id: entry for entry in entries}
        unique_entries = list(entry_map.values())
        
        # Strictly enforce the limit
        if limit is not None and len(unique_entries) > limit:
            logger.debug(f"Enforcing limit: trimming from {len(unique_entries)} to {limit} entries")
            unique_entries = unique_entries[:limit]
        
        return unique_entries, total
    
    # Replace the method with our wrapper
    DictionaryService.search_entries = search_entries_wrapper
    
    logger.info("Added pagination fix to DictionaryService.search_entries")

if __name__ == "__main__":
    add_pagination_fix()
    
    # Test the fix
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database='dictionary'
    )
    
    try:
        connector.connect()
        service = DictionaryService(connector)
        
        # Test with limit
        entries, total = service.search_entries("a", limit=5)
        logger.info(f"Search with limit=5 returned {len(entries)} entries (total: {total})")
        
        # Test with pagination
        entries_page1, _ = service.search_entries("a", limit=3, offset=0)
        entries_page2, _ = service.search_entries("a", limit=3, offset=3)
        entries_page3, _ = service.search_entries("a", limit=3, offset=6)
        
        # Check for duplicates
        page1_ids = {entry.id for entry in entries_page1}
        page2_ids = {entry.id for entry in entries_page2}
        page3_ids = {entry.id for entry in entries_page3}
        
        # Check for overlap
        overlap_1_2 = page1_ids.intersection(page2_ids)
        overlap_1_3 = page1_ids.intersection(page3_ids)
        overlap_2_3 = page2_ids.intersection(page3_ids)
        
        logger.info(f"Page 1: {len(entries_page1)} entries, Page 2: {len(entries_page2)} entries, Page 3: {len(entries_page3)} entries")
        logger.info(f"Overlap between pages 1 and 2: {len(overlap_1_2)}")
        logger.info(f"Overlap between pages 1 and 3: {len(overlap_1_3)}")
        logger.info(f"Overlap between pages 2 and 3: {len(overlap_2_3)}")
        
        # Run the pagination test
        logger.info("Running the pagination test file...")
        os.system("python tests/test_search_pagination.py")
        
    finally:
        connector.disconnect()
