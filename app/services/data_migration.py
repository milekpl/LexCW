"""
Data migration service for transitioning from SQLite to PostgreSQL.

This module provides functionality for migrating dictionary entries, 
parallel corpus data, and linguistic metadata from SQLite databases 
to PostgreSQL for enhanced search capabilities and performance.
"""
from __future__ import annotations

import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.database.postgresql_connector import PostgreSQLConnector
from app.utils.exceptions import DatabaseError


@dataclass
class MigrationConfig:
    """Configuration for data migration operations."""
    sqlite_path: str
    batch_size: int = 1000
    preserve_ids: bool = True
    validate_data: bool = True
    create_indexes: bool = True
    parallel_workers: int = 4


@dataclass
class MigrationStats:
    """Statistics for migration operations."""
    total_entries: int = 0
    migrated_entries: int = 0
    total_senses: int = 0
    migrated_senses: int = 0
    total_examples: int = 0
    migrated_examples: int = 0
    total_corpus_pairs: int = 0
    migrated_corpus_pairs: int = 0
    errors: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def duration(self) -> Optional[float]:
        """Migration duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_entries == 0:
            return 0.0
        return (self.migrated_entries / self.total_entries) * 100


class DataMigrationService:
    """
    Service for migrating data from SQLite to PostgreSQL.
    
    Handles dictionary entries, parallel corpus data, and linguistic metadata
    with validation, error handling, and progress tracking.
    """
    
    def __init__(
        self,
        pg_connector: PostgreSQLConnector,
        config: Optional[MigrationConfig] = None
    ) -> None:
        """
        Initialize migration service.
        
        Args:
            pg_connector: PostgreSQL database connector
            config: Migration configuration
        """
        self.pg_connector = pg_connector
        self.config = config or MigrationConfig(sqlite_path="")
        self.logger = logging.getLogger(__name__)
        self.stats = MigrationStats()
    
    def migrate_dictionary_from_sqlite(
        self,
        sqlite_path: str,
        create_schema: bool = True
    ) -> MigrationStats:
        """
        Migrate dictionary entries from SQLite to PostgreSQL.
        
        Args:
            sqlite_path: Path to SQLite database file
            create_schema: Whether to create PostgreSQL schema first
            
        Returns:
            Migration statistics
            
        Raises:
            DatabaseError: If migration fails
        """
        self.stats = MigrationStats()
        self.stats.start_time = datetime.now()
        
        try:
            if create_schema:
                self._create_dictionary_schema()
            
            # Connect to SQLite
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
            
            try:
                # Migrate in order: entries -> senses -> examples -> relations
                self._migrate_entries(sqlite_conn)
                self._migrate_senses(sqlite_conn)
                self._migrate_examples(sqlite_conn)
                self._migrate_relations(sqlite_conn)
                
                if self.config.create_indexes:
                    self._create_performance_indexes()
                
                self.logger.info(f"Dictionary migration completed: {self.stats.migrated_entries} entries")
                
            finally:
                sqlite_conn.close()
                
        except Exception as e:
            self.logger.error(f"Dictionary migration failed: {e}")
            if self.stats.errors is not None:
                self.stats.errors.append(f"Migration failed: {e}")
            raise DatabaseError(f"Dictionary migration failed: {e}")
        
        finally:
            self.stats.end_time = datetime.now()
        
        return self.stats
    
    def migrate_corpus_from_sqlite(
        self,
        sqlite_path: str,
        document_name: str = "migrated_corpus",
        source_lang: str = "en",
        target_lang: str = "pl"
    ) -> MigrationStats:
        """
        Migrate parallel corpus data from SQLite to PostgreSQL.
        
        Args:
            sqlite_path: Path to SQLite corpus database
            document_name: Name for the migrated document
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Migration statistics
        """
        self.stats = MigrationStats()
        self.stats.start_time = datetime.now()
        
        try:
            # Create corpus schema if needed
            self._create_corpus_schema()
            
            # Create document entry
            document_id = self._create_corpus_document(
                document_name, source_lang, target_lang
            )
            
            # Connect to SQLite
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
            
            try:
                # Detect corpus structure
                corpus_structure = self._detect_corpus_structure(sqlite_conn)
                
                if corpus_structure == "parallel_sentences":
                    self._migrate_parallel_sentences(sqlite_conn, document_id)
                elif corpus_structure == "search_index":
                    self._migrate_search_index_corpus(sqlite_conn, document_id)
                else:
                    self._migrate_generic_corpus(sqlite_conn, document_id)
                
                self.logger.info(f"Corpus migration completed: {self.stats.migrated_corpus_pairs} pairs")
                
            finally:
                sqlite_conn.close()
                
        except Exception as e:
            self.logger.error(f"Corpus migration failed: {e}")
            self.stats.errors.append(f"Corpus migration failed: {e}")
            raise DatabaseError(f"Corpus migration failed: {e}")
        
        finally:
            self.stats.end_time = datetime.now()
        
        return self.stats
    
    def _create_dictionary_schema(self) -> None:
        """Create PostgreSQL schema for dictionary data."""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS entries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                entry_id TEXT UNIQUE NOT NULL,
                headword TEXT NOT NULL,
                pronunciation TEXT,
                grammatical_info JSONB,
                date_created TIMESTAMP,
                date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                custom_fields JSONB,
                frequency_rank INTEGER,
                subtlex_frequency FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS senses (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                sense_id TEXT UNIQUE NOT NULL,
                entry_id UUID NOT NULL,
                definition TEXT,
                grammatical_info JSONB,
                custom_fields JSONB,
                sort_order INTEGER,
                semantic_field TEXT,
                usage_notes TEXT,
                FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS examples (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                example_id TEXT UNIQUE NOT NULL,
                sense_id UUID NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                custom_fields JSONB,
                sort_order INTEGER,
                source TEXT,
                confidence_score FLOAT,
                FOREIGN KEY (sense_id) REFERENCES senses (id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS entry_relations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID NOT NULL,
                target_id UUID NOT NULL,
                relation_type TEXT NOT NULL,
                is_sense_relation BOOLEAN DEFAULT false,
                confidence FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES entries (id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES entries (id) ON DELETE CASCADE
            );
            """
        ]
        
        for query in schema_queries:
            self.pg_connector.execute_query(query)
        
        self.logger.info("Dictionary schema created successfully")
    
    def _create_corpus_schema(self) -> None:
        """Create PostgreSQL schema for corpus data."""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS corpus_documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_name TEXT NOT NULL,
                source_language TEXT NOT NULL DEFAULT 'en',
                target_language TEXT NOT NULL DEFAULT 'pl',
                document_type TEXT DEFAULT 'parallel_corpus',
                metadata JSONB,
                sentence_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS corpus_sentence_pairs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL,
                source_text TEXT NOT NULL,
                target_text TEXT NOT NULL,
                source_id TEXT,
                alignment_score FLOAT DEFAULT 1.0,
                sentence_length_source INTEGER,
                sentence_length_target INTEGER,
                pos_tags_source JSONB,
                pos_tags_target JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES corpus_documents (id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS corpus_metadata (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                value_type TEXT DEFAULT 'text',
                FOREIGN KEY (document_id) REFERENCES corpus_documents (id) ON DELETE CASCADE
            );
            """
        ]
        
        for query in schema_queries:
            self.pg_connector.execute_query(query)
        
        self.logger.info("Corpus schema created successfully")
    
    def _migrate_entries(self, sqlite_conn: sqlite3.Connection) -> None:
        """Migrate entry records from SQLite to PostgreSQL."""
        cursor = sqlite_conn.cursor()
        
        # Count total entries
        cursor.execute("SELECT COUNT(*) FROM entries")
        self.stats.total_entries = cursor.fetchone()[0]
        
        # Fetch entries in batches
        offset = 0
        while offset < self.stats.total_entries:
            cursor.execute(
                "SELECT * FROM entries LIMIT ? OFFSET ?",
                (self.config.batch_size, offset)
            )
            entries = cursor.fetchall()
            
            if not entries:
                break
            
            # Batch insert to PostgreSQL
            self._insert_entries_batch(entries)
            offset += len(entries)
            
            self.logger.info(f"Migrated {offset}/{self.stats.total_entries} entries")
    
    def _insert_entries_batch(self, entries: List[sqlite3.Row]) -> None:
        """Insert a batch of entries into PostgreSQL."""
        insert_query = """
        INSERT INTO entries (
            entry_id, headword, pronunciation, grammatical_info,
            date_created, date_modified, custom_fields
        ) VALUES (
            %(entry_id)s, %(headword)s, %(pronunciation)s, %(grammatical_info)s,
            %(date_created)s, %(date_modified)s, %(custom_fields)s
        ) ON CONFLICT (entry_id) DO NOTHING
        """
        
        entry_data = []
        for entry in entries:
            # Parse custom fields JSON
            custom_fields = None
            if entry['custom_fields']:
                try:
                    custom_fields = json.loads(entry['custom_fields'])
                except json.JSONDecodeError:
                    custom_fields = {"raw": entry['custom_fields']}
            
            # Parse grammatical info
            grammatical_info = None
            if entry['grammatical_info']:
                try:
                    if entry['grammatical_info'].startswith('{'):
                        grammatical_info = json.loads(entry['grammatical_info'])
                    else:
                        grammatical_info = {"type": entry['grammatical_info']}
                except json.JSONDecodeError:
                    grammatical_info = {"type": entry['grammatical_info']}
            
            entry_data.append({
                'entry_id': entry['id'],
                'headword': entry['headword'],
                'pronunciation': entry['pronunciation'],
                'grammatical_info': json.dumps(grammatical_info) if grammatical_info else None,
                'date_created': entry['date_created'],
                'date_modified': entry['date_modified'],
                'custom_fields': json.dumps(custom_fields) if custom_fields else None
            })
        
        with self.pg_connector.get_cursor() as cursor:
            cursor.executemany(insert_query, entry_data)
        
        self.stats.migrated_entries += len(entry_data)
    
    def _migrate_senses(self, sqlite_conn: sqlite3.Connection) -> None:
        """Migrate sense records from SQLite to PostgreSQL."""
        cursor = sqlite_conn.cursor()
        
        # Count total senses
        cursor.execute("SELECT COUNT(*) FROM senses")
        self.stats.total_senses = cursor.fetchone()[0]
        
        # Get entry ID mapping
        entry_mapping = self._get_entry_id_mapping()
        
        # Fetch senses in batches
        offset = 0
        while offset < self.stats.total_senses:
            cursor.execute(
                "SELECT * FROM senses LIMIT ? OFFSET ?",
                (self.config.batch_size, offset)
            )
            senses = cursor.fetchall()
            
            if not senses:
                break
            
            # Batch insert to PostgreSQL
            self._insert_senses_batch(senses, entry_mapping)
            offset += len(senses)
            
            self.logger.info(f"Migrated {offset}/{self.stats.total_senses} senses")
    
    def _insert_senses_batch(
        self, 
        senses: List[sqlite3.Row], 
        entry_mapping: Dict[str, str]
    ) -> None:
        """Insert a batch of senses into PostgreSQL."""
        insert_query = """
        INSERT INTO senses (
            sense_id, entry_id, definition, grammatical_info,
            custom_fields, sort_order
        ) VALUES (
            %(sense_id)s, %(entry_id)s, %(definition)s, %(grammatical_info)s,
            %(custom_fields)s, %(sort_order)s
        ) ON CONFLICT (sense_id) DO NOTHING
        """
        
        sense_data = []
        for sense in senses:
            # Map SQLite entry_id to PostgreSQL UUID
            pg_entry_id = entry_mapping.get(sense['entry_id'])
            if not pg_entry_id:
                self.stats.errors.append(f"Entry not found for sense {sense['id']}")
                continue
            
            # Parse custom fields
            custom_fields = None
            if sense['custom_fields']:
                try:
                    custom_fields = json.loads(sense['custom_fields'])
                except json.JSONDecodeError:
                    custom_fields = {"raw": sense['custom_fields']}
            
            # Parse grammatical info
            grammatical_info = None
            if sense['grammatical_info']:
                try:
                    if sense['grammatical_info'].startswith('{'):
                        grammatical_info = json.loads(sense['grammatical_info'])
                    else:
                        grammatical_info = {"type": sense['grammatical_info']}
                except json.JSONDecodeError:
                    grammatical_info = {"type": sense['grammatical_info']}
            
            sense_data.append({
                'sense_id': sense['id'],
                'entry_id': pg_entry_id,
                'definition': sense['definition'],
                'grammatical_info': json.dumps(grammatical_info) if grammatical_info else None,
                'custom_fields': json.dumps(custom_fields) if custom_fields else None,
                'sort_order': sense['sort_order']
            })
        
        with self.pg_connector.get_cursor() as cursor:
            cursor.executemany(insert_query, sense_data)
        
        self.stats.migrated_senses += len(sense_data)
    
    def _migrate_examples(self, sqlite_conn: sqlite3.Connection) -> None:
        """Migrate example records from SQLite to PostgreSQL."""
        cursor = sqlite_conn.cursor()
        
        # Count total examples
        cursor.execute("SELECT COUNT(*) FROM examples")
        self.stats.total_examples = cursor.fetchone()[0]
        
        # Get sense ID mapping
        sense_mapping = self._get_sense_id_mapping()
        
        # Fetch examples in batches
        offset = 0
        while offset < self.stats.total_examples:
            cursor.execute(
                "SELECT * FROM examples LIMIT ? OFFSET ?",
                (self.config.batch_size, offset)
            )
            examples = cursor.fetchall()
            
            if not examples:
                break
            
            # Batch insert to PostgreSQL
            self._insert_examples_batch(examples, sense_mapping)
            offset += len(examples)
            
            self.logger.info(f"Migrated {offset}/{self.stats.total_examples} examples")
    
    def _insert_examples_batch(
        self, 
        examples: List[sqlite3.Row], 
        sense_mapping: Dict[str, str]
    ) -> None:
        """Insert a batch of examples into PostgreSQL."""
        insert_query = """
        INSERT INTO examples (
            example_id, sense_id, text, translation,
            custom_fields, sort_order
        ) VALUES (
            %(example_id)s, %(sense_id)s, %(text)s, %(translation)s,
            %(custom_fields)s, %(sort_order)s
        ) ON CONFLICT (example_id) DO NOTHING
        """
        
        example_data = []
        for example in examples:
            # Map SQLite sense_id to PostgreSQL UUID
            pg_sense_id = sense_mapping.get(example['sense_id'])
            if not pg_sense_id:
                self.stats.errors.append(f"Sense not found for example {example['id']}")
                continue
            
            # Parse custom fields
            custom_fields = None
            if example['custom_fields']:
                try:
                    custom_fields = json.loads(example['custom_fields'])
                except json.JSONDecodeError:
                    custom_fields = {"raw": example['custom_fields']}
            
            example_data.append({
                'example_id': example['id'],
                'sense_id': pg_sense_id,
                'text': example['text'],
                'translation': example['translation'],
                'custom_fields': json.dumps(custom_fields) if custom_fields else None,
                'sort_order': example['sort_order']
            })
        
        with self.pg_connector.get_cursor() as cursor:
            cursor.executemany(insert_query, example_data)
        
        self.stats.migrated_examples += len(example_data)
    
    def _migrate_relations(self, sqlite_conn: sqlite3.Connection) -> None:
        """Migrate relation records from SQLite to PostgreSQL."""
        cursor = sqlite_conn.cursor()
        
        # Check if relations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='relations'
        """)
        if not cursor.fetchone():
            self.logger.info("No relations table found in SQLite")
            return
        
        # Get entry ID mapping
        entry_mapping = self._get_entry_id_mapping()
        
        cursor.execute("SELECT * FROM relations")
        relations = cursor.fetchall()
        
        if not relations:
            return
        
        # Insert relations
        insert_query = """
        INSERT INTO entry_relations (
            source_id, target_id, relation_type, is_sense_relation
        ) VALUES (
            %(source_id)s, %(target_id)s, %(relation_type)s, %(is_sense_relation)s
        )
        """
        
        relation_data = []
        for relation in relations:
            source_id = entry_mapping.get(relation['source_id'])
            target_id = entry_mapping.get(relation['target_id'])
            
            if source_id and target_id:
                relation_data.append({
                    'source_id': source_id,
                    'target_id': target_id,
                    'relation_type': relation['relation_type'],
                    'is_sense_relation': bool(relation['is_sense_relation'])
                })
        
        if relation_data:
            with self.pg_connector.get_cursor() as cursor:
                cursor.executemany(insert_query, relation_data)
        
        self.logger.info(f"Migrated {len(relation_data)} relations")
    
    def _get_entry_id_mapping(self) -> Dict[str, str]:
        """Get mapping from SQLite entry_id to PostgreSQL UUID."""
        query = "SELECT entry_id, id FROM entries"
        results = self.pg_connector.fetch_all(query)
        return {row['entry_id']: str(row['id']) for row in results}
    
    def _get_sense_id_mapping(self) -> Dict[str, str]:
        """Get mapping from SQLite sense_id to PostgreSQL UUID."""
        query = "SELECT sense_id, id FROM senses"
        results = self.pg_connector.fetch_all(query)
        return {row['sense_id']: str(row['id']) for row in results}
    
    def _create_corpus_document(
        self, 
        document_name: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Create a corpus document entry and return its ID."""
        insert_query = """
        INSERT INTO corpus_documents (
            document_name, source_language, target_language,
            document_type, metadata
        ) VALUES (
            %(document_name)s, %(source_language)s, %(target_language)s,
            'parallel_corpus', %(metadata)s
        ) RETURNING id
        """
        
        metadata = {
            "migration_source": "sqlite",
            "migration_timestamp": datetime.now().isoformat(),
            "source_language": source_lang,
            "target_language": target_lang
        }
        
        with self.pg_connector.get_cursor() as cursor:
            cursor.execute(insert_query, {
                'document_name': document_name,
                'source_language': source_lang,
                'target_language': target_lang,
                'metadata': json.dumps(metadata)
            })
            result = cursor.fetchone()
            return str(result['id'])
    
    def _detect_corpus_structure(self, sqlite_conn: sqlite3.Connection) -> str:
        """Detect the structure of the SQLite corpus database."""
        cursor = sqlite_conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'search_index' in tables:
            return "search_index"
        elif 'parallel_sentences' in tables or ('english' in tables and 'polish' in tables):
            return "parallel_sentences"
        else:
            return "generic"
    
    def _migrate_parallel_sentences(
        self,
        sqlite_conn: sqlite3.Connection,
        document_id: str
    ) -> None:
        """Migrate parallel sentence data."""
        cursor = sqlite_conn.cursor()
        
        # Try different common table structures
        if self._table_exists(sqlite_conn, 'parallel_sentences'):
            query = "SELECT source_text, target_text, source_id FROM parallel_sentences"
        elif self._table_exists(sqlite_conn, 'english') and self._table_exists(sqlite_conn, 'polish'):
            query = """
            SELECT e.text as source_text, p.text as target_text, e.id as source_id 
            FROM english e 
            LEFT JOIN polish p ON e.id = p.id
            """
        else:
            self.logger.warning("No recognized parallel corpus structure found")
            return
        
        cursor.execute(query)
        
        insert_query = """
        INSERT INTO corpus_sentence_pairs (
            document_id, source_text, target_text, source_id,
            sentence_length_source, sentence_length_target
        ) VALUES (
            %(document_id)s, %(source_text)s, %(target_text)s, %(source_id)s,
            %(sentence_length_source)s, %(sentence_length_target)s
        )
        """
        
        batch_data = []
        for row in cursor:
            source_text = row[0] or ""
            target_text = row[1] or ""
            source_id = str(row[2]) if row[2] else None
            
            batch_data.append({
                'document_id': document_id,
                'source_text': source_text,
                'target_text': target_text,
                'source_id': source_id,
                'sentence_length_source': len(source_text.split()),
                'sentence_length_target': len(target_text.split())
            })
            
            if len(batch_data) >= self.config.batch_size:
                with self.pg_connector.get_cursor() as pg_cursor:
                    pg_cursor.executemany(insert_query, batch_data)
                self.stats.migrated_corpus_pairs += len(batch_data)
                batch_data = []
                self.logger.info(f"Migrated {self.stats.migrated_corpus_pairs} corpus pairs")
        
        # Insert remaining batch
        if batch_data:
            with self.pg_connector.get_cursor() as pg_cursor:
                pg_cursor.executemany(insert_query, batch_data)
            self.stats.migrated_corpus_pairs += len(batch_data)
        
        # Update document sentence count
        self._update_document_sentence_count(document_id, self.stats.migrated_corpus_pairs)
    
    def _migrate_search_index_corpus(
        self,
        sqlite_conn: sqlite3.Connection,
        document_id: str
    ) -> None:
        """Migrate corpus data from search index table."""
        cursor = sqlite_conn.cursor()
        
        # Extract examples from search_index
        cursor.execute("""
            SELECT DISTINCT example_text, definition, headword
            FROM search_index 
            WHERE example_text IS NOT NULL AND example_text != ''
        """)
        
        insert_query = """
        INSERT INTO corpus_sentence_pairs (
            document_id, source_text, target_text,
            sentence_length_source, sentence_length_target
        ) VALUES (
            %(document_id)s, %(source_text)s, %(target_text)s,
            %(sentence_length_source)s, %(sentence_length_target)s
        )
        """
        
        batch_data = []
        for row in cursor:
            example_text = row[0]
            definition = row[1]
            headword = row[2]
            
            # Use example as source, definition as target
            if example_text and definition:
                batch_data.append({
                    'document_id': document_id,
                    'source_text': example_text,
                    'target_text': definition,
                    'sentence_length_source': len(example_text.split()),
                    'sentence_length_target': len(definition.split())
                })
            
            if len(batch_data) >= self.config.batch_size:
                with self.pg_connector.get_cursor() as pg_cursor:
                    pg_cursor.executemany(insert_query, batch_data)
                self.stats.migrated_corpus_pairs += len(batch_data)
                batch_data = []
                self.logger.info(f"Migrated {self.stats.migrated_corpus_pairs} corpus pairs")
        
        # Insert remaining batch
        if batch_data:
            with self.pg_connector.get_cursor() as pg_cursor:
                pg_cursor.executemany(insert_query, batch_data)
            self.stats.migrated_corpus_pairs += len(batch_data)
        
        self._update_document_sentence_count(document_id, self.stats.migrated_corpus_pairs)
    
    def _migrate_generic_corpus(
        self,
        sqlite_conn: sqlite3.Connection,
        document_id: str
    ) -> None:
        """Migrate generic corpus data structure."""
        cursor = sqlite_conn.cursor()
        
        # Get all table names and try to find text columns
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            if table.startswith('sqlite_'):
                continue
            
            # Analyze table structure
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            text_columns = [col[1] for col in columns if 'text' in col[1].lower()]
            
            if len(text_columns) >= 2:
                # Assume first text column is source, second is target
                source_col = text_columns[0]
                target_col = text_columns[1]
                
                cursor.execute(f"SELECT {source_col}, {target_col} FROM {table}")
                
                insert_query = """
                INSERT INTO corpus_sentence_pairs (
                    document_id, source_text, target_text,
                    sentence_length_source, sentence_length_target
                ) VALUES (
                    %(document_id)s, %(source_text)s, %(target_text)s,
                    %(sentence_length_source)s, %(sentence_length_target)s
                )
                """
                
                batch_data = []
                for row in cursor:
                    source_text = str(row[0]) if row[0] else ""
                    target_text = str(row[1]) if row[1] else ""
                    
                    if source_text and target_text:
                        batch_data.append({
                            'document_id': document_id,
                            'source_text': source_text,
                            'target_text': target_text,
                            'sentence_length_source': len(source_text.split()),
                            'sentence_length_target': len(target_text.split())
                        })
                    
                    if len(batch_data) >= self.config.batch_size:
                        with self.pg_connector.get_cursor() as pg_cursor:
                            pg_cursor.executemany(insert_query, batch_data)
                        self.stats.migrated_corpus_pairs += len(batch_data)
                        batch_data = []
                        self.logger.info(f"Migrated {self.stats.migrated_corpus_pairs} corpus pairs")
                
                # Insert remaining batch
                if batch_data:
                    with self.pg_connector.get_cursor() as pg_cursor:
                        pg_cursor.executemany(insert_query, batch_data)
                    self.stats.migrated_corpus_pairs += len(batch_data)
                
                break  # Only migrate first suitable table
        
        self._update_document_sentence_count(document_id, self.stats.migrated_corpus_pairs)
    
    def _table_exists(self, sqlite_conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if table exists in SQLite database."""
        cursor = sqlite_conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None
    
    def _update_document_sentence_count(self, document_id: str, count: int) -> None:
        """Update the sentence count for a corpus document."""
        update_query = """
        UPDATE corpus_documents 
        SET sentence_count = %(count)s 
        WHERE id = %(document_id)s
        """
        
        self.pg_connector.execute_query(update_query, {
            'document_id': document_id,
            'count': count
        })
    
    def _create_performance_indexes(self) -> None:
        """Create performance indexes for migrated data."""
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_entries_headword ON entries(headword)",
            "CREATE INDEX IF NOT EXISTS idx_entries_entry_id ON entries(entry_id)",
            "CREATE INDEX IF NOT EXISTS idx_senses_entry_id ON senses(entry_id)",
            "CREATE INDEX IF NOT EXISTS idx_senses_sense_id ON senses(sense_id)",
            "CREATE INDEX IF NOT EXISTS idx_examples_sense_id ON examples(sense_id)",
            "CREATE INDEX IF NOT EXISTS idx_examples_example_id ON examples(example_id)",
            "CREATE INDEX IF NOT EXISTS idx_corpus_pairs_document_id ON corpus_sentence_pairs(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_corpus_pairs_source_text ON corpus_sentence_pairs USING gin(to_tsvector('english', source_text))",
            "CREATE INDEX IF NOT EXISTS idx_corpus_pairs_target_text ON corpus_sentence_pairs USING gin(to_tsvector('polish', target_text))",
        ]
        
        for query in index_queries:
            try:
                self.pg_connector.execute_query(query)
            except Exception as e:
                self.logger.warning(f"Failed to create index: {e}")
        
        self.logger.info("Performance indexes created")
    
    def validate_migration(self, sqlite_path: str) -> Dict[str, Any]:
        """
        Validate migration by comparing record counts and data integrity.
        
        Args:
            sqlite_path: Path to original SQLite database
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "counts": {},
            "sample_checks": []
        }
        
        try:
            # Connect to SQLite
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
            cursor = sqlite_conn.cursor()
            
            # Compare counts
            tables_to_check = [
                ("entries", "entries"),
                ("senses", "senses"),
                ("examples", "examples")
            ]
            
            for sqlite_table, pg_table in tables_to_check:
                # SQLite count
                cursor.execute(f"SELECT COUNT(*) FROM {sqlite_table}")
                sqlite_count = cursor.fetchone()[0]
                
                # PostgreSQL count
                pg_results = self.pg_connector.fetch_all(f"SELECT COUNT(*) as count FROM {pg_table}")
                pg_count = pg_results[0]['count']
                
                validation_results["counts"][pg_table] = {
                    "sqlite": sqlite_count,
                    "postgresql": pg_count,
                    "match": sqlite_count == pg_count
                }
                
                if sqlite_count != pg_count:
                    validation_results["valid"] = False
                    validation_results["errors"].append(
                        f"{pg_table}: SQLite has {sqlite_count}, PostgreSQL has {pg_count}"
                    )
            
            # Sample data validation
            cursor.execute("SELECT * FROM entries LIMIT 5")
            sample_entries = cursor.fetchall()
            
            for entry in sample_entries:
                pg_results = self.pg_connector.fetch_all(
                    "SELECT * FROM entries WHERE entry_id = %(entry_id)s",
                    {"entry_id": entry['id']}
                )
                
                if not pg_results:
                    validation_results["errors"].append(f"Entry {entry['id']} not found in PostgreSQL")
                    validation_results["valid"] = False
                else:
                    pg_entry = pg_results[0]
                    if pg_entry['headword'] != entry['headword']:
                        validation_results["errors"].append(
                            f"Entry {entry['id']}: headword mismatch"
                        )
                        validation_results["valid"] = False
            
            sqlite_conn.close()
            
        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Validation failed: {e}")
        
        return validation_results
