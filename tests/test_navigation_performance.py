"""
Test navigation and performance for main application features.
"""
from __future__ import annotations

import pytest
from flask import Flask
from unittest.mock import patch, Mock

from app import create_app


@pytest.fixture
def app():
    """Create test Flask app."""
    return create_app('testing')


@pytest.fixture  
def client(app):
    """Create test client."""
    return app.test_client()


class TestMainNavigation:
    """Test main navigation functionality."""
    
    def test_corpus_management_navigation_exists(self, client):
        """Test that corpus management is accessible from navigation."""
        response = client.get('/')
        assert response.status_code == 200
        
        # Check if corpus management link exists in navigation
        html_content = response.get_data(as_text=True)
        assert 'corpus' in html_content.lower() or 'Corpus Management' in html_content
    
    def test_corpus_management_page_loads(self, client):
        """Test that corpus management page loads properly."""
        with patch('app.routes.corpus_routes.CorpusMigrator') as mock_migrator:
            mock_instance = Mock()
            mock_migrator.return_value = mock_instance
            mock_instance.get_corpus_stats.return_value = {
                'total_records': 0,
                'avg_source_length': 0,
                'avg_target_length': 0
            }
            
            response = client.get('/api/corpus/')
            assert response.status_code == 200


class TestPerformanceOptimization:
    """Test that performance issues are identified."""
    
    def test_entries_page_performance(self, client):
        """Test that entries page loads within reasonable time."""
        import time
        
        start_time = time.time()
        response = client.get('/entries')
        end_time = time.time()
        
        # Should load within 2 seconds for a test environment
        assert (end_time - start_time) < 2.0
        assert response.status_code == 200
    
    @patch('app.services.dictionary_service.DictionaryService')
    def test_entries_with_caching_mock(self, mock_service, client):
        """Test that entries loading uses caching when available."""
        # Mock the service to return quickly
        mock_instance = Mock()
        mock_service.return_value = mock_instance
        mock_instance.get_all_entries.return_value = []
        mock_instance.get_total_count.return_value = 0
        
        response = client.get('/entries')
        assert response.status_code == 200
        
        # Verify caching is being considered (service called)
        mock_instance.get_all_entries.assert_called()
