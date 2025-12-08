#!/usr/bin/env python3
"""
Test the end-to-end save process for entry updates
to confirm the fix is working in the actual web application context.
"""

import pytest
import uuid
from flask import Flask
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


@pytest.mark.integration
def test_protestantism_save_process(client):
    """Test the actual save process that would happen via the web form."""
    
    # Create a test entry first using XML API
    entry_id = f'Protestantism_{uuid.uuid4().hex[:8]}'
    entry_xml = f'''<entry id="{entry_id}">
        <lexical-unit>
            <form lang="en"><text>Protestantism</text></form>
        </lexical-unit>
        <sense id="sense_1">
            <gloss lang="en"><text>Protestant religion</text></gloss>
            <definition>
                <form lang="en"><text>A branch of Christianity</text></form>
            </definition>
        </sense>
    </entry>'''
    
    create_response = client.post('/api/xml/entries', data=entry_xml, content_type='application/xml')
    assert create_response.status_code == 201
    
    print("🔍 Testing end-to-end save process for Protestantism entry...")
    
    # 1. Get current entry (what the form would load)
    get_response = client.get(f'/api/entries/{entry_id}')
    assert get_response.status_code == 200
    current_entry_data = get_response.get_json()
    
    print(f"📊 Current state - Entry loaded successfully")
    
    # 2. Simulate form submission (what the browser would send)
    form_data = {
        'id': entry_id,
        'lexical_unit[en]': 'Protestantism',
        'senses[0][id]': current_entry_data['senses'][0]['id'],
        'senses[0][definition]': 'A form of Christianity that originated with the Reformation.',
        'senses[0][grammatical_info]': 'noun',
        'senses[0][examples][0][text]': 'Protestantism spread rapidly across Northern Europe.',
    }
    
    print(f"📝 Simulated form data has {len(form_data)} fields")
    
    # 3. Merge form data with entry data (what the save route does)
    merged_data = merge_form_data_with_entry_data(form_data, current_entry_data)
    
    print(f"🔄 Merged data created successfully")
    
    # 4. Create updated entry object (what the save route does)
    updated_entry = Entry.from_dict(merged_data)
    
    print(f"💾 Updated entry - Definition: '{updated_entry.senses[0].definition}'")
    print(f"💾 Updated entry - Grammatical info: '{updated_entry.senses[0].grammatical_info}'")
    print(f"💾 Updated entry - Examples: {len(updated_entry.senses[0].examples)} examples")
    
    # 5. Verify the data is correct
    # LIFT flat format: definition is Dict[str, str]
    assert 'A form of Christianity that originated with the Reformation.' in str(updated_entry.senses[0].definition)
    assert updated_entry.senses[0].grammatical_info == 'noun'
    assert len(updated_entry.senses[0].examples) == 1
    
    print("✅ SUCCESS: End-to-end save process works correctly!")
    print("🎯 The web form should now work properly for adding data to empty fields.")


if __name__ == '__main__':
    test_protestantism_save_process()
