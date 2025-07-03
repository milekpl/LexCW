"""
Utilities for processing multilingual form data.
"""

from __future__ import annotations

from typing import Dict, Any


def process_multilingual_field_form_data(form_data: Dict[str, str], field_name: str) -> Dict[str, str]:
    """
    Process multilingual field data from form submission.
    
    Args:
        form_data: Dictionary containing form field names and values
        field_name: Name of the field to process (e.g., 'lexical_unit')
        
    Returns:
        Dictionary mapping language codes to field values
        
    Example:
        Input: {'lexical_unit[en]': 'house', 'lexical_unit[pt]': 'casa'}
        Output: {'en': 'house', 'pt': 'casa'}
    """
    field_data: Dict[str, str] = {}
    prefix = f"{field_name}["
    
    for key, value in form_data.items():
        if key.startswith(prefix) and value.strip():
            # Parse: lexical_unit[en] -> 'en'
            # Remove prefix from the beginning
            key_part = key[len(prefix):]
            
            # Remove trailing ']'
            if key_part.endswith(']'):
                language = key_part[:-1]
                field_data[language] = value.strip()
    
    return field_data


def process_multilingual_notes_form_data(form_data: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    """
    Process multilingual notes data from form submission.
    
    Args:
        form_data: Dictionary containing form field names and values
        
    Returns:
        Dictionary mapping note types to language-text mappings
        
    Example:
        Input: {'notes[general][en][text]': 'English note', 'notes[general][pt][text]': 'Portuguese note'}
        Output: {'general': {'en': 'English note', 'pt': 'Portuguese note'}}
    """
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
    
    return notes


def merge_form_data_with_entry_data(form_data: Dict[str, Any], entry_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge form data with existing entry data, processing multilingual notes and fields.
    
    Args:
        form_data: Raw form data from request
        entry_data: Existing entry data dictionary
        
    Returns:
        Merged entry data with processed multilingual notes and fields
    """
    # Start with existing entry data
    merged_data = entry_data.copy()
    
    # Process multilingual notes from form data
    notes = process_multilingual_notes_form_data(form_data)
    if notes:
        merged_data['notes'] = notes
    
    # Process multilingual lexical_unit
    lexical_unit = process_multilingual_field_form_data(form_data, 'lexical_unit')
    if lexical_unit:
        merged_data['lexical_unit'] = lexical_unit
    
    # Process other form fields (excluding notes and multilingual fields)
    for key, value in form_data.items():
        if not key.startswith('notes[') and not key.startswith('lexical_unit['):
            merged_data[key] = value
    
    return merged_data
