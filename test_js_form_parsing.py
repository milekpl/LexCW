#!/usr/bin/env python3
"""
Test the updated JavaScript form parsing by simulating the process in Python.
"""

def simulate_js_form_parsing(form_fields):
    """Simulate the JavaScript form parsing logic."""
    json_data = {}
    
    for key, value in form_fields.items():
        # Handle bracket notation AND dot notation for nested objects
        # Split on brackets first, then on dots within each part
        bracket_parts = []
        temp = key
        while '[' in temp and ']' in temp:
            start = temp.find('[')
            end = temp.find(']', start)
            if start == 0:
                # Key starts with bracket
                bracket_parts.append(temp[start+1:end])
                temp = temp[end+1:]
            else:
                # Key part before bracket
                bracket_parts.append(temp[:start])
                bracket_parts.append(temp[start+1:end])
                temp = temp[end+1:]
        
        if temp:  # Remaining part
            bracket_parts.append(temp)
        
        # Remove empty parts
        bracket_parts = [part for part in bracket_parts if part]
        
        keys = []
        
        # Process each bracket part and split on dots
        for part in bracket_parts:
            if '.' in part:
                # Split on dots and add each part
                keys.extend(part.split('.'))
            else:
                keys.append(part)
        
        # Build nested structure
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
                current = current[key_part]
    
    return json_data


def test_form_parsing():
    """Test the form parsing with real field names from the HTML form."""
    
    print("🧪 Testing JavaScript form parsing simulation...")
    
    # Simulate form fields like those in the actual HTML form
    form_fields = {
        'lexical_unit': 'Protestantism',
        'senses[0].definition': 'A form of Christianity that originated with the Reformation.',
        'senses[0].grammatical_info': 'noun',
        'senses[0].gloss': 'Protestant religion',
        'senses[0].note': 'Historical context important',
        'senses[0].examples[0].sentence': 'Protestantism spread rapidly across Northern Europe.',
        'senses[0].examples[0].translation': 'O protestantismo se espalhou rapidamente pelo norte da Europa.',
        'senses[0].examples[0].translation_type': 'free'
    }
    
    print(f"📝 Input form fields:")
    for key, value in form_fields.items():
        print(f"  {key}: '{value}'")
    
    # Parse the form data
    parsed_data = simulate_js_form_parsing(form_fields)
    
    print(f"\n🔄 Parsed JSON structure:")
    import json
    print(json.dumps(parsed_data, indent=2))
    
    # Test that critical data is present
    assert 'senses' in parsed_data, "Senses not found in parsed data"
    assert len(parsed_data['senses']) > 0, "No senses in parsed data"
    
    sense = parsed_data['senses'][0]
    assert 'definition' in sense, "Definition not found in sense"
    assert sense['definition'] == 'A form of Christianity that originated with the Reformation.', f"Definition incorrect: {sense.get('definition')}"
    
    assert 'grammatical_info' in sense, "Grammatical info not found in sense"
    assert sense['grammatical_info'] == 'noun', f"Grammatical info incorrect: {sense.get('grammatical_info')}"
    
    assert 'examples' in sense, "Examples not found in sense"
    assert len(sense['examples']) > 0, "No examples in sense"
    
    example = sense['examples'][0]
    assert 'sentence' in example, "Example sentence not found"
    assert example['sentence'] == 'Protestantism spread rapidly across Northern Europe.', f"Example sentence incorrect: {example.get('sentence')}"
    
    print("✅ SUCCESS: All form data properly parsed!")
    print("🎯 The JavaScript fix should now work correctly!")


if __name__ == '__main__':
    test_form_parsing()
