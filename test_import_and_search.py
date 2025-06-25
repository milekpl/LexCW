import os
import sys
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

def main():
    """
    Test importing a LIFT file and check if it updates the database correctly.
    """
    # Create a BaseX connector with the correct database name
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database='dictionary'
    )
    
    # Create a dictionary service
    service = DictionaryService(connector)
    
    # Check initial entry count
    try:
        initial_count = service.count_entries()
        print(f"Initial entry count: {initial_count}")
    except Exception as e:
        print(f"Error getting initial count: {e}")
        sys.exit(1)
    
    # Path to the sample LIFT file
    lift_file = os.path.join('sample-lift-file', 'sample-lift-file.lift')
    ranges_file = os.path.join('sample-lift-file', 'sample-lift-file.lift-ranges')
    
    if not os.path.exists(lift_file):
        print(f"LIFT file not found: {lift_file}")
        sys.exit(1)
    
    # Initialize the database (this should create a new database)
    try:
        print(f"Initializing database with {lift_file}")
        service.initialize_database(lift_file, ranges_file)
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
    
    # Check entry count after initialization
    try:
        new_count = service.count_entries()
        print(f"Entry count after initialization: {new_count}")
    except Exception as e:
        print(f"Error getting count after init: {e}")
        sys.exit(1)
    
    # Now try searching
    try:
        print("Searching for 'test'...")
        entries, total = service.search_entries("test")
        print(f"Found {total} entries for 'test'")
        for entry in entries[:5]:  # Print first 5 entries
            print(f"- {entry.id}: {entry.lexical_unit}")
    except Exception as e:
        print(f"Error searching entries: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
