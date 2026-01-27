"""
Simple BaseX database connector without connection pooling.
Optimized for single-user dictionary applications.
"""

import logging
import threading
import os
from typing import Any, Optional, Dict, List
from contextlib import contextmanager

try:
    from BaseXClient.BaseXClient import Session as BaseXSession
except ImportError:
    logging.warning("BaseXClient not found. BaseX connector will not work.")
    BaseXSession = None

from app.utils.exceptions import DatabaseError


class BaseXConnector:
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
        self._base_database = database  # Store original database name
        self.logger = logging.getLogger(__name__)
        self._session = None
        self._lock = threading.RLock()
        self._current_db = None
        # NEW: Control aggressive disconnection
        self.aggressive_disconnect = os.environ.get('BASEX_AGGRESSIVE_DISCONNECT') == 'true'
    
    @property
    def database(self) -> Optional[str]:
        """Get the effective database name, checking TEST_DB_NAME environment variable first.
        
        This allows tests to override the database dynamically without recreating the connector.
        """
        # In test mode, prefer TEST_DB_NAME environment variable
        test_db = os.environ.get('TEST_DB_NAME')
        if test_db:
            return test_db
        # Fall back to the base database name
        return self._base_database
    
    @database.setter
    def database(self, value: Optional[str]):
        """Set the base database name."""
        self._base_database = value
    
    def connect(self) -> bool:
        """
        Establish connection to BaseX server with safety checks.
        
        Returns:
            True if connection successful, False otherwise.
            
        Raises:
            DatabaseError: If connection fails or safety checks fail
        """
        with self._lock:
            try:
                if BaseXSession is None:
                    raise DatabaseError("BaseXClient module not found")
                
                # If already connected, check if connection is alive
                if self._session:
                    try:
                        self._session.execute("xquery 1")
                        return True
                    except:
                        self._session = None
                        self._current_db = None

                self._session = BaseXSession(self.host, self.port, self.username, self.password)

                if self.database:
                    # Safety check: Prevent connecting to production databases in test mode
                    if self._is_test_mode() and not self._is_safe_database_name(self.database):
                        raise DatabaseError(f"Refusing to connect to potentially unsafe database in test mode: {self.database}")

                    # Check if database exists, create if not
                    try:
                        self._session.execute(f"OPEN {self.database}")
                        self._current_db = self.database
                        self.logger.info(f"Opened BaseX database: {self.database}")
                    except Exception as open_error:
                        # Database doesn't exist, create it
                        if "not found" in str(open_error).lower() or "unknown database" in str(open_error).lower():
                            self.logger.info(f"Database '{self.database}' not found, creating empty database")
                            self._session.execute(f"CREATE DB {self.database}")
                            self._current_db = self.database
                        else:
                            raise
                else:
                    self.logger.info("No BaseX database configured for this connector")
                    self._current_db = None
                    
                self.logger.debug(f"Connected to BaseX server at {self.host}:{self.port} (database: {self.database})")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to connect to BaseX: {e}")
                self._session = None
                self._current_db = None
                raise DatabaseError(f"Connection failed: {e}")
    
    def _is_test_mode(self) -> bool:
        """
        Check if we're running in test mode.
        
        Returns:
            True if running in test mode, False otherwise
        """
        import os
        return os.environ.get('FLASK_CONFIG') == 'testing' or os.environ.get('TESTING') == 'true'
    
    def _is_safe_database_name(self, db_name: str) -> bool:
        """
        Validate that a database name is safe for testing.
        
        Args:
            db_name: The database name to validate
            
        Returns:
            True if the database name is safe for testing, False otherwise
        """
        if not db_name:
            return False
            
        # Must start with 'test_'
        if not db_name.startswith('test_'):
            return False
        
        # Must not contain protected patterns
        protected_patterns = {'dictionary', 'production', 'backup', 'main', 'dev', 'staging'}
        db_name_lower = db_name.lower()
        for protected in protected_patterns:
            if protected in db_name_lower:
                return False
                
        # In test mode, we allow anything starting with 'test_' that passed the protected check
        return True
    
    def disconnect(self) -> None:
        """Close the connection to BaseX server."""
        with self._lock:
            if self._session:
                try:
                    self._session.close()
                    self.logger.debug("Disconnected from BaseX server")
                except Exception as e:
                    self.logger.warning(f"Error during disconnect: {e}")
                finally:
                    self._session = None
                    self._current_db = None
    
    def _ensure_correct_database(self) -> None:
        """Ensure the correct database is open, switching if TEST_DB_NAME changed.
        
        This is called before each operation to handle dynamic database switching in tests.
        """
        if not self._session:
            return  # Will connect with correct DB later
        
        target_db = self.database
        if target_db and target_db != self._current_db:
            # Database changed (e.g., TEST_DB_NAME was updated), switch to it
            try:
                self.logger.debug(f"Switching database from {self._current_db} to {target_db}")
                self._session.execute(f"OPEN {target_db}")
                self._current_db = target_db
            except Exception as e:
                # Database might not exist, try creating it
                if "not found" in str(e).lower() or "unknown database" in str(e).lower():
                    self.logger.info(f"Database '{target_db}' not found, creating it")
                    self._session.execute(f"CREATE DB {target_db}")
                    self._current_db = target_db
                else:
                    raise
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        with self._lock:
            return self._session is not None
    
    def execute_query(self, query: str, db_name: str = None) -> str:
        """
        Execute an XQuery and return the result.
        Logs the full query string for debugging.
        Args:
            query: XQuery string to execute.
            db_name: Optional database name to execute query against.
        Returns:
            Query result as string.
        """
        with self._lock:
            if not self._session:
                self.connect()
            
            # Ensure we're using the correct database (handles TEST_DB_NAME changes)
            self._ensure_correct_database()

            # Determine target database priority:
            # 1. Explicit db_name argument
            # 2. Flask request context (g.project_db_name)
            # 3. collection('db_name') in query
            # 4. Connector's default database
            
            target_db = None
            target_db_from_regex = False
            if db_name:
                target_db = db_name
            else:
                # Try to get from Flask global context
                try:
                    from flask import has_request_context, g
                    if has_request_context() and hasattr(g, 'project_db_name'):
                        target_db = g.project_db_name
                except ImportError:
                    pass

                if not target_db:
                    try:
                        import re as _re
                        m = _re.search(r"collection\(\s*'([^']+)'\s*\)", query)
                        if m:
                            target_db = m.group(1)
                            target_db_from_regex = True
                    except Exception:
                        pass
            
            if not target_db:
                target_db = self.database

            # Switch database if needed
            if target_db and target_db != self._current_db:
                self.logger.debug(f"Switching from DB '{self._current_db}' to '{target_db}'")
                try:
                    self._session.execute(f"OPEN {target_db}")
                    self._current_db = target_db
                except Exception as e:
                    self.logger.error(f"Failed to switch to database '{target_db}': {e}")
                    # Proceeding might fail if the query depends on context, but let's try
                    pass

            # Log the full query string for debugging
            # Build request context info for tracing
            request_info = ''
            try:
                from flask import has_request_context, g, request
                if has_request_context():
                    request_info = f" [request_id={getattr(g, 'request_id', None)} path={request.path}]"
            except Exception:
                pass

            # Log query summary with truncated content instead of full query
            query_preview = query[:200] + '...' if len(query) > 200 else query
            self.logger.debug("BaseX query on DB '%s'%s: %s", self._current_db, request_info, query_preview)

            # Strip 'xquery ' prefix if present (it's often added by callers but Session.query doesn't want it)
            clean_query = query
            if query.strip().lower().startswith('xquery '):
                clean_query = query.strip()[7:].strip()

            q = None
            try:
                q = self._session.query(clean_query)
                result = q.execute()
                self.logger.debug(f"Query executed successfully: {query[:100]}...")
                return result
            except Exception as e:
                error_msg = f"Query execution failed: {e}\nQuery was:\n{query}"
                self.logger.error(error_msg)
                
                # Attempt intelligent DB substitution for missing DB resources.
                try:
                    import re as _re
                    m = _re.search(r"collection\(\s*'([^']+)'\s*\)", query)
                    if m:
                        referenced_db = m.group(1)
                        env_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')
                        if env_db and env_db != referenced_db:
                            self.logger.warning(f"Referenced DB '{referenced_db}' not found; trying substitution to TEST_DB_NAME '{env_db}'")
                            alt_query = query.replace(f"collection('{referenced_db}')", f"collection('{env_db}')")
                            try:
                                # Ensure session is opened to the env DB temporarily
                                self._session.execute(f"OPEN {env_db}")
                                self._current_db = env_db
                                q = self._session.query(alt_query)
                                result = q.execute()
                                self.logger.info(f"Query succeeded after substituting collection('{referenced_db}') -> collection('{env_db}')")
                                return result
                            except Exception as alt_e:
                                self.logger.error(f"Substitution retry failed: {alt_e}")
                except Exception:
                    pass

                # If error is related to connection/session, try to reconnect and retry once
                err_str = str(e)
                if isinstance(e, (IOError, OSError)) or "Unknown Query ID" in err_str or "Broken pipe" in err_str or "Connection reset" in err_str:
                    self.logger.warning("Connection issue detected, retrying query...")
                    try:
                        self.disconnect()
                        self.connect()
                        # Restore target DB after reconnect if it wasn't the default
                        if target_db and target_db != self.database:
                             self._session.execute(f"OPEN {target_db}")
                             self._current_db = target_db
                        
                        q = self._session.query(query)
                        result = q.execute()
                        return result
                    except Exception as retry_e:
                        self.logger.error(f"Retry failed: {retry_e}")
                        raise DatabaseError(error_msg)

                raise DatabaseError(error_msg)
            finally:
                if q:
                    try:
                        q.close()
                    except:
                        pass  # Ignore errors when closing
                
                # Optionally DISCONNECT after query to release ALL locks and sessions
                if self.aggressive_disconnect and self._session:
                    try:
                        self.disconnect()
                    except Exception:
                        pass
    
    def execute_lift_query(self, query: str, has_namespace: bool = False, db_name: str = None) -> str:
        """
        Execute a LIFT-specific query with namespace handling.
        
        Args:
            query: XQuery query string (may include namespace prologue)
            has_namespace: Whether the database contains namespaced LIFT elements
            db_name: Optional database name to execute query against.
            
        Returns:
            Query result as string
        """
        # Ensure the query has the 'xquery' prefix for BaseX compatibility
        if not query.strip().startswith('xquery'):
            query = f"xquery {query}"
        
        return self.execute_query(query, db_name=db_name)

    def execute_command(self, command: str) -> str:
        """
        Execute a BaseX command.
        
        Args:
            command: BaseX command to execute.
            
        Returns:
            Command result as string.
        """
        with self._lock:
            if not self._session:
                self.connect()
            
            # Ensure we're using the correct database (handles TEST_DB_NAME changes)
            self._ensure_correct_database()
            
            try:
                result = self._session.execute(command)
                self.logger.debug(f"Command executed successfully: {command}")
                return result
            except (IOError, OSError) as e:
                # Session might be lost (e.g. killed by another process)
                self.logger.warning(f"Session lost during command execution: {e}. Attempting to reconnect...")
                try:
                    self.disconnect()
                    self.connect()
                    # Retry once
                    result = self._session.execute(command)
                    self.logger.info(f"Reconnected and successfully executed command: {command}")
                    return result
                except Exception as retry_e:
                    error_msg = f"Command execution failed after reconnection attempt: {retry_e}"
                    self.logger.error(error_msg)
                    raise DatabaseError(error_msg)
            except Exception as e:
                error_msg = f"Command execution failed: {e}"
                self.logger.error(error_msg)
                raise DatabaseError(error_msg)
    
    def execute_update(self, query: str, db_name: str = None) -> None:
        """
        Execute an XQuery update.
        
        Args:
            query: XQuery update string to execute.
            db_name: Optional database name to execute update against.
        """
        with self._lock:
            if not self._session:
                self.connect()
            
            # Determine target database
            target_db = None
            if db_name:
                target_db = db_name
            else:
                # Try to get from Flask global context
                try:
                    from flask import has_request_context, g
                    if has_request_context() and hasattr(g, 'project_db_name'):
                        target_db = g.project_db_name
                except ImportError:
                    pass

                if not target_db:
                    try:
                        import re as _re
                        m = _re.search(r"collection\(\s*'([^']+)'\s*\)", query)
                        if m:
                            target_db = m.group(1)
                    except Exception:
                        pass
            
            if not target_db:
                target_db = self.database

            # Switch database if needed
            if target_db and target_db != self._current_db:
                self.logger.debug(f"Switching from DB '{self._current_db}' to '{target_db}' for update")
                try:
                    self._session.execute(f"OPEN {target_db}")
                    self._current_db = target_db
                except Exception:
                    # Proceeding, error might occur
                    pass

            # Log the full query string for debugging
            # Build request context info for tracing
            request_info = ''
            try:
                from flask import has_request_context, g, request
                if has_request_context():
                    request_info = f" [request_id={getattr(g, 'request_id', None)} path={request.path}]"
            except Exception:
                pass

            # Log the full query string for debugging
            self.logger.info("Executing BaseX update on DB '%s'%s:\n%s", self._current_db, request_info, query)

            # Strip 'xquery ' prefix if present
            clean_query = query
            if query.strip().lower().startswith('xquery '):
                clean_query = query.strip()[7:].strip()
            # If the query explicitly references a different database via collection('db'),
            # and a test DB is active (TEST_DB_NAME or BASEX_DATABASE), substitute the
            # referenced DB with the active test DB before executing. This prevents stale
            # queries that were built with a previous DB name from silently returning
            # results from the wrong database when tests switch DBs mid-run.
            try:
                import re as _re
                m = _re.search(r"collection\(\s*'([^']+)'\s*\)", clean_query)
                if m:
                    referenced_db = m.group(1)
                    # Decide which DB we should target for substitution. Use the
                    # runtime active DB (TEST_DB_NAME or connector default) so that
                    # queries built earlier with a stale db reference are corrected
                    # to the current test DB. This is especially important when the
                    # session Flask server services multiple tests and TEST_DB_NAME
                    # changes between requests.
                    runtime_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE') or self.database

                    if runtime_db and referenced_db != runtime_db:
                        alt_query = clean_query.replace(f"collection('{referenced_db}')", f"collection('{runtime_db}')")
                        self.logger.warning(f"Substituting collection('{referenced_db}') -> collection('{runtime_db}') before execution to target current DB")
                        clean_query = alt_query
                        # Ensure session is opened to runtime_db for consistency
                        try:
                            if self._current_db != runtime_db:
                                self._session.execute(f"OPEN {runtime_db}")
                                self._current_db = runtime_db
                        except Exception:
                            # If open fails, continue and let query execution handle errors
                            pass
            except Exception:
                pass
            q = None
            try:
                q = self._session.query(clean_query)
                result = q.execute()
                self.logger.debug(f"Update executed successfully: {query[:100]}...")
                
            except (IOError, OSError) as e:
                self.logger.warning(f"Session lost during update: {e}. Attempting to reconnect...")
                try:
                    self.disconnect()
                    self.connect()
                    # Restore target DB
                    if target_db:
                        self._session.execute(f"OPEN {target_db}")
                        self._current_db = target_db
                    
                    q = self._session.query(clean_query)
                    result = q.execute()
                    self.logger.info("Reconnected and successfully executed update")
                except Exception as retry_e:
                    error_msg = f"Update execution failed after reconnection: {retry_e}"
                    self.logger.error(error_msg)
                    raise DatabaseError(error_msg)
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
                
                # CRITICAL: Close and reopen connection to force persistence
                # BaseX doesn't commit changes until the session is properly closed
                try:
                    if self._session:
                        self.disconnect()
                        self.logger.debug("Disconnected session to persist changes")
                    
                    if not self.aggressive_disconnect:
                        # Reconnect for next operation
                        self.connect()
                        self.logger.debug("Reopened session after persist")
                        
                        # Always CLOSE after reconnect to ensure no DB is open by default
                        try:
                            if self._session:
                                self._session.execute("CLOSE")
                            self._current_db = None
                        except Exception:
                            pass
                except Exception as reconnect_error:
                    self.logger.warning(f"Failed to handle persistence after update: {reconnect_error}")
    
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
    
    def close_database(self) -> None:
        """
        Close the currently open database.
        """
        with self._lock:
            if self._session:
                try:
                    self._session.execute("CLOSE")
                    self.logger.debug(f"Closed database (previous: {self._current_db})")
                except Exception as e:
                    self.logger.debug(f"Error while closing database: {e}")
                finally:
                    self._current_db = None

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

    def get_status(self) -> Dict[str, Any]:
        """Return a snapshot of the connector's status for diagnostics.

        Returns:
            A dictionary containing connection status, current DB, configured
            runtime database (which considers TEST_DB_NAME), and flags such as
            aggressive_disconnect.
        """
        with self._lock:
            return {
                'connected': self._session is not None,
                'current_db': self._current_db,
                'configured_database': self.database,
                'aggressive_disconnect': self.aggressive_disconnect,
            }
