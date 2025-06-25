"""
Script for importing a LIFT file into the dictionary database.

Usage:
    python -m scripts.import_lift [--init] path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]

Options:
    --init    Initialize the database, replacing all existing data.
              If not provided, the script will merge the LIFT file into the existing database.
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
    
    # Parse arguments
    args = sys.argv[1:]
    if not args or '--help' in args or '-h' in args:
        print('Usage: python -m scripts.import_lift [--init] path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]')
        print('  --init: Initialize the database, replacing all existing data.')
        print('          If not provided, the script will merge the LIFT file into the existing database.')
        sys.exit(1)

    init_mode = False
    if '--init' in args:
        init_mode = True
        args.remove('--init')

    if not args:
        logger.error('Missing LIFT file argument')
        sys.exit(1)
    
    lift_file = args[0]
    ranges_file = args[1] if len(args) > 1 else None
    
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
        # Connect to the database
        if not connector.connect():
            raise DatabaseError("Failed to connect to the database.")

        if init_mode:
            logger.info('Initializing database with LIFT file: %s', lift_file)
            dict_service.initialize_database(lift_file, ranges_file)
            logger.info('Database initialized successfully.')
            _, total_count = dict_service.list_entries(limit=1)
            logger.info('Database now contains %d entries', total_count)
        else:
            logger.info('Merging LIFT file into database: %s', lift_file)
            imported_count = dict_service.import_lift(lift_file)
            logger.info('Merged %d entries.', imported_count)
        
        # Success
        sys.exit(0)
        
    except DatabaseError as e:
        logger.error('Database error: %s', e, exc_info=True)
        sys.exit(1)
    except (FileNotFoundError, IOError) as e:
        logger.error('File error: %s', e, exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error('Unexpected error: %s', e, exc_info=True)
        sys.exit(1)
    finally:
        if connector:
            connector.close()


if __name__ == '__main__':
    main()
