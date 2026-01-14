"""
High-performance corpus migrator with CSV export, PostgreSQL COPY, and TMX support.
Designed for massive parallel corpora (74M+ records) with optimal performance.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sqlite3
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional, Tuple, Dict, Any
import xml.etree.ElementTree as ET

import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from .postgresql_connector import PostgreSQLConfig


@dataclass
class MigrationStats:
    """Statistics for migration operations."""
    records_processed: int = 0
    records_exported: int = 0
    records_imported: int = 0
    errors_count: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get migration duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def records_per_second(self) -> Optional[float]:
        """Get processing rate in records per second."""
        if self.duration and self.duration > 0:
            return self.records_processed / self.duration
        return None


class TextCleaner:
    """Generator-based text cleaning for memory efficiency."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text for database storage."""
        if not text:
            return ""
        
        # Remove null bytes and other problematic characters
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Ensure proper encoding
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        return text.strip()
    
    @classmethod
    def clean_record_generator(cls, records: Generator[Tuple[str, str], None, None]) -> Generator[Tuple[str, str], None, None]:
        """Generator that cleans records on-the-fly."""
        for source, target in records:
            yield cls.clean_text(source), cls.clean_text(target)


class TMXParser:
    """TMX file parser for translation memory exchange format."""
    
    @staticmethod
    def _extract_text_from_tuv(tuv: ET.Element, target_lang: str) -> Optional[str]:
        """Extract text from TMX tuv element."""
        lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
        if not lang:
            lang = tuv.get('lang')
        
        if lang == target_lang:
            seg = tuv.find('seg')
            if seg is not None and seg.text:
                return TextCleaner.clean_text(seg.text)
        return None
    
    @staticmethod
    def parse_tmx_to_csv(tmx_path: Path, csv_path: Path, source_lang: str = 'en', target_lang: str = 'pl') -> int:
        """Parse TMX file and write to CSV format."""
        records_count = 0
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
            writer.writerow(['source_text', 'target_text'])  # Header
            
            # Parse TMX XML
            tree = ET.parse(tmx_path)
            root = tree.getroot()
            
            for tu in root.findall('.//tu'):
                source_text = ""
                target_text = ""
                
                for tuv in tu.findall('tuv'):
                    source_result = TMXParser._extract_text_from_tuv(tuv, source_lang)
                    target_result = TMXParser._extract_text_from_tuv(tuv, target_lang)
                    
                    if source_result:
                        source_text = source_result
                    if target_result:
                        target_text = target_result
                
                if source_text and target_text:
                    writer.writerow([source_text, target_text])
                    records_count += 1
        
        return records_count


