"""
Unit tests for pos_api endpoints.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient


def test_pos_tag_text_endpoint(client: FlaskClient) -> None:
    response = client.post("/api/pos/tag-text", json={"text": "the quick red fox jumps", "lang": "en"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "tokens" in data
    assert data["count"] > 0


def test_pos_tag_entry_endpoint(client: FlaskClient) -> None:
    entry = {"id": "test-1", "headword": "walk", "senses": [{"definition": "to move on foot"}]}
    response = client.post("/api/pos/tag-entry", json={"entry": entry})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["prediction"]["predicted_pos"] == "Verb"


def test_pos_batch_tag_endpoint(client: FlaskClient) -> None:
    entries = [
        {"id": "e1", "headword": "walk", "senses": [{"definition": "to move on foot"}]},
        {"id": "e2", "headword": "happiness"},
    ]
    response = client.post("/api/pos/batch-tag", json={"entries": entries})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["results"]) == 2


def test_pos_apply_tags_proposal_mode(client: FlaskClient) -> None:
    entries = [
        {"id": "e1", "headword": "walk", "senses": [{"definition": "to move on foot"}]},
    ]
    response = client.post(
        "/api/pos/apply-tags",
        json={"entries": entries, "mode": "proposal", "create_workset": True, "workset_name": "POS Test Workset"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["mode"] == "proposal"
    assert "workset_id" in data


def test_pos_get_mappings_endpoint(client: FlaskClient) -> None:
    response = client.get("/api/pos/mappings?lang=en")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "mappings" in data
    assert data["mappings"].get("NN") == "Noun"


def test_pos_save_mappings_endpoint(client: FlaskClient) -> None:
    response = client.put(
        "/api/pos/mappings",
        json={"lang": "fr", "mappings": {"NC": "Noun", "V": "Verb"}},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["mappings"]["NC"] == "Noun"


def test_pos_validate_definition_coherence_endpoint(client: FlaskClient) -> None:
    response = client.post(
        "/api/pos/validate-definition-coherence",
        json={
            "definition": "a domesticated carnivorous mammal, to catch mice, very playful",
            "expected_pos": "Noun",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "analysis" in data
    assert len(data["analysis"]["segments"]) == 3


