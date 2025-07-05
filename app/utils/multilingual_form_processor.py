"""
Utilities for processing multilingual form data.
"""

from __future__ import annotations

from typing import Dict, Any, List


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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.debug(f"[MERGE DEBUG] Input form_data keys: {list(form_data.keys())}")
    logger.debug(f"[MERGE DEBUG] Input entry_data keys: {list(entry_data.keys())}")
    
    # Start with existing entry data
    merged_data = entry_data.copy()
    
    # Process multilingual notes from form data
    notes = process_multilingual_notes_form_data(form_data)
    if notes:
        logger.debug(f"[MERGE DEBUG] Processed notes: {notes}")
        merged_data['notes'] = notes
    
    # Process multilingual lexical_unit
    lexical_unit = process_multilingual_field_form_data(form_data, 'lexical_unit')
    if lexical_unit:
        logger.debug(f"[MERGE DEBUG] Processed lexical_unit: {lexical_unit}")
        merged_data['lexical_unit'] = lexical_unit
    elif 'lexical_unit' in form_data and isinstance(form_data['lexical_unit'], dict):
        # Handle direct JSON object format: {"lexical_unit": {"en": "test"}}
        logger.debug(f"[MERGE DEBUG] Using direct lexical_unit object: {form_data['lexical_unit']}")
        merged_data['lexical_unit'] = form_data['lexical_unit']
    elif 'lexical_unit' in form_data and isinstance(form_data['lexical_unit'], str):
        # Handle backward compatibility: convert string format to multilingual format
        if form_data['lexical_unit'].strip():
            merged_data['lexical_unit'] = {'en': form_data['lexical_unit'].strip()}
    
    # Special handling for senses to preserve missing/empty fields
    if 'senses' in form_data and 'senses' in entry_data:
        # Direct senses array format - merge with existing
        merged_data['senses'] = _merge_senses_data(form_data['senses'], entry_data['senses'])
    elif 'senses' in form_data and isinstance(form_data['senses'], list):
        # Direct senses array format - new entry (no existing senses)
        logger.debug(f"[MERGE DEBUG] Using direct senses array for new entry: {form_data['senses']}")
        merged_data['senses'] = form_data['senses']
    else:
        # Check for complex form data structure (senses[0][field])
        form_senses = process_senses_form_data(form_data)
        if form_senses and 'senses' in entry_data:
            logger.debug(f"[MERGE DEBUG] Processed form_senses: {form_senses}")
            merged_data['senses'] = _merge_senses_data(form_senses, entry_data['senses'])
        elif form_senses:
            logger.debug(f"[MERGE DEBUG] Using form_senses as new senses: {form_senses}")
            merged_data['senses'] = form_senses
    
    # Process other form fields (excluding notes, multilingual fields, and senses)
    # Handle dot notation fields by converting them to nested structures
    dot_notation_fields = {}
    
    for key, value in form_data.items():
        if (not key.startswith('notes[') and 
            not key.startswith('lexical_unit[') and 
            not key.startswith('senses[') and
            key not in ['lexical_unit', 'senses']):
            
            if '.' in key:
                logger.debug(f"[MERGE DEBUG] Processing dot notation: {key} = {value}")
                # Handle dot notation (e.g., 'grammatical_info.part_of_speech')
                parts = key.split('.')
                current = dot_notation_fields
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                # Regular field
                logger.debug(f"[MERGE DEBUG] Processing regular field: {key} = {value}")
                merged_data[key] = value
    
    # Merge dot notation fields into merged_data
    for key, value in dot_notation_fields.items():
        merged_data[key] = value
    
    # Special handling for grammatical_info: flatten nested dict format to string
    if 'grammatical_info' in merged_data and isinstance(merged_data['grammatical_info'], dict):
        # Extract part_of_speech from nested structure
        pos_value = merged_data['grammatical_info'].get('part_of_speech', '')
        if isinstance(pos_value, str) and pos_value.strip():
            merged_data['grammatical_info'] = pos_value.strip()
        else:
            # If no valid part_of_speech, remove grammatical_info or set to empty
            merged_data['grammatical_info'] = ''
    
    return merged_data


