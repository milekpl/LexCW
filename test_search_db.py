from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a BaseX connector
connector = BaseXConnector(
    host='localhost',
    port=1984,
    username='admin',
    password='admin',
    database='dictionary'  # This is what's used in the app
)

# Create a dictionary service
service = DictionaryService(connector)

# Get entry count
try:
    count = service.count_entries()
    print(f"Total entries in database: {count}")
except Exception as e:
    print(f"Error counting entries: {e}")

# Try to search for entries
try:
    print("Searching for 'test'...")
    entries, total = service.search_entries("test")
    print(f"Found {total} entries")
    for entry in entries[:5]:  # Print first 5 entries
        print(f"- {entry.id}: {entry.lexical_unit}")
except Exception as e:
    print(f"Error searching entries: {e}")
