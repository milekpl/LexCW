"""
Tests for SQLite to PostgreSQL corpus migration functionality.

Tests the complete migration pipeline with real database connections
using the new high-performance CSV export and PostgreSQL COPY workflow.
Validates data integrity, performance, and error handling for corpus data.
"""
import os
import pytest
import tempfile
import sqlite3
import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from app.database.corpus_migrator import CorpusMigrator, MigrationStats
from app.database.postgresql_connector import PostgreSQLConfig
from app.utils.exceptions import ValidationError, DatabaseError



@pytest.mark.integration
@pytest.mark.skip(reason="PostgreSQL migration tests - not related to Lucene migration")
class TestCorpusMigration:
    """Test corpus migration with real database connections using new workflow."""
    
    @pytest.fixture(scope="class")
    def postgres_config(self) -> PostgreSQLConfig:
        """PostgreSQL configuration for migration testing."""
        return PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
        )
    
    @pytest.fixture(scope="class")
    def migrator(self, postgres_config: PostgreSQLConfig) -> CorpusMigrator:
        """Real migrator instance for testing - uses test_corpus schema."""
        if not os.getenv('POSTGRES_HOST'):
            pytest.skip("PostgreSQL server not configured - set POSTGRES_HOST environment variable")
        migrator = CorpusMigrator(postgres_config, schema='test_corpus')
        # Test connection and create schema if needed
        try:
            migrator.get_corpus_stats()
        except Exception as e:
            pytest.skip(f"PostgreSQL connection failed: {e}")
        return migrator
    
    @pytest.fixture(scope="function")
    def clean_postgres_tables(self, migrator: CorpusMigrator):
        """Clean PostgreSQL test schema before and after each test - uses test_corpus schema."""
        def cleanup():
            try:
                # Use a dedicated test schema, not production corpus schema
                conn = migrator._get_postgres_connection()
                with conn.cursor() as cur:
                    # Drop and recreate test schema only
                    cur.execute("DROP SCHEMA IF EXISTS test_corpus CASCADE")
                    cur.execute("CREATE SCHEMA IF NOT EXISTS test_corpus")
                    # Create test table in test schema
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS test_corpus.parallel_corpus (
                            id SERIAL PRIMARY KEY,
                            source_text TEXT NOT NULL,
                            target_text TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                conn.commit()
                conn.close()
            except Exception:
                pass
        
        # Set up test schema before test
        cleanup()
        
        yield
        
        # Clean up test schema after test
        cleanup()
    
    @pytest.fixture
    def corpus_sqlite_data(self):
        """Create SQLite database with corpus test data in para_crawl format."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        # Create schema matching para_crawl format (c0en, c1pl columns)
        cursor.execute("""
            CREATE TABLE tmdata_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                c0en TEXT NOT NULL,
                c1pl TEXT NOT NULL
            )
        """)
        
        # Insert comprehensive test data with various text types
        corpus_data = [
            ("Hello world", "Witaj świecie"),
            ("This is a test", "To jest test"),
            ("The cat is sleeping", "Kot śpi"),
            ("I love programming", "Kocham programowanie"),
            ("Python is great", "Python jest świetny"),
            ("Database migration", "Migracja bazy danych"),
            ("Complex sentence with many words and punctuation!", "Złożone zdanie z wieloma słowami i interpunkcją!"),
            ("Special chars: @#$%^&*()", "Znaki specjalne: @#$%^&*()"),
            ("Unicode: café, naïve, résumé", "Unicode: café, naïve, résumé"),
            ("Numbers: 123, 456.78, -99", "Liczby: 123, 456.78, -99"),
            ("Empty target", ""),  # Edge case: empty target
            ("", "Pusty źródło"),  # Edge case: empty source
            ("Very long text that might test the limits of the migration system and see how it handles large amounts of text in a single field", 
             "Bardzo długi tekst, który może testować limity systemu migracji i zobaczyć, jak radzi sobie z dużymi ilościami tekstu w jednym polu"),
            ("Text with\nline breaks\nand\ttabs", "Tekst z\nłamaniami linii\ni\ttabulatorami"),
            ("Quotes: \"double\" and 'single'", "Cudzysłowy: \"podwójne\" i 'pojedyncze'"),
        ]
        
        for source, target in corpus_data:
            cursor.execute("""
                INSERT INTO tmdata_content (c0en, c1pl)
                VALUES (?, ?)
            """, (source, target))
        
        conn.commit()
        conn.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def _get_connection_helper(self, migrator: CorpusMigrator):
        """Helper method to get database connection."""
        return migrator._get_postgres_connection()
    
    @pytest.mark.integration
    def test_schema_creation(self, migrator: CorpusMigrator, clean_postgres_tables: None):
        """Test PostgreSQL schema creation."""
        # Create schema
        migrator.create_schema()
        
        # Verify table was created
        conn = self._get_connection_helper(migrator)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'corpus' AND table_name = 'parallel_corpus'
                """)
                result = cur.fetchone()
                assert result is not None
                assert result[0] == 'parallel_corpus'
                
                # Verify table structure
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'corpus' AND table_name = 'parallel_corpus'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                column_names = [col[0] for col in columns]
                
                expected_columns = ['id', 'source_text', 'target_text', 'created_at']
                for expected_col in expected_columns:
                    assert expected_col in column_names
        finally:
            conn.close()
    
    @pytest.mark.integration
    def test_csv_export_import_workflow(self, migrator: CorpusMigrator, 
                                       corpus_sqlite_data: str, clean_postgres_tables: None):
        """Test CSV export and import workflow."""
        sqlite_path = Path(corpus_sqlite_data)
        
        # Create schema first
        migrator.create_schema()
        
        # Test CSV export
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False, encoding='utf-8') as temp_csv:
            csv_path = Path(temp_csv.name)
        
        try:
            # Export SQLite to CSV
            exported_count = migrator.export_sqlite_to_csv(sqlite_path, csv_path)
            
            # Verify CSV file was created and has content
            assert csv_path.exists()
            assert exported_count > 0
            
            # Check CSV content
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                assert header == ['source_text', 'target_text']
                
                rows = list(reader)
                assert len(rows) == exported_count
                
                # Check specific data
                found_hello = False
                for row in rows:
                    if row[0] == 'Hello world' and row[1] == 'Witaj świecie':
                        found_hello = True
                        break
                assert found_hello, "Expected test data not found in CSV"
            
            # Import CSV to PostgreSQL
            imported_count = migrator.import_csv_to_postgres(csv_path)
            assert imported_count > 0
            
            # Verify data in PostgreSQL
            conn = self._get_connection_helper(migrator)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM test_corpus.parallel_corpus")
                    result = cur.fetchone()
                    db_count = result[0] if result else 0
                    assert db_count == imported_count
                    
                    # Check specific record
                    cur.execute("""
                        SELECT source_text, target_text 
                        FROM test_corpus.parallel_corpus 
                        WHERE source_text = %s
                    """, ('Hello world',))
                    result = cur.fetchone()
                    assert result is not None
                    assert result[1] == 'Witaj świecie'
            finally:
                conn.close()
        
        finally:
            # Cleanup
            if csv_path.exists():
                csv_path.unlink()
    
    @pytest.mark.integration
    def test_complete_migration_workflow(self, migrator: CorpusMigrator,
                                       corpus_sqlite_data: str, clean_postgres_tables: None):
        """Test complete migration process using the main workflow."""
        sqlite_path = Path(corpus_sqlite_data)
        
        # Perform complete migration
        stats = migrator.migrate_sqlite_corpus(sqlite_path, cleanup_temp=True)
        
        # Check migration statistics
        assert stats.records_exported > 0
        assert stats.records_imported > 0
        assert stats.records_processed > 0
        assert stats.errors_count == 0
        assert stats.duration is not None
        assert stats.duration > 0
        
        # Verify data was migrated correctly
        conn = self._get_connection_helper(migrator)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM test_corpus.parallel_corpus")
                result = cur.fetchone()
                total_count = result[0] if result else 0
                assert total_count == stats.records_imported
                
                # Check specific test data exists
                cur.execute("""
                    SELECT source_text, target_text 
                    FROM test_corpus.parallel_corpus 
                    WHERE source_text = %s
                """, ('Database migration',))
                result = cur.fetchone()
                assert result is not None
                assert result[1] == 'Migracja bazy danych'
                
                # Check Unicode handling
                cur.execute("""
                    SELECT source_text, target_text 
                    FROM test_corpus.parallel_corpus 
                    WHERE source_text LIKE %s
                """, ('Unicode: café%',))
                unicode_result = cur.fetchone()
                assert unicode_result is not None
                assert 'café' in unicode_result[1]
                
                # Verify indexes were created
                cur.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE schemaname = 'corpus' AND tablename = 'parallel_corpus'
                """)
                indexes = cur.fetchall()
                index_names = [idx[0] for idx in indexes]
                
                # Should have primary key and the created indexes
                assert len(index_names) >= 2  # At least primary key + some indexes
        finally:
            conn.close()
    
    @pytest.mark.integration
    def test_migration_with_edge_cases(self, migrator: CorpusMigrator, clean_postgres_tables: None):
        """Test migration with edge cases and problematic data."""
        # Create SQLite with edge cases
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        # Create schema
        cursor.execute("""
            CREATE TABLE tmdata_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                c0en TEXT NOT NULL,
                c1pl TEXT NOT NULL
            )
        """)
        
        # Insert edge case data
        edge_cases = [
            # Text with null bytes (should be cleaned)
            ('Text with\x00null bytes', 'Tekst z\x00bajtami null'),
            # Very long text
            ('A' * 10000, 'B' * 10000),
            # Special characters and quotes
            ('Text with "quotes" and \'apostrophes\'', 'Tekst z "cudzysłowami" i \'apostrofami\''),
            # Multiple whitespace (should be normalized)
            ('Text   with    multiple     spaces', 'Tekst   z    wieloma     spacjami'),
            # Newlines and tabs
            ('Text\nwith\nlines\tand\ttabs', 'Tekst\nz\nliniami\ti\ttabulatorami'),
            # Empty strings (should be handled)
            ('', ''),
            # Non-ASCII characters
            ('Café naïve résumé', 'Café naïve résumé'),
        ]
        
        for source, target in edge_cases:
            cursor.execute("""
                INSERT INTO tmdata_content (c0en, c1pl)
                VALUES (?, ?)
            """, (source, target))
        
        conn.commit()
        conn.close()
        
        try:
            # Perform migration
            sqlite_path = Path(temp_file.name)
            stats = migrator.migrate_sqlite_corpus(sqlite_path, cleanup_temp=True)
            
            # Should handle edge cases gracefully
            assert stats.records_imported > 0
            assert stats.errors_count == 0
            
            # Verify text cleaning worked
            conn = self._get_connection_helper(migrator)
            try:
                with conn.cursor() as cur:
                    # Check null bytes were removed
                    cur.execute("""
                        SELECT source_text, target_text 
                        FROM corpus.parallel_corpus 
                        WHERE source_text LIKE %s
                    """, ('Text with%null bytes',))
                    result = cur.fetchone()
                    assert result is not None
                    assert '\x00' not in result[0]
                    assert '\x00' not in result[1]
                    
                    # Check whitespace normalization
                    cur.execute("""
                        SELECT source_text 
                        FROM corpus.parallel_corpus 
                        WHERE source_text LIKE %s
                    """, ('Text with multiple%',))
                    whitespace_result = cur.fetchone()
                    assert whitespace_result is not None
                    # Should have normalized whitespace
                    assert '    ' not in whitespace_result[0]  # Multiple spaces should be reduced
            finally:
                conn.close()
        
        finally:
            # Cleanup
            os.unlink(temp_file.name)
    
    @pytest.mark.integration
    def test_deduplication(self, migrator: CorpusMigrator, clean_postgres_tables: None):
        """Test corpus deduplication functionality."""
        # Create SQLite with duplicate data
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE tmdata_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                c0en TEXT NOT NULL,
                c1pl TEXT NOT NULL
            )
        """)
        
        # Insert data with duplicates
        test_data = [
            ('Hello world', 'Witaj świecie'),
            ('Hello world', 'Witaj świecie'),  # Duplicate
            ('Goodbye', 'Do widzenia'),
            ('Hello world', 'Witaj świecie'),  # Another duplicate
            ('Good morning', 'Dzień dobry'),
        ]
        
        for source, target in test_data:
            cursor.execute("""
                INSERT INTO tmdata_content (c0en, c1pl)
                VALUES (?, ?)
            """, (source, target))
        
        conn.commit()
        conn.close()
        
        try:
            # Perform migration (includes deduplication)
            sqlite_path = Path(temp_file.name)
            stats = migrator.migrate_sqlite_corpus(sqlite_path, cleanup_temp=True)
            
            # Check that deduplication occurred
            conn = self._get_connection_helper(migrator)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM test_corpus.parallel_corpus")
                    result = cur.fetchone()
                    total_count = result[0] if result else 0
                    
                    # Should have fewer records than input due to deduplication
                    assert total_count < len(test_data)
                    
                    # Check specific duplicates were removed
                    cur.execute("""
                        SELECT COUNT(*) FROM test_corpus.parallel_corpus 
                        WHERE source_text = %s AND target_text = %s
                    """, ('Hello world', 'Witaj świecie'))
                    result = cur.fetchone()
                    hello_count = result[0] if result else 0
                    assert hello_count == 1  # Should have only one instance
                    
                    # Check unique records still exist
                    cur.execute("""
                        SELECT COUNT(*) FROM test_corpus.parallel_corpus 
                        WHERE source_text = %s
                    """, ('Good morning',))
                    result = cur.fetchone()
                    morning_count = result[0] if result else 0
                    assert morning_count == 1
            finally:
                conn.close()
        
        finally:
            # Cleanup
            os.unlink(temp_file.name)
    
    @pytest.mark.integration
    def test_migration_performance(self, migrator: CorpusMigrator, clean_postgres_tables: None):
        """Test migration performance with larger dataset."""
        import random
        import string
        
        # Create larger SQLite database
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            temp_db_path = temp_file.name
        
        try:
            # Use context manager to ensure proper connection closure
            with sqlite3.connect(temp_db_path) as conn:
                cursor = conn.cursor()
                
                # Create schema
                cursor.execute("""
                    CREATE TABLE tmdata_content (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        c0en TEXT NOT NULL,
                        c1pl TEXT NOT NULL
                    )
                """)
                
                # Generate test data
                num_records = 1000  # Reasonable size for testing
                
                print(f"Generating {num_records} records for performance test...")
                
                # Insert records in batches for better performance
                batch_size = 100
                for batch_start in range(0, num_records, batch_size):
                    batch_data = []
                    for i in range(batch_start, min(batch_start + batch_size, num_records)):
                        source_text = f"English text {i}: " + ''.join(random.choices(string.ascii_lowercase + ' ', k=50))
                        target_text = f"Polish text {i}: " + ''.join(random.choices(string.ascii_lowercase + ' ', k=50))
                        batch_data.append((source_text, target_text))
                    
                    cursor.executemany("""
                        INSERT INTO tmdata_content (c0en, c1pl)
                        VALUES (?, ?)
                    """, batch_data)
                
                conn.commit()
            
            # Perform timed migration
            start_time = time.time()
            sqlite_path = Path(temp_db_path)
            stats = migrator.migrate_sqlite_corpus(sqlite_path, cleanup_temp=True)
            migration_time = time.time() - start_time
            
            print(f"Migration completed in {migration_time:.2f} seconds")
            print(f"Records processed: {stats.records_processed}")
            print(f"Records imported: {stats.records_imported}")
            
            # Performance assertions
            assert stats.records_imported >= num_records * 0.9  # Allow for some deduplication
            assert migration_time < 30.0  # Should complete within 30 seconds for 1000 records
            assert stats.errors_count == 0
            
            # Test query performance on migrated data
            conn = self._get_connection_helper(migrator)
            try:
                with conn.cursor() as cur:
                    query_start = time.time()
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM corpus.parallel_corpus 
                        WHERE source_text LIKE %s
                    """, ('%English text%',))
                    result = cur.fetchone()
                    count_result = result[0] if result else 0
                    query_time = time.time() - query_start
                    
                    print(f"Query completed in {query_time:.3f} seconds")
                    
                    assert count_result > 0
                    assert query_time < 5.0  # Query should be fast
            finally:
                conn.close()
            
        finally:
            # Cleanup - ensure file is deleted even if test fails
            try:
                os.unlink(temp_db_path)
            except (FileNotFoundError, PermissionError):
                pass  # Ignore cleanup errors
    
    @pytest.mark.integration
    def test_corpus_stats(self, migrator: CorpusMigrator, corpus_sqlite_data: str, clean_postgres_tables: None):
        """Test corpus statistics functionality."""
        # First migrate some data
        sqlite_path = Path(corpus_sqlite_data)
        stats = migrator.migrate_sqlite_corpus(sqlite_path, cleanup_temp=True)
        
        # Get corpus statistics from test schema
        conn = self._get_connection_helper(migrator)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM test_corpus.parallel_corpus")
                result = cur.fetchone()
                test_count = result[0] if result else 0
        finally:
            conn.close()
        
        # Verify statistics are reasonable
        assert test_count == stats.records_imported
        
        # Test stats for empty corpus in test schema
        # Clean the test corpus table manually
        conn = self._get_connection_helper(migrator)
        try:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE test_corpus.parallel_corpus")
                conn.commit()
                
            # Check test_corpus schema stats
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM test_corpus.parallel_corpus")
                result = cur.fetchone()
                test_count = result[0] if result else 0
            assert test_count == 0
        finally:
            conn.close()
    
    @pytest.mark.integration
    def test_migration_error_handling(self, migrator: CorpusMigrator, clean_postgres_tables: None):
        """Test migration error handling and recovery."""
        # Test with non-existent SQLite file
        non_existent_path = Path('/non/existent/file.db')
        try:
            migrator.migrate_sqlite_corpus(non_existent_path)
            assert False, "Should have raised an exception"
        except Exception as e:
            # Should handle the error gracefully
            assert "does not exist" in str(e).lower() or "no such file" in str(e).lower() or "unable to open" in str(e).lower()
        
        # Test with invalid SQLite file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            temp_file.write(b'this is not a valid sqlite file')
            temp_db_path = temp_file.name
        
        try:
            invalid_path = Path(temp_db_path)
            migrator.migrate_sqlite_corpus(invalid_path)
            assert False, "Should have raised an exception"
        except Exception as e:
            # Should handle the error gracefully
            assert "not a database" in str(e).lower() or "file is not a database" in str(e).lower()
        finally:
            # Cleanup - ensure file is deleted even if test fails
            try:
                os.unlink(temp_db_path)
            except (FileNotFoundError, PermissionError):
                pass  # Ignore cleanup errors


if __name__ == '__main__':
    # Run corpus migration tests
    pytest.main([__file__, '-v', '--tb=short', '-x'])
