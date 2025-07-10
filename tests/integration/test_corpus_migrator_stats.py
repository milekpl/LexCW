"""
Test for CorpusMigrator.get_corpus_stats() method to handle missing table gracefully.
"""

import pytest
from unittest.mock import Mock, patch
import psycopg2

from app.database.corpus_migrator import CorpusMigrator
from app.database.postgresql_connector import PostgreSQLConfig



@pytest.mark.integration
class TestCorpusMigratorStats:
    """Test CorpusMigrator statistics functionality."""
    
    @pytest.fixture
    def config(self) -> PostgreSQLConfig:
        """Create test configuration."""
        return PostgreSQLConfig(
            host='localhost',
            port=5432,
            database='test_db',
            username='test_user',
            password='test_pass'
        )
    
    @pytest.fixture
    def migrator(self, config: PostgreSQLConfig) -> CorpusMigrator:
        """Create test migrator."""
        return CorpusMigrator(config)
    
    @pytest.mark.integration
    def test_get_corpus_stats_table_not_exists(self, migrator: CorpusMigrator) -> None:
        """Test get_corpus_stats when parallel_corpus table doesn't exist."""
        with patch.object(migrator, '_get_postgres_connection') as mock_conn:
            # Mock the cursor and connection
            mock_cursor = Mock()
            mock_connection = Mock()
            
            # Properly mock the context manager for cursor
            cursor_context = Mock()
            cursor_context.__enter__ = Mock(return_value=mock_cursor)
            cursor_context.__exit__ = Mock(return_value=None)
            mock_connection.cursor.return_value = cursor_context
            mock_conn.return_value = mock_connection
            
            # Simulate table not existing error
            mock_cursor.execute.side_effect = psycopg2.errors.UndefinedTable(
                "relation \"parallel_corpus\" does not exist"
            )
            
            # Should return default stats when table doesn't exist
            stats = migrator.get_corpus_stats()
            
            expected_stats = {
                'total_records': 0,
                'avg_source_length': 0.0,
                'avg_target_length': 0.0,
                'first_record': None,
                'last_record': None
            }
            
            assert stats == expected_stats
            mock_connection.close.assert_called_once()
    
    @pytest.mark.integration
    def test_get_corpus_stats_with_data(self, migrator: CorpusMigrator) -> None:
        """Test get_corpus_stats when table exists with data."""
        with patch.object(migrator, '_get_postgres_connection') as mock_conn:
            # Mock the cursor and connection
            mock_cursor = Mock()
            mock_connection = Mock()
            
            # Properly mock the context manager for cursor
            cursor_context = Mock()
            cursor_context.__enter__ = Mock(return_value=mock_cursor)
            cursor_context.__exit__ = Mock(return_value=None)
            mock_connection.cursor.return_value = cursor_context
            mock_conn.return_value = mock_connection
            
            # Mock successful query result
            mock_result = {
                'total_records': 1000,
                'avg_source_length': 25.5,
                'avg_target_length': 30.2,
                'first_record': '2024-01-01 10:00:00',
                'last_record': '2024-12-31 15:30:00'
            }
            mock_cursor.fetchone.return_value = mock_result
            
            stats = migrator.get_corpus_stats()
            
            assert stats == mock_result
            mock_connection.close.assert_called_once()
    
    @pytest.mark.integration
    def test_get_corpus_stats_empty_table(self, migrator: CorpusMigrator) -> None:
        """Test get_corpus_stats when table exists but is empty."""
        with patch.object(migrator, '_get_postgres_connection') as mock_conn:
            # Mock the cursor and connection
            mock_cursor = Mock()
            mock_connection = Mock()
            
            # Properly mock the context manager for cursor
            cursor_context = Mock()
            cursor_context.__enter__ = Mock(return_value=mock_cursor)
            cursor_context.__exit__ = Mock(return_value=None)
            mock_connection.cursor.return_value = cursor_context
            mock_conn.return_value = mock_connection
            
            # Mock empty result (fetchone returns None)
            mock_cursor.fetchone.return_value = None
            
            stats = migrator.get_corpus_stats()
            
            expected_stats = {
                'total_records': 0,
                'avg_source_length': 0.0,
                'avg_target_length': 0.0,
                'first_record': None,
                'last_record': None
            }
            assert stats == expected_stats
            mock_connection.close.assert_called_once()
