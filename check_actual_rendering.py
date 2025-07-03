import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from flask import render_template, request, url_for
from app.services.dictionary_service import DictionaryService

app = create_app()
with app.app_context():
    # Create a request context for proper URL generation
    with app.test_request_context('/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit'):
        # Get the entry
        entry_id = "Protestantism_b97495fb-d52f-4755-94bf-a7a762339605"
        dict_service = app.injector.get(DictionaryService)
        entry = dict_service.get_entry(entry_id)
        ranges = dict_service.get_lift_ranges()
        
        # Render the actual template
        rendered = render_template('entry_form.html', entry=entry, ranges=ranges)
        
        # Find the pronunciation initialization code in the rendered HTML
        js_init_pattern = r'if \(window\.PronunciationFormsManager.*?window\.pronunciationFormsManager.*?;'
        js_init_code = re.search(js_init_pattern, rendered, re.DOTALL)
        
        if js_init_code:
            print("Found pronunciation initialization code:")
            print(js_init_code.group(0))
        else:
            print("No pronunciation initialization code found")
            
        # Check for any pronunciation input fields
        input_pattern = r'<input.*?name="pronunciations\[\d+\]\.value".*?>'
        input_matches = re.findall(input_pattern, rendered)
        
        if input_matches:
            print("\nFound pronunciation input fields:")
            for input_match in input_matches:
                print(input_match)
        else:
            print("\nNo pronunciation input fields found")
