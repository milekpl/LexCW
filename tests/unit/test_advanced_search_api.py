"""
Unit tests for Advanced Search API endpoints.

Tests the new endpoints:
- GET /api/search/facets
- GET /api/search/export
- POST /api/search/save
- GET /api/search/saved
"""

import json
import pytest
from unittest.mock import Mock, patch
from flask.testing import FlaskClient
from app.models.entry import Entry
from app.models.sense import Sense


@pytest.mark.unit
class TestFacetsEndpoint:
    """Test the /api/search/facets endpoint."""

    def test_facets_returns_counts(self, client, mock_dict_service):
        """Facets endpoint should return facet counts."""
        sense1 = Sense(id_="sense_1", definitions={"en": "A cat"})
        sense1.grammatical_info = {"value": "Noun"}
        entry1 = Entry(id_="entry1", lexical_unit={"en": "cat"})
        entry1.senses = [sense1]
        entry1.grammatical_info = {"value": "Noun"}

        sense2 = Sense(id_="sense_2", definitions={"en": "A dog"})
        sense2.grammatical_info = {"value": "Noun"}
        entry2 = Entry(id_="entry2", lexical_unit={"en": "dog"})
        entry2.senses = [sense2]
        entry2.grammatical_info = {"value": "Noun"}

        sense3 = Sense(id_="sense_3", definitions={"en": "To run"})
        sense3.grammatical_info = {"value": "Verb"}
        entry3 = Entry(id_="entry3", lexical_unit={"en": "run"})
        entry3.senses = [sense3]
        entry3.grammatical_info = {"value": "Verb"}

        mock_dict_service.search_entries.return_value = ([entry1, entry2, entry3], 3)

        response = client.get('/api/search/facets?q=a')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'facets' in data
        assert 'grammatical-info' in data['facets']
        assert data['facets']['grammatical-info']['Noun'] == 2
        assert data['facets']['grammatical-info']['Verb'] == 1

    def test_facets_empty_query(self, client):
        """Empty query should return empty facets."""
        response = client.get('/api/search/facets?q=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['facets'] == {}

    def test_facets_no_results(self, client, mock_dict_service):
        """No results should return empty facet groups."""
        mock_dict_service.search_entries.return_value = ([], 0)

        response = client.get('/api/search/facets?q=nonexistent')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['facets']['grammatical-info'] == {}
        assert data['facets']['semantic-domain'] == {}


@pytest.mark.unit
class TestExportEndpoint:
    """Test the /api/search/export endpoint."""

    def test_export_json_format(self, client, mock_dict_service):
        """Export as JSON should return JSON file."""
        entry = Entry(id_="entry1", lexical_unit={"en": "cat"})
        entry.grammatical_info = {"value": "Noun"}
        mock_dict_service.search_entries.return_value = ([entry], 1)

        response = client.get('/api/search/export?q=cat&format=json')
        assert response.status_code == 200
        assert response.mimetype == 'application/json'
        assert 'attachment; filename=search-results.json' in response.headers.get('Content-Disposition', '')

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_export_csv_format(self, client, mock_dict_service):
        """Export as CSV should return CSV file."""
        entry = Entry(id_="entry1", lexical_unit={"en": "cat"})
        entry.grammatical_info = {"value": "Noun"}
        mock_dict_service.search_entries.return_value = ([entry], 1)

        response = client.get('/api/search/export?q=cat&format=csv')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert 'attachment; filename=search-results.csv' in response.headers.get('Content-Disposition', '')

    def test_export_invalid_format(self, client):
        """Invalid format should return 400."""
        response = client.get('/api/search/export?q=cat&format=pdf')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_export_empty_query(self, client):
        """Empty query should return 400."""
        response = client.get('/api/search/export?q=')
        assert response.status_code == 400


@pytest.mark.unit
class TestSaveLoadSearch:
    """Test save and load search functionality."""

    def test_save_search(self, client):
        """Saving a search should return success."""
        response = client.post('/api/search/save', json={
            'name': 'Test Search',
            'query': {'query': 'cat', 'pos': 'Noun'}
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['name'] == 'Test Search'
        assert 'search_id' in data

    def test_save_search_missing_name(self, client):
        """Saving without name should return 400."""
        response = client.post('/api/search/save', json={
            'query': {'query': 'cat'}
        })
        assert response.status_code == 400

    def test_save_search_missing_query(self, client):
        """Saving without query should return 400."""
        response = client.post('/api/search/save', json={
            'name': 'Test Search'
        })
        assert response.status_code == 400

    def test_get_saved_searches_empty(self, client):
        """Initially saved searches should be empty."""
        response = client.get('/api/search/saved')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'searches' in data
        assert len(data['searches']) == 0

    def test_save_and_retrieve_searches(self, client):
        """Saved searches should appear in the list."""
        client.post('/api/search/save', json={
            'name': 'Search 1',
            'query': {'query': 'cat', 'pos': 'Noun'}
        })
        client.post('/api/search/save', json={
            'name': 'Search 2',
            'query': {'query': 'dog', 'pos': ''}
        })

        response = client.get('/api/search/saved')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['searches']) == 2
        names = [s['name'] for s in data['searches']]
        assert 'Search 1' in names
        assert 'Search 2' in names


@pytest.mark.unit
class TestSemanticSearchEndpoint:
    """Test semantic vector search handling in /api/search/ endpoint."""

    @patch("app.api.search.get_dictionary_service")
    @patch("app.services.embedding_service.get_embedding_service")
    def test_semantic_search_invoked(self, mock_get_emb_svc, mock_get_dict_svc, client):
        """Passing use_semantic=1 should invoke EmbeddingService.semantic_search."""
        mock_emb_svc = Mock()
        mock_emb_svc.semantic_search.return_value = [
            {"entry_id": "entry1", "score": 0.95}
        ]
        mock_get_emb_svc.return_value = mock_emb_svc

        mock_dict_inst = Mock()
        entry1 = Entry(id_="entry1", lexical_unit={"en": "feline"})
        mock_dict_inst.get_entries_by_ids.return_value = [entry1]
        mock_get_dict_svc.return_value = mock_dict_inst

        response = client.get('/api/search/?q=cat&use_semantic=1')
        assert response.status_code == 200
        data = json.loads(response.data)

        assert data.get("is_semantic") is True
        assert len(data.get("entries", [])) == 1
        assert data["entries"][0]["id"] == "entry1"
        mock_emb_svc.semantic_search.assert_called_once()
        mock_dict_inst.get_entries_by_ids.assert_called_once_with(["entry1"], project_id=None)
