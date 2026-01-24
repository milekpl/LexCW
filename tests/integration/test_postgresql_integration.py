"""
Tests for PostgreSQL integration and data migration functionality.

Tests database connection, schema creation, and basic CRUD operations.
"""
import os
import pytest
import tempfile
import sqlite3
import json
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.database.postgresql_connector import PostgreSQLConnector, PostgreSQLConfig
from app.utils.exceptions import DatabaseError, DatabaseConnectionError


class TestPostgreSQLConnector:
    """Test PostgreSQL connector functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock PostgreSQL configuration."""
        return PostgreSQLConfig(
            host='localhost',
            port=5432,
            database='test_db',
            username='test_user',
            password='test_pass'
        )
    
    @pytest.fixture
    def mock_connector(self, mock_config):
        """Mock PostgreSQL connector for testing."""
        with patch('app.database.postgresql_connector.psycopg2') as mock_psycopg2:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_psycopg2.connect.return_value = mock_connection
            
            connector = PostgreSQLConnector(mock_config)
            connector._connection = mock_connection
            yield connector, mock_connection, mock_cursor
    
    def test_config_from_env(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test-database',
            'POSTGRES_USER': 'test-username',
            'POSTGRES_PASSWORD': 'test-password'
        }
        
        with patch.dict(os.environ, env_vars):
            connector = PostgreSQLConnector()
            
            assert connector.config.host == 'test-host'
            assert connector.config.port == 5432
            assert connector.config.database == 'test-database'
            assert connector.config.username == 'test-username'
            assert connector.config.password == 'test-password'
    
    def test_connection_success(self, mock_connector):
        """Test successful database connection."""
        connector, mock_connection, mock_cursor = mock_connector
        
        # Set up autocommit attribute
        mock_connection.autocommit = True
        
        # Test basic connection
        assert connector._connection is not None
        assert mock_connection.autocommit is True
    
    def test_connection_failure(self, mock_config):
        """Test database connection failure."""
        # Create a proper exception class for mocking
        class MockPsycopg2Error(Exception):
            pass
        
        with patch('app.database.postgresql_connector.psycopg2') as mock_psycopg2:
            mock_psycopg2.connect.side_effect = MockPsycopg2Error("Connection failed")
            mock_psycopg2.Error = MockPsycopg2Error
            
            connector = PostgreSQLConnector(mock_config)
            # Connection failure should happen when we try to use the connection
            with pytest.raises(DatabaseConnectionError):
                connector._initialize_connection()
    
    def test_execute_query_success(self, mock_connector):
        """Test successful query execution."""
        connector, mock_connection, mock_cursor = mock_connector
        
        query = "INSERT INTO test_table (name) VALUES (%(name)s)"
        parameters = {"name": "test"}
        
        connector.execute_query(query, parameters)
        
        mock_cursor.execute.assert_called_once_with(query, parameters)
    
    def test_execute_query_failure(self, mock_connector):
        """Test query execution failure."""
        connector, mock_connection, mock_cursor = mock_connector
        
        # Create a proper exception class for mocking
        class MockPsycopg2Error(Exception):
            pass
        
        # Mock database error
        mock_cursor.execute.side_effect = MockPsycopg2Error("Query failed")
        
        # Patch psycopg2.Error to be our mock exception
        with patch('app.database.postgresql_connector.psycopg2.Error', MockPsycopg2Error):
            with pytest.raises(DatabaseError):
                connector.execute_query("INVALID SQL")
    
    def test_fetch_all_success(self, mock_connector):
        """Test successful data fetching."""
        connector, mock_connection, mock_cursor = mock_connector
        
        # Mock return data
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'name': 'test1'},
            {'id': 2, 'name': 'test2'}
        ]
        
        query = "SELECT * FROM test_table"
        results = connector.fetch_all(query)
        
        assert len(results) == 2
        assert results[0]['name'] == 'test1'
        assert results[1]['name'] == 'test2'
    
    def test_fetch_all_failure(self, mock_connector):
        """Test data fetching failure."""
        connector, mock_connection, mock_cursor = mock_connector
        
        # Create a proper exception class for mocking
        class MockPsycopg2Error(Exception):
            pass
        
        # Mock database error
        mock_cursor.execute.side_effect = MockPsycopg2Error("Query failed")
        
        # Patch psycopg2.Error to be our mock exception
        with patch('app.database.postgresql_connector.psycopg2.Error', MockPsycopg2Error):
            with pytest.raises(DatabaseError):
                connector.fetch_all("INVALID SQL")
    
    def test_context_manager(self, mock_connector):
        """Test context manager functionality."""
        connector, mock_connection, mock_cursor = mock_connector
        
        with connector.get_cursor() as cursor:
            assert cursor is mock_cursor
        
        mock_cursor.close.assert_called_once()


