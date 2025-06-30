"""
Integration test for corpus management view with real PostgreSQL table missing scenario.
"""

import pytest
from unittest.mock import patch, Mock
import psycopg2.errors

from app import create_app
from app.database.corpus_migrator import CorpusMigrator
from app.database.postgresql_connector import PostgreSQLConfig


class TestCorpusManagementIntegrationTableMissing:
    """Test corpus management view when PostgreSQL table is missing."""
    
    @pytest.fixture
    def app(self):
        """Create test app."""
        app = create_app('testing')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_corpus_management_handles_missing_table_gracefully(self, client) -> None:
        """Test that corpus management page works when parallel_corpus table doesn't exist."""
        # Mock the PostgreSQL connection to simulate missing table
        with patch('app.database.corpus_migrator.CorpusMigrator._get_postgres_connection') as mock_conn:
            # Set up mock connection
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
            
            # Test the corpus management HTML page loads successfully
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Test the API endpoint that provides status and stats
            api_response = client.get('/api/corpus/stats/ui')
            assert api_response.status_code == 200
            
            # Parse the JSON response
            data = api_response.get_json()
            
            # Should return success with connection established (connection works, table just doesn't exist)
            assert data['success'] is True
            assert data['postgres_status']['connected'] is True
            
            # Should show default stats (0 records, etc.) when table doesn't exist
            assert data['corpus_stats']['total_records'] == 0
            assert data['corpus_stats']['avg_source_length'] == '0.00'
            assert data['corpus_stats']['avg_target_length'] == '0.00'
            assert data['corpus_stats']['last_updated'] == 'N/A'
            
            # Connection should be closed properly
            mock_connection.close.assert_called_once()
    
    def test_corpus_management_shows_real_stats_when_table_exists(self, client) -> None:
        """Test that corpus management page shows real stats when table exists."""
        # Mock the PostgreSQL connection to simulate existing table with data
        with patch('app.database.corpus_migrator.CorpusMigrator._get_postgres_connection') as mock_conn:
            # Set up mock connection
            mock_cursor = Mock()
            mock_connection = Mock()
            
            # Properly mock the context manager for cursor
            cursor_context = Mock()
            cursor_context.__enter__ = Mock(return_value=mock_cursor)
            cursor_context.__exit__ = Mock(return_value=None)
            mock_connection.cursor.return_value = cursor_context
            mock_conn.return_value = mock_connection
            
            # Mock successful query result with real data
            mock_result = {
                'total_records': 74000000,
                'avg_source_length': 25.5,
                'avg_target_length': 30.2,
                'first_record': None,
                'last_record': None
            }
            mock_cursor.fetchone.return_value = mock_result
            
            # Test the corpus management HTML page loads successfully
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Test the API endpoint that provides status and stats
            api_response = client.get('/api/corpus/stats/ui')
            assert api_response.status_code == 200
            
            # Parse the JSON response
            data = api_response.get_json()
            
            # Should return success with connection established
            assert data['success'] is True
            assert data['postgres_status']['connected'] is True
            
            # Should show real stats
            assert data['corpus_stats']['total_records'] == 74000000
            assert data['corpus_stats']['avg_source_length'] == '25.50'
            assert data['corpus_stats']['avg_target_length'] == '30.20'
            
            # Connection should be closed properly
            mock_connection.close.assert_called_once()
