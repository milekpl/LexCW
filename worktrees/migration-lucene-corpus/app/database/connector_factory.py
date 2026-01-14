"""
Database connector factory that chooses between BaseX and mock connectors.
"""

import logging
from typing import Union
from flask import current_app

from .basex_connector import BaseXConnector, BaseXSession
from .mock_connector import MockDatabaseConnector

logger = logging.getLogger(__name__)


def create_database_connector(host: str, port: int, username: str, password: str, 
                            database: str) -> Union[BaseXConnector, MockDatabaseConnector]:
    """
    Create a database connector, preferring BaseX if available.
    
    Args:
        host: Database host
        port: Database port
        username: Database username  
        password: Database password
        database: Database name
        
    Returns:
        Either a BaseXConnector or MockDatabaseConnector instance
    """
    
    # Check if we should force mock mode (for testing)
    if hasattr(current_app, 'config') and current_app.config.get('USE_MOCK_DATABASE', False):
        logger.info("Using mock database connector (forced by config)")
        return MockDatabaseConnector(host, port, username, password, database)
    
    # Try to use BaseX first (this is the preferred option)
    if BaseXSession is not None:
        try:
            connector = BaseXConnector(host, port, username, password, database)
            if connector.connect():
                logger.info("Successfully connected to BaseX database")
                return connector
            else:
                logger.error("BaseX connection failed - check if BaseX server is running on %s:%s", host, port)
                logger.info("To start BaseX server, run: basexserver")
        except Exception as e:
            logger.error("BaseX connector error: %s", str(e))
            logger.info("Make sure BaseX server is running and accessible")
    else:
        logger.error("BaseXClient library not found. Install with: pip install BaseXClient")
    
    # Fall back to mock connector only if BaseX fails
    logger.warning("Falling back to mock database connector. To use real BaseX:")
    logger.warning("1. Install BaseX server from https://basex.org/download/")
    logger.warning("2. Start BaseX server with: basexserver")
    logger.warning("3. Install Python client: pip install BaseXClient")
    return MockDatabaseConnector(host, port, username, password, database)
