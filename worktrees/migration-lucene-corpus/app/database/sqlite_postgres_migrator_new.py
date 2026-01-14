"""
SQLite to PostgreSQL corpus migration utility.

Migrates flat corpus databases (like para_crawl.db) from SQLite to PostgreSQL
with full-text search capabilities and data validation.
"""
from __future__ import annotations

import os
import sqlite3
import logging
import argparse
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from app.database.postgresql_connector import PostgreSQLConnector, PostgreSQLConfig
from app.utils.exceptions import DatabaseError, ValidationError


@dataclass
class MigrationStats:
    """Statistics for migration process."""
    records_migrated: int = 0
    errors: List[str] = field(default_factory=list)


class SQLiteToPostgreSQLMigrator:
    """
    Migrates flat corpus data from SQLite to PostgreSQL.
    
    Supports various corpus formats including parallel text corpora.
    """
    
    def __init__(self, postgres_config: Optional[PostgreSQLConfig] = None):
        """
        Initialize migrator.
        
        Args:
            postgres_config: PostgreSQL configuration. If None, loads from environment.
        """
        self.postgres_connector = PostgreSQLConnector(postgres_config)
        self.logger = logging.getLogger(__name__)
        self.stats = MigrationStats()
    
    def migrate_corpus(self, sqlite_path: str, batch_size: int = 1000, validate_integrity: bool = True) -> MigrationStats:
        """
        Migrate corpus data from SQLite to PostgreSQL.
        
        Args:
            sqlite_path: Path to SQLite database file
            batch_size: Number of records to process in each batch
            validate_integrity: Whether to validate data integrity after migration
            
        Returns:
            Migration statistics
        """
        self.logger.info(f"Starting corpus migration from {sqlite_path}")
        
        # Ensure target database exists
        db_created = self.postgres_connector.ensure_database_exists()
        if db_created:
            self.logger.info("Created target database")
            # Reconnect to the new database
            self.postgres_connector.close()
            self.postgres_connector.reconnect()
        
        # Detect corpus format and migrate accordingly
        corpus_format = self.detect_corpus_format(sqlite_path)
        self.logger.info(f"Detected corpus format: {corpus_format}")
        
        if corpus_format == "para_crawl":
            return self.migrate_para_crawl(sqlite_path, batch_size, validate_integrity)
        elif corpus_format == "parallel_corpus":
            return self.migrate_parallel_corpus(sqlite_path, batch_size, validate_integrity)
        else:
            raise ValidationError(f"Unsupported corpus format: {corpus_format}")
    
    def detect_corpus_format(self, sqlite_path: str) -> str:
        """
        Detect the format of the corpus database.
        
        Returns:
            String identifying the corpus format
        """
        try:
            with sqlite3.connect(sqlite_path) as conn:
                cursor = conn.cursor()
                
                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Check for para_crawl format (tmdata_content table)
                if 'tmdata_content' in tables:
                    cursor.execute("PRAGMA table_info(tmdata_content)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if all(col in columns for col in ['c0en', 'c1pl', 'c2source']):
                        return "para_crawl"
                
                # Check for generic parallel corpus format
                if any('source' in table.lower() and 'target' in table.lower() for table in tables):
                    return "parallel_corpus"
                
                # Default fallback
                return "unknown"
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to detect corpus format: {e}")
            raise ValidationError(f"Cannot read SQLite database: {e}")
    
    def migrate_para_crawl(self, sqlite_path: str, batch_size: int, validate_integrity: bool) -> MigrationStats:
        """Migrate para_crawl format corpus data."""
        self.logger.info("Migrating para_crawl format corpus")
        
        # Setup schema
        self.setup_para_crawl_schema()
        
        # Migrate data
        migrated_count = self.migrate_para_crawl_data(sqlite_path, batch_size)
        self.stats.records_migrated = migrated_count
        
        # Validate if requested
        if validate_integrity:
            self.validate_para_crawl_integrity(sqlite_path)
        
        return self.stats
    
    def setup_para_crawl_schema(self) -> None:
        """Setup PostgreSQL schema for para_crawl corpus data."""
        self.logger.info("Setting up para_crawl schema...")
        
        # Enable extensions
        extensions = [
            'CREATE EXTENSION IF NOT EXISTS pg_trgm',
            'CREATE EXTENSION IF NOT EXISTS unaccent'
        ]
        for ext in extensions:
            self.postgres_connector.execute_query(ext)
        
        # Create main corpus table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS parallel_corpus (
            id SERIAL PRIMARY KEY,
            docid INTEGER,
            english_text TEXT NOT NULL,
            polish_text TEXT NOT NULL,
            source_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.postgres_connector.execute_query(create_table_sql)
        
        # Create full-text search indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_parallel_corpus_docid ON parallel_corpus(docid)",
            "CREATE INDEX IF NOT EXISTS idx_parallel_corpus_english_fts ON parallel_corpus USING GIN(to_tsvector('english', english_text))",
            "CREATE INDEX IF NOT EXISTS idx_parallel_corpus_polish_fts ON parallel_corpus USING GIN(to_tsvector('polish', polish_text))",
            "CREATE INDEX IF NOT EXISTS idx_parallel_corpus_source ON parallel_corpus(source_info)"
        ]
        
        for index_sql in indexes:
            self.postgres_connector.execute_query(index_sql)
        
        self.logger.info("Para_crawl schema created successfully")
    
    def migrate_para_crawl_data(self, sqlite_path: str, batch_size: int) -> int:
        """Migrate para_crawl data in batches."""
        migrated_count = 0
        
        try:
            with sqlite3.connect(sqlite_path) as sqlite_conn:
                cursor = sqlite_conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM tmdata_content")
                total_records = cursor.fetchone()[0]
                self.logger.info(f"Total records to migrate: {total_records:,}")
                
                # Migrate in batches
                offset = 0
                while True:
                    cursor.execute("""
                        SELECT docid, c0en, c1pl, c2source 
                        FROM tmdata_content 
                        ORDER BY docid 
                        LIMIT ? OFFSET ?
                    """, (batch_size, offset))
                    
                    batch = cursor.fetchall()
                    if not batch:
                        break
                    
                    # Insert batch into PostgreSQL
                    insert_sql = """
                        INSERT INTO parallel_corpus (docid, english_text, polish_text, source_info)
                        VALUES (%s, %s, %s, %s)
                    """
                    
                    with self.postgres_connector.get_cursor() as pg_cursor:
                        pg_cursor.executemany(insert_sql, batch)
                    
                    migrated_count += len(batch)
                    offset += batch_size
                    
                    # Progress logging
                    progress = (migrated_count / total_records) * 100
                    self.logger.info(f"Progress: {migrated_count:,}/{total_records:,} ({progress:.1f}%)")
                
        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            self.logger.error(error_msg)
            self.stats.errors.append(error_msg)
            raise DatabaseError(error_msg)
        
        return migrated_count
    
    def validate_para_crawl_integrity(self, sqlite_path: str) -> bool:
        """Validate migration integrity for para_crawl data."""
        try:
            # Count records in SQLite
            with sqlite3.connect(sqlite_path) as sqlite_conn:
                cursor = sqlite_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tmdata_content")
                sqlite_count = cursor.fetchone()[0]
            
            # Count records in PostgreSQL
            result = self.postgres_connector.fetch_one("SELECT COUNT(*) as count FROM parallel_corpus")
            postgres_count = result['count'] if result else 0
            
            if sqlite_count == postgres_count:
                self.logger.info(f"✓ Integrity check passed: {sqlite_count:,} records in both databases")
                return True
            else:
                error_msg = f"✗ Integrity check failed: SQLite has {sqlite_count:,} records, PostgreSQL has {postgres_count:,}"
                self.logger.error(error_msg)
                self.stats.errors.append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Integrity validation failed: {e}"
            self.logger.error(error_msg)
            self.stats.errors.append(error_msg)
            return False
    
    def migrate_parallel_corpus(self, sqlite_path: str, batch_size: int, validate_integrity: bool) -> MigrationStats:
        """Migrate generic parallel corpus format."""
        # This can be extended for other corpus formats
        raise ValidationError("Generic parallel corpus migration not yet implemented")


