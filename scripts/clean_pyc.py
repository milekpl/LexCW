#!/usr/bin/env python3
"""
Clean up Python bytecode files (.pyc) and __pycache__ directories.
This script removes all .pyc files and __pycache__ directories from the project.
"""

import os
import shutil
import sys
from pathlib import Path


def clean_pyc_files(directory):
    """Remove all .pyc files and __pycache__ directories from the specified directory."""
    directory_path = Path(directory)
    
    # Counter for cleaned items
    pyc_count = 0
    cache_count = 0
    
    print(f"Cleaning Python bytecode files in: {directory_path.absolute()}")
    
    # Walk through all directories
    for root, dirs, files in os.walk(directory_path):
        # Remove __pycache__ directories
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            print(f"Removing directory: {cache_dir}")
            shutil.rmtree(cache_dir)
            cache_count += 1
            dirs.remove('__pycache__')  # Don't walk into it
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc') or file.endswith('.pyo'):
                pyc_file = os.path.join(root, file)
                print(f"Removing file: {pyc_file}")
                os.remove(pyc_file)
                pyc_count += 1
    
    print("\nCleaning complete!")
    print(f"Removed {cache_count} __pycache__ directories")
    print(f"Removed {pyc_count} .pyc/.pyo files")


if __name__ == "__main__":
    # Use current directory if no argument provided
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    clean_pyc_files(target_dir)
