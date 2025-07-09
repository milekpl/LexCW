#!/usr/bin/env python3
"""
Test the updated JavaScript form parsing by simulating the process in Python.
"""

from __future__ import annotations
from typing import Any, Dict

def simulate_js_form_parsing(form_fields: Dict[str, Any]) -> dict[str, Any]:
    """Simulate the JavaScript form parsing logic."""
    json_data: dict[str, Any] = {}
    for key, value in form_fields.items():
        # Split the key into field and nested parts (e.g. lexical_unit[en] -> ['lexical_unit', 'en'])
        parts: list[str] = []
        temp = ""
        in_bracket = False
        for c in key:
            if c == '[':
                if temp:
                    parts.append(temp)
                temp = ""
                in_bracket = True
            elif c == ']':
                if temp:
                    parts.append(temp)
                temp = ""
                in_bracket = False
            elif c == '.' and not in_bracket:
                if temp:
                    parts.append(temp)
                temp = ""
            else:
                temp += c
        if temp:
            parts.append(temp)

        # Now build the nested structure
        current = json_data
        for i, part in enumerate(parts):
            is_last = i == len(parts) - 1
            is_index = part.isdigit()
            key_part = int(part) if is_index else part
            if is_last:
                if isinstance(current, list) and isinstance(key_part, int):
                    while len(current) <= key_part:
                        current.append({})
                    current[key_part] = value
                elif isinstance(current, dict):
                    # If the key already exists and is a dict, and value is a dict, merge
                    if key_part in current and isinstance(current[key_part], dict) and isinstance(value, dict):
                        current[key_part].update(value)
                    else:
                        current[key_part] = value
            else:
                use_array = False
                next_part = parts[i + 1] if i + 1 < len(parts) else None
                if next_part is not None and next_part.isdigit():
                    use_array = True
                if isinstance(current, list) and isinstance(key_part, int):
                    while len(current) <= key_part:
                        current.append({})
                    if use_array:
                        if not isinstance(current[key_part], list):
                            current[key_part] = []
                    else:
                        if not isinstance(current[key_part], dict):
                            current[key_part] = {}
                    current = current[key_part]
                elif isinstance(current, dict):
                    if key_part not in current:
                        current[key_part] = [] if use_array else {}
                    current = current[key_part]
    return json_data



import pytest

def test_form_parsing() -> None:
    """
    Test the form parsing with multilingual/nested dict multitext fields.
    Simulates JS form parsing for fields like lexical_unit[en], senses[0].glosses[en], etc.
    """
    print("🧪 Testing JavaScript form parsing simulation (multilingual support)...")

    # Simulate multilingual/nested form fields as would be submitted by the HTML form
    form_fields = {
        'lexical_unit[en]': 'Protestantism',
        'lexical_unit[pt]': 'Protestantismo',
        'senses[0].definition[en]': 'A form of Christianity that originated with the Reformation.',
        'senses[0].definition[pt]': 'Uma forma de Cristianismo originada na Reforma.',
        'senses[0].grammatical_info': 'noun',
        'senses[0].glosses[en]': 'Protestant religion',
        'senses[0].glosses[pt]': 'Religião protestante',
        'senses[0].note[en]': 'Historical context important',
        'senses[0].examples[0].sentence[en]': 'Protestantism spread rapidly across Northern Europe.',
        'senses[0].examples[0].sentence[pt]': 'O protestantismo se espalhou rapidamente pelo norte da Europa.',
        'senses[0].examples[0].translation[en]': 'Protestantism spread rapidly across Northern Europe.',
        'senses[0].examples[0].translation[pt]': 'O protestantismo se espalhou rapidamente pelo norte da Europa.',
        'senses[0].examples[0].translation_type': 'free'
    }

    print(f"📝 Input form fields:")
    for key, value in form_fields.items():
        print(f"  {key}: '{value}'")

    # Parse the form data
    parsed_data = simulate_js_form_parsing(form_fields)

    print(f"\n🔄 Parsed JSON structure:")
    import json
    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))

    # Test that critical data is present and in nested dict (multilingual) format
    assert 'lexical_unit' in parsed_data, "lexical_unit not found in parsed data"
    assert isinstance(parsed_data['lexical_unit'], dict), "lexical_unit should be a dict"
    assert parsed_data['lexical_unit']['en'] == 'Protestantism', f"lexical_unit[en] incorrect: {parsed_data['lexical_unit'].get('en')}"
    assert parsed_data['lexical_unit']['pt'] == 'Protestantismo', f"lexical_unit[pt] incorrect: {parsed_data['lexical_unit'].get('pt')}"

    assert 'senses' in parsed_data, "Senses not found in parsed data"
    assert isinstance(parsed_data['senses'], list) and len(parsed_data['senses']) > 0, "No senses in parsed data"
    sense = parsed_data['senses'][0]

    assert 'definition' in sense and isinstance(sense['definition'], dict), "Definition should be a dict"
    assert sense['definition']['en'] == 'A form of Christianity that originated with the Reformation.'
    assert sense['definition']['pt'] == 'Uma forma de Cristianismo originada na Reforma.'

    assert 'grammatical_info' in sense, "Grammatical info not found in sense"
    assert sense['grammatical_info'] == 'noun', f"Grammatical info incorrect: {sense.get('grammatical_info')}"

    assert 'glosses' in sense and isinstance(sense['glosses'], dict), "Glosses should be a dict"
    assert sense['glosses']['en'] == 'Protestant religion'
    assert sense['glosses']['pt'] == 'Religião protestante'

    assert 'note' in sense and isinstance(sense['note'], dict), "Note should be a dict"
    assert sense['note']['en'] == 'Historical context important'

    assert 'examples' in sense and isinstance(sense['examples'], list) and len(sense['examples']) > 0, "Examples missing or not a list"
    example = sense['examples'][0]
    assert 'sentence' in example and isinstance(example['sentence'], dict), "Example sentence should be a dict"
    assert example['sentence']['en'] == 'Protestantism spread rapidly across Northern Europe.'
    assert example['sentence']['pt'] == 'O protestantismo se espalhou rapidamente pelo norte da Europa.'
    assert 'translation' in example and isinstance(example['translation'], dict), "Example translation should be a dict"
    assert example['translation']['en'] == 'Protestantism spread rapidly across Northern Europe.'
    assert example['translation']['pt'] == 'O protestantismo se espalhou rapidamente pelo norte da Europa.'
    assert example['translation_type'] == 'free'

    print("✅ SUCCESS: All multilingual form data properly parsed!")
    print("🎯 The JavaScript fix should now work correctly for nested dict multitext fields!")


if __name__ == '__main__':
    test_form_parsing()