class CorpusMigrator:
    """High-performance corpus migrator with CSV export and PostgreSQL COPY."""
    
    def __init__(self, postgres_config: PostgreSQLConfig, schema: str = 'corpus'):
        """Initialize migrator with PostgreSQL configuration.
        
        Args:
            postgres_config: PostgreSQL connection configuration
            schema: Schema name for parallel_corpus table (default: 'corpus')
        """
        self.postgres_config = postgres_config
        self.schema = schema
        self.logger = logging.getLogger(__name__)
        self.stats = MigrationStats()
    
    def _get_postgres_connection(self, autocommit: bool = False) -> psycopg2.extensions.connection:
        """Get PostgreSQL connection with proper encoding."""
        conn = psycopg2.connect(
            host=self.postgres_config.host,
            port=self.postgres_config.port,
            database=self.postgres_config.database,
            user=self.postgres_config.username,
            password=self.postgres_config.password,
            client_encoding='UTF8'
        )
        
        if autocommit:
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        return conn
    
    def create_database_if_not_exists(self) -> None:
        """Create target database if it doesn't exist."""
        # First try to connect to the target database directly
        try:
            test_conn = self._get_postgres_connection()
            test_conn.close()
            self.logger.info(f"Database {self.postgres_config.database} already exists and is accessible")
            return
        except psycopg2.OperationalError:
            # Database doesn't exist or is not accessible, try to create it
            pass
        
        # Try to connect to default database to create target database
        try:
            temp_config = PostgreSQLConfig(
                host=self.postgres_config.host,
                port=self.postgres_config.port,
                database='postgres',
                username=self.postgres_config.username,
                password=self.postgres_config.password
            )
            
            conn = psycopg2.connect(
                host=temp_config.host,
                port=temp_config.port,
                database=temp_config.database,
                user=temp_config.username,
                password=temp_config.password,
                client_encoding='UTF8'
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            try:
                with conn.cursor() as cur:
                    # Check if database exists
                    cur.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (self.postgres_config.database,)
                    )
                    
                    if not cur.fetchone():
                        cur.execute(f'CREATE DATABASE "{self.postgres_config.database}" ENCODING \'UTF8\'')
                        self.logger.info(f"Created database: {self.postgres_config.database}")
            finally:
                conn.close()
        except psycopg2.Error as e:
            # If we can't connect to postgres database or create the target database,
            # assume the target database already exists (common in testing scenarios)
            self.logger.warning(f"Could not create database {self.postgres_config.database}: {e}")
            self.logger.info("Assuming target database already exists")
    
    def drop_database(self) -> None:
        """Drop the target database (for cleanup)."""
        try:
            temp_config = PostgreSQLConfig(
                host=self.postgres_config.host,
                port=self.postgres_config.port,
                database='postgres',
                username=self.postgres_config.username,
                password=self.postgres_config.password
            )
            
            conn = psycopg2.connect(
                host=temp_config.host,
                port=temp_config.port,
                database=temp_config.database,
                user=temp_config.username,
                password=temp_config.password,
                client_encoding='UTF8'
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            try:
                with conn.cursor() as cur:
                    # Terminate connections to target database
                    cur.execute("""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = %s
                        AND pid <> pg_backend_pid()
                    """, (self.postgres_config.database,))
                    
                    # Drop database
                    cur.execute(f'DROP DATABASE IF EXISTS "{self.postgres_config.database}"')
                    self.logger.info(f"Dropped database: {self.postgres_config.database}")
            finally:
                conn.close()
        except psycopg2.Error as e:
            self.logger.warning(f"Could not drop database {self.postgres_config.database}: {e}")
    
    def create_schema(self) -> None:
        """Create corpus schema without indexes (for fast loading)."""
        conn = self._get_postgres_connection()
        
        try:
            with conn.cursor() as cur:
                # Create corpus schema if it doesn't exist
                cur.execute("CREATE SCHEMA IF NOT EXISTS corpus")
                
                # Set search path to use corpus schema
                cur.execute("SET search_path TO corpus, public")
                
                # Check if table already exists
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_name = 'parallel_corpus'
                    AND table_schema = %s
                """, (self.schema,))
                table_exists = cur.fetchone()[0] > 0
                
                if not table_exists:
                    # Drop table if exists and create new one
                    cur.execute(f"DROP TABLE IF EXISTS {self.schema}.parallel_corpus")
                    
                    # Create table without indexes
                    cur.execute(f"""
                        CREATE TABLE {self.schema}.parallel_corpus (
                            id SERIAL PRIMARY KEY,
                            source_text TEXT NOT NULL,
                            target_text TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    conn.commit()
                    self.logger.info("Created corpus schema (without indexes)")
                else:
                    self.logger.info("Corpus table already exists, skipping creation")
        finally:
            conn.close()
    
    def create_indexes(self) -> None:
        """Create indexes after data loading for optimal performance."""
        conn = self._get_postgres_connection(autocommit=True)  # Use autocommit for CONCURRENTLY
        
        try:
            with conn.cursor() as cur:
                # Set search path to use specified schema
                cur.execute(f"SET search_path TO {self.schema}, public")
                
                self.logger.info("Creating indexes...")
                
                # Create B-tree indexes for exact searches
                cur.execute(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_source_text ON {self.schema}.parallel_corpus USING btree (source_text)")
                cur.execute(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_target_text ON {self.schema}.parallel_corpus USING btree (target_text)")
                
                # Create full-text search indexes
                try:
                    # Try Polish configuration first
                    cur.execute(f"""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_source_fts 
                        ON {self.schema}.parallel_corpus USING gin (to_tsvector('english', source_text))
                    """)
                    cur.execute(f"""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_target_fts 
                        ON {self.schema}.parallel_corpus USING gin (to_tsvector('polish', target_text))
                    """)
                except psycopg2.Error:
                    # Fallback to simple configuration
                    self.logger.warning("Polish text search config not available, using simple")
                    cur.execute(f"""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_target_fts 
                        ON {self.schema}.parallel_corpus USING gin (to_tsvector('simple', target_text))
                    """)
                
                self.logger.info("Indexes created successfully")
        finally:
            conn.close()
    
    def export_sqlite_to_csv(self, sqlite_path: Path, csv_path: Path) -> int:
        """Export SQLite corpus to CSV with text cleaning."""
        self.logger.info(f"Exporting SQLite {sqlite_path} to CSV {csv_path}")
        
        conn = sqlite3.connect(str(sqlite_path))
        conn.row_factory = sqlite3.Row
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                writer.writerow(['source_text', 'target_text'])  # Header
                
                # Use the correct table and column names for para_crawl format
                cursor = conn.execute("SELECT c0en, c1pl FROM tmdata_content")
                
                # Use generator for memory efficiency
                def record_generator():
                    while True:
                        batch = cursor.fetchmany(10000)  # Process in batches
                        if not batch:
                            break
                        for row in batch:
                            yield row['c0en'], row['c1pl']
                
                # Clean and write records
                for source, target in TextCleaner.clean_record_generator(record_generator()):
                    if source and target:  # Skip empty records
                        writer.writerow([source, target])
                        self.stats.records_exported += 1
                        
                        if self.stats.records_exported % 100000 == 0:
                            self.logger.info(f"Exported {self.stats.records_exported} records")
        
        finally:
            conn.close()
        
        self.logger.info(f"Export complete: {self.stats.records_exported} records")
        return self.stats.records_exported
    
    def import_csv_to_postgres(self, csv_path: Path) -> int:
        """Import CSV to PostgreSQL using COPY for maximum performance."""
        self.logger.info(f"Importing CSV {csv_path} to PostgreSQL")
        
        conn = self._get_postgres_connection()
        
        try:
            with conn.cursor() as cur:
                # Set search path to use specified schema
                cur.execute(f"SET search_path TO {self.schema}, public")
                
                # Use COPY for fast bulk import
                with open(csv_path, 'r', encoding='utf-8') as csvfile:
                    # Skip header
                    next(csvfile)
                    
                    cur.copy_expert(f"""
                        COPY {self.schema}.parallel_corpus (source_text, target_text) 
                        FROM STDIN WITH CSV QUOTE '"'
                    """, csvfile)
                
                # Get count of imported records
                cur.execute(f"SELECT COUNT(*) FROM {self.schema}.parallel_corpus")
                count_result = cur.fetchone()
                if count_result:
                    self.stats.records_imported = count_result[0]
                
                conn.commit()
                self.logger.info(f"Import complete: {self.stats.records_imported} records")
        
        finally:
            conn.close()
        
        return self.stats.records_imported
    
    def deduplicate_corpus(self) -> int:
        """Remove duplicate entries from the corpus."""
        self.logger.info("Deduplicating corpus...")
        
        conn = self._get_postgres_connection()
        
        try:
            with conn.cursor() as cur:
                # Set search path to use specified schema
                cur.execute(f"SET search_path TO {self.schema}, public")
                
                # Delete duplicates keeping the first occurrence
                cur.execute(f"""
                    DELETE FROM {self.schema}.parallel_corpus 
                    WHERE id NOT IN (
                        SELECT MIN(id) 
                        FROM {self.schema}.parallel_corpus 
                        GROUP BY source_text, target_text
                    )
                """)
                
                duplicates_removed = cur.rowcount
                conn.commit()
                
                self.logger.info(f"Removed {duplicates_removed} duplicate records")
                return duplicates_removed
        
        finally:
            conn.close()
    
    def migrate_sqlite_corpus(self, sqlite_path: Path, cleanup_temp: bool = True) -> MigrationStats:
        """Complete migration workflow: SQLite -> CSV -> PostgreSQL with indexes."""
        self.stats.start_time = time.time()
        
        try:
            # Create database and schema
            self.create_database_if_not_exists()
            self.create_schema()
            
            # Export to temporary CSV
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False, encoding='utf-8') as temp_csv:
                csv_path = Path(temp_csv.name)
            
            try:
                # Export SQLite to CSV
                self.export_sqlite_to_csv(sqlite_path, csv_path)
                
                # Import CSV to PostgreSQL
                self.import_csv_to_postgres(csv_path)
                
                # Create indexes after data loading
                self.create_indexes()
                
                # Deduplicate if needed
                duplicates = self.deduplicate_corpus()
                self.logger.info(f"Deduplication removed {duplicates} records")
                
            finally:
                # Cleanup temporary CSV
                if cleanup_temp and csv_path.exists():
                    csv_path.unlink()
                    self.logger.info("Cleaned up temporary CSV file")
        
        finally:
            self.stats.end_time = time.time()
            self.stats.records_processed = self.stats.records_imported
        
        return self.stats
    
    def convert_tmx_to_csv(self, tmx_path: Path, csv_path: Path, source_lang: str = 'en', target_lang: str = 'pl') -> int:
        """Convert TMX file to CSV format."""
        return TMXParser.parse_tmx_to_csv(tmx_path, csv_path, source_lang, target_lang)
    
    def migrate_tmx_corpus(self, tmx_path: Path, source_lang: str = 'en', target_lang: str = 'pl', cleanup_temp: bool = True) -> MigrationStats:
        """Complete migration workflow: TMX -> CSV -> PostgreSQL with indexes."""
        self.stats.start_time = time.time()
        
        try:
            # Create database and schema
            self.create_database_if_not_exists()
            self.create_schema()
            
            # Convert to temporary CSV
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False, encoding='utf-8') as temp_csv:
                csv_path = Path(temp_csv.name)
            
            try:
                # Convert TMX to CSV
                records_converted = self.convert_tmx_to_csv(tmx_path, csv_path, source_lang, target_lang)
                self.stats.records_exported = records_converted
                
                # Import CSV to PostgreSQL
                self.import_csv_to_postgres(csv_path)
                
                # Create indexes after data loading
                self.create_indexes()
                
                # Deduplicate if needed
                duplicates = self.deduplicate_corpus()
                self.logger.info(f"Deduplication removed {duplicates} records")
                
            finally:
                # Cleanup temporary CSV
                if cleanup_temp and csv_path.exists():
                    csv_path.unlink()
                    self.logger.info("Cleaned up temporary CSV file")
        
        finally:
            self.stats.end_time = time.time()
            self.stats.records_processed = self.stats.records_imported
        
        return self.stats
    
    def get_corpus_stats(self) -> Dict[str, Any]:
        """Get corpus statistics from PostgreSQL."""
        conn = self._get_postgres_connection()
        
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Use specified schema
                try:
                    cur.execute(f"SET search_path TO {self.schema}, public")
                    
                    cur.execute(f"""
                        SELECT 
                            COUNT(*) as total_records,
                            AVG(LENGTH(source_text)) as avg_source_length,
                            AVG(LENGTH(target_text)) as avg_target_length,
                            MIN(created_at) as first_record,
                            MAX(created_at) as last_record
                        FROM {self.schema}.parallel_corpus
                    """)
                    
                    result = cur.fetchone()
                    if result and result['total_records'] > 0:
                        return dict(result)
                
                except psycopg2.errors.UndefinedTable:
                    # Table doesn't exist in corpus schema, rollback and try public schema
                    conn.rollback()
                
                # Fallback to public schema (legacy location)
                try:
                    cur.execute("SET search_path TO public")
                    
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_records,
                            AVG(LENGTH(source_text)) as avg_source_length,
                            AVG(LENGTH(target_text)) as avg_target_length,
                            MIN(created_at) as first_record,
                            MAX(created_at) as last_record
                        FROM parallel_corpus
                    """)
                    
                    result = cur.fetchone()
                    if result:
                        return dict(result)
                        
                except psycopg2.errors.UndefinedTable:
                    # Neither table exists
                    conn.rollback()
                
                # No data found in either location
                return {
                    'total_records': 0,
                    'avg_source_length': 0.0,
                    'avg_target_length': 0.0,
                    'first_record': None,
                    'last_record': None
                }
        
        finally:
            conn.close()


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(description='High-performance corpus migrator')
    parser.add_argument('input_file', help='Input file (SQLite .db, TMX .tmx, or CSV .csv)')
    parser.add_argument('--format', choices=['sqlite', 'tmx', 'csv'], help='Input format (auto-detected if not specified)')
    parser.add_argument('--source-lang', default='en', help='Source language code (for TMX)')
    parser.add_argument('--target-lang', default='pl', help='Target language code (for TMX)')
    parser.add_argument('--drop-existing', action='store_true', help='Drop existing database before migration')
    parser.add_argument('--no-cleanup', action='store_true', help='Keep temporary files')
    parser.add_argument('--stats-only', action='store_true', help='Show corpus statistics only')
    return parser


def _detect_format(input_path: Path, specified_format: Optional[str]) -> Optional[str]:
    """Auto-detect input file format."""
    if specified_format:
        return specified_format
    
    suffix = input_path.suffix.lower()
    if suffix == '.db':
        return 'sqlite'
    elif suffix == '.tmx':
        return 'tmx'
    elif suffix == '.csv':
        return 'csv'
    return None


def _perform_migration(migrator: CorpusMigrator, format_type: str, input_path: Path, args: argparse.Namespace) -> MigrationStats:
    """Perform the actual migration based on format type."""
    cleanup_temp = not args.no_cleanup
    
    if format_type == 'sqlite':
        return migrator.migrate_sqlite_corpus(input_path, cleanup_temp)
    elif format_type == 'tmx':
        return migrator.migrate_tmx_corpus(input_path, args.source_lang, args.target_lang, cleanup_temp)
    elif format_type == 'csv':
        # For CSV, create schema and import directly
        migrator.create_database_if_not_exists()
        migrator.create_schema()
        migrator.import_csv_to_postgres(input_path)
        migrator.create_indexes()
        return migrator.stats
    else:
        raise ValueError(f"Unsupported format: {format_type}")


def main():
    """CLI entry point for corpus migration."""
    from pathlib import Path
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv('.env.local')
    
    parser = _setup_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # PostgreSQL configuration from environment
    postgres_config = PostgreSQLConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'parallel_corpus'),
        username=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', '')
    )
    
    migrator = CorpusMigrator(postgres_config)
    
    if args.stats_only:
        stats = migrator.get_corpus_stats()
        print("Corpus Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist")
        return
    
    # Auto-detect format if not specified
    format_type = _detect_format(input_path, args.format)
    if not format_type:
        print(f"Error: Cannot auto-detect format for {input_path}. Please specify --format")
        return
    
    # Drop database if requested
    if args.drop_existing:
        migrator.drop_database()
    
    # Perform migration
    try:
        stats = _perform_migration(migrator, format_type, input_path, args)
        
        # Print results
        print("\nMigration completed successfully!")
        print(f"Records processed: {stats.records_processed:,}")
        if stats.duration:
            print(f"Duration: {stats.duration:.2f} seconds")
        if stats.records_per_second:
            print(f"Rate: {stats.records_per_second:,.0f} records/second")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == '__main__':
    main()
