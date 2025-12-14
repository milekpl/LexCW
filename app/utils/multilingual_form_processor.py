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

    # entry_data may be None when creating a new entry via the form
    if entry_data is None:
        logger.debug("[MERGE DEBUG] Input entry_data is None - treating as empty dict")
        entry_data = {}
    else:
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
        # Handle direct JSON object format
        raw_lu = form_data['lexical_unit']
        
        # Check if it's the new format: {"en": {"lang": "en", "text": "test"}}
        # or old format: {"en": "test"}
        processed_lu = {}
        for lang_code, lang_data in raw_lu.items():
            if isinstance(lang_data, dict) and 'text' in lang_data:
                # New format from multilingual form fields
                text = lang_data['text']
                if text and isinstance(text, str) and text.strip():
                    processed_lu[lang_code] = text.strip()
            elif isinstance(lang_data, str):
                # Old format - simple string
                if lang_data.strip():
                    processed_lu[lang_code] = lang_data.strip()
            else:
                logger.warning(f"[MERGE] Invalid lexical_unit format for language {lang_code}: {lang_data}")
        
        if not processed_lu:
            raise ValueError("lexical_unit must have at least one language with non-empty text")
        
        logger.debug(f"[MERGE DEBUG] Using processed lexical_unit object: {processed_lu}")
        merged_data['lexical_unit'] = processed_lu
    elif 'lexical_unit' in form_data and isinstance(form_data['lexical_unit'], str):
        # DEPRECATED: String format is no longer supported
        # This should not happen with the new form, but keep for transition period
        raise ValueError("lexical_unit must be a dict {lang: text}, got string format")
    
    # LIFT 0.13 Custom Fields (Day 28): Process literal_meaning (entry-level)
    literal_meaning = process_multilingual_field_form_data(form_data, 'literal_meaning')
    if literal_meaning:
        logger.debug(f"[MERGE DEBUG] Processed literal_meaning: {literal_meaning}")
        merged_data['literal_meaning'] = literal_meaning
    elif 'literal_meaning' in form_data and isinstance(form_data['literal_meaning'], dict):
        # Handle direct JSON object format
        raw_lm = form_data['literal_meaning']
        processed_lm = {}
        for lang_code, lang_data in raw_lm.items():
            if isinstance(lang_data, dict) and 'text' in lang_data:
                text = lang_data['text']
                if text and isinstance(text, str) and text.strip():
                    processed_lm[lang_code] = text.strip()
            elif isinstance(lang_data, str):
                if lang_data.strip():
                    processed_lm[lang_code] = lang_data.strip()
        
        if processed_lm:
            logger.debug(f"[MERGE DEBUG] Using processed literal_meaning object: {processed_lm}")
            merged_data['literal_meaning'] = processed_lm
    
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
    
    # Process new components from form data and add to relations
    form_components = process_components_form_data(form_data)
    if form_components:
        logger.debug(f"[MERGE DEBUG] Adding {len(form_components)} new components to relations")
        # Get existing relations or initialize empty list
        existing_relations = merged_data.get('relations', [])
        if not isinstance(existing_relations, list):
            existing_relations = []
        # Append new component relations
        merged_data['relations'] = existing_relations + form_components
    
    # Process other form fields (excluding notes, multilingual fields, senses, and components)
    # Handle dot notation fields by converting them to nested structures
    dot_notation_fields = {}
    
    for key, value in form_data.items():
        if (not key.startswith('notes[') and 
            not key.startswith('lexical_unit[') and 
            not key.startswith('senses[') and
            not key.startswith('components[') and
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
    
    # Backward compatibility: convert empty/invalid pronunciations list to dict
    if 'pronunciations' in merged_data:
        if isinstance(merged_data['pronunciations'], list):
            # Form sends pronunciations as array: [{type: 'seh-fonipa', value: '/test/'}]
            # Convert to dict format: {'seh-fonipa': '/test/'}
            pron_dict = {}
            for pron in merged_data['pronunciations']:
                if isinstance(pron, dict) and 'type' in pron and 'value' in pron:
                    pron_type = pron['type']
                    pron_value = pron['value']
                    if pron_value and pron_value.strip():
                        pron_dict[pron_type] = pron_value.strip()
            merged_data['pronunciations'] = pron_dict
        elif not isinstance(merged_data['pronunciations'], dict):
            # Invalid format
            merged_data['pronunciations'] = {}
    
    # Backward compatibility: convert empty/invalid citations list to dict
    if 'citations' in merged_data and not isinstance(merged_data['citations'], list):
        merged_data['citations'] = []
    
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
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a mapping of existing senses by ID for quick lookup
    existing_by_id = {sense.get('id'): sense for sense in existing_senses if sense.get('id')}
    
    merged_senses = []
    
    multitext_fields = {'definition', 'definitions', 'glosses', 'notes'}
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
                'definitions',          # Plural variant for some test cases
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
                form_value = form_sense.get(field)
                # For multitext fields, treat missing, empty, or empty dict as 'preserve existing'
                if field in multitext_fields:
                    preserve = False
                    if field not in form_sense:
                        preserve = True
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': NOT in form_sense, preserving")
                    elif form_value is None:
                        preserve = True
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': is None, preserving")
                    elif isinstance(form_value, dict) and not form_value:
                        preserve = True
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': empty dict, preserving")
                    elif isinstance(form_value, str) and form_value.strip() == '':
                        preserve = True
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': empty string, preserving")
                    else:
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': using form value: {form_value}")
                    
                    if preserve and existing_sense.get(field) is not None:
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': PRESERVING from existing: {existing_sense.get(field)}")
                        merged_sense[field] = existing_sense[field]
                    # Always ensure nested format for definitions and glosses
                    if field in ('definition', 'definitions', 'gloss', 'glosses') and field in merged_sense:
                        val = merged_sense[field]
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': normalizing format, current value: {val}")
                        if isinstance(val, dict):
                            # Ensure all values are in flattened format {lang: {text: value}}
                            for lang, v in list(val.items()):
                                if not isinstance(v, dict) or 'text' not in v:
                                    # Convert to flattened format
                                    merged_sense[field][lang] = {'text': str(v) if not isinstance(v, dict) else str(v.get('text', ''))}
                        elif isinstance(val, str):
                            # Convert string to flattened format
                            merged_sense[field] = {'en': {'text': val}}
                        logger.debug(f"[MERGE] Sense {sense_id} field '{field}': after normalization: {merged_sense[field]}")
                else:
                    # For other fields, preserve if missing, empty, or whitespace-only string
                    # Exception: For list fields (relations, examples), empty list means "clear it"
                    preserve = False
                    if field not in form_sense:
                        preserve = True
                    elif field in ('relations', 'examples', 'subsenses', 'variants'):
                        # For list fields, explicitly allow empty lists (they mean "clear")
                        # Only preserve if the field is missing entirely
                        preserve = False
                    elif not form_value:
                        preserve = True
                    elif isinstance(form_value, str) and form_value.strip() == '':
                        preserve = True
                    if preserve and existing_sense.get(field) is not None:
                        merged_sense[field] = existing_sense[field]

        merged_senses.append(merged_sense)
    
    return merged_senses


def process_entry_form_data(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process entry-level form data from form submission.
    
    Handles form fields like:
    - lexical_unit.en (multilingual entry text)
    
    Args:
        form_data: Dictionary containing form field names and values
        
    Returns:
        Dictionary suitable for creating Entry objects
    """
    import logging
    logger = logging.getLogger(__name__)
    
    entry_data: Dict[str, Any] = {}
    
    logger.debug(f"[ENTRY DEBUG] Processing entry form data: {list(form_data.keys())}")
    
    # Process multilingual lexical unit fields
    lexical_unit = process_multilingual_field_form_data(form_data, 'lexical_unit')
    if lexical_unit:
        logger.debug(f"[ENTRY DEBUG] Processed lexical_unit: {lexical_unit}")
        entry_data['lexical_unit'] = lexical_unit
    elif 'lexical_unit' in form_data and isinstance(form_data['lexical_unit'], str):
        # Handle backward compatibility: convert string format to multilingual format
        if form_data['lexical_unit'].strip():
            entry_data['lexical_unit'] = {'en': form_data['lexical_unit'].strip()}
    
    # NOTE: academic_domain is now ONLY at sense level, not entry level
    
    logger.debug(f"[ENTRY DEBUG] Processed entry_data: {entry_data}")
    return entry_data


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
        # Check if it's a sense-related key and has a non-empty value
        if key.startswith('senses['):
            # Skip empty values - handle both strings and lists
            if isinstance(value, str) and not value.strip():
                continue
            elif isinstance(value, list) and not value:
                continue
            elif not value:  # None or other falsy non-list/non-string
                continue
                
            logger.debug(f"[SENSES DEBUG] Processing: {key} = {value}")
            # Parse both bracket notation: senses[0][definition] -> (0, 'definition')
            # And dot notation: senses[0].definition -> (0, 'definition')
            # And complex: senses[0][examples][0][text] -> (0, 'examples', 0, 'text')
            # And mixed: senses[0].relations[0].type -> (0, 'relations', 0, 'type')
            
            # Remove 'senses[' from the beginning
            key_part = key[7:]  # Remove 'senses['
            
            # Handle both bracket and dot notation
            if '][' in key_part:
                # Bracket notation: senses[0][definition]
                parts = key_part.split('][')
                # Remove trailing ']' from the last part
                if parts and parts[-1].endswith(']'):
                    parts[-1] = parts[-1][:-1]
            elif '.' in key_part:
                # Dot notation: senses[0].definition or senses[0].relations[0].type
                # First, split on the first '].' to get the sense index
                close_bracket_pos = key_part.find(']')
                if close_bracket_pos == -1:
                    logger.debug(f"[SENSES DEBUG] Unrecognized format (no closing bracket): {key}")
                    continue
                    
                index_part = key_part[:close_bracket_pos]
                remainder = key_part[close_bracket_pos + 1:]  # Skip ']'
                
                # Now split the remainder on dots, but handle brackets within
                # e.g., ".relations[0].type" -> ['', 'relations[0]', 'type']
                parts = [index_part]
                current = ''
                in_bracket = False
                for char in remainder:
                    if char == '[':
                        in_bracket = True
                        if current and current != '.':
                            parts.append(current.lstrip('.'))
                            current = ''
                    elif char == ']':
                        in_bracket = False
                        if current:
                            parts.append(current)
                            current = ''
                    elif char == '.' and not in_bracket:
                        if current:
                            parts.append(current)
                            current = ''
                    else:
                        current += char
                
                if current and current != '.':
                    parts.append(current.lstrip('.'))
                    
                logger.debug(f"[SENSES DEBUG] Parsed dot notation: {key} -> {parts}")
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
                        # Convert to LIFT flat format for multilingual fields: {lang: text}
                        if field_name in ('definition', 'gloss'):
                            if isinstance(value, str):
                                senses_data[sense_index][field_name] = {'en': value.strip()}
                            else:
                                senses_data[sense_index][field_name] = value
                        # Handle list fields (usage_type, domain_type) - multiple selections from form
                        elif field_name in ('usage_type', 'domain_type'):
                            # If value is a list (multiple selections), use as-is after stripping each element
                            # If value is a string, split by semicolon (LIFT format)
                            if isinstance(value, list):
                                senses_data[sense_index][field_name] = [v.strip() if isinstance(v, str) else v for v in value if v]
                            elif isinstance(value, str) and value.strip():
                                senses_data[sense_index][field_name] = [v.strip() for v in value.split(';') if v.strip()]
                            else:
                                senses_data[sense_index][field_name] = []
                        else:
                            if isinstance(value, str):
                                senses_data[sense_index][field_name] = value.strip()
                            else:
                                senses_data[sense_index][field_name] = value
                    
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
                            # LIFT flat format: {lang: text} (string values, not nested dicts)
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
                    
                    elif len(parts) == 4 and parts[1] == 'relations':
                        # Relation field: senses[0][relations][0][type] or senses[0].relations[0].type
                        try:
                            relation_index = int(parts[2])
                            relation_field = parts[3]
                            
                            # Initialize relations list if not exists
                            if 'relations' not in senses_data[sense_index]:
                                senses_data[sense_index]['relations'] = []
                            
                            # Extend relations list if needed
                            while len(senses_data[sense_index]['relations']) <= relation_index:
                                senses_data[sense_index]['relations'].append({})
                            
                            logger.debug(f"[SENSES DEBUG] Setting relation: senses[{sense_index}][relations][{relation_index}][{relation_field}] = {value}")
                            # Store as string, don't strip if it's already stripped
                            if isinstance(value, str):
                                senses_data[sense_index]['relations'][relation_index][relation_field] = value.strip()
                            else:
                                senses_data[sense_index]['relations'][relation_index][relation_field] = value
                        
                        except ValueError:
                            logger.debug(f"[SENSES DEBUG] Invalid relation index in: {key}")
                            # Invalid relation index, skip
                            continue
                
                except ValueError:
                    logger.debug(f"[SENSES DEBUG] Invalid sense index in: {key}")
                    # Invalid sense index, skip
                    continue
    
    # Convert to list format, maintaining order
    result = []
    for sense_index in sorted(senses_data.keys()):
        sense_dict = senses_data[sense_index]
        
        # If this is an existing sense (has ID) and no relations were submitted,
        # explicitly set relations to empty list to clear any existing relations
        if sense_dict.get('id') and 'relations' not in sense_dict:
            sense_dict['relations'] = []
            logger.debug(f"[SENSES DEBUG] Sense {sense_index} has ID but no relations in form - setting to empty list")
        
        logger.debug(f"[SENSES DEBUG] Final sense {sense_index}: {sense_dict}")
        result.append(sense_dict)
    
    logger.debug(f"[SENSES DEBUG] Final result: {result}")
    return result


def process_components_form_data(form_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process components[n].field form data into a list of component dictionaries.
    Components are converted to _component-lexeme relations with complex-form-type traits.
    
    Args:
        form_data: Raw form data containing components[n].field entries
        
    Returns:
        List of component dictionaries to be converted to Relation objects
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.debug(f"[COMPONENTS DEBUG] Starting components form data processing")
    
    components_data = {}
    
    for key, value in form_data.items():
        if key.startswith('components[') and '].' in key:
            try:
                # Extract index and field name: components[0].ref -> index=0, field=ref
                index_end = key.index(']')
                index_str = key[len('components['):index_end]
                field = key[index_end + 2:]  # Skip '].''
                
                component_index = int(index_str)
                
                if component_index not in components_data:
                    components_data[component_index] = {}
                
                # Store the field value
                if value and isinstance(value, str):
                    components_data[component_index][field] = value.strip()
                    logger.debug(f"[COMPONENTS DEBUG] components[{component_index}][{field}] = {value.strip()}")
                    
            except (ValueError, IndexError):
                logger.debug(f"[COMPONENTS DEBUG] Invalid component key: {key}")
                continue
    
    # Convert to list of relation dicts with _component-lexeme type
    result = []
    for component_index in sorted(components_data.keys()):
        comp = components_data[component_index]
        
        # Skip if no ref provided
        if 'ref' not in comp or not comp['ref']:
            logger.debug(f"[COMPONENTS DEBUG] Skipping component {component_index} - no ref")
            continue
        
        # Convert to _component-lexeme relation format
        relation_dict = {
            'type': '_component-lexeme',
            'ref': comp['ref'],
            'traits': {
                'complex-form-type': comp.get('type', 'compound')
            }
        }
        
        # Add order if provided
        if 'order' in comp:
            try:
                relation_dict['order'] = int(comp['order'])
            except ValueError:
                pass
        
        logger.debug(f"[COMPONENTS DEBUG] Component {component_index} -> relation: {relation_dict}")
        result.append(relation_dict)
    
    logger.debug(f"[COMPONENTS DEBUG] Final result: {result}")
    return result
