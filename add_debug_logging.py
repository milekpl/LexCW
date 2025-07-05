#!/usr/bin/env python3
"""
Quick test to add debugging to the views.py to see what data is actually being received.
"""

# Read current views.py to add debugging
with open('app/views.py', 'r') as f:
    content = f.read()

# Check if debug logging is already present
if 'DEBUG FORM DATA' in content:
    print("Debug logging already present in views.py")
else:
    # Add debug logging after the line that gets JSON data
    updated_content = content.replace(
        'data = request.get_json()',
        '''data = request.get_json()
            print(f"[DEBUG FORM DATA] Received JSON data: {data}")
            print(f"[DEBUG FORM DATA] Data type: {type(data)}")
            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"[DEBUG FORM DATA]   {key}: {value} (type: {type(value)})")'''
    )
    
    # Write updated content
    with open('app/views.py', 'w') as f:
        f.write(updated_content)
    
    print("✅ Added debug logging to views.py")
    print("🔍 Now when you submit the form, you'll see exactly what data is being received.")
    print("📝 Check the Flask console output for '[DEBUG FORM DATA]' messages.")
