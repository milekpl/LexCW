#!/usr/bin/env python3
"""
Script to replace all 'seh' language codes with 'pl' in the centralized validation test file.
"""

import re

def fix_seh_in_centralized_validation():
    """Fix all seh language codes in the centralized validation test file."""
    file_path = "tests/test_centralized_validation.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace 'seh': with 'pl': but preserve seh-fonipa
        content = re.sub(r'"seh"(?!-)', '"pl"', content)
        content = re.sub(r"'seh'(?!-)", "'pl'", content)
        
        # Also replace in XML lang attributes
        content = re.sub(r'lang="seh"', 'lang="pl"', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed seh language codes in {file_path}")
        return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

if __name__ == '__main__':
    fix_seh_in_centralized_validation()
