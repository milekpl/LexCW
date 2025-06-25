"""
Script for importing a LIFT file into the dictionary database.

Usage:
    python -m scripts.import_lift path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import DatabaseError


def main():
    """Main entry point for the script."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
      # Load environment variables
    load_dotenv()
    
    # Check arguments
    if len(sys.argv) < 2:
        logger.error('Missing LIFT file argument')
        print('Usage: python -m scripts.import_lift path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]')
        sys.exit(1)
    
    lift_file = sys.argv[1]
    ranges_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check if the LIFT file exists
    if not os.path.exists(lift_file):
        logger.error('LIFT file not found: %s', lift_file)
        sys.exit(1)
    
    # Check if the ranges file exists if provided
    if ranges_file and not os.path.exists(ranges_file):
        logger.error('Ranges file not found: %s', ranges_file)
        sys.exit(1)
    
    # Get configuration from environment variables
    host = os.getenv('BASEX_HOST', 'localhost')
    port = int(os.getenv('BASEX_PORT', '1984'))
    username = os.getenv('BASEX_USERNAME', 'admin')
    password = os.getenv('BASEX_PASSWORD', 'admin')
    database = os.getenv('BASEX_DATABASE', 'dictionary')
    
    # Create a BaseX connector
    connector = BaseXConnector(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database
    )
    
    # Create a dictionary service
    dict_service = DictionaryService(connector)
      try:
        # Initialize the database with the LIFT file
        logger.info('Initializing database with LIFT file: %s', lift_file)
        dict_service.initialize_database(lift_file, ranges_file)
        
        # Get entry count
        entry_count = dict_service.get_entry_count()
        logger.info('Database initialized with %d entries', entry_count)
        
        # Success
        sys.exit(0)
        
    except DatabaseError as e:
        logger.error('Database error: %s', e)
        sys.exit(1)
    except Exception as e:
        logger.error('Error: %s', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
