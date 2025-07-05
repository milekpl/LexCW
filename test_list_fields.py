"""Simple test to verify the list error fix."""

from app.models.entry import Entry

def test_entry_with_list_fields():
    """Test entry creation with various field types that might become lists."""
    
    # Test with potentially problematic data
    entry_data = {
        'id_': 'test_entry',
        'lexical_unit': ['headword_text'],  # List instead of dict
        'notes': ['note_text'],            # List instead of dict  
        'pronunciations': ['pronunciation'], # List instead of dict
        'custom_fields': ['field_value'],   # List instead of dict
        'citations': ['citation_text'],     # List of strings
        'variants': []                      # Empty list
    }
    
    try:
        entry = Entry(**entry_data)
        print("Entry created successfully!")
        print(f"lexical_unit type: {type(entry.lexical_unit)}")
        print(f"notes type: {type(entry.notes)}")
        print(f"pronunciations type: {type(entry.pronunciations)}")
        print(f"custom_fields type: {type(entry.custom_fields)}")
        print(f"citations type: {type(entry.citations)}")
        
        # Test calling .items() on each to ensure no errors
        try:
            list(entry.lexical_unit.items())
            print("lexical_unit.items() works")
        except Exception as e:
            print(f"lexical_unit.items() error: {e}")
            
        try:
            list(entry.notes.items())
            print("notes.items() works")
        except Exception as e:
            print(f"notes.items() error: {e}")
            
        try:
            list(entry.pronunciations.items())
            print("pronunciations.items() works")
        except Exception as e:
            print(f"pronunciations.items() error: {e}")
            
        try:
            list(entry.custom_fields.items())
            print("custom_fields.items() works")
        except Exception as e:
            print(f"custom_fields.items() error: {e}")
            
    except Exception as e:
        print(f"Error creating entry: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_entry_with_list_fields()
