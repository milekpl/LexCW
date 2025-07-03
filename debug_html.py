#!/usr/bin/env python3
"""Save the rendered HTML to check manually."""

from app import create_app

def main():
    app = create_app()
    with app.test_client() as client:
        response = client.get('/entries/add')
        html = response.get_data(as_text=True)
        
        with open('entry_form_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("HTML saved to entry_form_debug.html")
        
        # Check the exact strings
        print(f"'class=\"dynamic-lift-range\"' in html: {'class=\"dynamic-lift-range\"' in html}")
        print(f"'class=\"dynamic-grammatical-info\"' in html: {'class=\"dynamic-grammatical-info\"' in html}")
        
        # Let's see what classes we do have
        import re
        classes = re.findall(r'class="([^"]*)"', html)
        unique_classes = set(classes)
        for cls in sorted(unique_classes):
            if 'dynamic' in cls or 'range' in cls or 'grammatical' in cls:
                print(f"Found class: '{cls}'")

if __name__ == "__main__":
    main()
