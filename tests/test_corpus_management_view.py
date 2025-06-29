"""
Test for corpus management view functionality.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Any
from flask.testing import FlaskClient


class TestCorpusManagement:
    """Tests for corpus management page functionality."""

    def test_corpus_management_displays_stats_when_connected(self, client: FlaskClient) -> None:
        """Test that corpus management page displays statistics when PostgreSQL is connected."""
        # Mock the CorpusMigrator to return test data
        with patch('app.views.CorpusMigrator') as mock_migrator_class:
            mock_migrator = Mock()
            mock_migrator_class.return_value = mock_migrator
            
            # Mock successful connection test
            mock_migrator._get_postgres_connection.return_value = Mock()
            
            # Mock statistics data
            mock_stats: dict[str, Any] = {
                'total_records': 1000,
                'avg_source_length': 25.5,
                'avg_target_length': 30.2,
                'first_record': datetime(2023, 1, 1, 10, 0, 0),
                'last_record': datetime(2023, 12, 31, 15, 30, 0)
            }
            mock_migrator.get_corpus_stats.return_value = mock_stats
            
            # Mock render_template to avoid template not found error in tests
            with patch('app.views.render_template') as mock_render:
                mock_render.return_value = "Mocked template response"
                
                # Make request to corpus management page
                response = client.get('/corpus-management')
                
                # Verify response
                assert response.status_code == 200
                
                # Verify render_template was called with correct arguments
                mock_render.assert_called_once()
                call_args = mock_render.call_args
                assert call_args[0][0] == 'corpus_management.html'
                
                # Check that the stats were formatted correctly in the context
                context = call_args[1]
                corpus_stats = context['corpus_stats']
                postgres_status = context['postgres_status']
                
                assert corpus_stats['total_records'] == 1000
                assert corpus_stats['avg_source_length'] == "25.50"
                assert corpus_stats['avg_target_length'] == "30.20"
                assert corpus_stats['last_updated'] == "2023-12-31 15:30:00"
                
                assert postgres_status['connected'] is True
                assert postgres_status['error'] is None

    def test_corpus_management_handles_connection_failure(self, client: FlaskClient) -> None:
        """Test that corpus management page handles PostgreSQL connection failure gracefully."""
        # Mock the CorpusMigrator to raise an exception
        with patch('app.views.CorpusMigrator') as mock_migrator_class:
            mock_migrator_class.side_effect = Exception("Connection failed")
            
            # Mock render_template to avoid template not found error in tests
            with patch('app.views.render_template') as mock_render:
                mock_render.return_value = "Mocked template response"
                
                # Make request to corpus management page
                response = client.get('/corpus-management')
                
                # Verify response
                assert response.status_code == 200
                
                # Verify render_template was called with correct arguments
                mock_render.assert_called_once()
                call_args = mock_render.call_args
                assert call_args[0][0] == 'corpus_management.html'
                
                # Check that the error was captured
                context = call_args[1]
                postgres_status = context['postgres_status']
                
                assert postgres_status['connected'] is False
                assert 'Connection failed' in postgres_status['error']

    def test_corpus_management_handles_empty_stats(self, client: FlaskClient) -> None:
        """Test that corpus management page handles empty statistics gracefully."""
        with patch('app.views.CorpusMigrator') as mock_migrator_class:
            mock_migrator = Mock()
            mock_migrator_class.return_value = mock_migrator
            
            # Mock successful connection but empty stats
            mock_migrator._get_postgres_connection.return_value = Mock()
            mock_migrator.get_corpus_stats.return_value = {}
            
            # Mock render_template to avoid template not found error in tests
            with patch('app.views.render_template') as mock_render:
                mock_render.return_value = "Mocked template response"
                
                # Make request to corpus management page
                response = client.get('/corpus-management')
                
                # Verify response
                assert response.status_code == 200
                
                # Verify render_template was called with correct arguments
                mock_render.assert_called_once()
                call_args = mock_render.call_args
                assert call_args[0][0] == 'corpus_management.html'
                
                # Check that default values are shown
                context = call_args[1]
                corpus_stats = context['corpus_stats']
                postgres_status = context['postgres_status']
                
                assert corpus_stats['total_records'] == 0
                assert corpus_stats['avg_source_length'] == "0.00"
                assert corpus_stats['avg_target_length'] == "0.00"
                assert corpus_stats['last_updated'] == "N/A"
                
                assert postgres_status['connected'] is True
                assert postgres_status['error'] is None
