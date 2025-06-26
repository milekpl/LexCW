"""
A simple monkey patch to fix the pagination issue in the search_entries method.
"""

def fix_search_entries(original_method):
    """
    Create a wrapper around the original search_entries method to ensure no duplicates.
    """
    def wrapper(self, query, fields=None, limit=None, offset=None):
        # Call the original method
        entries, total = original_method(self, query, fields, limit, offset)
        
        # Remove duplicates by creating a dictionary keyed by entry ID
        entry_map = {entry.id: entry for entry in entries}
        unique_entries = list(entry_map.values())
        
        # If we have more entries than the limit, trim them
        if limit is not None and len(unique_entries) > limit:
            unique_entries = unique_entries[:limit]
            
        return unique_entries, total
    
    return wrapper

# Apply the fix to the DictionaryService.search_entries method
from app.services.dictionary_service import DictionaryService
DictionaryService.search_entries = fix_search_entries(DictionaryService.search_entries)
