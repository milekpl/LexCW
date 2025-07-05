#!/usr/bin/env python3
"""
Test to see what JSON structure is created by the frontend logic
"""

def simulate_frontend_processing():
    """Simulate the exact frontend JavaScript logic"""
    
    # Simulate FormData - this is what the browser form creates
    form_data = {
        'lexical_unit[en]': 'Protestantism',
        'grammatical_info.part_of_speech': 'Noun',
        'notes[general][en]': 'A form of Christianity',
        'senses[0][definition][en]': 'Christian movement'
    }
    
    print("=== Simulating Frontend Form Processing ===")
    print(f"Original form data: {form_data}")
    
    # This is the exact logic from entry-form.js
    json_data = {}
    
    for key, value in form_data.items():
        print(f"\nProcessing: {key} = {value}")
        
        # Handle bracket notation AND dot notation for nested objects
        # Split on brackets first, then on dots within each part
        bracket_parts = [k for k in key.replace('[', '|').replace(']', '|').split('|') if k != '']
        keys = []
        
        # Process each bracket part and split on dots
        for part in bracket_parts:
            if '.' in part:
                # Split on dots and add each part
                keys.extend(part.split('.'))
            else:
                keys.append(part)
        
        print(f"Keys array: {keys}")
        
        current = json_data
        
        for i, key_part in enumerate(keys):
            is_last = i == len(keys) - 1
            
            if is_last:
                current[key_part] = value
            else:
                # Handle numeric array indices
                next_key = keys[i + 1] if i + 1 < len(keys) else None
                use_array = next_key and next_key.isdigit()
                
                if key_part not in current:
                    current[key_part] = [] if use_array else {}
                
                # Move into nested object/array
                if use_array and isinstance(current[key_part], list):
                    # Ensure list is long enough
                    next_idx = int(next_key)
                    while len(current[key_part]) <= next_idx:
                        current[key_part].append({})
                    current = current[key_part][next_idx]
                else:
                    current = current[key_part]
    
    print(f"\n=== Final JSON Structure ===")
    import json
    print(json.dumps(json_data, indent=2))
    
    # Check the problematic field
    if 'grammatical_info' in json_data:
        gi = json_data['grammatical_info']
        print(f"\ngrammatical_info: {gi}")
        print(f"grammatical_info type: {type(gi)}")
        print(f"Is it a dict? {isinstance(gi, dict)}")
        
        if isinstance(gi, dict) and 'part_of_speech' in gi:
            print(f"part_of_speech value: {gi['part_of_speech']}")

if __name__ == "__main__":
    simulate_frontend_processing()
