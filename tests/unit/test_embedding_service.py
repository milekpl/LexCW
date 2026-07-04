"""
Unit tests for EmbeddingService and embedding API blueprint.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app.api.embedding_api import embedding_bp
from app.services.embedding_service import (
    EmbeddingService,
    EmbeddingServiceError,
    AVAILABLE_MODELS,
    get_embedding_service,
)


class TestEmbeddingServiceUnit(unittest.TestCase):
    """Unit tests for core EmbeddingService methods."""

    def setUp(self):
        self.service = EmbeddingService(qdrant_host="localhost", qdrant_port=6333)

    def test_available_models(self):
        """Verify available models list structure."""
        self.assertGreater(len(AVAILABLE_MODELS), 0)
        for model in AVAILABLE_MODELS:
            self.assertIn("id", model)
            self.assertIn("dimension", model)
            self.assertIn("label", model)

    def test_get_collection_name(self):
        """Verify collection naming for projects."""
        self.assertEqual(self.service.get_collection_name(1), "project_1_senses")
        self.assertEqual(self.service.get_collection_name(42), "project_42_senses")
        self.assertEqual(self.service.get_collection_name(None), "project_1_senses")

    def test_compose_sense_text(self):
        """Test sense text composition formatting."""
        text = self.service._compose_sense_text(
            headword="cat",
            definition="a small domesticated carnivorous mammal",
            glosses=["kot", "kotek"],
            pos="noun",
        )
        self.assertEqual(
            text,
            "cat (noun): a small domesticated carnivorous mammal [kot, kotek]"
        )

    def test_compose_sense_text_minimal(self):
        """Test sense text composition with headword only."""
        text = self.service._compose_sense_text(
            headword="dog",
            definition="",
            glosses=[],
            pos=None,
        )
        self.assertEqual(text, "dog")

    @patch("qdrant_client.QdrantClient")
    def test_ensure_collection(self, mock_qdrant_cls):
        """Test Qdrant collection creation."""
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = False
        mock_qdrant_cls.return_value = mock_client

        self.service._qdrant_client = mock_client
        self.service.ensure_collection(project_id=1, model_name="jinaai/jina-embeddings-v3")

        mock_client.collection_exists.assert_called_with("project_1_senses")
        mock_client.create_collection.assert_called_once()

    @patch.object(EmbeddingService, "_get_model")
    @patch.object(EmbeddingService, "_get_qdrant_client")
    def test_semantic_search_mocked(self, mock_get_qdrant, mock_get_model):
        """Test semantic search method with mocked model and Qdrant."""
        mock_model = MagicMock()
        mock_model.encode.return_value = [[0.1] * 1024]
        mock_get_model.return_value = mock_model

        hit = MagicMock()
        hit.score = 0.88
        hit.payload = {
            "entry_id": "entry-1",
            "headword": "feline",
            "sense_id": "sense-1",
            "pos": "noun",
            "definition": "cat family animal",
        }

        mock_client = MagicMock()
        mock_client.search.return_value = [hit]
        mock_get_qdrant.return_value = mock_client

        results = self.service.semantic_search(
            query="cat",
            project_id=1,
            top_k=5,
            threshold=0.5,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["entry_id"], "entry-1")
        self.assertEqual(results[0]["headword"], "feline")
        self.assertEqual(results[0]["score"], 0.88)


class TestEmbeddingAPIEndpoints(unittest.TestCase):
    """Test Flask API endpoints for embedding blueprint."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.config["QDRANT_HOST"] = "localhost"
        self.app.config["QDRANT_PORT"] = 6333
        self.app.register_blueprint(embedding_bp)
        self.client = self.app.test_client()

    def test_get_models_endpoint(self):
        """Test GET /api/embeddings/models."""
        res = self.client.get("/api/embeddings/models")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["models"]), 0)

    @patch("app.api.embedding_api.get_embedding_service")
    def test_get_status_endpoint(self, mock_get_service):
        """Test GET /api/embeddings/status."""
        mock_service = MagicMock()
        mock_service.get_index_status.return_value = {
            "collection_exists": True,
            "vectors_count": 1500,
            "model_name": "jinaai/jina-embeddings-v3",
            "device": "cpu",
            "last_built": None,
        }
        mock_get_service.return_value = mock_service

        res = self.client.get("/api/embeddings/status?project_id=1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"]["vectors_count"], 1500)

    @patch("app.api.embedding_api.get_embedding_service")
    def test_search_endpoint(self, mock_get_service):
        """Test GET /api/embeddings/search."""
        mock_service = MagicMock()
        mock_service.semantic_search.return_value = [
            {
                "entry_id": "e1",
                "headword": "cat",
                "sense_id": "s1",
                "pos": "noun",
                "definition": "small feline",
                "score": 0.92,
            }
        ]
        mock_get_service.return_value = mock_service

        res = self.client.get("/api/embeddings/search?q=cat&top_k=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["headword"], "cat")

    def test_search_endpoint_empty_query(self):
        """Test GET /api/embeddings/search with missing query."""
        res = self.client.get("/api/embeddings/search?q=")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main()
