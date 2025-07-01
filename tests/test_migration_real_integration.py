"""
Tests for SQLite to PostgreSQL migration functionality.

Tests the complete migration pipeline with real database connections
and validates data integrity, performance, and error handling.
"""
import os
import pytest
import tempfile
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any

from app.database.sqlite_postgres_migrator import SQLiteToPostgreSQLMigrator, MigrationStats
from app.database.postgresql_connector import PostgreSQLConnector, PostgreSQLConfig
from app.utils.exceptions import ValidationError, DatabaseError


class TestSQLiteToPostgreSQLMigration:
    """Test SQLite to PostgreSQL migration with real database connections."""
    
    @pytest.fixture(scope="class")
    def postgres_config(self) -> PostgreSQLConfig:
        """PostgreSQL configuration for migration testing."""
        return PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_test'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
        )
    
    @pytest.fixture(scope="class")
    def migrator(self, postgres_config: PostgreSQLConfig) -> SQLiteToPostgreSQLMigrator:
        """Real migrator instance for testing."""
        try:
            migrator = SQLiteToPostgreSQLMigrator(postgres_config)
            # Test connection
            migrator.postgres_connector.fetch_all("SELECT 1")
            return migrator
        except (Exception,) as e:
            pytest.skip(f"PostgreSQL not available for migration testing: {e}")
    
    @pytest.fixture(scope="function")
    def clean_postgres_tables(self, migrator: SQLiteToPostgreSQLMigrator):
        """Clean PostgreSQL tables before and after each test."""
        tables = ['examples', 'senses', 'entries', 'frequency_data', 'word_sketches']
        
        for table in tables:
            try:
                migrator.postgres_connector.execute_query(f"DROP TABLE IF EXISTS {table} CASCADE")
            except Exception:
                pass
        
        yield
        
        # Clean up after test
        for table in tables:
            try:
                migrator.postgres_connector.execute_query(f"DROP TABLE IF EXISTS {table} CASCADE")
            except Exception:
                pass
    
    @pytest.fixture
    def comprehensive_sqlite_data(self):
        """Create comprehensive SQLite database with complex test data."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        # Create schema
        cursor.execute("""
            CREATE TABLE entries (
                id TEXT PRIMARY KEY,
                headword TEXT NOT NULL,
                pronunciation TEXT,
                grammatical_info TEXT,
                date_created TEXT,
                date_modified TEXT,
                custom_fields TEXT,
                frequency_rank INTEGER,
                subtlex_frequency REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE senses (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                definition TEXT,
                grammatical_info TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (entry_id) REFERENCES entries (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE examples (
                id TEXT PRIMARY KEY,
                sense_id TEXT NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (sense_id) REFERENCES senses (id)
            )
        """)
        
        # Insert comprehensive test data
        now = datetime.now().isoformat()
        
        # Entries with various data types
        entries_data = [
            {
                'id': 'entry_001', 'headword': 'test', 'pronunciation': '/tɛst/',
                'grammatical_info': '{"type": "noun", "number": "singular", "gender": "neuter"}',
                'date_created': now, 'date_modified': now,
                'custom_fields': '{"frequency": 1000, "difficulty": "easy", "tags": ["common", "basic"]}',
                'frequency_rank': 100, 'subtlex_frequency': 15.3
            },
            {
                'id': 'entry_002', 'headword': 'example', 'pronunciation': '/ɪɡˈzæm.pəl/',
                'grammatical_info': '{"type": "noun", "number": "singular"}',
                'date_created': now, 'date_modified': now,
                'custom_fields': '{"frequency": 800, "difficulty": "medium"}',
                'frequency_rank': 200, 'subtlex_frequency': 12.7
            },
            {
                'id': 'entry_003', 'headword': 'complex', 'pronunciation': '/ˈkɒm.pleks/',
                'grammatical_info': '{"type": "adjective"}',
                'date_created': now, 'date_modified': now,
                'custom_fields': None,  # Test NULL handling
                'frequency_rank': None, 'subtlex_frequency': None
            },
            {
                'id': 'entry_004', 'headword': 'special_chars', 'pronunciation': None,
                'grammatical_info': 'simple_string',  # Test non-JSON grammatical info
                'date_created': '2023-01-01', 'date_modified': '2023-06-15T10:30:00',
                'custom_fields': 'not_json_either',  # Test non-JSON custom fields
                'frequency_rank': 500, 'subtlex_frequency': 5.2
            }
        ]
        
        for entry_data in entries_data:
            cursor.execute("""
                INSERT INTO entries (id, headword, pronunciation, grammatical_info, 
                                   date_created, date_modified, custom_fields, 
                                   frequency_rank, subtlex_frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_data['id'], entry_data['headword'], entry_data['pronunciation'],
                entry_data['grammatical_info'], entry_data['date_created'], 
                entry_data['date_modified'], entry_data['custom_fields'],
                entry_data['frequency_rank'], entry_data['subtlex_frequency']
            ))
        
        # Senses with various relationships
        senses_data = [
            {
                'id': 'sense_001', 'entry_id': 'entry_001', 
                'definition': 'A procedure intended to establish the quality or performance of something.',
                'grammatical_info': '{"type": "noun"}', 'custom_fields': '{"examples_count": 3}',
                'sort_order': 0
            },
            {
                'id': 'sense_002', 'entry_id': 'entry_001',
                'definition': 'A means of examining knowledge or ability.',
                'grammatical_info': '{"type": "noun"}', 'custom_fields': None,
                'sort_order': 1
            },
            {
                'id': 'sense_003', 'entry_id': 'entry_002',
                'definition': 'A thing characteristic of its kind or illustrating a general rule.',
                'grammatical_info': None, 'custom_fields': '{"difficulty": "high"}',
                'sort_order': 0
            },
            {
                'id': 'sense_004', 'entry_id': 'entry_003',
                'definition': 'Consisting of many different and connected parts.',
                'grammatical_info': 'adjective', 'custom_fields': 'simple_text',
                'sort_order': 0
            }
        ]
        
        for sense_data in senses_data:
            cursor.execute("""
                INSERT INTO senses (id, entry_id, definition, grammatical_info, 
                                  custom_fields, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sense_data['id'], sense_data['entry_id'], sense_data['definition'],
                sense_data['grammatical_info'], sense_data['custom_fields'],
                sense_data['sort_order']
            ))
        
        # Examples with various languages and formats
        examples_data = [
            {
                'id': 'example_001', 'sense_id': 'sense_001',
                'text': 'The test results were positive.',
                'translation': 'Wyniki testu były pozytywne.',
                'custom_fields': '{"language": "English", "register": "formal"}',
                'sort_order': 0
            },
            {
                'id': 'example_002', 'sense_id': 'sense_001',
                'text': 'We need to test the new software.',
                'translation': 'Musimy przetestować nowe oprogramowanie.',
                'custom_fields': None, 'sort_order': 1
            },
            {
                'id': 'example_003', 'sense_id': 'sense_002',
                'text': 'The final test is tomorrow.',
                'translation': 'Egzamin końcowy jest jutro.',
                'custom_fields': '{"language": "English", "register": "informal"}',
                'sort_order': 0
            },
            {
                'id': 'example_004', 'sense_id': 'sense_003',
                'text': 'For example, water boils at 100°C.',
                'translation': 'Na przykład, woda wrze w temperaturze 100°C.',
                'custom_fields': 'scientific_context', 'sort_order': 0
            },
            {
                'id': 'example_005', 'sense_id': 'sense_004',
                'text': 'This is a complex problem.',
                'translation': 'To jest skomplikowany problem.',
                'custom_fields': None, 'sort_order': 0
            }
        ]
        
        for example_data in examples_data:
            cursor.execute("""
                INSERT INTO examples (id, sense_id, text, translation, 
                                    custom_fields, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                example_data['id'], example_data['sense_id'], example_data['text'],
                example_data['translation'], example_data['custom_fields'],
                example_data['sort_order']
            ))
        
        conn.commit()
        conn.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_sqlite_schema_validation(self, migrator: SQLiteToPostgreSQLMigrator, 
                                    comprehensive_sqlite_data: str):
        """Test SQLite schema validation."""
        # Valid schema should pass
        assert migrator.validate_sqlite_schema(comprehensive_sqlite_data)
        
        # Test with invalid schema
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            temp_db_path = temp_file.name
        
        try:
            # Use context manager to ensure proper connection closure
            with sqlite3.connect(temp_db_path) as conn:
                cursor = conn.cursor()
                
                # Create incomplete schema (missing examples table)
                cursor.execute("""
                    CREATE TABLE entries (
                        id TEXT PRIMARY KEY,
                        headword TEXT NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE senses (
                        id TEXT PRIMARY KEY,
                        entry_id TEXT NOT NULL
                    )
                """)
                conn.commit()
            
            # Should fail validation
            assert not migrator.validate_sqlite_schema(temp_db_path)
        finally:
            # Cleanup - ensure file is deleted even if test fails
            try:
                os.unlink(temp_db_path)
            except (FileNotFoundError, PermissionError):
                pass  # Ignore cleanup errors
    
    def test_data_transformation(self, migrator: SQLiteToPostgreSQLMigrator):
        """Test data transformation for PostgreSQL compatibility."""
        # Test JSON field transformation
        sqlite_data = {
            'id': 'test_001',
            'headword': 'test',
            'grammatical_info': '{"type": "noun", "number": "singular"}',
            'custom_fields': '{"tags": ["common"], "frequency": 100}',
            'date_created': '2023-01-01',
            'date_modified': '2023-06-15T10:30:00'
        }
        
        transformed = migrator.transform_data_for_postgresql(sqlite_data)
        
        # Check JSON parsing
        assert isinstance(transformed['grammatical_info'], dict)
        assert transformed['grammatical_info']['type'] == 'noun'
        assert isinstance(transformed['custom_fields'], dict)
        assert transformed['custom_fields']['frequency'] == 100
        
        # Check datetime parsing
        assert isinstance(transformed['date_created'], datetime)
        assert isinstance(transformed['date_modified'], datetime)
        
        # Test invalid JSON handling
        invalid_json_data = {
            'grammatical_info': 'not_json',
            'custom_fields': 'also_not_json',
            'date_created': 'invalid_date'
        }
        
        transformed_invalid = migrator.transform_data_for_postgresql(invalid_json_data)
        
        # Should wrap non-JSON strings
        assert transformed_invalid['grammatical_info']['raw'] == 'not_json'
        assert transformed_invalid['custom_fields']['raw'] == 'also_not_json'
        # Should handle invalid dates gracefully
        assert isinstance(transformed_invalid['date_created'], datetime)
    
    def test_postgresql_schema_creation(self, migrator: SQLiteToPostgreSQLMigrator, 
                                      clean_postgres_tables):
        """Test PostgreSQL schema creation."""
        # Setup schema
        migrator.setup_postgresql_schema()
        
        # Verify tables were created
        tables_result = migrator.postgres_connector.fetch_all("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables_result]
        expected_tables = ['entries', 'senses', 'examples', 'frequency_data', 'word_sketches']
        
        for expected_table in expected_tables:
            assert expected_table in table_names
        
        # Verify foreign key constraints
        constraints_result = migrator.postgres_connector.fetch_all("""
            SELECT constraint_name, table_name, column_name 
            FROM information_schema.key_column_usage 
            WHERE table_schema = 'public' AND constraint_name LIKE '%fkey%'
        """)
        
        assert len(constraints_result) >= 2  # At least senses->entries and examples->senses
        
        # Verify indexes were created
        indexes_result = migrator.postgres_connector.fetch_all("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
        """)
        
        assert len(indexes_result) >= 5  # Multiple indexes should be created
    
    def test_complete_migration(self, migrator: SQLiteToPostgreSQLMigrator,
                              comprehensive_sqlite_data: str, clean_postgres_tables):
        """Test complete migration process."""
        # Perform migration
        stats = migrator.migrate_database(comprehensive_sqlite_data, validate_integrity=True)
        
        # Check migration statistics
        assert stats.entries_migrated == 4
        assert stats.senses_migrated == 4
        assert stats.examples_migrated == 5
        assert len(stats.errors) == 0
        
        # Verify data was migrated correctly
        entries = migrator.postgres_connector.fetch_all("""
            SELECT entry_id, headword, pronunciation, grammatical_info, custom_fields 
            FROM entries ORDER BY entry_id
        """)
        
        assert len(entries) == 4
        
        # Check specific entry data
        test_entry = next(e for e in entries if e['entry_id'] == 'entry_001')
        assert test_entry['headword'] == 'test'
        assert test_entry['pronunciation'] == '/tɛst/'
        
        # Check JSON fields were properly converted
        grammatical_info = test_entry['grammatical_info']  # Already a dict from JSONB
        assert grammatical_info['type'] == 'noun'
        assert grammatical_info['number'] == 'singular'
        
        custom_fields = test_entry['custom_fields']  # Already a dict from JSONB
        assert custom_fields['frequency'] == 1000
        assert 'common' in custom_fields['tags']
        
        # Check relationships are preserved
        complex_query = migrator.postgres_connector.fetch_all("""
            SELECT e.headword, s.definition, ex.text, ex.translation
            FROM entries e
            JOIN senses s ON e.entry_id = s.entry_id
            JOIN examples ex ON s.sense_id = ex.sense_id
            WHERE e.headword = 'test'
            ORDER BY s.sort_order, ex.sort_order
        """)
        
        assert len(complex_query) == 3  # 'test' has 2 senses with 3 total examples
        assert complex_query[0]['text'] == 'The test results were positive.'
        assert complex_query[0]['translation'] == 'Wyniki testu były pozytywne.'
    
    def test_migration_with_edge_cases(self, migrator: SQLiteToPostgreSQLMigrator, 
                                     clean_postgres_tables):
        """Test migration with edge cases and problematic data."""
        # Create SQLite with edge cases
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        # Create schema
        cursor.execute("""
            CREATE TABLE entries (
                id TEXT PRIMARY KEY,
                headword TEXT NOT NULL,
                pronunciation TEXT,
                grammatical_info TEXT,
                date_created TEXT,
                date_modified TEXT,
                custom_fields TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE senses (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                definition TEXT,
                grammatical_info TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (entry_id) REFERENCES entries (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE examples (
                id TEXT PRIMARY KEY,
                sense_id TEXT NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (sense_id) REFERENCES senses (id)
            )
        """)
        
        # Insert edge case data
        edge_cases = [
            # Entry with Unicode characters
            ('edge_001', 'café', '/kaˈfe/', '{"type": "noun", "origin": "français"}', 
             '2023-01-01', '2023-01-01', '{"unicode": "test", "emoji": "☕"}'),
            # Entry with very long text
            ('edge_002', 'supercalifragilisticexpialidocious', None, 
             '{"type": "adjective", "note": "' + 'x' * 1000 + '"}',
             None, None, None),
            # Entry with special characters
            ('edge_003', 'test&<>"\'', '/test/', '{"type": "noun&verb"}',
             'invalid-date', '2023-13-45', '{"key": "value with \\"quotes\\""}'),
        ]
        
        for edge_case in edge_cases:
            cursor.execute("""
                INSERT INTO entries (id, headword, pronunciation, grammatical_info,
                                   date_created, date_modified, custom_fields)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, edge_case)
        
        # Add senses and examples for edge cases
        cursor.execute("""
            INSERT INTO senses (id, entry_id, definition, sort_order)
            VALUES ('edge_sense_001', 'edge_001', 'A coffee shop.', 0)
        """)
        
        cursor.execute("""
            INSERT INTO examples (id, sense_id, text, sort_order)
            VALUES ('edge_example_001', 'edge_sense_001', 'Let\\'s go to the café.', 0)
        """)
        
        conn.commit()
        conn.close()
        
        try:
            # Perform migration
            stats = migrator.migrate_database(temp_file.name, validate_integrity=True)
            
            # Should handle edge cases gracefully
            assert stats.entries_migrated == 3
            assert stats.senses_migrated == 1
            assert stats.examples_migrated == 1
            
            # Verify Unicode handling
            unicode_entry = migrator.postgres_connector.fetch_all("""
                SELECT headword, grammatical_info, custom_fields 
                FROM entries WHERE entry_id = 'edge_001'
            """)
            
            assert len(unicode_entry) == 1
            assert unicode_entry[0]['headword'] == 'café'
            
            # Verify JSON with Unicode
            custom_fields = json.loads(unicode_entry[0]['custom_fields'])
            assert custom_fields['emoji'] == '☕'
            
        finally:
            # Cleanup
            os.unlink(temp_file.name)
    
    def test_migration_performance(self, migrator: SQLiteToPostgreSQLMigrator, 
                                 clean_postgres_tables):
        """Test migration performance with larger dataset."""
        import time
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
                    CREATE TABLE entries (
                        id TEXT PRIMARY KEY,
                        headword TEXT NOT NULL,
                        pronunciation TEXT,
                        grammatical_info TEXT,
                        date_created TEXT,
                        date_modified TEXT,
                        custom_fields TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE senses (
                        id TEXT PRIMARY KEY,
                        entry_id TEXT NOT NULL,
                        definition TEXT,
                        grammatical_info TEXT,
                        custom_fields TEXT,
                        sort_order INTEGER,
                        FOREIGN KEY (entry_id) REFERENCES entries (id)
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE examples (
                        id TEXT PRIMARY KEY,
                        sense_id TEXT NOT NULL,
                        text TEXT NOT NULL,
                        translation TEXT,
                        custom_fields TEXT,
                        sort_order INTEGER,
                        FOREIGN KEY (sense_id) REFERENCES senses (id)
                    )
                """)
                
                # Generate test data
                num_entries = 500
                now = datetime.now().isoformat()
                
                print(f"Generating {num_entries} entries for performance test...")
                
                # Insert entries
                for i in range(num_entries):
                    entry_id = f'perf_entry_{i:04d}'
                    headword = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 12)))
                    pronunciation = f'/{headword}/'
                    grammatical_info = json.dumps({
                        'type': random.choice(['noun', 'verb', 'adjective', 'adverb']),
                        'complexity': random.randint(1, 5)
                    })
                    custom_fields = json.dumps({
                        'frequency': random.randint(1, 10000),
                        'tags': random.sample(['common', 'rare', 'technical', 'colloquial'], k=2)
                    })
                    
                    cursor.execute("""
                        INSERT INTO entries (id, headword, pronunciation, grammatical_info,
                                           date_created, date_modified, custom_fields)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (entry_id, headword, pronunciation, grammatical_info, now, now, custom_fields))
                    
                    # Add 1-3 senses per entry
                    num_senses = random.randint(1, 3)
                    for j in range(num_senses):
                        sense_id = f'perf_sense_{i:04d}_{j}'
                        definition = f'Definition {j+1} for {headword}'
                        
                        cursor.execute("""
                            INSERT INTO senses (id, entry_id, definition, sort_order)
                            VALUES (?, ?, ?, ?)
                        """, (sense_id, entry_id, definition, j))
                        
                        # Add 0-2 examples per sense
                        num_examples = random.randint(0, 2)
                        for k in range(num_examples):
                            example_id = f'perf_example_{i:04d}_{j}_{k}'
                            text = f'Example {k+1} for sense {j+1} of {headword}'
                            translation = f'Przykład {k+1} dla znaczenia {j+1} słowa {headword}'
                            
                            cursor.execute("""
                                INSERT INTO examples (id, sense_id, text, translation, sort_order)
                                VALUES (?, ?, ?, ?, ?)
                            """, (example_id, sense_id, text, translation, k))
                
                conn.commit()
            
            # Perform timed migration
            start_time = time.time()
            stats = migrator.migrate_database(temp_db_path, validate_integrity=True)
            migration_time = time.time() - start_time
            
            print(f"Migration completed in {migration_time:.2f} seconds")
            print(f"Entries migrated: {stats.entries_migrated}")
            print(f"Senses migrated: {stats.senses_migrated}")
            print(f"Examples migrated: {stats.examples_migrated}")
            
            # Performance assertions
            assert stats.entries_migrated == num_entries
            assert migration_time < 60.0  # Should complete within 1 minute for 500 entries
            assert len(stats.errors) == 0
            
            # Test query performance on migrated data
            query_start = time.time()
            complex_results = migrator.postgres_connector.fetch_all("""
                SELECT e.headword, COUNT(s.sense_id) as sense_count, COUNT(ex.example_id) as example_count
                FROM entries e
                LEFT JOIN senses s ON e.entry_id = s.entry_id
                LEFT JOIN examples ex ON s.sense_id = ex.sense_id
                GROUP BY e.entry_id, e.headword
                ORDER BY sense_count DESC, example_count DESC
                LIMIT 50
            """)
            query_time = time.time() - query_start
            
            print(f"Complex query completed in {query_time:.3f} seconds")
            
            assert len(complex_results) == 50
            assert query_time < 5.0  # Complex query should be fast
            
        finally:
            # Cleanup - ensure file is deleted even if test fails
            try:
                os.unlink(temp_db_path)
            except (FileNotFoundError, PermissionError):
                pass  # Ignore cleanup errors
    
    def test_migration_error_handling(self, migrator: SQLiteToPostgreSQLMigrator, 
                                    clean_postgres_tables):
        """Test migration error handling and recovery."""
        # Test with non-existent SQLite file
        with pytest.raises(ValidationError):
            migrator.migrate_database('/non/existent/file.db')
        
        # Test with invalid SQLite file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            temp_file.write(b'this is not a valid sqlite file')
            temp_db_path = temp_file.name
        
        try:
            with pytest.raises(ValidationError):
                migrator.migrate_database(temp_db_path)
        finally:
            # Cleanup - ensure file is deleted even if test fails
            try:
                os.unlink(temp_db_path)
            except (FileNotFoundError, PermissionError):
                pass  # Ignore cleanup errors


if __name__ == '__main__':
    # Run migration tests
    pytest.main([__file__, '-v', '--tb=short', '-x'])
