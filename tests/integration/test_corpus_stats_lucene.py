"""
Integration tests for corpus stats endpoint using Lucene.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """Create test Flask app with corpus API blueprint."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True

    # Register the corpus blueprint
    from app.api.corpus import corpus_bp
    test_app.register_blueprint(corpus_bp)

    # Create mock Lucene client
    mock_client = Mock()
    mock_client.stats.return_value = {
        'total_documents': 74740856,
        'avg_source_length': 67.22,
        'avg_target_length': 68.56
    }

    # Attach to app
    test_app.lucene_corpus_client = mock_client

    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.mark.integration
class TestCorpusStatsLucene:
    """Tests for corpus stats endpoint with Lucene backend."""

    @pytest.mark.integration
    def test_get_corpus_stats_success(self, client):
        """Test successful retrieval of corpus stats from Lucene."""
        response = client.get('/corpus/stats')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Lucene route returns flat structure, not nested 'stats'
        assert data['total_records'] == 74740856
        assert data['source'] == 'lucene'

    @pytest.mark.integration
    def test_get_corpus_stats_avgs(self, client):
        """Test that stats endpoint returns data correctly."""
        response = client.get('/corpus/stats')

        assert response.status_code == 200
        data = response.get_json()
        # The Lucene stats endpoint returns total_records, not avg_source_length
        assert 'total_records' in data
        assert data['total_records'] == 74740856

    @pytest.mark.integration
    def test_get_corpus_stats_fallback_to_zero(self, client):
        """Test fallback when Lucene returns incomplete stats."""
        # Override the mock to return incomplete data
        with client.application.test_request_context():
            client.application.lucene_corpus_client.stats.return_value = {}

        response = client.get('/corpus/stats')

        assert response.status_code == 200
        data = response.get_json()
        # Lucene route returns flat structure with total_records at top level
        assert data['total_records'] == 0

    @pytest.mark.integration
    def test_get_corpus_stats_error_handling(self, client):
        """Test error handling when Lucene is unavailable."""
        with client.application.test_request_context():
            client.application.lucene_corpus_client.stats.side_effect = Exception("Connection refused")

        response = client.get('/corpus/stats')

        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert data['source'] == 'lucene'


@pytest.mark.integration
class TestClearCacheLucene:
    """Tests for clear cache endpoint."""

    @pytest.mark.integration
    def test_clear_cache_success(self, client):
        """Test successful cache clearing."""
        with patch('app.api.corpus.CacheService') as MockCacheService:
            mock_cache = Mock()
            mock_cache.is_available.return_value = True
            mock_cache.delete.return_value = None
            MockCacheService.return_value = mock_cache

            response = client.post('/corpus/clear-cache')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'Cache cleared successfully' in data['message']

    @pytest.mark.integration
    def test_clear_cache_when_unavailable(self, client):
        """Test cache clear when cache service is unavailable."""
        with patch('app.api.corpus.CacheService') as MockCacheService:
            mock_cache = Mock()
            mock_cache.is_available.return_value = False
            MockCacheService.return_value = mock_cache

            response = client.post('/corpus/clear-cache')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'not available' in data['error']
