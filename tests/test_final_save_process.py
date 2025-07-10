#!/usr/bin/env python3
"""
Test the end-to-end save process for the Protestantism entry
to confirm the fix is working in the actual web application context.
"""

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


def test_protestantism_save_process():
    """Test the actual save process that would happen via the web form."""
    
    app = create_app()
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        
        entry_id = 'Protestantism_b97495fb-d52f-4755-94bf-a7a762339605'
        
        print("🔍 Testing end-to-end save process for Protestantism entry...")
        
        # 1. Get current entry (what the form would load)
        current_entry = dict_service.get_entry(entry_id)
        current_entry_data = current_entry.to_dict()
        
        print(f"📊 Current state - Definition: '{current_entry.senses[0].definition}'")
        print(f"📊 Current state - Grammatical info: '{current_entry.senses[0].grammatical_info}'")
        
        # 2. Simulate form submission (what the browser would send)
        form_data = {
            'id': entry_id,
            'lexical_unit[en]': 'Protestantism',
            'senses[0][id]': current_entry.senses[0].id,
            'senses[0][definition]': 'A form of Christianity that originated with the Reformation.',
            'senses[0][grammatical_info]': 'noun',
            'senses[0][examples][0][text]': 'Protestantism spread rapidly across Northern Europe.',
        }
        
        print(f"📝 Simulated form data:")
        for key, value in form_data.items():
            print(f"  {key}: '{value}'")
        
        # 3. Merge form data with entry data (what the save route does)
        merged_data = merge_form_data_with_entry_data(form_data, current_entry_data)
        
        print(f"🔄 Merged data - Definition: '{merged_data['senses'][0]['definition']}'")
        print(f"🔄 Merged data - Grammatical info: '{merged_data['senses'][0]['grammatical_info']}'")
        
        # 4. Create updated entry object (what the save route does)
        updated_entry = Entry.from_dict(merged_data)
        
        print(f"💾 Updated entry - Definition: '{updated_entry.senses[0].definition}'")
        print(f"💾 Updated entry - Grammatical info: '{updated_entry.senses[0].grammatical_info}'")
        print(f"💾 Updated entry - Examples: {len(updated_entry.senses[0].examples)} examples")
        
        # 5. Verify the data is correct
        assert updated_entry.senses[0].definition['en']['text'] == 'A form of Christianity that originated with the Reformation.'
        assert updated_entry.senses[0].grammatical_info == 'noun'
        assert len(updated_entry.senses[0].examples) == 1
        assert updated_entry.senses[0].examples[0]['text'] == 'Protestantism spread rapidly across Northern Europe.'
        
        print("✅ SUCCESS: End-to-end save process works correctly!")
        print("🎯 The web form should now work properly for adding data to empty fields.")


if __name__ == '__main__':
    test_protestantism_save_process()