def _merge_senses_data(form_senses: List[Dict[str, Any]], existing_senses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Intelligently merge sense data from form with existing sense data.
    
    Preserves fields that are missing or empty in form data to prevent
    accidental clearing of important sense information.
    
    Args:
        form_senses: Sense data from form submission
        existing_senses: Existing sense data from database
        
    Returns:
        Merged sense data preserving missing/empty fields
    """
    # Create a mapping of existing senses by ID for quick lookup
    existing_by_id = {sense.get('id'): sense for sense in existing_senses if sense.get('id')}
    
    merged_senses = []
    
    for form_sense in form_senses:
        sense_id = form_sense.get('id')
        
        # Start with form data
        merged_sense = form_sense.copy()
        
        # If we have an existing sense with the same ID, preserve important fields
        if sense_id and sense_id in existing_by_id:
            existing_sense = existing_by_id[sense_id]
            
            # Preserve ALL important sense fields that might be missing from form data
            # This prevents critical data loss when saving entries
            critical_fields = [
                'definition',           # CRITICAL: Definitions must never be lost
                'grammatical_info',     # CRITICAL: Part-of-speech information
                'pronunciation',        # Pronunciation data
                'semantic_domain',      # Semantic domain classification
                'subsense_type',        # Type of subsense
                'examples',             # CRITICAL: Example sentences
                'glosses',              # CRITICAL: Glosses/translations
                'subsenses',            # CRITICAL: Nested subsenses
                'notes',                # Additional notes
                'variants',             # Variant forms
                'etymologies',          # Etymology information
                'relations'             # Lexical relations
            ]
            
            for field in critical_fields:
                # Preserve field if it's missing, empty, or whitespace-only in form data
                if (field not in form_sense or 
                    not form_sense.get(field) or 
                    (isinstance(form_sense.get(field), str) and form_sense.get(field, '').strip() == '')):
                    # Only preserve if existing sense has meaningful data for this field
                    if existing_sense.get(field):
                        merged_sense[field] = existing_sense[field]
        
        merged_senses.append(merged_sense)
    
    return merged_senses


def process_senses_form_data(form_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process sense data from complex form submission.
    
    Handles form fields like:
    - senses[0][definition] (bracket notation)
    - senses[0].definition (dot notation)
    - senses[0][grammatical_info]
    - senses[0][examples][0][text]
    
    Args:
        form_data: Dictionary containing form field names and values
        
    Returns:
        List of sense dictionaries
    """
    import logging
    logger = logging.getLogger(__name__)
    
    senses_data: Dict[int, Dict[str, Any]] = {}
    
    logger.debug(f"[SENSES DEBUG] Processing form data for senses, keys: {[k for k in form_data.keys() if k.startswith('senses[')]}")
    
    for key, value in form_data.items():
        if key.startswith('senses[') and value.strip():
            logger.debug(f"[SENSES DEBUG] Processing: {key} = {value}")
            # Parse both bracket notation: senses[0][definition] -> (0, 'definition')
            # And dot notation: senses[0].definition -> (0, 'definition')
            # And complex: senses[0][examples][0][text] -> (0, 'examples', 0, 'text')
            
            # Remove 'senses[' from the beginning
            key_part = key[7:]  # Remove 'senses['
            
            # Handle both bracket and dot notation
            if '][' in key_part:
                # Bracket notation: senses[0][definition]
                parts = key_part.split('][')
                # Remove trailing ']' from the last part
                if parts and parts[-1].endswith(']'):
                    parts[-1] = parts[-1][:-1]
            elif key_part.count(']') == 1 and '.' in key_part:
                # Dot notation: senses[0].definition
                # Split on first ']' then split the rest on '.'
                close_bracket_pos = key_part.find(']')
                index_part = key_part[:close_bracket_pos]
                field_part = key_part[close_bracket_pos + 2:]  # Skip '].'
                parts = [index_part] + field_part.split('.')
            else:
                logger.debug(f"[SENSES DEBUG] Unrecognized format: {key}")
                continue
                
            logger.debug(f"[SENSES DEBUG] Parsed parts: {parts}")
            
            if len(parts) >= 2:  # At least sense_index and field_name
                try:
                    sense_index = int(parts[0])
                    
                    # Initialize sense if not exists
                    if sense_index not in senses_data:
                        senses_data[sense_index] = {}
                    
                    if len(parts) == 2:
                        # Simple field: senses[0][definition] or senses[0].definition
                        field_name = parts[1]
                        logger.debug(f"[SENSES DEBUG] Setting simple field: senses[{sense_index}][{field_name}] = {value}")
                        senses_data[sense_index][field_name] = value.strip()
                    
                    elif len(parts) == 3:
                        # Could be multilingual field: senses[0][definition][en]
                        # Or nested array: senses[0][examples][0] (but this would need 4 parts)
                        field_name = parts[1]
                        third_part = parts[2]
                        
                        # Check if third part is numeric (array index) or language code
                        try:
                            # Try to parse as number for array index
                            int(third_part)
                            # This suggests we need 4 parts for examples, skip for now
                            logger.debug(f"[SENSES DEBUG] Skipping incomplete array field: {key}")
                            continue
                        except ValueError:
                            # Not numeric, treat as language code
                            if field_name not in senses_data[sense_index]:
                                senses_data[sense_index][field_name] = {}
                            
                            logger.debug(f"[SENSES DEBUG] Setting multilingual field: senses[{sense_index}][{field_name}][{third_part}] = {value}")
                            senses_data[sense_index][field_name][third_part] = value.strip()
                    
                    elif len(parts) == 4 and parts[1] == 'examples':
                        # Example field: senses[0][examples][0][text]
                        try:
                            example_index = int(parts[2])
                            example_field = parts[3]
                            
                            # Initialize examples list if not exists
                            if 'examples' not in senses_data[sense_index]:
                                senses_data[sense_index]['examples'] = []
                            
                            # Extend examples list if needed
                            while len(senses_data[sense_index]['examples']) <= example_index:
                                senses_data[sense_index]['examples'].append({})
                            
                            logger.debug(f"[SENSES DEBUG] Setting example: senses[{sense_index}][examples][{example_index}][{example_field}] = {value}")
                            senses_data[sense_index]['examples'][example_index][example_field] = value.strip()
                        
                        except ValueError:
                            logger.debug(f"[SENSES DEBUG] Invalid example index in: {key}")
                            # Invalid example index, skip
                            continue
                
                except ValueError:
                    logger.debug(f"[SENSES DEBUG] Invalid sense index in: {key}")
                    # Invalid sense index, skip
                    continue
    
    # Convert to list format, maintaining order
    result = []
    for sense_index in sorted(senses_data.keys()):
        sense_dict = senses_data[sense_index]
        logger.debug(f"[SENSES DEBUG] Final sense {sense_index}: {sense_dict}")
        result.append(sense_dict)
    
    logger.debug(f"[SENSES DEBUG] Final result: {result}")
    return result
