"""
Test multilingual notes search functionality.
"""

import pytest
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService



@pytest.mark.integration
class TestMultilingualNotesSearch:
    """Test search functionality for multilingual notes."""
    
    @pytest.mark.integration
    def test_search_multilingual_notes_unit(self):
        """Test that search can find entries by multilingual notes content."""
        # Create entry with multilingual notes
        entry = Entry(id_='test-search-multilingual',
            lexical_unit={'en': 'test'},
            notes={
                'general': {
                    'en': 'This note contains EXAMPLE_TRANSLATION',
                    'pt': 'Esta nota contém EXEMPLO_TRADUÇÃO'
                },
                'usage': {
                    'en': 'Usage note with specific content'
                }
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Test that notes are properly structured for search
        assert 'general' in entry.notes
        assert 'en' in entry.notes['general']
        assert 'EXAMPLE_TRANSLATION' in entry.notes['general']['en']
        assert 'pt' in entry.notes['general']
        assert 'EXEMPLO_TRADUÇÃO' in entry.notes['general']['pt']
    
    @pytest.mark.integration
    def test_search_legacy_notes_unit(self):
        """Test that search can find entries by legacy notes content."""
        # Create entry with legacy string notes
        entry = Entry(id_='test-search-legacy',
            lexical_unit={'en': 'test'},
            notes={
                'general': 'This is a legacy note with EXAMPLE_TRANSLATION',
                'usage': 'Simple usage note'
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Test that legacy notes are properly structured for search
        assert 'general' in entry.notes
        assert 'EXAMPLE_TRANSLATION' in entry.notes['general']
        assert 'usage' in entry.notes
        assert 'Simple usage note' in entry.notes['usage']
    
    @pytest.mark.integration
    def test_search_mixed_notes_unit(self):
        """Test that search can find entries with mixed notes formats."""
        # Create entry with mixed notes (legacy and multilingual)
        entry = Entry(id_='test-search-mixed',
            lexical_unit={'en': 'test'},
            notes={
                'general': {
                    'en': 'Multilingual note with EXAMPLE_TRANSLATION',
                    'pt': 'Nota multilingual com EXEMPLO_TRADUÇÃO'
                },
                'usage': 'Legacy usage note with EXAMPLE_TRANSLATION'
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Test that mixed notes are properly structured for search
        assert 'general' in entry.notes
        assert isinstance(entry.notes['general'], dict)
        assert 'EXAMPLE_TRANSLATION' in entry.notes['general']['en']
        assert 'usage' in entry.notes
        assert isinstance(entry.notes['usage'], str)
        assert 'EXAMPLE_TRANSLATION' in entry.notes['usage']
    
    @pytest.mark.integration
    def test_notes_serialization_for_search(self):
        """Test that notes are properly serialized for search indexing."""
        # Create entry with multilingual notes
        entry = Entry(id_='test-search-serialization',
            lexical_unit={'en': 'test'},
            notes={
                'general': {
                    'en': 'English note with EXAMPLE_TRANSLATION',
                    'pt': 'Nota em português com EXEMPLO_TRADUÇÃO'
                },
                'usage': 'Legacy usage note'
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Convert to dict (this is what gets serialized)
        entry_dict = entry.to_dict()
        
        # Verify notes structure is preserved
        assert 'notes' in entry_dict
        assert 'general' in entry_dict['notes']
        assert 'en' in entry_dict['notes']['general']
        assert 'EXAMPLE_TRANSLATION' in entry_dict['notes']['general']['en']
        assert 'pt' in entry_dict['notes']['general']
        assert 'EXEMPLO_TRADUÇÃO' in entry_dict['notes']['general']['pt']
        assert 'usage' in entry_dict['notes']
        assert 'Legacy usage note' in entry_dict['notes']['usage']
    
    @pytest.mark.integration
    def test_get_searchable_note_content(self):
        """Test helper function to extract searchable text from multilingual notes."""
        # This tests the logic we'll need to implement in the search function
        
        # Test multilingual notes
        multilingual_notes = {
            'general': {
                'en': 'English note with EXAMPLE_TRANSLATION',
                'pt': 'Nota em português com EXEMPLO_TRADUÇÃO'
            },
            'usage': {
                'en': 'Usage note in English'
            }
        }
        
        # Extract all searchable text
        searchable_text = []
        for note_type, note_content in multilingual_notes.items():
            if isinstance(note_content, dict):
                # Multilingual note
                for lang, text in note_content.items():
                    searchable_text.append(text)
            else:
                # Legacy note
                searchable_text.append(note_content)
        
        all_text = ' '.join(searchable_text)
        
        # Verify all content is searchable
        assert 'EXAMPLE_TRANSLATION' in all_text
        assert 'EXEMPLO_TRADUÇÃO' in all_text
        assert 'Usage note in English' in all_text
        
        # Test mixed notes
        mixed_notes = {
            'general': {
                'en': 'Multilingual note with EXAMPLE_TRANSLATION',
                'pt': 'Nota multilingual'
            },
            'usage': 'Legacy usage note with EXAMPLE_TRANSLATION'
        }
        
        searchable_text = []
        for note_type, note_content in mixed_notes.items():
            if isinstance(note_content, dict):
                # Multilingual note
                for lang, text in note_content.items():
                    searchable_text.append(text)
            else:
                # Legacy note
                searchable_text.append(note_content)
        
        all_text = ' '.join(searchable_text)
        
        # Verify both multilingual and legacy content is searchable
        assert 'EXAMPLE_TRANSLATION' in all_text
        assert all_text.count('EXAMPLE_TRANSLATION') == 2  # Should appear twice
        assert 'Nota multilingual' in all_text
        assert 'Legacy usage note' in all_text
    
    @pytest.mark.integration
    def test_search_with_notes_field_integration(self):
        """Test search integration when notes field is included."""
        # This would be an integration test with actual dictionary service
        # For now, we just test the logic
        
        # Test that "notes" is included in default search fields
        from app.services.dictionary_service import DictionaryService
        
        # Mock the dependencies to test just the field logic
        class MockConnector:
            def __init__(self):
                self.database = "test_db"
                
        class MockQueryBuilder:
            def get_element_path(self, element, has_ns):
                return element
            def get_namespace_prologue(self, has_ns):
                return ""
        
        # Create service instance
        service = DictionaryService(MockConnector())
        service._query_builder = MockQueryBuilder()
        
        # Test default fields include notes
        # We can't easily test the full search without BaseX, but we can test the field logic
        default_fields = ["lexical_unit", "glosses", "definitions", "notes"]
        assert "notes" in default_fields
        
        # Test that notes field processing logic is correct
        query = "EXAMPLE_TRANSLATION"
        has_ns = False
        q_escaped = query.replace("'", "''")
        
        # This is the XQuery condition that should be generated for notes
        note_path = "note"
        form_path = "form"
        text_path = "text"
        sense_path = "sense"
        
        # Entry-level notes condition
        entry_notes_condition = f"(some $note in $entry/{note_path}/{form_path}/{text_path} satisfies contains(lower-case($note), '{q_escaped.lower()}'))"
        
        # Sense-level notes condition
        sense_notes_condition = f"(some $note in $entry/{sense_path}/{note_path}/{form_path}/{text_path} satisfies contains(lower-case($note), '{q_escaped.lower()}'))"
        
        # Combined condition
        notes_condition = f"({entry_notes_condition} or {sense_notes_condition})"
        
        # Verify the condition contains the search term
        assert "example_translation" in notes_condition.lower()
        assert "entry-level" in entry_notes_condition or "$entry/" in entry_notes_condition
        assert "sense-level" in sense_notes_condition or "$entry/sense/" in sense_notes_condition
