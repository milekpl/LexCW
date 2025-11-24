
import re
import sys

def check_jinja(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    stack = []
    
    # Regex for Jinja tags
    # We want to match {% tag ... %}
    tag_re = re.compile(r'{%\s*(\w+)(?:\s+.*?)?\s*%}')
    
    for i, line in enumerate(lines):
        # Ignore comments
        if '{#' in line:
            continue
            
        for match in tag_re.finditer(line):
            tag_name = match.group(1)
            
            if tag_name in ['if', 'for', 'block', 'macro', 'call', 'filter']:
                stack.append((tag_name, i+1))
                
            elif tag_name.startswith('end'):
                expected_tag = tag_name[3:]
                if not stack:
                    print(f"Line {i+1}: Unexpected {{% {tag_name} %}}")
                    continue
                    
                last_tag, last_line = stack[-1]
                if last_tag == expected_tag:
                    stack.pop()
                else:
                    print(f"Line {i+1}: Mismatched {{% {tag_name} %}}. Expected {{% end{last_tag} %}} (opened at line {last_line})")
                    
            elif tag_name in ['else', 'elif']:
                if not stack:
                    print(f"Line {i+1}: Unexpected {{% {tag_name} %}}")
                else:
                    last_tag, last_line = stack[-1]
                    if last_tag not in ['if', 'for']:
                        print(f"Line {i+1}: {{% {tag_name} %}} inside {{% {last_tag} %}} (opened at line {last_line})")

    if stack:
        print("\nUnclosed tags:")
        for tag, line in stack:
            print(f"Line {line}: {{% {tag} %}}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = 'app/templates/entry_form.html'
    check_jinja(filepath)
