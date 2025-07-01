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

    def test_corpus_management_renders_successfully(self, client: FlaskClient) -> None:
        """Test that corpus management page renders successfully with loading state."""
        response = client.get('/corpus-management')
        
        # Verify response
        assert response.status_code == 200
        
        # Should render with loading indicators (spinner)
        response_text = response.data.decode('utf-8')
        assert 'fa-spinner' in response_text
        assert 'corpus-management' in response_text or 'Corpus Management' in response_text

    def test_corpus_management_default_context(self, client: FlaskClient) -> None:
        """Test that corpus management page provides correct default context."""
        # Mock render_template to capture context
        with patch('app.views.render_template') as mock_render:
            mock_render.return_value = "Mocked template response"
            
            response = client.get('/corpus-management')
            
            # Verify response
            assert response.status_code == 200
            
            # Verify render_template was called with correct arguments
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == 'corpus_management.html'
            
            # Check that default context is provided
            context = call_args[1]
            corpus_stats = context['corpus_stats']
            postgres_status = context['postgres_status']
            
            # Default loading state
            assert corpus_stats['total_records'] == 0
            assert corpus_stats['avg_source_length'] == '0.00'
            assert corpus_stats['avg_target_length'] == '0.00'
            assert corpus_stats['last_updated'] == 'Loading...'
            
            # Default connection state
            assert postgres_status['connected'] is False
            assert postgres_status['error'] is None

    def test_corpus_management_template_structure(self, client: FlaskClient) -> None:
        """Test that corpus management page has expected HTML structure."""
        response = client.get('/corpus-management')
        
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        
        # Check for key elements that should be present
        assert 'total-records' in response_text or 'Total Records' in response_text
        assert 'avg-source-length' in response_text or 'Source Length' in response_text
        assert 'avg-target-length' in response_text or 'Target Length' in response_text
        assert 'last-updated' in response_text or 'Last Updated' in response_text
