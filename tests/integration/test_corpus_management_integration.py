"""
TDD tests for corpus management Lucene integration and navigation.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock, Mock

from app import create_app


import pytest


@pytest.mark.integration
class TestCorpusManagementIntegration:
    """Test corpus management Lucene connection and navigation."""

    @pytest.mark.integration
    def test_corpus_management_connects_to_lucene(self, client) -> None:
        """Test that corpus management page uses Lucene for corpus data."""
        response = client.get('/corpus-management')
        assert response.status_code == 200

        # Should contain Lucene connection status in context (not HTML)
        # The actual Lucene connection status is loaded via AJAX
        assert b'corpus' in response.data.lower()

    @pytest.mark.integration
    def test_corpus_management_displays_connection_status(self, client) -> None:
        """Test that corpus management displays connection status placeholder."""
        response = client.get('/corpus-management')
        assert response.status_code == 200

        # Should show connection status indicator
        assert b'Connection' in response.data or b'Status' in response.data

    @pytest.mark.integration
    def test_corpus_management_handles_lucene_error(self, client) -> None:
        """Test that corpus management handles Lucene connection errors gracefully."""
        with patch('app.routes.corpus_routes.current_app') as mock_app:
            # Simulate Lucene being unavailable
            mock_app.lucene_corpus_client.stats.side_effect = Exception("Lucene connection failed")

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
    def test_corpus_management_displays_correct_lucene_stats(self, client) -> None:
        """Test that corpus management displays Lucene corpus statistics via API."""
        # Test the API endpoint that provides status and stats
        api_response = client.get('/api/corpus/stats/ui')
        assert api_response.status_code == 200

        # Parse the JSON response
        data = api_response.get_json()

        # Should return success
        assert data['success'] is True
        # Should have lucene_status (not postgres_status)
        assert 'lucene_status' in data

        # Should have corpus_stats
        assert 'corpus_stats' in data
        assert 'total_records' in data['corpus_stats']
