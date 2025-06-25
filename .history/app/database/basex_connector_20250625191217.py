"""
BaseX database connector for interacting with the BaseX XML database.
"""

import logging
from typing import Any, Optional, Dict, List, Callable, ContextManager
from contextlib import contextmanager

try:
    from BaseXClient.BaseXClient import Session as BaseXSession
except ImportError:
    logging.warning("BaseXClient not found. BaseX connector will not work.")
    BaseXSession = None

from app.utils.exceptions import DatabaseError
from .mock_connector import MockDatabaseConnector


class BaseXConnector:
    """
    Connector for interacting with the BaseX XML database.
    
    Attributes:
        host: Hostname of the BaseX server.
        port: Port number of the BaseX server.
        username: Username for authentication.
        password: Password for authentication.
        database: Name of the database to use.
        session: Active BaseX session, if connected.
    """
    
    def __init__(self, host: str, port: int, username: str, password: str, database: Optional[str] = None):
        """
        Initialize a BaseX connector.
        
        Args:
            host: Hostname of the BaseX server.
            port: Port number of the BaseX server.
            username: Username for authentication.
            password: Password for authentication.
            database: Name of the database to use.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.session = None
    
    def connect(self) -> bool:
        """
        Connect to the BaseX server.
        
        Returns:
            True if the connection was successful.
            
        Raises:
            DatabaseError: If the connection failed.
        """
        if BaseXSession is None:
            raise DatabaseError("BaseXClient module not found")
        
        try:
            self.session = BaseXSession(self.host, self.port, self.username, self.password)
            return True
        except Exception as e:
            self.session = None
            raise DatabaseError(f"Failed to connect to BaseX server: {str(e)}", e)
    
    def disconnect(self) -> None:
        """
        Disconnect from the BaseX server.
        """
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
            finally:
                self.session = None
    
    def is_connected(self) -> bool:
        """
        Check if the connector is connected to the BaseX server.
        
        Returns:
            True if connected, False otherwise.
        """
        return self.session is not None
    
    def execute_query(self, query: str) -> str:
        """
        Execute an XQuery query.
        
        Args:
            query: XQuery query string.
            
        Returns:
            Query result as a string.
            
        Raises:
            DatabaseError: If the query failed.
        """
        if not self.is_connected() or self.session is None:
            try:
                # Attempt to reconnect if the connection was lost
                self.connect()
                self.logger.info("Reconnected to BaseX server")
            except Exception as e:
                raise DatabaseError(f"Not connected to the database and reconnection failed: {str(e)}")
        try:
            return self.session.execute(query)
        except Exception as e:
            raise DatabaseError(f"Failed to execute query: {str(e)}", e)
    
    def execute_update(self, command: str) -> None:
        """
        Execute an update command.
        
        Args:
            command: Update command string.
            
        Raises:
            DatabaseError: If the command failed.
        """
        if not self.is_connected() or self.session is None:
            raise DatabaseError("Not connected to the database")
        try:
            self.session.execute(command)
        except Exception as e:
            raise DatabaseError(f"Failed to execute command: {str(e)}", e)
    
    def begin_transaction(self) -> None:
        """
        Begin a transaction.
        
        Raises:
            DatabaseError: If the transaction could not be started.
        """
        self.execute_query("BEGIN")
    
    def commit_transaction(self) -> None:
        """
        Commit a transaction.
        
        Raises:
            DatabaseError: If the transaction could not be committed.
        """
        self.execute_query("COMMIT")
    
    def rollback_transaction(self) -> None:
        """
        Rollback a transaction.
        
        Raises:
            DatabaseError: If the transaction could not be rolled back.
        """
        self.execute_query("ROLLBACK")
    
    @contextmanager
    def transaction(self) -> ContextManager:
        """
        Context manager for transactions.
        
        Yields:
            The connector instance.
            
        Raises:
            DatabaseError: If a transaction error occurs.
        """
        self.begin_transaction()
        try:
            yield self
            self.commit_transaction()
        except Exception as e:
            self.rollback_transaction()
            raise DatabaseError(f"Transaction failed: {str(e)}", e)
    
    def create_database(self, name: str) -> None:
        """
        Create a new database.
        
        Args:
            name: Name of the database to create.
            
        Raises:
            DatabaseError: If the database could not be created.
        """
        self.execute_query(f"CREATE DB {name}")
        self.database = name
    
    def drop_database(self, name: str) -> None:
        """
        Drop a database.
        
        Args:
            name: Name of the database to drop.
            
        Raises:
            DatabaseError: If the database could not be dropped.
        """
        self.execute_query(f"DROP DB {name}")
        if self.database == name:
            self.database = None
    
    def list_databases(self) -> List[str]:
        """
        List all databases on the server.
        
        Returns:
            List of database names.
            
        Raises:
            DatabaseError: If the databases could not be listed.
        """
        result = self.execute_query("LIST")
        return [line.strip() for line in result.split('\n') if line.strip()]
    
    def __enter__(self) -> 'BaseXConnector':
        """
        Enter context manager.
        
        Returns:
            The connector instance.
            
        Raises:
            DatabaseError: If the connection failed.
        """
        self.connect()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit context manager.
        
        Args:
            exc_type: Exception type, if an exception was raised.
            exc_val: Exception value, if an exception was raised.
            exc_tb: Exception traceback, if an exception was raised.
        """
        self.disconnect()
