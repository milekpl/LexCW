#!/usr/bin/env python3
"""
Script to find all instances of non-standard ID mappings in the codebase.
This helps identify where the non-standard plural/alternate forms are used.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Define the mapping of non-standard IDs to standard IDs
NON_STANDARD_TO_STANDARD_MAPPINGS = {
    'relation type': 'lexical-relations',
    'variant type': 'variant-types',
    'semantic domain': 'semantic-domain-ddp4',
    'usage note': 'usage-type',
    'note type': 'note-type',
    'Publication': 'Publications',
    # Plural vs singular forms that might be used interchangeably
    'relations': 'lexical-relations',
    'variants': 'variant-types',
    'domains': 'semantic-domain-ddp4',
    'notes': 'note-type',
    'usages': 'usage-type',
    # Other potential mappings
    'lexical-relation': 'lexical-relations',
    'variant-types': 'variant-types',
    'semantic-domain-ddp4': 'semantic-domain-ddp4',
    'usage-type': 'usage-type',
    'note-type': 'note-type',
    'Publications': 'Publications'
}

def find_non_standard_ids_in_file(file_path: str) -> List[Tuple[int, str, str]]:
    """
    Find all instances of non-standard IDs in a given file.

    Args:
        file_path: Path to the file to search

    Returns:
        List of tuples containing (line_number, matched_text, non_standard_id)
    """
    results = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            for non_std_id, std_id in NON_STANDARD_TO_STANDARD_MAPPINGS.items():
                # Search for the non-standard ID in the line
                if non_std_id in line:
                    # More specific match to avoid partial matches within other strings
                    pattern = r'\b' + re.escape(non_std_id) + r'\b'
                    if re.search(pattern, line):
                        results.append((line_num, line.strip(), non_std_id))
    except UnicodeDecodeError:
        print(f"Could not decode file: {file_path}")
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

    return results

def find_all_non_standard_ids(root_dir: str) -> Dict[str, List[Tuple[int, str, str]]]:
    """
    Find all instances of non-standard IDs in the entire codebase.

    Args:
        root_dir: Root directory to search in

    Returns:
        Dictionary mapping file paths to lists of findings
    """
    results = {}

    # Walk through all Python, JavaScript, HTML, JSON, and other text files
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories that shouldn't contain source code
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]

        for file in files:
            if file.endswith(('.py', '.js', '.html', '.json', '.md', '.txt', '.xml')):
                file_path = os.path.join(root, file)

                findings = find_non_standard_ids_in_file(file_path)
                if findings:
                    results[file_path] = findings

    return results

def print_findings(results: Dict[str, List[Tuple[int, str, str]]]):
    """Print the findings in a readable format."""
    if not results:
        print("No non-standard IDs found in the codebase.")
        return

    print(f"\nFound {sum(len(findings) for findings in results.values())} instances of non-standard IDs in {len(results)} files:\n")

    for file_path, findings in results.items():
        print(f"File: {file_path}")
        for line_num, line_content, non_std_id in findings:
            std_id = NON_STANDARD_TO_STANDARD_MAPPINGS[non_std_id]
            print(f"  Line {line_num}: '{non_std_id}' should be '{std_id}'")
            print(f"    Content: {line_content[:100]}{'...' if len(line_content) > 100 else ''}")
        print()

def print_mapping_summary():
    """Print a summary of the non-standard to standard ID mappings."""
    print("\nNon-standard ID to Standard ID Mappings:")
    print("=" * 50)
    for non_std_id, std_id in NON_STANDARD_TO_STANDARD_MAPPINGS.items():
        print(f"  '{non_std_id}' → '{std_id}'")

if __name__ == "__main__":
    print("Searching for non-standard ID mappings in the codebase...")
    print_mapping_summary()

    root_directory = "/mnt/d/Dokumenty/slownik-wielki/flask-app"
    findings = find_all_non_standard_ids(root_directory)

    print_findings(findings)

    print(f"\nSummary: Found {sum(len(findings) for findings in findings.values())} instances in {len(findings)} files")