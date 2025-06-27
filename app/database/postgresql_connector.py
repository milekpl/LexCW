"""
PostgreSQL connector for word sketch and corpus analysis functionality.

Implements database operations for word sketches, SUBTLEX norms, and 
sentence-aligned corpus processing with PostgreSQL backend.
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
    PostgreSQL database connector for advanced linguistics analytics.
    
    Provides connection management, query execution, and transaction support
    for word sketch functionality, corpus analysis, and SUBTLEX integration.
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
        """Create all word sketch related tables."""
        tables_sql = [
            self._create_word_sketches_table(),
            self._create_sketch_grammars_table(),
            self._create_subtlex_norms_table(),
            self._create_frequency_analysis_table(),
            self._create_corpus_sentences_table(),
            self._create_linguistic_cache_table(),
            self._create_processing_batches_table()
        ]
        
        for sql in tables_sql:
            self.execute_query(sql)
        
        # Create indexes for performance
        self._create_performance_indexes()
    
    def _create_word_sketches_table(self) -> str:
        """SQL for word sketches table creation."""
        return """
        CREATE TABLE IF NOT EXISTS word_sketches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            headword TEXT NOT NULL,
            headword_lemma TEXT NOT NULL,
            headword_pos TEXT,
            collocate TEXT NOT NULL,
            collocate_lemma TEXT NOT NULL,
            collocate_pos TEXT,
            grammatical_relation TEXT NOT NULL,
            relation_pattern TEXT,
            frequency INTEGER DEFAULT 1,
            logdice_score FLOAT NOT NULL,
            mutual_information FLOAT,
            t_score FLOAT,
            sentence_ids UUID[],
            corpus_source TEXT DEFAULT 'parallel_corpus',
            confidence_level FLOAT DEFAULT 1.0,
            sketch_grammar_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    
    def _create_sketch_grammars_table(self) -> str:
        """SQL for sketch grammars table creation."""
        return """
        CREATE TABLE IF NOT EXISTS sketch_grammars (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pattern_name TEXT NOT NULL,
            pattern_cqp TEXT NOT NULL,
            pattern_description TEXT,
            language TEXT DEFAULT 'en',
            pos_constraints JSONB,
            bidirectional BOOLEAN DEFAULT false,
            priority INTEGER DEFAULT 1,
            grammar_source TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    
    def _create_subtlex_norms_table(self) -> str:
        """SQL for SUBTLEX norms table creation."""
        return """
        CREATE TABLE IF NOT EXISTS subtlex_norms (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            word TEXT NOT NULL,
            pos_tag TEXT,
            frequency_per_million FLOAT NOT NULL,
            context_diversity FLOAT,
            word_length INTEGER,
            log_frequency FLOAT,
            zipf_score FLOAT,
            phonological_neighbors INTEGER,
            orthographic_neighbors INTEGER,
            age_of_acquisition FLOAT,
            concreteness_rating FLOAT,
            valence_rating FLOAT,
            arousal_rating FLOAT,
            dominance_rating FLOAT,
            subtlex_dataset TEXT DEFAULT 'subtlex_us',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_subtlex_entry UNIQUE(word, pos_tag, subtlex_dataset)
        );
        """
    
    def _create_frequency_analysis_table(self) -> str:
        """SQL for frequency analysis table creation."""
        return """
        CREATE TABLE IF NOT EXISTS frequency_analysis (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            word TEXT NOT NULL,
            lemma TEXT,
            pos_tag TEXT,
            corpus_frequency INTEGER DEFAULT 0,
            corpus_relative_freq FLOAT,
            subtlex_frequency FLOAT,
            subtlex_context_diversity FLOAT,
            frequency_ratio FLOAT,
            psychological_accessibility FLOAT,
            corpus_source TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    
    def _create_corpus_sentences_table(self) -> str:
        """SQL for corpus sentences table creation."""
        return """
        CREATE TABLE IF NOT EXISTS corpus_sentences (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID,
            sentence_number INTEGER,
            source_text TEXT NOT NULL,
            target_text TEXT NOT NULL,
            source_tokens TEXT[],
            target_tokens TEXT[],
            source_lemmas TEXT[],
            target_lemmas TEXT[],
            source_pos_tags TEXT[],
            target_pos_tags TEXT[],
            alignment_score FLOAT DEFAULT 1.0,
            linguistic_processed BOOLEAN DEFAULT false,
            processing_timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    
    def _create_linguistic_cache_table(self) -> str:
        """SQL for linguistic analysis cache table creation."""
        return """
        CREATE TABLE IF NOT EXISTS linguistic_cache (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            text_hash TEXT UNIQUE NOT NULL,
            original_text TEXT NOT NULL,
            language TEXT NOT NULL,
            tokens TEXT[],
            lemmas TEXT[],
            pos_tags TEXT[],
            dependencies JSONB,
            processor_version TEXT,
            cache_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    
    def _create_processing_batches_table(self) -> str:
        """SQL for processing batches table creation."""
        return """
        CREATE TABLE IF NOT EXISTS processing_batches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            batch_type TEXT NOT NULL,
            document_ids UUID[],
            sentence_range_start INTEGER,
            sentence_range_end INTEGER,
            status TEXT DEFAULT 'pending',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            processing_stats JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    
    def _create_performance_indexes(self) -> None:
        """Create performance indexes for word sketch tables."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_word_sketches_headword ON word_sketches(headword_lemma);",
            "CREATE INDEX IF NOT EXISTS idx_word_sketches_relation ON word_sketches(grammatical_relation);",
            "CREATE INDEX IF NOT EXISTS idx_word_sketches_logdice ON word_sketches(logdice_score DESC);",
            "CREATE INDEX IF NOT EXISTS idx_subtlex_word ON subtlex_norms(word, pos_tag);",
            "CREATE INDEX IF NOT EXISTS idx_frequency_analysis_lemma ON frequency_analysis(lemma, pos_tag);",
            "CREATE INDEX IF NOT EXISTS idx_corpus_sentences_processed ON corpus_sentences(linguistic_processed);",
            "CREATE INDEX IF NOT EXISTS idx_linguistic_cache_hash ON linguistic_cache(text_hash);"
        ]
        
        for index_sql in indexes:
            self.execute_query(index_sql)
    
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
