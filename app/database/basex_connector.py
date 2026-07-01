"""
BaseX database connector with connection pooling.
Enables concurrent queries while serializing operations per-session.
"""

import logging
import threading
import os
import queue
from typing import Any, Optional, Dict, List
from contextlib import contextmanager

try:
    from BaseXClient.BaseXClient import Session as BaseXSession
except ImportError:
    logging.warning("BaseXClient not found. BaseX connector will not work.")
    BaseXSession = None

from app.utils.exceptions import DatabaseError


class _BaseXConnection:
    """Wraps a raw BaseX session with per-connection state."""

    __slots__ = ('session', 'current_db', 'logger')

    def __init__(self, host: str, port: int, username: str, password: str):
        self.session = BaseXSession(host, port, username, password) if BaseXSession else None
        self.current_db: Optional[str] = None
        self.logger = logging.getLogger(__name__)

    def ensure_db(self, db_name: Optional[str]) -> None:
        if db_name and db_name != self.current_db:
            self.session.execute(f"OPEN {db_name}")
            self.current_db = db_name

    def close(self) -> None:
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None
            self.current_db = None


class BaseXConnector:
    """
    Thread-safe BaseX connector with connection pooling.

    Maintains a pool of TCP connections to BaseX, allowing concurrent
    read operations. Each connection is used by at most one thread at a time.

    Attributes:
        host: Hostname of the BaseX server.
        port: Port number of the BaseX server.
        username: Username for authentication.
        password: Password for authentication.
        database: Name of the database to use.
    """

    def __init__(self, host: str, port: int, username: str, password: str,
                 database: Optional[str] = None, pool_size: int = 4):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._base_database = database
        self.logger = logging.getLogger(__name__)

        self._pool: queue.Queue = queue.Queue()
        self._max_pool = pool_size
        self._semaphore = threading.BoundedSemaphore(pool_size)
        self._created = 0

    # ---- Database name resolution ----

    @property
    def database(self) -> Optional[str]:
        test_db = os.environ.get('TEST_DB_NAME')
        if test_db:
            return test_db
        return self._base_database

    @database.setter
    def database(self, value: Optional[str]):
        self._base_database = value

    # ---- Connection lifecycle ----

    def _make_connection(self) -> _BaseXConnection:
        if BaseXSession is None:
            raise DatabaseError("BaseXClient module not found")
        conn = _BaseXConnection(self.host, self.port, self.username, self.password)
        if self.database:
            if self._is_test_mode() and not self._is_safe_database_name(self.database):
                raise DatabaseError(
                    f"Refusing to connect to potentially unsafe database in test mode: {self.database}"
                )
            try:
                conn.session.execute(f"OPEN {self.database}")
                conn.current_db = self.database
                self.logger.info(f"Opened BaseX database: {self.database}")
            except Exception as open_error:
                if "not found" in str(open_error).lower() or "unknown database" in str(open_error).lower():
                    self.logger.info(f"Database '{self.database}' not found, creating empty database")
                    conn.session.execute(f"CREATE DB {self.database}")
                    conn.current_db = self.database
                else:
                    conn.close()
                    raise
        else:
            self.logger.info("No BaseX database configured for this connector")
        self.logger.debug(
            f"Connected to BaseX server at {self.host}:{self.port} (database: {self.database})"
        )
        return conn

    def _acquire(self, timeout: float = 30) -> _BaseXConnection:
        """Get a connection from the pool. Creates a new one if under max."""
        self._semaphore.acquire()

        try:
            conn = self._pool.get_nowait()
            return conn
        except queue.Empty:
            pass

        conn = self._make_connection()
        self._created += 1
        return conn

    def _release(self, conn: _BaseXConnection) -> None:
        self._pool.put(conn)
        self._semaphore.release()

    def _discard(self, conn: _BaseXConnection) -> None:
        conn.close()
        self._semaphore.release()

    # ---- Compat shim: connect/disconnect for legacy callers ----

    def connect(self) -> bool:
        """Pre-warm the pool by creating one connection."""
        try:
            conn = self._acquire()
            self._release(conn)
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to BaseX: {e}")
            raise DatabaseError(f"Connection failed: {e}")

    def disconnect(self) -> None:
        """Close all pooled connections and release semaphore slots."""
        n = 0
        while True:
            try:
                conn = self._pool.get_nowait()
                conn.close()
                n += 1
            except queue.Empty:
                break
        for _ in range(n):
            try:
                self._semaphore.release()
            except ValueError:
                break
        self._created = 0

    def is_connected(self) -> bool:
        """Check if we have a live connection WITHOUT creating a new one."""
        try:
            conn = self._pool.get_nowait()
            alive = conn.session is not None
            self._pool.put(conn)
            return alive
        except queue.Empty:
            return False
        except Exception:
            return False

    # ---- XQuery execution (read) ----

    _RE_COLLECTION = None  # lazy import

    @staticmethod
    def _extract_collection_db(query: str) -> Optional[str]:
        import re
        m = re.search(r"collection\(\s*'([^']+)'\s*\)", query)
        if m:
            return m.group(1)
        return None

    def execute_query(self, query: str, db_name: str = None) -> str:
        """
        Execute an XQuery and return the result.

        Args:
            query: XQuery string to execute.
            db_name: Optional database name to execute query against.

        Returns:
            Query result as string.
        """
        conn = self._acquire()
        try:
            # Determine target database
            target_db = db_name
            if not target_db:
                try:
                    from flask import has_request_context, g
                    if has_request_context() and hasattr(g, 'project_db_name'):
                        target_db = g.project_db_name
                except ImportError:
                    pass
            if not target_db:
                target_db = self._extract_collection_db(query)
            if not target_db:
                target_db = self.database

            if target_db:
                conn.ensure_db(target_db)

            request_info = ''
            try:
                from flask import has_request_context, g, request
                if has_request_context():
                    request_info = f" [request_id={getattr(g, 'request_id', None)} path={request.path}]"
            except Exception:
                pass

            query_preview = query[:200] + '...' if len(query) > 200 else query
            self.logger.debug("BaseX query on DB '%s'%s: %s", conn.current_db, request_info, query_preview)

            clean_query = query
            if query.strip().lower().startswith('xquery '):
                clean_query = query.strip()[7:].strip()

            q = None
            try:
                q = conn.session.query(clean_query)
                result = q.execute()
                self.logger.debug(f"Query executed successfully: {query[:100]}...")
                return result
            except Exception as e:
                # Attempt DB substitution for test mode
                try:
                    ref_db = self._extract_collection_db(clean_query)
                    if ref_db:
                        env_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')
                        if env_db and env_db != ref_db:
                            alt_query = clean_query.replace(
                                f"collection('{ref_db}')", f"collection('{env_db}')"
                            )
                            self.logger.warning(
                                f"Substituting collection('{ref_db}') -> collection('{env_db}')"
                            )
                            conn.ensure_db(env_db)
                            q = conn.session.query(alt_query)
                            result = q.execute()
                            self.logger.info("Query succeeded after DB substitution")
                            return result
                except Exception:
                    pass

                err_str = str(e)
                if isinstance(e, (IOError, OSError)) or "Broken pipe" in err_str or "Connection reset" in err_str:
                    self.logger.warning("Connection lost, discarding...")
                    self._discard(conn)
                    conn = self._acquire()
                    if target_db:
                        conn.ensure_db(target_db)
                    q = conn.session.query(clean_query)
                    result = q.execute()
                    return result

                raise DatabaseError(f"Query execution failed: {e}\nQuery:\n{query}")
            finally:
                if q:
                    try:
                        q.close()
                    except Exception:
                        pass
        finally:
            self._release(conn)

    def execute_lift_query(self, query: str, has_namespace: bool = False, db_name: str = None) -> str:
        if not query.strip().startswith('xquery'):
            query = f"xquery {query}"
        return self.execute_query(query, db_name=db_name)

    # ---- BaseX command execution ----

    def execute_command(self, command: str) -> str:
        # e2e tests can experience transient socket drops.
        # Retry with a fresh connection a few times before failing.
        last_error: Exception | None = None
        attempts = 3
        for attempt in range(1, attempts + 1):
            conn = self._acquire()
            try:
                if conn.current_db is None and self.database:
                    conn.ensure_db(self.database)

                try:
                    result = conn.session.execute(command)
                    self.logger.debug(f"Command executed successfully: {command}")
                    return result
                except (IOError, OSError) as e:
                    last_error = e
                    self.logger.warning(
                        "Session lost during command (attempt %s/%s): %s; discarding...",
                        attempt,
                        attempts,
                        e,
                    )
                    self._discard(conn)
                    # Acquire/discard again next attempt.
                    conn = None
                    continue
                except Exception as e:
                    raise DatabaseError(f"Command execution failed: {e}")
            finally:
                # Only release if we didn't discard.
                if conn is not None:
                    self._release(conn)

        raise DatabaseError(f"Command execution failed after {attempts} attempts: {last_error}")

    # ---- XQuery update execution ----

    def execute_update(self, query: str, db_name: str = None) -> None:
        # Retry transient socket drops during update execution.
        last_error: Exception | None = None
        attempts = 3
        for attempt in range(1, attempts + 1):
            conn = self._acquire()
            try:
                target_db = db_name
                if not target_db:
                    try:
                        from flask import has_request_context, g
                        if has_request_context() and hasattr(g, 'project_db_name'):
                            target_db = g.project_db_name
                    except ImportError:
                        pass
                if not target_db:
                    target_db = self._extract_collection_db(query)
                if not target_db:
                    target_db = self.database

                if target_db:
                    conn.ensure_db(target_db)

                # Substitute collection DB in test mode
                try:
                    ref_db = self._extract_collection_db(query)
                    if ref_db:
                        runtime_db = (
                            os.environ.get('TEST_DB_NAME')
                            or os.environ.get('BASEX_DATABASE')
                            or self.database
                        )
                        if runtime_db and ref_db != runtime_db:
                            query = query.replace(
                                f"collection('{ref_db}')",
                                f"collection('{runtime_db}')",
                            )
                            if conn.current_db != runtime_db:
                                conn.ensure_db(runtime_db)
                except Exception:
                    pass

                clean_query = query
                if query.strip().lower().startswith('xquery '):
                    clean_query = query.strip()[7:].strip()

                q = None
                try:
                    q = conn.session.query(clean_query)
                    q.execute()
                    self.logger.debug(f"Update executed successfully: {query[:100]}...")
                    return
                except (IOError, OSError) as e:
                    last_error = e
                    self.logger.warning(
                        "Session lost during update (attempt %s/%s): %s; discarding...",
                        attempt,
                        attempts,
                        e,
                    )
                    self._discard(conn)
                    conn = None
                    continue
                except Exception as e:
                    raise DatabaseError(f"Update execution failed: {e}\nQuery:\n{query}")
                finally:
                    if q:
                        try:
                            q.close()
                        except Exception:
                            pass
            finally:
                if conn is not None:
                    self._release(conn)

        raise DatabaseError(f"Update execution failed after {attempts} attempts: {last_error}")

    # ---- Database management ----

    def create_database(self, db_name: str, content: str = "") -> None:
        try:
            command = f"CREATE DB {db_name}"
            if content:
                command += f" {content}"
            self.execute_command(command)
            self.logger.info(f"Database '{db_name}' created successfully")
        except Exception as e:
            raise DatabaseError(f"Failed to create database '{db_name}': {e}")

    def drop_database(self, db_name: str) -> None:
        try:
            self.execute_command(f"DROP DB {db_name}")
            self.logger.info(f"Database '{db_name}' dropped successfully")
        except Exception as e:
            raise DatabaseError(f"Failed to drop database '{db_name}': {e}")

    def close_database(self) -> None:
        conn = self._acquire()
        try:
            if conn.session:
                try:
                    conn.session.execute("CLOSE")
                    self.logger.debug(f"Closed database (previous: {conn.current_db})")
                except Exception as e:
                    self.logger.debug(f"Error while closing database: {e}")
                finally:
                    conn.current_db = None
        finally:
            self._release(conn)

    # ---- Context manager ----

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        if hasattr(self, '_pool'):
            self.disconnect()

    # ---- Diagnostics ----

    def get_status(self) -> Dict[str, Any]:
        return {
            'connected': self._created > 0,
            'pool_size': self._created,
            'max_pool': self._max_pool,
            'configured_database': self.database,
        }

    # ---- Safety checks (test mode) ----

    def _is_test_mode(self) -> bool:
        return os.environ.get('FLASK_CONFIG') == 'testing' or os.environ.get('TESTING') == 'true'

    def _is_safe_database_name(self, db_name: str) -> bool:
        if not db_name:
            return False
        if not db_name.startswith('test_'):
            return False
        protected_patterns = {'dictionary', 'production', 'backup', 'main', 'dev', 'staging'}
        db_name_lower = db_name.lower()
        for protected in protected_patterns:
            if protected in db_name_lower:
                return False
        return True

