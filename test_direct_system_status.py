#!/usr/bin/env python
"""
Test script to check system status directly.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_system_status():
    """Test getting system status from DictionaryService."""
    # Create connector and service
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=os.getenv('BASEX_DATABASE', 'dictionary')
    )
    
    # Connect to BaseX
    try:
        connector.connect()
        logger.info("Connected to BaseX server")
    except Exception as e:
        logger.error(f"Failed to connect to BaseX server: {e}")
        return False
    
    # Create dictionary service
    dict_service = DictionaryService(connector)
    
    # Get system status
    try:
        system_status = dict_service.get_system_status()
        logger.info(f"System status retrieved: {system_status}")
        
        # Check values
        logger.info(f"db_connected: {system_status.get('db_connected', 'ERROR')}")
        logger.info(f"last_backup: {system_status.get('last_backup', 'ERROR')}")
        logger.info(f"storage_percent: {system_status.get('storage_percent', 'ERROR')}")
        
        return True
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return False
    finally:
        # Disconnect
        connector.disconnect()

if __name__ == "__main__":
    result = test_system_status()
    logger.info(f"Test result: {'Success' if result else 'Failure'}")
