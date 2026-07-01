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
import psycopg2.pool
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
    minconn: int = 2
    maxconn: int = 10


class PostgreSQLConnector:
    """
    PostgreSQL database connector for worksets and project settings.

    Thread-safe: uses a ThreadedConnectionPool so each thread gets its own
    connection. Connections are returned to the pool after each cursor use.
    """

    def __init__(self, config: Optional[PostgreSQLConfig] = None) -> None:
        self.config = config or self._load_config_from_env()
        self.logger = logging.getLogger(__name__)
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

        testing_mode = os.getenv('TESTING', '').lower() in ('true', '1', 'yes')
        pytest_running = 'PYTEST_CURRENT_TEST' in os.environ

        if not (testing_mode or pytest_running):
            self._ensure_pool()

    def _load_config_from_env(self) -> PostgreSQLConfig:
        return PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            minconn=int(os.getenv('POSTGRES_MINCONN', 2)),
            maxconn=int(os.getenv('POSTGRES_MAXCONN', 10))
        )

    def _ensure_pool(self) -> None:
        if self._pool is not None:
            return
        try:
            connection_string = (
                f"host={self.config.host} "
                f"port={self.config.port} "
                f"dbname={self.config.database} "
                f"user={self.config.username} "
                f"password={self.config.password}"
            )
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                self.config.minconn,
                self.config.maxconn,
                connection_string,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.logger.info(
                "PostgreSQL connection pool created (min=%s, max=%s)",
                self.config.minconn, self.config.maxconn
            )
        except psycopg2.Error as e:
            self.logger.error(f"Failed to create PostgreSQL pool: {e}")
            raise DatabaseConnectionError(f"PostgreSQL pool creation failed: {e}")

    @contextmanager
    def get_cursor(self):
        if self._pool is None:
            self._ensure_pool()

        conn = self._pool.getconn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            self.logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
        finally:
            cursor.close()
            self._pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        with self.get_cursor() as cursor:
            cursor.execute(query, parameters if parameters else None)
            self.logger.debug(f"Executed query: {query[:100]}...")

    def fetch_all(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        with self.get_cursor() as cursor:
            cursor.execute(query, parameters if parameters else None)
            results = cursor.fetchall()
            self.logger.debug(f"Query returned {len(results)} rows")
            return [dict(row) for row in results]

    def fetch_one(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        with self.get_cursor() as cursor:
            cursor.execute(query, parameters if parameters else None)
            result = cursor.fetchone()
            return dict(result) if result else None

    def execute_transaction(self, queries: List[Tuple[str, Dict[str, Any]]]) -> None:
        if self._pool is None:
            self._ensure_pool()

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cursor:
                for query, parameters in queries:
                    cursor.execute(query, parameters)
            conn.commit()
            self.logger.debug(f"Transaction completed with {len(queries)} queries")
        except psycopg2.Error as e:
            conn.rollback()
            self.logger.error(f"Transaction failed: {e}")
            raise DatabaseError(f"Transaction execution failed: {e}")
        finally:
            self._pool.putconn(conn)

    def create_word_sketch_tables(self) -> None:
        import warnings
        warnings.warn(
            "create_word_sketch_tables() is deprecated. "
            "Word sketch functionality is now handled by Lucene service.",
            DeprecationWarning,
            stacklevel=2
        )

    def close(self) -> None:
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            self.logger.info("PostgreSQL connection pool closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def ensure_database_exists(self) -> bool:
        default_config = PostgreSQLConfig(
            host=self.config.host,
            port=self.config.port,
            database='postgres',
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
                    cursor.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (self.config.database,)
                    )

                    if cursor.fetchone():
                        self.logger.info(f"Database '{self.config.database}' already exists")
                        return False

                    cursor.execute(f'CREATE DATABASE "{self.config.database}"')
                    self.logger.info(f"Created database '{self.config.database}'")
                    return True

        except psycopg2.Error as e:
            self.logger.error(f"Failed to ensure database exists: {e}")
            raise DatabaseConnectionError(f"Database creation failed: {e}")

    def reconnect(self) -> None:
        self.close()
        self._pool = None
        self._ensure_pool()

    def test_connection(self) -> bool:
        try:
            if self._pool is None:
                self._ensure_pool()
            conn = self._pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return True
            finally:
                self._pool.putconn(conn)
        except Exception as e:
            self.logger.warning(f"PostgreSQL connection test failed: {e}")
            return False
