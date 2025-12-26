"""
TDD tests for corpus management PostgreSQL integration and navigation.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock, Mock

from app import create_app


import pytest


@pytest.mark.integration
class TestCorpusManagementIntegration:
    """Test corpus management PostgreSQL connection and navigation."""
    
    @pytest.mark.integration
    def test_corpus_management_connects_to_postgresql(self, client) -> None:
        """Test that corpus management page connects to PostgreSQL for corpus data."""
        with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
            mock_instance = MagicMock()
            mock_connector.return_value = mock_instance
            mock_instance.test_connection.return_value = True
            mock_instance.fetch_all.return_value = [
                {'count': 1000, 'table_name': 'parallel_corpus'},
                {'count': 500, 'table_name': 'corpus_documents'}
            ]

            response = client.get('/corpus-management')
            assert response.status_code == 200

            # Should contain PostgreSQL connection status
            assert b'PostgreSQL' in response.data
            # Should contain corpus statistics
            assert b'corpus' in response.data.lower()
                
    @pytest.mark.integration
    def test_corpus_management_displays_connection_status(self, client) -> None:
        """Test that corpus management displays PostgreSQL connection status."""
        with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
            mock_instance = MagicMock()
            mock_connector.return_value = mock_instance
            mock_instance.test_connection.return_value = False

            response = client.get('/corpus-management')
            assert response.status_code == 200

            # Should show connection status (even if failed)
            assert b'Connection' in response.data or b'Status' in response.data
                
    @pytest.mark.integration
    def test_corpus_management_handles_postgresql_error(self, client) -> None:
        """Test that corpus management handles PostgreSQL connection errors gracefully."""
        with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
            mock_connector.side_effect = Exception("PostgreSQL connection failed")

            response = client.get('/corpus-management')
            assert response.status_code == 200  # Should still render page

            # Should handle error gracefully
            assert response.data is not None
                
    @pytest.mark.integration
    def test_corpus_management_navigation_to_home(self, client) -> None:
        """Test that corpus management page has navigation link to home."""
        response = client.get('/corpus-management')
        assert response.status_code == 200

        # Should have navigation to home page
        assert b'href="/"' in response.data or b"href='/'" in response.data
            
    @pytest.mark.integration
    def test_corpus_management_breadcrumb_navigation(self, client) -> None:
        """Test that corpus management has proper breadcrumb navigation."""
        response = client.get('/corpus-management')
        assert response.status_code == 200

        # Should have breadcrumb or navigation elements
        assert (b'Home' in response.data and b'Corpus' in response.data) or \
               b'breadcrumb' in response.data or \
               b'nav' in response.data
                   
    @pytest.mark.integration
    def test_corpus_management_displays_correct_postgresql_stats(self, client) -> None:
        """Test that corpus management displays actual PostgreSQL corpus statistics."""
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
            from datetime import datetime
            mock_result = {
                'total_records': 74000000,
                'avg_source_length': 25.5,
                'avg_target_length': 30.2,
                'first_record': None,
                'last_record': datetime(2025, 6, 28, 10, 30, 0)
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

        # Should display the correct corpus statistics
        assert data['corpus_stats']['total_records'] == 74000000
        assert data['corpus_stats']['avg_source_length'] == '25.50'
        assert data['corpus_stats']['avg_target_length'] == '30.20'
        assert '2025-06-28' in data['corpus_stats']['last_updated']

        # Connection should be closed properly
        mock_connection.close.assert_called_once()