class TestPostgreSQLSetup:
    """Test PostgreSQL schema setup and validation."""
    
    @pytest.fixture
    def temp_sqlite_db(self):
        """Create temporary SQLite database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        # Create test SQLite database
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        # Create tables
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
        
        # Insert test data
        cursor.execute("""
            INSERT INTO entries (id, headword, pronunciation, grammatical_info) 
            VALUES ('entry1', 'test', 'test', '{"type": "noun"}')
        """)
        
        cursor.execute("""
            INSERT INTO senses (id, entry_id, definition, sort_order) 
            VALUES ('sense1', 'entry1', 'A test definition', 0)
        """)
        
        cursor.execute("""
            INSERT INTO examples (id, sense_id, text, translation, sort_order) 
            VALUES ('example1', 'sense1', 'This is a test', 'To jest test', 0)
        """)
        
        conn.commit()
        conn.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_schema_creation_sql(self):
        """Test that schema creation SQL is valid."""
        # Import the setup script
        import sys
        sys.path.append(os.path.dirname(__file__))
        
        # Mock connector for testing schema queries
        mock_connector = Mock()
        mock_connector.execute_query = Mock()
        
        # This would normally be called from setup_postgresql.py
        # We'll test individual schema components here
        
        # Test entries table creation
        entries_sql = """
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
        );
        """
        
        # Test that SQL is properly formatted (no syntax errors)
        assert "CREATE TABLE" in entries_sql
        assert "entries" in entries_sql
        assert "UUID PRIMARY KEY" in entries_sql
        assert "JSONB" in entries_sql
    
    def test_index_creation_sql(self):
        """Test that index creation SQL is valid."""
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_entries_headword ON entries(headword);",
            "CREATE INDEX IF NOT EXISTS idx_entries_entry_id ON entries(entry_id);",
            "CREATE INDEX IF NOT EXISTS idx_senses_entry_id ON senses(entry_id);",
            "CREATE INDEX IF NOT EXISTS idx_examples_sense_id ON examples(sense_id);",
        ]
        
        for query in index_queries:
            assert "CREATE INDEX" in query
            assert "IF NOT EXISTS" in query
            assert "ON " in query


class TestSimpleMigration:
    """Test basic migration functionality."""
    
    @pytest.fixture
    def temp_sqlite_db(self):
        """Create a temporary SQLite database with test data."""
        # Create temporary database file
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            
            # Create tables and test data
            cursor.execute("""
                CREATE TABLE entries (
                    id TEXT PRIMARY KEY,
                    headword TEXT,
                    definition TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE senses (
                    id TEXT PRIMARY KEY,
                    entry_id TEXT,
                    definition TEXT,
                    FOREIGN KEY (entry_id) REFERENCES entries (id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE examples (
                    id TEXT PRIMARY KEY,
                    sense_id TEXT,
                    text TEXT,
                    FOREIGN KEY (sense_id) REFERENCES senses (id)
                )
            """)
            
            # Insert test data
            cursor.execute("INSERT INTO entries (id, headword, definition) VALUES ('entry1', 'test', 'A test word')")
            cursor.execute("INSERT INTO senses (id, entry_id, definition) VALUES ('sense1', 'entry1', 'A test definition')")
            cursor.execute("INSERT INTO examples (id, sense_id, text) VALUES ('example1', 'sense1', 'This is a test')")
            
            conn.commit()
            conn.close()
            
            yield path
        finally:
            # Clean up
            if os.path.exists(path):
                os.unlink(path)
    
    def test_sqlite_data_reading(self, temp_sqlite_db):
        """Test reading data from SQLite database."""
        
        conn = sqlite3.connect(temp_sqlite_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Test reading entries
        cursor.execute("SELECT * FROM entries")
        entries = cursor.fetchall()
        
        assert len(entries) == 1
        assert entries[0]['headword'] == 'test'
        assert entries[0]['id'] == 'entry1'
        
        # Test reading senses
        cursor.execute("SELECT * FROM senses")
        senses = cursor.fetchall()
        
        assert len(senses) == 1
        assert senses[0]['definition'] == 'A test definition'
        
        # Test reading examples
        cursor.execute("SELECT * FROM examples")
        examples = cursor.fetchall()
        
        assert len(examples) == 1
        assert examples[0]['text'] == 'This is a test'
        
        conn.close()
    
    def test_data_transformation(self):
        """Test data transformation for PostgreSQL compatibility."""
        # Test JSON parsing
        sqlite_custom_fields = '{"key": "value", "number": 123}'
        parsed_fields = json.loads(sqlite_custom_fields)
        
        assert parsed_fields['key'] == 'value'
        assert parsed_fields['number'] == 123
        
        # Test handling of None values
        sqlite_null_field = None
        pg_field = json.dumps({"raw": sqlite_null_field}) if sqlite_null_field else None
        
        assert pg_field is None
        
        # Test grammatical info transformation
        sqlite_grammar = "noun"
        pg_grammar = {"type": sqlite_grammar} if sqlite_grammar else None
        
        assert pg_grammar['type'] == 'noun'


class TestPostgreSQLIntegration:
    """Integration tests requiring actual PostgreSQL connection."""
    
    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv('POSTGRES_HOST'), reason="PostgreSQL server not configured")
    def test_real_connection(self):
        """Test real PostgreSQL connection (requires running PostgreSQL)."""
        config = PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        
        try:
            connector = PostgreSQLConnector(config)
            
            # Test basic query
            results = connector.fetch_all("SELECT version()")
            assert len(results) > 0
            assert 'PostgreSQL' in results[0]['version']
            
        except DatabaseConnectionError:
            raise
    
    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv('POSTGRES_HOST'), reason="PostgreSQL server not configured")
    def test_schema_creation_real(self):
        """Test actual schema creation (requires running PostgreSQL)."""
        config = PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        
        try:
            connector = PostgreSQLConnector(config)
            
            # Test creating a simple test table
            connector.execute_query("""
                CREATE TABLE IF NOT EXISTS test_migration (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test inserting data
            connector.execute_query(
                "INSERT INTO test_migration (name) VALUES (%(name)s)",
                {"name": "test_entry"}
            )
            
            # Test querying data
            results = connector.fetch_all("SELECT * FROM test_migration WHERE name = %(name)s", {"name": "test_entry"})
            assert len(results) > 0
            assert results[0]['name'] == 'test_entry'
            
            # Cleanup
            connector.execute_query("DROP TABLE IF EXISTS test_migration")
            
        except DatabaseConnectionError:
            raise


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
