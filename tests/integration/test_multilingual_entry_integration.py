"""
Integration tests for multilingual entry editing workflow.
"""

import json
import pytest

from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data



@pytest.mark.integration
class TestMultilingualEntryIntegration:
    """Test the complete workflow of multilingual entry editing."""
    
    @pytest.mark.integration
    def test_entry_creation_with_multilingual_notes(self):
        """Test creating an entry with multilingual notes."""
        # Simulate form data with multilingual notes
        form_data = {
            'lexical_unit[en]': 'house',
            'lexical_unit[pt]': 'casa',
            'notes[general][en][text]': 'A building for human habitation',
            'notes[general][pt][text]': 'Um edifício para habitação humana',
            'notes[usage][en][text]': 'Common noun',
            'notes[usage][pt][text]': 'Substantivo comum'
        }
        
        # Process the form data
        empty_entry_data = {}
        merged_data = merge_form_data_with_entry_data(form_data, empty_entry_data)
        
        # Create entry from merged data
        entry = Entry.from_dict(merged_data)
        
        # Verify multilingual notes are properly set
        assert 'general' in entry.notes
        assert 'usage' in entry.notes
        assert entry.notes['general']['en'] == 'A building for human habitation'
        assert entry.notes['general']['pt'] == 'Um edifício para habitação humana'
        assert entry.notes['usage']['en'] == 'Common noun'
        assert entry.notes['usage']['pt'] == 'Substantivo comum'
        
        # Verify lexical unit is properly set
        assert entry.lexical_unit['en'] == 'house'
        assert entry.lexical_unit['pt'] == 'casa'
    
    @pytest.mark.integration
    def test_entry_update_with_multilingual_notes(self):
        """Test updating an existing entry with multilingual notes."""
        # Create an existing entry
        existing_entry = Entry(id_='test-entry-1',
            lexical_unit={'en': 'old_house'},
            notes={'general': {'en': 'Old note'}}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        existing_data = existing_entry.to_dict()
        
        # Simulate form data for update
        form_data = {
            'lexical_unit[en]': 'house',
            'lexical_unit[pt]': 'casa',
            'notes[general][en][text]': 'Updated English note',
            'notes[general][pt][text]': 'Nota em português',
            'notes[etymology][en][text]': 'From Old English hus'
        }
        
        # Process the form data
        merged_data = merge_form_data_with_entry_data(form_data, existing_data)
        
        # Create updated entry from merged data
        updated_entry = Entry.from_dict(merged_data)
        updated_entry.id = existing_entry.id
        
        # Verify the entry was updated correctly
        assert updated_entry.id == 'test-entry-1'
        assert updated_entry.lexical_unit['en'] == 'house'
        assert updated_entry.lexical_unit['pt'] == 'casa'
        
        # Verify multilingual notes are properly updated
        assert 'general' in updated_entry.notes
        assert 'etymology' in updated_entry.notes
        assert updated_entry.notes['general']['en'] == 'Updated English note'
        assert updated_entry.notes['general']['pt'] == 'Nota em português'
        assert updated_entry.notes['etymology']['en'] == 'From Old English hus'
    
    @pytest.mark.integration
    def test_entry_roundtrip_to_dict_from_dict(self):
        """Test that entry with multilingual notes survives to_dict/from_dict roundtrip."""
        # Create an entry with multilingual notes
        original_entry = Entry(id_='test-entry-roundtrip',
            lexical_unit={'en': 'book', 'pt': 'livro'},
            notes={
                'general': {
                    'en': 'A written work',
                    'pt': 'Uma obra escrita'
                },
                'usage': {
                    'en': 'Can be physical or digital',
                    'pt': 'Pode ser físico ou digital'
                }
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Convert to dict and back
        entry_dict = original_entry.to_dict()
        reconstructed_entry = Entry.from_dict(entry_dict)
        
        # Verify the roundtrip preserved all data
        assert reconstructed_entry.id == original_entry.id
        assert reconstructed_entry.lexical_unit == original_entry.lexical_unit
        assert reconstructed_entry.notes == original_entry.notes
        
        # Verify specific multilingual notes
        assert reconstructed_entry.notes['general']['en'] == 'A written work'
        assert reconstructed_entry.notes['general']['pt'] == 'Uma obra escrita'
        assert reconstructed_entry.notes['usage']['en'] == 'Can be physical or digital'
        assert reconstructed_entry.notes['usage']['pt'] == 'Pode ser físico ou digital'
    
    @pytest.mark.integration
    def test_entry_mixed_notes_legacy_and_multilingual(self):
        """Test that entry can handle both legacy (string) and multilingual (dict) notes."""
        # Create entry with mixed notes structure
        entry_data = {
            'id': 'test-mixed-notes',
            'lexical_unit': {'en': 'test'},
            'notes': {
                'legacy_note': 'Simple string note',  # Legacy format
                'multilingual_note': {  # New multilingual format
                    'en': 'English text',
                    'pt': 'Portuguese text'
                }
            }
        }
        
        # Create entry from mixed data
        entry = Entry.from_dict(entry_data)
        
        # Verify both types of notes are preserved
        assert entry.notes['legacy_note'] == 'Simple string note'
        assert entry.notes['multilingual_note']['en'] == 'English text'
        assert entry.notes['multilingual_note']['pt'] == 'Portuguese text'
        
        # Verify roundtrip preserves mixed structure
        roundtrip_dict = entry.to_dict()
        roundtrip_entry = Entry.from_dict(roundtrip_dict)
        
        assert roundtrip_entry.notes['legacy_note'] == 'Simple string note'
        assert roundtrip_entry.notes['multilingual_note']['en'] == 'English text'
        assert roundtrip_entry.notes['multilingual_note']['pt'] == 'Portuguese text'
    
    @pytest.mark.integration
    def test_entry_with_empty_multilingual_notes(self):
        """Test handling of empty multilingual notes."""
        form_data = {
            'lexical_unit[en]': 'test',
            'notes[general][en][text]': '',  # Empty note
            'notes[usage][en][text]': '   ',  # Whitespace-only note
            'notes[etymology][pt][text]': 'Valid note'
        }
        
        # Process form data (empty notes should be filtered out)
        empty_entry_data = {}
        merged_data = merge_form_data_with_entry_data(form_data, empty_entry_data)
        
        # Create entry
        entry = Entry.from_dict(merged_data)
        
        # Verify empty notes are not included
        assert 'general' not in entry.notes
        assert 'usage' not in entry.notes
        assert 'etymology' in entry.notes
        assert entry.notes['etymology']['pt'] == 'Valid note'
    
    @pytest.mark.integration
    def test_entry_json_serialization_with_multilingual_notes(self):
        """Test JSON serialization of entries with multilingual notes."""
        entry = Entry(id_='test-json',
            lexical_unit={'en': 'test', 'pt': 'teste'},
            notes={
                'general': {
                    'en': 'English note',
                    'pt': 'Nota em português'
                }
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Test JSON serialization
        json_str = entry.to_json()
        assert json_str  # Should not be empty
        
        # Parse JSON and verify structure
        parsed_data = json.loads(json_str)
        assert parsed_data['id'] == 'test-json'
        assert parsed_data['lexical_unit']['en'] == 'test'
        assert parsed_data['lexical_unit']['pt'] == 'teste'
        assert parsed_data['notes']['general']['en'] == 'English note'
        assert parsed_data['notes']['general']['pt'] == 'Nota em português'
        
        # Test JSON deserialization
        reconstructed_entry = Entry.from_json(json_str)
        assert reconstructed_entry.id == entry.id
        assert reconstructed_entry.lexical_unit == entry.lexical_unit
        assert reconstructed_entry.notes == entry.notes
