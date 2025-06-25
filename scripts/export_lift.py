"""
Script for exporting the dictionary to a LIFT file.

Usage:
    python -m scripts.export_lift path/to/output.lift
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
        logger.error('Missing output file argument')
        print('Usage: python -m scripts.export_lift path/to/output.lift')
        sys.exit(1)
    
    output_file = sys.argv[1]
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
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
            logger.error('Failed to connect to the database')
            sys.exit(1)
        
        # Export the dictionary
        logger.info('Exporting dictionary to LIFT file: %s', output_file)
        dict_service.export_to_lift(output_file)
        
        # Get entry count
        entry_count = dict_service.get_entry_count()
        logger.info('Dictionary exported with %d entries', entry_count)
        
        # Success
        sys.exit(0)
        
    except DatabaseError as e:
        logger.error('Database error: %s', e, exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error('Error: %s', e, exc_info=True)
        sys.exit(1)
    finally:
        if connector:
            connector.disconnect()


if __name__ == '__main__':
    main()
