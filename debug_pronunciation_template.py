"""
Debugging script for pronunciation display in the entry form.
"""

import os
from flask import render_template_string
from app import create_app
from app.models.entry import Entry

def debug_template_rendering():
    """Debug how pronunciations are rendered in the template."""
    app = create_app()
    
    # Create a test entry with pronunciations
    entry = Entry(
        id_="test_pronunciation_entry",
        lexical_unit={"en": "pronunciation test"},
        pronunciations={"seh-fonipa": "/pro.nun.si.eɪ.ʃən/"},
        grammatical_info="noun"
    )
    
    # Create a simplified template to test pronunciation rendering
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pronunciation Debug</title>
    </head>
    <body>
        <h1>Pronunciation Debug</h1>
        <p>Entry: {{ entry.id }}</p>
        <p>Lexical Unit: {{ entry.lexical_unit }}</p>
        <p>Pronunciations: {{ entry.pronunciations }}</p>
        
        <script>
        // Initialize pronunciation forms manager
        {% if entry.pronunciations %}
            console.log("Entry has pronunciations");
            const pronunciations = [];
            {% for writing_system, value in entry.pronunciations.items() %}
                console.log("Adding pronunciation: {{ writing_system }} = {{ value }}");
                pronunciations.push({
                    type: "{{ writing_system }}",
                    value: "{{ value }}",
                    audio_file: "",
                    is_default: true
                });
            {% endfor %}
            console.log("Final pronunciations array:", JSON.stringify(pronunciations));
        {% else %}
            console.log("Entry has no pronunciations");
            const pronunciations = [];
        {% endif %}
        </script>
    </body>
    </html>
    """
    
    # Render the template with the test entry
    with app.app_context():
        rendered = render_template_string(template, entry=entry)
        print("Rendered HTML:")
        print(rendered)
        
        # Check if the JavaScript includes the pronunciation data
        if "const pronunciations = [];" in rendered:
            print("\nWarning: pronunciations array is initialized as empty.")
        else:
            print("\nPronunciations array initialization looks good.")
            
        if "pronunciations.push({" in rendered:
            print("Found push operation to add pronunciations.")
        else:
            print("No push operation found - pronunciations not being added!")
            
        if "/pro.nun.si.eɪ.ʃən/" in rendered:
            print("Success: pronunciation value is in the rendered template.")
        else:
            print("Error: pronunciation value is not in the rendered template!")

if __name__ == '__main__':
    debug_template_rendering()
