
import re

def check_tags(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    stack = []
    
    # Tags that don't need closing
    void_tags = ['input', 'img', 'br', 'hr', 'meta', 'link', 'source', 'col', 'embed', 'param', 'track', 'area', 'base', 'wbr']
    
    # Regex to find tags
    tag_re = re.compile(r'<(/?)(\w+)([^>]*)>')
    
    for i, line in enumerate(lines):
        # Remove jinja comments
        line = re.sub(r'{#.*?#}', '', line)
        
        # Find all tags
        for match in tag_re.finditer(line):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            attrs = match.group(3)
            
            if tag_name in void_tags:
                continue
                
            if is_closing:
                if not stack:
                    print(f"Line {i+1}: Unexpected closing tag </{tag_name}>")
                    continue
                    
                last_tag, last_line = stack[-1]
                if last_tag == tag_name:
                    stack.pop()
                else:
                    # Check if we can find the matching tag deeper in the stack (handling missing closing tags)
                    found = False
                    for j in range(len(stack)-1, -1, -1):
                        if stack[j][0] == tag_name:
                            print(f"Line {i+1}: Closing tag </{tag_name}> matches open tag from line {stack[j][1]}, but unclosed tags in between: {[t[0] for t in stack[j+1:]]}")
                            # Pop everything up to this tag
                            while len(stack) > j:
                                stack.pop()
                            found = True
                            break
                    
                    if not found:
                        print(f"Line {i+1}: Mismatched closing tag </{tag_name}>. Expected </{last_tag}> (opened at line {last_line})")
            else:
                # Check for self-closing tags (e.g. <div />) - though rare in HTML5, possible
                if attrs.strip().endswith('/'):
                    continue
                stack.append((tag_name, i+1))

    if stack:
        print("\nUnclosed tags:")
        for tag, line in stack:
            print(f"Line {line}: <{tag}>")

if __name__ == "__main__":
    check_tags('app/templates/entry_form.html')
