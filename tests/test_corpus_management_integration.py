"""
TDD tests for corpus management PostgreSQL integration and navigation.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from app import create_app


class TestCorpusManagementIntegration:
    """Test corpus management PostgreSQL connection and navigation."""
    
    def test_corpus_management_connects_to_postgresql(self) -> None:
        """Test that corpus management page connects to PostgreSQL for corpus data."""
        app = create_app('testing')
        
        with app.test_client() as client:
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
                
    def test_corpus_management_displays_connection_status(self) -> None:
        """Test that corpus management displays PostgreSQL connection status."""
        app = create_app('testing')
        
        with app.test_client() as client:
            with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
                mock_instance = MagicMock()
                mock_connector.return_value = mock_instance
                mock_instance.test_connection.return_value = False
                
                response = client.get('/corpus-management')
                assert response.status_code == 200
                
                # Should show connection status (even if failed)
                assert b'Connection' in response.data or b'Status' in response.data
                
    def test_corpus_management_handles_postgresql_error(self) -> None:
        """Test that corpus management handles PostgreSQL connection errors gracefully."""
        app = create_app('testing')
        
        with app.test_client() as client:
            with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
                mock_connector.side_effect = Exception("PostgreSQL connection failed")
                
                response = client.get('/corpus-management')
                assert response.status_code == 200  # Should still render page
                
                # Should handle error gracefully
                assert response.data is not None
                
    def test_corpus_management_navigation_to_home(self) -> None:
        """Test that corpus management page has navigation link to home."""
        app = create_app('testing')
        
        with app.test_client() as client:
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Should have navigation to home page
            assert b'href="/"' in response.data or b"href='/'" in response.data
            
    def test_corpus_management_breadcrumb_navigation(self) -> None:
        """Test that corpus management has proper breadcrumb navigation."""
        app = create_app('testing')
        
        with app.test_client() as client:
            response = client.get('/corpus-management')
            assert response.status_code == 200
            
            # Should have breadcrumb or navigation elements
            assert (b'Home' in response.data and b'Corpus' in response.data) or \
                   b'breadcrumb' in response.data or \
                   b'nav' in response.data
                   
    def test_corpus_management_displays_correct_postgresql_stats(self) -> None:
        """Test that corpus management displays actual PostgreSQL corpus statistics."""
        app = create_app('testing')
        
        with app.test_client() as client:
            with patch('app.database.postgresql_connector.PostgreSQLConnector') as mock_connector:
                mock_instance = MagicMock()
                mock_connector.return_value = mock_instance
                mock_instance.test_connection.return_value = True
                
                # Mock table discovery to return actual corpus table names
                mock_instance.fetch_all.side_effect = [
                    # First call: table discovery
                    [
                        {'table_name': 'parallel_corpus'},
                        {'table_name': 'corpus_metadata'},
                        {'table_name': 'sentence_pairs'}
                    ],
                    # Second call: count query for parallel_corpus  
                    [{'count': 74000000}],  # 74 million rows
                    # Third call: last update query
                    [{'last_update': '2025-06-28 10:30:00'}]
                ]
                
                response = client.get('/corpus-management')
                assert response.status_code == 200
                
                # Should display the correct corpus statistics
                content = response.data.decode('utf-8')
                assert '74,000,000' in content or '74000000' in content
                assert '2025-06-28' in content
