#!/usr/bin/env python3
"""
Debug script to understand pagination behavior.
"""

import logging
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_pagination():
    """Debug pagination behavior"""
    config = Config()
    connector = BaseXConnector(config.BASEX_HOST, config.BASEX_PORT, config.BASEX_USERNAME, config.BASEX_PASSWORD)
    connector.database = config.BASEX_DATABASE
    service = DictionaryService(connector)
    
    # Test the pagination behavior
    query = "a"
    limit = 3
    
    print(f"Testing pagination with query '{query}' and limit {limit}")
    
    # Page 1 (offset=0)
    entries_page1, total = service.search_entries(query, limit=limit, offset=0)
    print(f"Page 1 (offset=0): {len(entries_page1)} entries")
    for i, entry in enumerate(entries_page1):
        print(f"  {i+1}. ID: {entry.id}, Headword: {entry.headword}")
    
    # Page 2 (offset=3)  
    entries_page2, _ = service.search_entries(query, limit=limit, offset=limit)
    print(f"Page 2 (offset=3): {len(entries_page2)} entries")
    for i, entry in enumerate(entries_page2):
        print(f"  {i+1}. ID: {entry.id}, Headword: {entry.headword}")
    
    # Check for duplicates
    page1_ids = {entry.id for entry in entries_page1}
    page2_ids = {entry.id for entry in entries_page2}
    duplicates = page1_ids.intersection(page2_ids)
    
    if duplicates:
        print(f"DUPLICATES FOUND: {duplicates}")
    else:
        print("No duplicates found")
    
    print(f"Total entries matching '{query}': {total}")

if __name__ == "__main__":
    debug_pagination()
