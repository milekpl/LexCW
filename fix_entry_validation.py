#!/usr/bin/env python3
"""
Script to automatically fix Entry validation issues by adding missing senses.
"""

import os
import re
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def fix_entry_creation_in_file(file_path: str) -> bool:
    """Fix Entry creations missing senses in a test file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match Entry() constructor calls that don't have senses
    # Look for Entry(id_="...", lexical_unit=...) without senses
    pattern = r'Entry\s*\(\s*([^)]*?)\)'
    
    def replace_entry(match):
        args = match.group(1)
        # Check if 'senses' is already present
        if 'senses' in args:
            return match.group(0)  # Already has senses, don't change
        
        # Check if this is a minimal Entry creation with just id and/or lexical_unit
        if ('id_=' in args or 'id=' in args) and ('lexical_unit' in args):
            # Add senses parameter
            if args.strip().endswith(','):
                # Already has trailing comma
                new_args = args + '\n            senses=[{"id": "sense1", "definition": {"en": "test definition"}}]'
            else:
                # Add comma and senses
                new_args = args + ',\n            senses=[{"id": "sense1", "definition": {"en": "test definition"}}]'
            
            return f'Entry({new_args})'
        
        return match.group(0)  # Don't change this Entry
    
    # Apply the replacements
    content = re.sub(pattern, replace_entry, content, flags=re.DOTALL)
    
    # Check if content was changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed Entry creations in {file_path}")
        return True
    
    return False

def main():
    """Main function to fix all test files."""
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    fixed_files = []
    
    # Find all Python test files
    for filename in os.listdir(test_dir):
        if filename.startswith('test_') and filename.endswith('.py'):
            file_path = os.path.join(test_dir, filename)
            if fix_entry_creation_in_file(file_path):
                fixed_files.append(filename)
    
    if fixed_files:
        print(f"\\nFixed {len(fixed_files)} files:")
        for filename in fixed_files:
            print(f"  - {filename}")
    else:
        print("No files needed fixing.")

if __name__ == "__main__":
    main()