def main():
    """CLI interface for corpus migration utility."""
    parser = argparse.ArgumentParser(description='Migrate corpus data from SQLite to PostgreSQL')
    parser.add_argument('--sqlite-path', required=True, help='Path to SQLite database file')
    parser.add_argument('--postgres-url', required=True, help='PostgreSQL connection URL')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for migration')
    parser.add_argument('--validate', action='store_true', help='Validate migration integrity')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else args.log_level
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Parse PostgreSQL URL
        parsed_url = urlparse(args.postgres_url)
        
        postgres_config = PostgreSQLConfig(
            host=parsed_url.hostname or 'localhost',
            port=parsed_url.port or 5432,
            database=parsed_url.path.lstrip('/') if parsed_url.path else 'corpus_db',
            username=parsed_url.username or 'postgres',
            password=parsed_url.password or ''
        )
        
        migrator = SQLiteToPostgreSQLMigrator(postgres_config)
        stats = migrator.migrate_corpus(args.sqlite_path, args.batch_size, args.validate)
        
        print("\n" + "="*50)
        print("MIGRATION COMPLETED")
        print("="*50)
        print(f"Records migrated: {stats.records_migrated:,}")
        
        if stats.errors:
            print(f"Errors encountered: {len(stats.errors)}")
            for error in stats.errors:
                print(f"  ✗ {error}")
        else:
            print("✓ No errors encountered")
        
        print("="*50)
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        exit(1)


if __name__ == '__main__':
    main()
