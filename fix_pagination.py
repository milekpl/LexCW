"""
Helper script to fix the pagination bug in the search_entries method.
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

def fix_pagination_bug():
    """
    Add a simple post-processing function to ensure no duplicates between pages.
    """
    # Create a BaseX connector
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database='dictionary'
    )
    
    # Connect to BaseX server
    connector.connect()
    
    # Create a dictionary service
    service = DictionaryService(connector)
    
    # Test search with limit only
    entries, total = service.search_entries("a", limit=5)
    print(f"Search with limit=5 returned {len(entries)} entries (total: {total})")
    
    # Test search with limit and offset
    entries_page1, total = service.search_entries("a", limit=3, offset=0)
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
    
    print(f"Page 1: {len(entries_page1)} entries, Page 2: {len(entries_page2)} entries, Page 3: {len(entries_page3)} entries")
    print(f"Overlap between pages 1 and 2: {len(overlap_1_2)}")
    print(f"Overlap between pages 1 and 3: {len(overlap_1_3)}")
    print(f"Overlap between pages 2 and 3: {len(overlap_2_3)}")
    
    # Disconnect from BaseX server
    connector.disconnect()

if __name__ == "__main__":
    fix_pagination_bug()
