"""
Simple BaseX database connector without connection pooling.
Optimized for single-user dictionary applications.
"""

import logging
from typing import Optional

try:
    from BaseXClient.BaseXClient import Session as BaseXSession
except ImportError:
    logging.warning("BaseXClient not found. BaseX connector will not work.")
    BaseXSession = None

from app.utils.exceptions import DatabaseError


class BaseXConnectorSimple:
    """
    Simple connector for interacting with the BaseX XML database.
    No connection pooling - just direct connections for simplicity and speed.
    
    Attributes:
        host: Hostname of the BaseX server.
        port: Port number of the BaseX server.
        username: Username for authentication.
        password: Password for authentication.
        database: Name of the database to use.
    """
    
    def __init__(self, host: str, port: int, username: str, password: str, database: Optional[str] = None):
        """
        Initialize a simple BaseX connector.
        
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
        self.logger = logging.getLogger(__name__)
        self._session = None
    
    def connect(self) -> bool:
        """
        Establish connection to BaseX server.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            if BaseXSession is None:
                raise DatabaseError("BaseXClient module not found")
            
            self._session = BaseXSession(self.host, self.port, self.username, self.password)
            
            if self.database:
                self._session.execute(f"OPEN {self.database}")
                
            self.logger.debug(f"Connected to BaseX server at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to BaseX: {e}")
            self._session = None
            raise DatabaseError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Close the connection to BaseX server."""
        if self._session:
            try:
                self._session.close()
                self.logger.debug("Disconnected from BaseX server")
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {e}")
            finally:
                self._session = None
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._session is not None
    
    def execute_query(self, query: str) -> str:
        """
        Execute an XQuery and return the result.
        
        Args:
            query: XQuery string to execute.
            
        Returns:
            Query result as string.
        """
        if not self._session:
            self.connect()
        
        q = None
        try:
            q = self._session.query(query)
            result = q.execute()
            self.logger.debug(f"Query executed successfully: {query[:100]}...")
            return result
        except Exception as e:
            error_msg = f"Query execution failed: {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg)
        finally:
            if q:
                try:
                    q.close()
                except:
                    pass  # Ignore errors when closing
    
    def execute_command(self, command: str) -> str:
        """
        Execute a BaseX command.
        
        Args:
            command: BaseX command to execute.
            
        Returns:
            Command result as string.
        """
        if not self._session:
            self.connect()
        
        try:
            result = self._session.execute(command)
            self.logger.debug(f"Command executed successfully: {command}")
            return result
        except Exception as e:
            error_msg = f"Command execution failed: {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def execute_update(self, query: str) -> None:
        """
        Execute an XQuery update.
        
        Args:
            query: XQuery update string to execute.
        """
        if not self._session:
            self.connect()
        
        q = None
        try:
            q = self._session.query(query)
            q.execute()
            self.logger.debug(f"Update executed successfully: {query[:100]}...")
        except Exception as e:
            error_msg = f"Update execution failed: {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg)
        finally:
            if q:
                try:
                    q.close()
                except:
                    pass  # Ignore errors when closing
    
    def create_database(self, db_name: str, content: str = "") -> None:
        """
        Create a new database.
        
        Args:
            db_name: Name of the database to create.
            content: Initial content for the database.
        """
        try:
            command = f"CREATE DB {db_name}"
            if content:
                command += f" {content}"
            self.execute_command(command)
            self.logger.info(f"Database '{db_name}' created successfully")
        except Exception as e:
            error_msg = f"Failed to create database '{db_name}': {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def drop_database(self, db_name: str) -> None:
        """
        Drop a database.
        
        Args:
            db_name: Name of the database to drop.
        """
        try:
            self.execute_command(f"DROP DB {db_name}")
            self.logger.info(f"Database '{db_name}' dropped successfully")
        except Exception as e:
            error_msg = f"Failed to drop database '{db_name}': {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, '_session') and self._session:
            try:
                self._session.close()
            except:
                pass  # Ignore errors during cleanup
