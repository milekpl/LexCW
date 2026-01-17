"""
PostgreSQL connector for workset and project settings storage.

NOTE: Word sketch and corpus analysis functionality has been migrated to Lucene.
The following PostgreSQL tables are no longer used and should be removed:
- word_sketches (replaced by Lucene word-sketch index at port 8083)
- sketch_grammars
- subtlex_norms
- frequency_analysis
- corpus_sentences
- linguistic_cache
- processing_batches
- parallel_corpus (replaced by Lucene corpus index at port 8082)

This connector now only handles:
- Workset management (worksets, workset_entries)
- Project settings
"""
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import contextmanager
import logging
from dataclasses import dataclass

from app.utils.exceptions import DatabaseError, DatabaseConnectionError


@dataclass
class PostgreSQLConfig:
    """PostgreSQL connection configuration."""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20


class PostgreSQLConnector:
    """
    PostgreSQL database connector for worksets and project settings.

    NOTE: Word sketch and corpus-related methods are deprecated.
    Use Lucene services instead:
    - Corpus queries: app.lucene_corpus_client (port 8082)
    - Word sketches: Will be available via Lucene at port 8083
    """
    
    def __init__(self, config: Optional[PostgreSQLConfig] = None) -> None:
        """
        Initialize PostgreSQL connector.
        
        Args:
            config: Database configuration. If None, loads from environment.
        """
        self.config = config or self._load_config_from_env()
        self.logger = logging.getLogger(__name__)
        self._connection: Optional[psycopg2.extensions.connection] = None
        
        # Only initialize connection if not in test mode
        testing_mode = os.getenv('TESTING', '').lower() in ('true', '1', 'yes')
        pytest_running = 'PYTEST_CURRENT_TEST' in os.environ
        
        if not (testing_mode or pytest_running):
            self._initialize_connection()
    
    def _load_config_from_env(self) -> PostgreSQLConfig:
        """Load configuration from environment variables."""
        return PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            pool_size=int(os.getenv('POSTGRES_POOL_SIZE', 10)),
            max_overflow=int(os.getenv('POSTGRES_MAX_OVERFLOW', 20))
        )
    
    def _initialize_connection(self) -> None:
        """Initialize database connection."""
        try:
            # Set locale environment variables to avoid encoding issues
            import os
            original_env = {}
            locale_vars = ['LC_ALL', 'LC_CTYPE', 'LANG']
            
            # Save original values and set to UTF-8
            for var in locale_vars:
                original_env[var] = os.environ.get(var)
                os.environ[var] = 'en_US.UTF-8'
            
            try:
                connection_string = (
                    f"host={self.config.host} "
                    f"port={self.config.port} "
                    f"dbname={self.config.database} "
                    f"user={self.config.username} "
                    f"password={self.config.password}"
                )
                self._connection = psycopg2.connect(
                    connection_string,
                    cursor_factory=psycopg2.extras.RealDictCursor
                )
                self._connection.autocommit = True
                self.logger.info("PostgreSQL connection established")
            finally:
                # Restore original environment variables
                for var, value in original_env.items():
                    if value is None:
                        os.environ.pop(var, None)
                    else:
                        os.environ[var] = value
            
        except psycopg2.Error as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise DatabaseConnectionError(f"PostgreSQL connection failed: {e}")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor."""
        if not self._connection or self._connection.closed:
            self._initialize_connection()
        
        cursor = self._connection.cursor()
        try:
            yield cursor
        except psycopg2.Error as e:
            self.logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
        finally:
            cursor.close()
    
    def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Execute a query without returning results (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query string
            parameters: Query parameters dictionary
            
        Raises:
            DatabaseError: If query execution fails
        """
        with self.get_cursor() as cursor:
            try:
                cursor.execute(query, parameters if parameters else None)
                self.logger.debug(f"Executed query: {query[:100]}...")
            except psycopg2.Error as e:
                self.logger.error(f"Query execution failed: {e}")
                raise DatabaseError(f"Failed to execute query: {e}")
    
    def fetch_all(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query and return all results.
        
        Args:
            query: SQL query string
            parameters: Query parameters dictionary
            
        Returns:
            List of result dictionaries
            
        Raises:
            DatabaseError: If query execution fails
        """
        with self.get_cursor() as cursor:
            try:
                cursor.execute(query, parameters if parameters else None)
                results = cursor.fetchall()
                self.logger.debug(f"Query returned {len(results)} rows")
                return [dict(row) for row in results]
            except psycopg2.Error as e:
                self.logger.error(f"Query execution failed: {e}")
                raise DatabaseError(f"Failed to fetch results: {e}")
    
    def fetch_one(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and return first result.
        
        Args:
            query: SQL query string
            parameters: Query parameters dictionary
            
        Returns:
            First result dictionary or None
            
        Raises:
            DatabaseError: If query execution fails
        """
        with self.get_cursor() as cursor:
            try:
                cursor.execute(query, parameters if parameters else None)
                result = cursor.fetchone()
                return dict(result) if result else None
            except psycopg2.Error as e:
                self.logger.error(f"Query execution failed: {e}")
                raise DatabaseError(f"Failed to fetch result: {e}")
    
    def execute_transaction(self, queries: List[Tuple[str, Dict[str, Any]]]) -> None:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of (query, parameters) tuples
            
        Raises:
            DatabaseError: If transaction fails
        """
        if not self._connection:
            self._initialize_connection()
        
        old_autocommit = self._connection.autocommit
        try:
            self._connection.autocommit = False
            with self.get_cursor() as cursor:
                for query, parameters in queries:
                    cursor.execute(query, parameters)
                self._connection.commit()
                self.logger.debug(f"Transaction completed with {len(queries)} queries")
                
        except psycopg2.Error as e:
            self._connection.rollback()
            self.logger.error(f"Transaction failed: {e}")
            raise DatabaseError(f"Transaction execution failed: {e}")
        finally:
            self._connection.autocommit = old_autocommit
    
    def create_word_sketch_tables(self) -> None:
        """
        DEPRECATED: Word sketch tables are no longer created.

        Word sketch functionality has been migrated to Lucene (port 8083).
        This method is kept for backwards compatibility but does nothing.

        Raises:
            DeprecationWarning: Always raised to indicate deprecated usage.
        """
        import warnings
        warnings.warn(
            "create_word_sketch_tables() is deprecated. "
            "Word sketch functionality is now handled by Lucene service.",
            DeprecationWarning,
            stacklevel=2
        )
        # No-op: tables are no longer created in PostgreSQL
    
    def _create_word_sketches_table(self) -> str:
        """DEPRECATED: Word sketch tables are no longer used."""
        raise NotImplementedError(
            "Word sketch tables are no longer created. "
            "Use Lucene word-sketch service (port 8083) instead."
        )

    def _create_sketch_grammars_table(self) -> str:
        """DEPRECATED: Sketch grammars are no longer stored in PostgreSQL."""
        raise NotImplementedError(
            "Sketch grammars are no longer stored in PostgreSQL. "
            "Use Lucene word-sketch service (port 8083) instead."
        )

    def _create_subtlex_norms_table(self) -> str:
        """DEPRECATED: SUBTLEX norms are no longer stored in PostgreSQL."""
        raise NotImplementedError(
            "SUBTLEX norms are no longer stored in PostgreSQL."
        )

    def _create_frequency_analysis_table(self) -> str:
        """DEPRECATED: Frequency analysis is no longer stored in PostgreSQL."""
        raise NotImplementedError(
            "Frequency analysis is no longer stored in PostgreSQL. "
            "Use Lucene corpus service (port 8082) instead."
        )

    def _create_corpus_sentences_table(self) -> str:
        """DEPRECATED: Corpus sentences are no longer stored in PostgreSQL."""
        raise NotImplementedError(
            "Corpus sentences are no longer stored in PostgreSQL. "
            "Use Lucene corpus service (port 8082) instead."
        )

    def _create_linguistic_cache_table(self) -> str:
        """DEPRECATED: Linguistic cache is no longer stored in PostgreSQL."""
        raise NotImplementedError(
            "Linguistic cache is no longer stored in PostgreSQL."
        )

    def _create_processing_batches_table(self) -> str:
        """DEPRECATED: Processing batches are no longer tracked in PostgreSQL."""
        raise NotImplementedError(
            "Processing batches are no longer tracked in PostgreSQL."
        )

    def _create_performance_indexes(self) -> None:
        """DEPRECATED: Performance indexes are no longer needed."""
        pass  # No-op
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self.logger.info("PostgreSQL connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def ensure_database_exists(self) -> bool:
        """
        Ensure target database exists, create if it doesn't.
        
        Returns:
            True if database was created, False if it already existed
            
        Raises:
            DatabaseConnectionError: If unable to create database
        """
        # Connect to default postgres database to check/create target
        default_config = PostgreSQLConfig(
            host=self.config.host,
            port=self.config.port,
            database='postgres',  # Default database
            username=self.config.username,
            password=self.config.password
        )
        
        try:
            connection_string = (
                f"host={default_config.host} "
                f"port={default_config.port} "
                f"dbname={default_config.database} "
                f"user={default_config.username} "
                f"password={default_config.password}"
            )
            
            with psycopg2.connect(connection_string) as conn:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    # Check if database exists
                    cursor.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (self.config.database,)
                    )
                    
                    if cursor.fetchone():
                        self.logger.info(f"Database '{self.config.database}' already exists")
                        return False
                    
                    # Create database
                    # Use format() for database name as it can't be parameterized
                    cursor.execute(f'CREATE DATABASE "{self.config.database}"')
                    self.logger.info(f"Created database '{self.config.database}'")
                    return True
                    
        except psycopg2.Error as e:
            self.logger.error(f"Failed to ensure database exists: {e}")
            raise DatabaseConnectionError(f"Database creation failed: {e}")
    
    def reconnect(self) -> None:
        """Reconnect to the database (useful after database creation)."""
        self._initialize_connection()
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            if not self._connection:
                self._initialize_connection()
            
            # Test the connection with a simple query
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
                
        except Exception as e:
            self.logger.warning(f"PostgreSQL connection test failed: {e}")
            return False
