#!/usr/bin/env python3

"""
Add a debug route to test ranges loading.
"""

def add_debug_route():
    """Add a debug route to the Flask app for testing ranges."""
    
    # Read the main views file
    with open('app/views.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add the debug route
    debug_route = '''

@main.route('/debug/ranges')
def debug_ranges():
    """Debug page for testing ranges loading."""
    return render_template('ranges_test.html')
'''
    
    # Insert before the last line (likely a closing comment or similar)
    lines = content.split('\n')
    
    # Find a good place to insert - before the end
    insert_position = len(lines) - 1
    for i, line in enumerate(lines):
        if line.strip() == '' and i > len(lines) - 10:  # Near the end
            insert_position = i
            break
    
    lines.insert(insert_position, debug_route)
    
    modified_content = '\n'.join(lines)
    
    # Write back
    with open('app/views.py', 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("✅ Added debug route /debug/ranges to app/views.py")


if __name__ == '__main__':
    add_debug_route()
