"""
Integration test for corpus management view with Lucene backend.
Tests how corpus management handles various scenarios with the Lucene index.
"""

import pytest
from unittest.mock import patch, Mock

from app import create_app


@pytest.mark.integration
class TestCorpusManagementIntegrationTableMissing:
    """Test corpus management view with Lucene backend."""

    @pytest.mark.integration
    def test_corpus_management_handles_lucene_gracefully(self, client) -> None:
        """Test that corpus management page works with Lucene backend."""
        # Test the corpus management HTML page loads successfully
        response = client.get('/corpus-management')
        assert response.status_code == 200

        # Test the API endpoint that provides status and stats
        api_response = client.get('/api/corpus/stats/ui')
        assert api_response.status_code == 200

        # Parse the JSON response
        data = api_response.get_json()

        # Should return success
        assert data['success'] is True
        # Should have lucene_status (not postgres_status)
        assert 'lucene_status' in data

        # Should show stats (may be 0 if Lucene is not available)
        assert 'corpus_stats' in data
        assert 'total_records' in data['corpus_stats']

    @pytest.mark.integration
    def test_corpus_management_shows_stats_when_lucene_available(self, client) -> None:
        """Test that corpus management page shows stats when Lucene is available."""
        # Mock the Lucene client to return stats
        with patch.object(client.application, 'lucene_corpus_client') as mock_client:
            mock_client.stats.return_value = {
                'total_documents': 74000000,
                'avg_source_length': 25.5,
                'avg_target_length': 30.2
            }

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
            assert data['lucene_status']['connected'] is True

            # Should show real stats
            assert data['corpus_stats']['total_records'] == 74000000
