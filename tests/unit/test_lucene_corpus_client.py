"""
Unit tests for Lucene corpus client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from app.services.lucene_corpus_client import LuceneCorpusClient, ConcordanceHit


class TestLuceneCorpusClient:
    """Tests for LuceneCorpusClient."""

    @pytest.fixture
    def client(self):
        """Create a LuceneCorpusClient for testing."""
        return LuceneCorpusClient(base_url="http://localhost:8082")

    def test_init_with_default_url(self):
        """Test client initialization with default URL."""
        client = LuceneCorpusClient()
        assert client.base_url == "http://localhost:8082"

    def test_init_with_custom_url(self):
        """Test client initialization with custom URL."""
        client = LuceneCorpusClient(base_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slashes are stripped from URL."""
        client = LuceneCorpusClient(base_url="http://localhost:8082/")
        assert client.base_url == "http://localhost:8082"

    def test_health_success(self, client):
        """Test successful health check."""
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.health()

            assert result["status"] == "ok"
            mock_get.assert_called_once_with(f"{client.base_url}/health", timeout=5)

    def test_health_failure(self, client):
        """Test health check failure."""
        with patch.object(client._session, 'get') as mock_get:
            mock_get.side_effect = requests.RequestException("Connection refused")

            result = client.health()

            assert result["status"] == "unhealthy"
            assert "Connection refused" in result["error"]

    def test_is_available_true(self, client):
        """Test is_available returns True when healthy."""
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "ok"}
            mock_get.return_value = mock_response

            assert client.is_available() is True

    def test_is_available_false(self, client):
        """Test is_available returns False when unhealthy."""
        with patch.object(client._session, 'get') as mock_get:
            mock_get.side_effect = requests.RequestException("Connection refused")

            assert client.is_available() is False

    def test_concordance_success(self, client):
        """Test successful concordance search."""
        mock_hits = [
            {"left": "The", "match": "cat", "right": "is here", "sentence_id": "1"},
            {"left": "A big", "match": "cat", "right": "sat down", "sentence_id": "2"},
        ]

        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"hits": mock_hits, "total": 2}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            total, hits = client.concordance("cat", limit=10)

            assert total == 2
            assert len(hits) == 2
            assert hits[0].match == "cat"
            assert hits[0].left == "The"
            assert hits[0].sentence_id == "1"

    def test_concordance_failure(self, client):
        """Test concordance search failure returns empty result."""
        with patch.object(client._session, 'get') as mock_get:
            mock_get.side_effect = requests.RequestException("Timeout")

            total, hits = client.concordance("test")

            assert total == 0
            assert hits == []

    def test_count_success(self, client):
        """Test successful count query."""
        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"count": 1500}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            count = client.count("house")

            assert count == 1500
            mock_get.assert_called_once_with(
                f"{client.base_url}/count",
                params={"q": "house"},
                timeout=30
            )

    def test_count_failure(self, client):
        """Test count query failure returns zero."""
        with patch.object(client._session, 'get') as mock_get:
            mock_get.side_effect = requests.RequestException("Error")

            count = client.count("test")

            assert count == 0

    def test_stats_success(self, client):
        """Test successful stats query via /health endpoint."""
        mock_health = {
            "status": "ok",
            "docs": 74740856,
            "heapUsedMb": 57,
            "heapMaxMb": 4096,
            "uptimeSeconds": 36
        }

        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_health
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.stats()

            assert result["total_documents"] == 74740856
            assert result["status"] == "ok"
            assert result["heap_used_mb"] == 57

    def test_stats_failure(self, client):
        """Test stats query failure raises exception."""
        with patch.object(client._session, 'get') as mock_get:
            mock_get.side_effect = requests.RequestException("Connection refused")

            with pytest.raises(requests.RequestException):
                client.stats()

    def test_health_success(self, client):
        """Test successful health check."""
        mock_health = {
            "status": "ok",
            "docs": 74740856,
            "heapUsedMb": 57,
            "heapMaxMb": 4096,
            "uptimeSeconds": 36
        }

        with patch.object(client._session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_health
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = client.health()

            assert result["status"] == "ok"
            assert result["docs"] == 74740856
            mock_get.assert_called_with(f"{client.base_url}/health", timeout=5)

    def test_health_failure(self, client):
        """Test health check failure returns unhealthy status."""
        with patch.object(client._session, 'get') as mock_get:
            mock_get.side_effect = requests.RequestException("Connection refused")

            result = client.health()

            assert result["status"] == "unhealthy"
            assert "Connection refused" in result["error"]

    def test_compare_success(self, client):
        """Test successful compare query."""
        mock_result = {
            "a": "test",
            "b": "example",
            "frequency_a": 100,
            "frequency_b": 50
        }

        with patch.object(client._session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_result
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = client.compare("test", "example")

            assert result["frequency_a"] == 100
            mock_post.assert_called_once()

    def test_compare_failure(self, client):
        """Test compare query failure returns error."""
        with patch.object(client._session, 'post') as mock_post:
            mock_post.side_effect = requests.RequestException("Error")

            result = client.compare("a", "b")

            assert "error" in result

    def test_optimize_success(self, client):
        """Test successful index optimization."""
        mock_result = {
            "status": "ok",
            "docs": 1000,
            "segmentsMerged": 5,
            "message": "Index optimized from 5 segments to 1"
        }

        with patch.object(client._session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_result
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = client.optimize()

            assert result["status"] == "ok"
            assert result["segmentsMerged"] == 5
            mock_post.assert_called_once_with(f"{client.base_url}/optimize", timeout=300)

    def test_optimize_failure(self, client):
        """Test optimize failure raises exception."""
        with patch.object(client._session, 'post') as mock_post:
            mock_post.side_effect = requests.RequestException("Connection refused")

            with pytest.raises(requests.RequestException):
                client.optimize()

    def test_clear_success(self, client):
        """Test successful index clear."""
        mock_result = {
            "status": "ok",
            "documentsDeleted": 500,
            "message": "Index cleared successfully"
        }

        with patch.object(client._session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_result
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = client.clear()

            assert result["status"] == "ok"
            assert result["documentsDeleted"] == 500
            mock_post.assert_called_once_with(f"{client.base_url}/clear", timeout=300)

    def test_clear_failure(self, client):
        """Test clear failure raises exception."""
        with patch.object(client._session, 'post') as mock_post:
            mock_post.side_effect = requests.RequestException("Connection refused")

            with pytest.raises(requests.RequestException):
                client.clear()


class TestConcordanceHit:
    """Tests for ConcordanceHit dataclass."""

    def test_create_hit(self):
        """Test creating a concordance hit."""
        hit = ConcordanceHit(
            left="The quick",
            match="brown",
            right="fox jumps",
            sentence_id="123"
        )

        assert hit.left == "The quick"
        assert hit.match == "brown"
        assert hit.right == "fox jumps"
        assert hit.sentence_id == "123"

    def test_hit_without_sentence_id(self):
        """Test creating a hit without sentence ID."""
        hit = ConcordanceHit(left="Before", match="word", right="After")

        assert hit.sentence_id is None
