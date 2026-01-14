#!/usr/bin/env python3
"""
Cleanup Script for Flask Dictionary App

This script removes temporary, debug, and test files that clutter the main directory.
It keeps only production files and moves test files to the appropriate directories.

Usage: python cleanup_project.py [--dry-run]
"""

import os
import shutil
import argparse
from pathlib import Path
import re


def get_files_to_cleanup():
    """Define patterns and specific files to clean up."""
    
    # Patterns for files to remove
    cleanup_patterns = [
        r'^debug_.*\.py$',
        r'^fix_.*\.py$',
        r'^test_.*\.py$',  # Test files in root should be moved to tests/
        r'^.*_demo\.py$',
        r'^.*_test\.html$',
        r'^simulate_.*\.py$',
        r'^quick_.*\.py$',
        r'^final_verification\.py$',
        r'^comprehensive_edit_test\.py$',
        r'^manual_test_.*\.py$',
        r'^validation_demo\.py$',
        r'^demo_.*\.py$',
        r'^form_state_demo\.html$',
        r'^debug_serializer\.js$',
    ]
    
    # Specific files to remove
    specific_files = [
        'add_debug_logging.py',
        'assign_homograph_numbers.py', 
        'check_homographs.py',
        'find_entry.py',
        'list_entries.py',
        'setup_postgresql.py',
    ]
    
    # Documentation files to keep in docs/ if they exist in root
    docs_files = [
        'CENTRALIZED_VALIDATION_REQUIREMENTS.md',
        'CENTRALIZED_VALIDATION_STATUS.md', 
        'ENTRY_FORM_REFACTORING_PLAN.md',
        'FORM_SERIALIZATION_ANALYSIS.md',
        'FORM_SERIALIZER_COMPLETION_SUMMARY.md',
        'MULTILINGUAL_NOTES_IMPLEMENTATION.md',
        'PRONUNCIATION_IMPLEMENTATION_SUMMARY.md',
        'VALIDATION_IMPLEMENTATION_SUMMARY.md',
        'VALIDATION_REQUIREMENTS_SUMMARY.md',
        'validation_rules.md',
    ]
    
    return cleanup_patterns, specific_files, docs_files


def should_cleanup_file(filename, patterns, specific_files):
    """Check if a file should be cleaned up based on patterns."""
    
    # Check specific files
    if filename in specific_files:
        return True
    
    # Check patterns
    for pattern in patterns:
        if re.match(pattern, filename):
            return True
    
    return False


def cleanup_project(dry_run=False):
    """Clean up the project directory."""
    
    project_root = Path(__file__).parent
    cleanup_patterns, specific_files, docs_files = get_files_to_cleanup()
    
    print(f"🧹 Cleaning up project directory: {project_root}")
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be actually deleted")
    
    files_to_remove = []
    files_to_move_to_docs = []
    files_to_move_to_tests = []
    
    # Scan root directory
    for item in project_root.iterdir():
        if item.is_file():
            filename = item.name
            
            # Check if it's a documentation file that should be in docs/
            if filename in docs_files:
                files_to_move_to_docs.append(item)
            # Check if it's a test file that should be in tests/
            elif filename.startswith('test_') and filename.endswith('.py'):
                files_to_move_to_tests.append(item)
            # Check if it should be cleaned up
            elif should_cleanup_file(filename, cleanup_patterns, specific_files):
                files_to_remove.append(item)
    
    # Report what will be done
    print(f"\n📋 Cleanup Summary:")
    print(f"   Files to remove: {len(files_to_remove)}")
    print(f"   Files to move to docs/: {len(files_to_move_to_docs)}")
    print(f"   Files to move to tests/: {len(files_to_move_to_tests)}")
    
    if not files_to_remove and not files_to_move_to_docs and not files_to_move_to_tests:
        print("✅ No cleanup needed - directory is already clean!")
        return
    
    # Show files that will be removed
    if files_to_remove:
        print(f"\n🗑️  Files to remove:")
        for file_path in files_to_remove:
            print(f"   - {file_path.name}")
    
    # Show files that will be moved to docs
    if files_to_move_to_docs:
        print(f"\n📚 Files to move to docs/:")
        for file_path in files_to_move_to_docs:
            print(f"   - {file_path.name}")
    
    # Show files that will be moved to tests
    if files_to_move_to_tests:
        print(f"\n🧪 Files to move to tests/:")
        for file_path in files_to_move_to_tests:
            print(f"   - {file_path.name}")
    
    if dry_run:
        print("\n🔍 DRY RUN COMPLETE - No changes made")
        return
    
    # Perform cleanup
    docs_dir = project_root / "docs"
    tests_dir = project_root / "tests"
    
    # Ensure target directories exist
    docs_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)
    
    # Remove files
    removed_count = 0
    for file_path in files_to_remove:
        try:
            file_path.unlink()
            removed_count += 1
            print(f"✅ Removed: {file_path.name}")
        except Exception as e:
            print(f"❌ Failed to remove {file_path.name}: {e}")
    
    # Move files to docs
    moved_to_docs_count = 0
    for file_path in files_to_move_to_docs:
        try:
            target_path = docs_dir / file_path.name
            if target_path.exists():
                print(f"⚠️  Skipping {file_path.name} - already exists in docs/")
            else:
                shutil.move(str(file_path), str(target_path))
                moved_to_docs_count += 1
                print(f"📚 Moved to docs/: {file_path.name}")
        except Exception as e:
            print(f"❌ Failed to move {file_path.name} to docs/: {e}")
    
    # Move files to tests
    moved_to_tests_count = 0
    for file_path in files_to_move_to_tests:
        try:
            target_path = tests_dir / file_path.name
            if target_path.exists():
                print(f"⚠️  Skipping {file_path.name} - already exists in tests/")
            else:
                shutil.move(str(file_path), str(target_path))
                moved_to_tests_count += 1
                print(f"🧪 Moved to tests/: {file_path.name}")
        except Exception as e:
            print(f"❌ Failed to move {file_path.name} to tests/: {e}")
    
    print(f"\n🎉 Cleanup completed!")
    print(f"   Files removed: {removed_count}")
    print(f"   Files moved to docs/: {moved_to_docs_count}")
    print(f"   Files moved to tests/: {moved_to_tests_count}")
    print(f"\n📁 Project directory is now clean and organized!")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Clean up Flask dictionary app project")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be cleaned up without making changes")
    
    args = parser.parse_args()
    
    try:
        cleanup_project(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n⏹️  Cleanup cancelled by user")
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
