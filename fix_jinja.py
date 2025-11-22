
import re

def fix_jinja(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix split {% endif %}
    # Pattern: {% endif followed by whitespace/newline and then %}
    # We want to join them.
    
    # Look for {% endif\s*%} where \s* includes newlines
    new_content = re.sub(r'{% endif\s*%}', '{% endif %}', content)
    
    # Also check for other split tags if any
    # But let's focus on the one causing issues
    
    if content != new_content:
        print("Fixed split Jinja tags.")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
    else:
        print("No split Jinja tags found matching the pattern.")

if __name__ == "__main__":
    fix_jinja('app/templates/entry_form.html')
