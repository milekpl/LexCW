#!/usr/bin/env python3
"""
Script to systematically refactor non-standard ID mappings to standard IDs in the codebase.
This replaces all instances of non-standard plural/alternate forms with their canonical forms.
"""

import os
import re
from pathlib import Path
from typing import Dict, List

# Define the mapping of non-standard IDs to standard IDs
NON_STANDARD_TO_STANDARD_MAPPINGS = {
    'relation-types': 'lexical-relation',
    'variant-types-from-traits': 'variant-types',
    'semantic-domains': 'semantic-domain-ddp4',
    'usage-types': 'usage-type',
    'note-types': 'note-type',
    'publications': 'Publications'
}

def replace_non_standard_ids_in_line(line: str) -> tuple[str, int]:
    """
    Replace all non-standard IDs in a line with their standard equivalents.
    
    Args:
        line: The line to process
        
    Returns:
        Tuple of (modified_line, number_of_replacements_made)
    """
    modified_line = line
    replacements_made = 0
    
    for non_std_id, std_id in NON_STANDARD_TO_STANDARD_MAPPINGS.items():
        # Use word boundaries to avoid partial matches within other strings
        pattern = r'\b' + re.escape(non_std_id) + r'\b'
        if re.search(pattern, modified_line):
            modified_line = re.sub(pattern, std_id, modified_line)
            replacements_made += 1
    
    return modified_line, replacements_made

def refactor_file(file_path: str) -> int:
    """
    Refactor a single file by replacing non-standard IDs with standard ones.
    
    Args:
        file_path: Path to the file to refactor
        
    Returns:
        Number of replacements made
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
        
        modified_lines = []
        total_replacements = 0
        
        for line in original_lines:
            modified_line, replacements = replace_non_standard_ids_in_line(line)
            modified_lines.append(modified_line)
            total_replacements += replacements
        
        if total_replacements > 0:
            # Write the modified content back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)
            
            print(f"  - {file_path}: {total_replacements} replacements made")
        
        return total_replacements
    
    except UnicodeDecodeError:
        print(f"Could not decode file: {file_path}")
        return 0
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return 0

def refactor_codebase(root_dir: str):
    """
    Refactor the entire codebase by replacing non-standard IDs with standard ones.
    
    Args:
        root_dir: Root directory to refactor
    """
    total_replacements = 0
    files_processed = 0
    
    # Walk through all Python, JavaScript, HTML, JSON, and other text files
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories that shouldn't contain source code
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'htmlcov', 'coverage']]
        
        for file in files:
            if file.endswith(('.py', '.js', '.html', '.json', '.md', '.txt', '.xml')):
                file_path = os.path.join(root, file)
                
                # Skip our own script file to avoid self-modification
                if file_path.endswith('refactor_non_standard_ids.py'):
                    continue
                    
                replacements = refactor_file(file_path)
                if replacements > 0:
                    files_processed += 1
                    total_replacements += replacements
    
    print(f"\nRefactoring complete!")
    print(f"Processed {files_processed} files with {total_replacements} total replacements.")
    
    # Print the mapping summary
    print("\nApplied mappings:")
    for non_std_id, std_id in NON_STANDARD_TO_STANDARD_MAPPINGS.items():
        print(f"  '{non_std_id}' → '{std_id}'")

def preview_changes(root_dir: str) -> Dict[str, int]:
    """
    Preview what changes would be made without actually modifying files.
    
    Args:
        root_dir: Root directory to scan
        
    Returns:
        Dictionary mapping file paths to number of replacements that would be made
    """
    changes_to_make = {}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories that shouldn't contain source code
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'htmlcov', 'coverage']]
        
        for file in files:
            if file.endswith(('.py', '.js', '.html', '.json', '.md', '.txt', '.xml')):
                file_path = os.path.join(root, file)
                
                # Skip our own script file
                if file_path.endswith('refactor_non_standard_ids.py'):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    file_replacements = 0
                    for line in lines:
                        for non_std_id in NON_STANDARD_TO_STANDARD_MAPPINGS.keys():
                            if re.search(r'\b' + re.escape(non_std_id) + r'\b', line):
                                file_replacements += 1
                                break  # Count file once even if multiple occurrences
                                # Note: Actually counting each occurrence would be:
                                # file_replacements += len(re.findall(r'\b' + re.escape(non_std_id) + r'\b', line))
                    
                    if file_replacements > 0:
                        changes_to_make[file_path] = file_replacements
                
                except UnicodeDecodeError:
                    print(f"Could not decode file: {file_path}")
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
    
    return changes_to_make

if __name__ == "__main__":
    print("Refactoring script to replace non-standard IDs with standard IDs")
    print("Non-standard ID to Standard ID Mappings:")
    print("=" * 60)
    for non_std_id, std_id in NON_STANDARD_TO_STANDARD_MAPPINGS.items():
        print(f"  '{non_std_id}' → '{std_id}'")
    print("=" * 60)
    
    root_directory = "/mnt/d/Dokumenty/slownik-wielki/flask-app"
    
    # First show a preview of changes
    print("\nPreviewing changes...")
    changes = preview_changes(root_directory)
    
    if changes:
        print(f"\nWould modify {len(changes)} files:")
        for file_path, replacements in changes.items():
            print(f"  {file_path} ({replacements} occurrences)")
        
        print("Auto-proceeding with refactoring...")
        refactor_codebase(root_directory)
    else:
        print("No files would be modified - all non-standard IDs already cleaned up!")