"""
SQLite to PostgreSQL data migration utility.

Provides tools to migrate dictionary data from SQLite to PostgreSQL
with full data validation and integrity checks.
"""
import os
import json
import sqlite3
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from app.database.postgresql_connector import PostgreSQLConnector, PostgreSQLConfig
from app.utils.exceptions import DatabaseError, ValidationError


@dataclass
class MigrationStats:
    """Statistics for migration process."""
    entries_migrated: int = 0
    senses_migrated: int = 0
    examples_migrated: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SQLiteToPostgreSQLMigrator:
    """
    Migrates dictionary data from SQLite to PostgreSQL.
    
    Handles schema differences, data transformation, and validation.
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
    
    def setup_postgresql_schema(self) -> None:
        """Create PostgreSQL schema for dictionary data."""
        self.logger.info("Setting up PostgreSQL schema...")
        
        # Enable required extensions
        self.postgres_connector.execute_query('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        self.postgres_connector.execute_query('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        
        # Create entries table
        self.postgres_connector.execute_query("""
            CREATE TABLE IF NOT EXISTS entries (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
            )
        """)
        
        # Create senses table
        self.postgres_connector.execute_query("""
            CREATE TABLE IF NOT EXISTS senses (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                sense_id TEXT UNIQUE NOT NULL,
                entry_id TEXT NOT NULL,
                definition TEXT,
                grammatical_info JSONB,
                custom_fields JSONB,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES entries (entry_id) ON DELETE CASCADE
            )
        """)
        
        # Create examples table
        self.postgres_connector.execute_query("""
            CREATE TABLE IF NOT EXISTS examples (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                example_id TEXT UNIQUE NOT NULL,
                sense_id TEXT NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                custom_fields JSONB,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sense_id) REFERENCES senses (sense_id) ON DELETE CASCADE
            )
        """)
        
        # Create frequency data table for SUBTLEX integration
        self.postgres_connector.execute_query("""
            CREATE TABLE IF NOT EXISTS frequency_data (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                word TEXT NOT NULL,
                lemma TEXT,
                frequency INTEGER NOT NULL,
                subtlex_cd FLOAT,
                subtlex_frequency FLOAT,
                pos_tag TEXT,
                length INTEGER,
                syllable_count INTEGER,
                phonetic_form TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create word sketches table
        self.postgres_connector.execute_query("""
            CREATE TABLE IF NOT EXISTS word_sketches (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                target_word TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                collocate TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                significance_score FLOAT,
                mutual_information FLOAT,
                t_score FLOAT,
                dice_coefficient FLOAT,
                pos_pattern TEXT,
                example_sentences TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_entries_headword ON entries(headword)",
            "CREATE INDEX IF NOT EXISTS idx_entries_entry_id ON entries(entry_id)",
            "CREATE INDEX IF NOT EXISTS idx_senses_entry_id ON senses(entry_id)",
            "CREATE INDEX IF NOT EXISTS idx_examples_sense_id ON examples(sense_id)",
            "CREATE INDEX IF NOT EXISTS idx_frequency_word ON frequency_data(word)",
            "CREATE INDEX IF NOT EXISTS idx_frequency_lemma ON frequency_data(lemma)",
            "CREATE INDEX IF NOT EXISTS idx_word_sketches_target ON word_sketches(target_word)",
            "CREATE INDEX IF NOT EXISTS idx_word_sketches_relation ON word_sketches(relation_type)",
            # Full-text search indexes
            "CREATE INDEX IF NOT EXISTS idx_entries_headword_trgm ON entries USING gin (headword gin_trgm_ops)",
            "CREATE INDEX IF NOT EXISTS idx_frequency_word_trgm ON frequency_data USING gin (word gin_trgm_ops)",
        ]
        
        for index_sql in indexes:
            try:
                self.postgres_connector.execute_query(index_sql)
            except DatabaseError as e:
                self.logger.warning(f"Failed to create index: {e}")
        
        self.logger.info("PostgreSQL schema setup completed")
    
    def validate_sqlite_schema(self, sqlite_path: str) -> bool:
        """
        Validate SQLite database schema.
        
        Args:
            sqlite_path: Path to SQLite database file
            
        Returns:
            True if schema is valid, False otherwise
        """
        try:
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Check required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['entries', 'senses', 'examples']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                self.logger.error(f"Missing required tables: {missing_tables}")
                return False
            
            # Check required columns in entries table
            cursor.execute("PRAGMA table_info(entries)")
            entry_columns = [row[1] for row in cursor.fetchall()]
            
            required_entry_columns = ['id', 'headword']
            missing_columns = [col for col in required_entry_columns if col not in entry_columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns in entries table: {missing_columns}")
                return False
            
            conn.close()
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"SQLite validation failed: {e}")
            return False
    
    def transform_data_for_postgresql(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform SQLite data for PostgreSQL compatibility.
        
        Args:
            data: Raw SQLite row data
            
        Returns:
            Transformed data for PostgreSQL
        """
        transformed = {}
        
        for key, value in data.items():
            if value is None:
                transformed[key] = None
            elif key in ['grammatical_info', 'custom_fields']:
                # Parse JSON strings
                if isinstance(value, str):
                    try:
                        transformed[key] = json.loads(value)
                    except json.JSONDecodeError:
                        # Treat as simple string, wrap in object
                        transformed[key] = {"raw": value}
                else:
                    transformed[key] = value
            elif key in ['date_created', 'date_modified']:
                # Parse datetime strings
                if isinstance(value, str):
                    try:
                        # Try common formats
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                            try:
                                transformed[key] = datetime.strptime(value, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            # Fallback to current time
                            transformed[key] = datetime.now()
                    except ValueError:
                        transformed[key] = datetime.now()
                else:
                    transformed[key] = value
            else:
                transformed[key] = value
        
        return transformed
    
    def migrate_entries(self, sqlite_path: str) -> int:
        """
        Migrate entries from SQLite to PostgreSQL.
        
        Args:
            sqlite_path: Path to SQLite database file
            
        Returns:
            Number of entries migrated
        """
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM entries")
        entries = cursor.fetchall()
        
        migrated_count = 0
        
        for entry in entries:
            try:
                entry_data = dict(entry)
                transformed_data = self.transform_data_for_postgresql(entry_data)
                
                # Map SQLite id to entry_id
                transformed_data['entry_id'] = transformed_data.pop('id')
                
                # Convert grammatical_info to JSONB
                if 'grammatical_info' in transformed_data:
                    gi = transformed_data['grammatical_info']
                    if isinstance(gi, dict):
                        transformed_data['grammatical_info'] = json.dumps(gi)
                    elif isinstance(gi, str) and gi:
                        try:
                            # Try to parse as JSON
                            json.loads(gi)
                            # It's valid JSON, keep as string for JSONB
                        except json.JSONDecodeError:
                            # Not valid JSON, wrap as object
                            transformed_data['grammatical_info'] = json.dumps({"type": gi})
                
                # Similar for custom_fields
                if 'custom_fields' in transformed_data:
                    cf = transformed_data['custom_fields']
                    if isinstance(cf, dict):
                        transformed_data['custom_fields'] = json.dumps(cf)
                    elif isinstance(cf, str) and cf:
                        try:
                            json.loads(cf)
                        except json.JSONDecodeError:
                            transformed_data['custom_fields'] = json.dumps({"raw": cf})
                
                # Insert into PostgreSQL
                self.postgres_connector.execute_query("""
                    INSERT INTO entries 
                    (entry_id, headword, pronunciation, grammatical_info, date_created, 
                     date_modified, custom_fields, frequency_rank, subtlex_frequency)
                    VALUES (%(entry_id)s, %(headword)s, %(pronunciation)s, %(grammatical_info)s,
                            %(date_created)s, %(date_modified)s, %(custom_fields)s, 
                            %(frequency_rank)s, %(subtlex_frequency)s)
                    ON CONFLICT (entry_id) DO NOTHING
                """, {
                    'entry_id': transformed_data.get('entry_id'),
                    'headword': transformed_data.get('headword'),
                    'pronunciation': transformed_data.get('pronunciation'),
                    'grammatical_info': transformed_data.get('grammatical_info'),
                    'date_created': transformed_data.get('date_created'),
                    'date_modified': transformed_data.get('date_modified'),
                    'custom_fields': transformed_data.get('custom_fields'),
                    'frequency_rank': transformed_data.get('frequency_rank'),
                    'subtlex_frequency': transformed_data.get('subtlex_frequency')
                })
                
                migrated_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to migrate entry {entry.get('id', 'unknown')}: {e}")
                self.stats.errors.append(f"Entry migration error: {e}")
        
        conn.close()
        self.stats.entries_migrated = migrated_count
        return migrated_count
    
    def migrate_senses(self, sqlite_path: str) -> int:
        """
        Migrate senses from SQLite to PostgreSQL.
        
        Args:
            sqlite_path: Path to SQLite database file
            
        Returns:
            Number of senses migrated
        """
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM senses")
        senses = cursor.fetchall()
        
        migrated_count = 0
        
        for sense in senses:
            try:
                sense_data = dict(sense)
                transformed_data = self.transform_data_for_postgresql(sense_data)
                
                # Map SQLite id to sense_id
                transformed_data['sense_id'] = transformed_data.pop('id')
                
                # Handle JSONB fields
                for field in ['grammatical_info', 'custom_fields']:
                    if field in transformed_data:
                        value = transformed_data[field]
                        if isinstance(value, dict):
                            transformed_data[field] = json.dumps(value)
                        elif isinstance(value, str) and value:
                            try:
                                json.loads(value)
                            except json.JSONDecodeError:
                                transformed_data[field] = json.dumps({"raw": value})
                
                self.postgres_connector.execute_query("""
                    INSERT INTO senses 
                    (sense_id, entry_id, definition, grammatical_info, custom_fields, sort_order)
                    VALUES (%(sense_id)s, %(entry_id)s, %(definition)s, %(grammatical_info)s,
                            %(custom_fields)s, %(sort_order)s)
                    ON CONFLICT (sense_id) DO NOTHING
                """, {
                    'sense_id': transformed_data.get('sense_id'),
                    'entry_id': transformed_data.get('entry_id'),
                    'definition': transformed_data.get('definition'),
                    'grammatical_info': transformed_data.get('grammatical_info'),
                    'custom_fields': transformed_data.get('custom_fields'),
                    'sort_order': transformed_data.get('sort_order', 0)
                })
                
                migrated_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to migrate sense {sense.get('id', 'unknown')}: {e}")
                self.stats.errors.append(f"Sense migration error: {e}")
        
        conn.close()
        self.stats.senses_migrated = migrated_count
        return migrated_count
    
    def migrate_examples(self, sqlite_path: str) -> int:
        """
        Migrate examples from SQLite to PostgreSQL.
        
        Args:
            sqlite_path: Path to SQLite database file
            
        Returns:
            Number of examples migrated
        """
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM examples")
        examples = cursor.fetchall()
        
        migrated_count = 0
        
        for example in examples:
            try:
                example_data = dict(example)
                transformed_data = self.transform_data_for_postgresql(example_data)
                
                # Map SQLite id to example_id
                transformed_data['example_id'] = transformed_data.pop('id')
                
                # Handle custom_fields JSONB
                if 'custom_fields' in transformed_data:
                    value = transformed_data['custom_fields']
                    if isinstance(value, dict):
                        transformed_data['custom_fields'] = json.dumps(value)
                    elif isinstance(value, str) and value:
                        try:
                            json.loads(value)
                        except json.JSONDecodeError:
                            transformed_data['custom_fields'] = json.dumps({"raw": value})
                
                self.postgres_connector.execute_query("""
                    INSERT INTO examples 
                    (example_id, sense_id, text, translation, custom_fields, sort_order)
                    VALUES (%(example_id)s, %(sense_id)s, %(text)s, %(translation)s,
                            %(custom_fields)s, %(sort_order)s)
                    ON CONFLICT (example_id) DO NOTHING
                """, {
                    'example_id': transformed_data.get('example_id'),
                    'sense_id': transformed_data.get('sense_id'),
                    'text': transformed_data.get('text'),
                    'translation': transformed_data.get('translation'),
                    'custom_fields': transformed_data.get('custom_fields'),
                    'sort_order': transformed_data.get('sort_order', 0)
                })
                
                migrated_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to migrate example {example.get('id', 'unknown')}: {e}")
                self.stats.errors.append(f"Example migration error: {e}")
        
        conn.close()
        self.stats.examples_migrated = migrated_count
        return migrated_count
    
    def migrate_database(self, sqlite_path: str, validate_integrity: bool = True) -> MigrationStats:
        """
        Perform complete database migration from SQLite to PostgreSQL.
        
        Args:
            sqlite_path: Path to SQLite database file
            validate_integrity: Whether to validate data integrity after migration
            
        Returns:
            Migration statistics
        """
        self.logger.info(f"Starting migration from {sqlite_path}")
        
        # Validate SQLite schema
        if not self.validate_sqlite_schema(sqlite_path):
            raise ValidationError("SQLite schema validation failed")
        
        # Setup PostgreSQL schema
        self.setup_postgresql_schema()
        
        # Migrate data in order (respecting foreign keys)
        try:
            entries_count = self.migrate_entries(sqlite_path)
            self.logger.info(f"Migrated {entries_count} entries")
            
            senses_count = self.migrate_senses(sqlite_path)
            self.logger.info(f"Migrated {senses_count} senses")
            
            examples_count = self.migrate_examples(sqlite_path)
            self.logger.info(f"Migrated {examples_count} examples")
            
            # Validate integrity if requested
            if validate_integrity:
                self.validate_migration_integrity(sqlite_path)
            
            self.logger.info("Migration completed successfully")
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            self.stats.errors.append(f"Migration failed: {e}")
            raise DatabaseError(f"Migration failed: {e}")
    
    def validate_migration_integrity(self, sqlite_path: str) -> bool:
        """
        Validate that migration preserved data integrity.
        
        Args:
            sqlite_path: Path to original SQLite database
            
        Returns:
            True if integrity is preserved, False otherwise
        """
        self.logger.info("Validating migration integrity...")
        
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Check counts match
        sqlite_cursor.execute("SELECT COUNT(*) FROM entries")
        sqlite_entries_count = sqlite_cursor.fetchone()[0]
        
        sqlite_cursor.execute("SELECT COUNT(*) FROM senses")
        sqlite_senses_count = sqlite_cursor.fetchone()[0]
        
        sqlite_cursor.execute("SELECT COUNT(*) FROM examples")
        sqlite_examples_count = sqlite_cursor.fetchone()[0]
        
        sqlite_conn.close()
        
        # Check PostgreSQL counts
        pg_entries = self.postgres_connector.fetch_all("SELECT COUNT(*) as count FROM entries")
        pg_senses = self.postgres_connector.fetch_all("SELECT COUNT(*) as count FROM senses")
        pg_examples = self.postgres_connector.fetch_all("SELECT COUNT(*) as count FROM examples")
        
        pg_entries_count = pg_entries[0]['count']
        pg_senses_count = pg_senses[0]['count']
        pg_examples_count = pg_examples[0]['count']
        
        # Validate counts
        integrity_valid = True
        
        if sqlite_entries_count != pg_entries_count:
            self.logger.error(f"Entries count mismatch: SQLite={sqlite_entries_count}, PostgreSQL={pg_entries_count}")
            integrity_valid = False
        
        if sqlite_senses_count != pg_senses_count:
            self.logger.error(f"Senses count mismatch: SQLite={sqlite_senses_count}, PostgreSQL={pg_senses_count}")
            integrity_valid = False
        
        if sqlite_examples_count != pg_examples_count:
            self.logger.error(f"Examples count mismatch: SQLite={sqlite_examples_count}, PostgreSQL={pg_examples_count}")
            integrity_valid = False
        
        if integrity_valid:
            self.logger.info("Migration integrity validation passed")
        else:
            self.stats.errors.append("Migration integrity validation failed")
        
        return integrity_valid


def main():
    """CLI interface for migration utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate dictionary data from SQLite to PostgreSQL')
    parser.add_argument('sqlite_path', help='Path to SQLite database file')
    parser.add_argument('--validate', action='store_true', help='Validate migration integrity')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        migrator = SQLiteToPostgreSQLMigrator()
        stats = migrator.migrate_database(args.sqlite_path, args.validate)
        
        print(f"\nMigration completed:")
        print(f"  Entries migrated: {stats.entries_migrated}")
        print(f"  Senses migrated: {stats.senses_migrated}")
        print(f"  Examples migrated: {stats.examples_migrated}")
        
        if stats.errors:
            print(f"  Errors: {len(stats.errors)}")
            for error in stats.errors:
                print(f"    - {error}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        exit(1)


if __name__ == '__main__':
    main()
