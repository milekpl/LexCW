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
    Create a database connector, using BaseX if available, otherwise mock.
    
    Args:
        host: Database host
        port: Database port
        username: Database username  
        password: Database password
        database: Database name
        
    Returns:
        Either a BaseXConnector or MockDatabaseConnector instance
    """
    
    # Check if we should force mock mode
    if hasattr(current_app, 'config') and current_app.config.get('USE_MOCK_DATABASE', False):
        logger.info("Using mock database connector (forced by config)")
        return MockDatabaseConnector(host, port, username, password, database)
    
    # Try to use BaseX if available
    if BaseXSession is not None:
        try:
            connector = BaseXConnector(host, port, username, password, database)
            if connector.connect():
                logger.info("Using BaseX database connector")
                return connector
            else:
                logger.warning("BaseX connection failed, falling back to mock connector")
        except Exception as e:
            logger.warning(f"BaseX connector failed: {e}, falling back to mock connector")
    
    # Fall back to mock connector
    logger.info("Using mock database connector")
    return MockDatabaseConnector(host, port, username, password, database)
