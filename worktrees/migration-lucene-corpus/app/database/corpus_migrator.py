"""Deprecated shim: CorpusMigrator removed.

This module used to contain PostgreSQL-based corpus migration utilities.
It has been replaced by Lucene-based corpus services. The dataclass
`MigrationStats` is retained for compatibility, but instantiating
`CorpusMigrator` will raise an `ImportError` explaining the removal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MigrationStats:
    """Compatibility dataclass for migration statistics (deprecated)."""
    records_processed: int = 0
    records_exported: int = 0
    records_imported: int = 0
    errors_count: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class CorpusMigrator:
    """Deprecated: CorpusMigrator removed. Instantiation raises ImportError."""

    def __init__(self, *args, **kwargs):
        raise ImportError(
            "CorpusMigrator has been removed. Use the Lucene corpus service and ingestion tools."
        )


# Legacy implementation removed. See docs for migration details.
# This file is intentionally kept as a deprecated shim; the formerly
# large PostgreSQL-backed implementation has been removed to avoid
# accidental usage. If tests or other code still reference parts of
# the old implementation, please update them to use the Lucene corpus
# services instead.

# NOTE: If you absolutely need the old functionality, consult the
# project's archive history or the migration plan in docs/plans/2026-01-14-corpus-postgresql-to-lucene-migration.md


    
# Legacy import functions removed. See docs/plans/2026-01-14-corpus-postgresql-to-lucene-migration.md for history and rationale.
# The rest of the original PostgreSQL-backed implementation was intentionally removed to avoid accidental usage.

# End of deprecated shim


(self, sqlite_path: Path, cleanup_temp: bool = True) -> MigrationStats:
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
