import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from flask import render_template_string
from app.services.dictionary_service import DictionaryService

app = create_app()
with app.app_context():
    # Check entry for Protestantism
    entry_id = "Protestantism_b97495fb-d52f-4755-94bf-a7a762339605"
    dict_service = app.injector.get(DictionaryService)
    entry = dict_service.get_entry(entry_id)
    
    # Test with the old approach
    template_old = """
    {% if entry.pronunciations %}
        const pronunciations = [];
        {% for writing_system, value in entry.pronunciations.items() %}
            pronunciations.push({
                type: "{{ writing_system }}",
                value: "{{ value }}",
                audio_file: "",
                is_default: true
            });
        {% endfor %}
    {% else %}
        const pronunciations = [];
    {% endif %}
    """
    
    # Test with the new approach
    template_new = """
    {% if entry.pronunciations %}
        const pronunciations = [];
        {% for writing_system, value in entry.pronunciations.items() %}
            pronunciations.push({
                type: {{ writing_system | tojson | safe }},
                value: {{ value | tojson | safe }},
                audio_file: "",
                is_default: true
            });
        {% endfor %}
    {% else %}
        const pronunciations = [];
    {% endif %}
    """
    
    rendered_old = render_template_string(template_old, entry=entry)
    rendered_new = render_template_string(template_new, entry=entry)
    
    print("=== OLD APPROACH ===")
    print(rendered_old)
    print("\n=== NEW APPROACH ===")
    print(rendered_new)
