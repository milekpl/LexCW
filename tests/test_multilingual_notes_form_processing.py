"""
Test cases for multilingual notes form processing.
"""

from __future__ import annotations

from typing import Dict, Any
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


class TestMultilingualNotesFormProcessing:
    """Test cases for processing multilingual notes from form data."""

    def test_process_multilingual_notes_form_data(self):
        """Test processing multilingual notes data from form submission."""
        form_data = {
            'lexical_unit': 'mukwa',
            'notes[general][en][text]': 'This is an English general note',
            'notes[general][pt][text]': 'Esta é uma nota geral em português',
            'notes[general][seh][text]': 'Ichi ndi chida chachikulu mu Chisena',
            'notes[usage][en][text]': 'Used in formal contexts',
            'notes[usage][pt][text]': 'Usado em contextos formais',
            'notes[semantic][en][text]': 'Refers to large trees'
        }
        
        processed_data = self._process_form_data_to_entry_dict(form_data)
        
        # Verify the structure
        assert 'notes' in processed_data
        assert isinstance(processed_data['notes'], dict)
        
        # Check general note
        assert 'general' in processed_data['notes']
        general_note = processed_data['notes']['general']
        assert isinstance(general_note, dict)
        assert general_note['en'] == 'This is an English general note'
        assert general_note['pt'] == 'Esta é uma nota geral em português'
        assert general_note['seh'] == 'Ichi ndi chida chachikulu mu Chisena'
        
        # Check usage note
        assert 'usage' in processed_data['notes']
        usage_note = processed_data['notes']['usage']
        assert isinstance(usage_note, dict)
        assert usage_note['en'] == 'Used in formal contexts'
        assert usage_note['pt'] == 'Usado em contextos formais'
        
        # Check semantic note
        assert 'semantic' in processed_data['notes']
        semantic_note = processed_data['notes']['semantic']
        assert isinstance(semantic_note, dict)
        assert semantic_note['en'] == 'Refers to large trees'

    def test_entry_creation_with_multilingual_notes(self):
        """Test creating an Entry object with multilingual notes data."""
        entry_data = {
            'id_': 'test_entry',
            'lexical_unit': {'seh': 'mukwa'},
            'notes': {
                'general': {
                    'en': 'This is an English general note',
                    'pt': 'Esta é uma nota geral em português',
                    'seh': 'Ichi ndi chida chachikulu mu Chisena'
                },
                'usage': {
                    'en': 'Used in formal contexts',
                    'pt': 'Usado em contextos formais'
                }
            }
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Verify the entry was created correctly
        assert entry.id == 'test_entry'
        assert 'general' in entry.notes
        assert 'usage' in entry.notes
        
        # Verify multilingual structure is preserved
        general_note = entry.notes['general']
        assert isinstance(general_note, dict)
        assert general_note['en'] == 'This is an English general note'
        assert general_note['pt'] == 'Esta é uma nota geral em português'
        assert general_note['seh'] == 'Ichi ndi chida chachikulu mu Chisena'
        
        usage_note = entry.notes['usage']
        assert isinstance(usage_note, dict)
        assert usage_note['en'] == 'Used in formal contexts'
        assert usage_note['pt'] == 'Usado em contextos formais'

    def test_entry_serialization_with_multilingual_notes(self):
        """Test that Entry.to_dict() preserves multilingual notes structure."""
        entry = Entry(
            id_='test_entry',
            lexical_unit={'seh': 'mukwa'},
            notes={
                'general': {
                    'en': 'This is an English general note',
                    'pt': 'Esta é uma nota geral em português'
                },
                'usage': {
                    'en': 'Used in formal contexts'
                }
            }
        )
        
        entry_dict = entry.to_dict()
        
        # Verify serialization preserves structure
        assert 'notes' in entry_dict
        assert isinstance(entry_dict['notes'], dict)
        assert 'general' in entry_dict['notes']
        assert 'usage' in entry_dict['notes']
        
        general_note = entry_dict['notes']['general']
        assert isinstance(general_note, dict)
        assert general_note['en'] == 'This is an English general note'
        assert general_note['pt'] == 'Esta é uma nota geral em português'
        
        usage_note = entry_dict['notes']['usage']
        assert isinstance(usage_note, dict)
        assert usage_note['en'] == 'Used in formal contexts'

    def test_backward_compatibility_with_simple_notes(self):
        """Test that simple (non-multilingual) notes still work."""
        entry_data = {
            'id_': 'test_entry',
            'lexical_unit': {'seh': 'mukwa'},
            'notes': {
                'general': 'This is a simple note',
                'usage': 'Another simple note'
            }
        }
        
        entry = Entry.from_dict(entry_data)
        
        # Verify the entry was created correctly with simple notes
        assert entry.id == 'test_entry'
        assert 'general' in entry.notes
        assert 'usage' in entry.notes
        assert entry.notes['general'] == 'This is a simple note'
        assert entry.notes['usage'] == 'Another simple note'
        
        # Verify serialization preserves simple format
        entry_dict = entry.to_dict()
        assert entry_dict['notes']['general'] == 'This is a simple note'
        assert entry_dict['notes']['usage'] == 'Another simple note'

    def test_process_multilingual_field_form_data(self):
        """Test processing multilingual field data from form submission."""
        from app.utils.multilingual_form_processor import process_multilingual_field_form_data
        
        form_data = {
            'lexical_unit[en]': 'house',
            'lexical_unit[pt]': 'casa',
            'lexical_unit[fr]': 'maison',
            'other_field': 'ignored',
            'lexical_unit[es]': '   ',  # Empty value should be ignored
        }
        
        result = process_multilingual_field_form_data(form_data, 'lexical_unit')
        
        expected = {
            'en': 'house',
            'pt': 'casa',
            'fr': 'maison'
        }
        
        assert result == expected
    
    def test_process_multilingual_field_form_data_empty_field(self):
        """Test processing empty multilingual field."""
        from app.utils.multilingual_form_processor import process_multilingual_field_form_data
        
        form_data = {
            'other_field': 'value',
            'lexical_unit[en]': '   ',  # Only whitespace
        }
        
        result = process_multilingual_field_form_data(form_data, 'lexical_unit')
        assert result == {}
    
    def test_merge_form_data_with_multilingual_lexical_unit(self):
        """Test merging form data with multilingual lexical unit processing."""
        form_data = {
            'lexical_unit[en]': 'book',
            'lexical_unit[pt]': 'livro',
            'notes[general][en][text]': 'A written work',
            'grammatical_info': 'noun'
        }
        
        existing_entry_data = {
            'id': 'test-entry',
            'lexical_unit': {'en': 'old_book'},
            'notes': {'old_note': 'old content'}
        }
        
        result = merge_form_data_with_entry_data(form_data, existing_entry_data)
        
        # Verify lexical unit is updated
        assert result['lexical_unit']['en'] == 'book'
        assert result['lexical_unit']['pt'] == 'livro'
        
        # Verify notes are updated
        assert result['notes']['general']['en'] == 'A written work'
        
        # Verify other fields are preserved/updated
        assert result['id'] == 'test-entry'
        assert result['grammatical_info'] == 'noun'

    def _process_form_data_to_entry_dict(self, form_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Helper method to process form data into entry dictionary format.
        This simulates the backend form processing logic.
        """
        entry_dict: Dict[str, Any] = {}
        notes: Dict[str, Dict[str, str]] = {}
        
        for key, value in form_data.items():
            if key.startswith('notes[') and value.strip():
                # Parse: notes[general][en][text] -> ('general', 'en', 'text')
                # Remove 'notes[' from the beginning
                key_part = key[6:]  # Remove 'notes['
                
                # Find the parts by splitting on '][' pattern first
                if '][' in key_part:
                    # Split by '][' first
                    parts = key_part.split('][')
                    # Remove the trailing ']' from the last part
                    if parts and parts[-1].endswith(']'):
                        parts[-1] = parts[-1][:-1]
                    
                    if len(parts) >= 3:  # note_type, language, field_type
                        note_type, language, field_type = parts[0], parts[1], parts[2]
                        
                        if field_type == 'text':  # Only process text fields
                            if note_type not in notes:
                                notes[note_type] = {}
                            
                            notes[note_type][language] = value.strip()
            else:
                # Handle other form fields
                entry_dict[key] = value
        
        if notes:
            entry_dict['notes'] = notes
        
        return entry_dict
