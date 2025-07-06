#!/usr/bin/env python3
"""
Script to replace 'seh' language codes with 'pl' in test files.
This is needed after updating validation rules to use Polish instead of Sena.
"""

import os
import re

def fix_seh_codes_in_file(file_path):
    """Fix seh language codes in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace 'seh': with 'pl': (but not seh-fonipa)
        # Use negative lookahead to avoid matching seh-fonipa
        pattern = r"'seh'(?!-)"
        new_content = re.sub(pattern, "'pl'", content)
        
        # Also handle double quotes
        pattern = r'"seh"(?!-)'
        new_content = re.sub(pattern, '"pl"', new_content)
        
        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed: {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all test files."""
    test_files = [
        "tests/test_multilingual_editing.py",
        "tests/test_multilingual_notes_form_processing.py",
    ]
    
    fixed_count = 0
    for file_path in test_files:
        if os.path.exists(file_path):
            if fix_seh_codes_in_file(file_path):
                fixed_count += 1
        else:
            print(f"File not found: {file_path}")
    
    print(f"Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
