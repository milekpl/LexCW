"""
Integration tests for pronunciation API endpoints (compress, deduplicate, deduplicate/apply).

Uses the Flask test client with mocked database fixtures from conftest.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.fixture
def authed_client(app, client):
    """Create an authenticated test client with a session user."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "testuser"
    with patch("app.utils.auth_decorators.get_current_user") as mock_user:
        mock_user.return_value = MagicMock(id=1, is_admin=True, username="testuser")
        yield client


class TestCompressEndpoint:
    """Tests for POST /api/pronunciation/compress."""

    def test_compress_simple(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/compress",
            json={"entries": [{"lexeme": "scottishism", "ipa": "ˈskɒtɪˌsɪz(ə)m"}]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["lexeme"] == "scottishism"
        assert set(result["variants"]) == {"ˈskɒtɪˌsɪzm", "ˈskɒtɪˌsɪzəm"}

    def test_compress_multiple(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/compress",
            json={
                "entries": [
                    {"lexeme": "lactation", "ipa": "(ˌ)lækˈteɪʃ(ə)n"},
                    {"lexeme": "scottishism", "ipa": "ˈskɒtɪˌsɪz(ə)m"},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) == 2

    def test_compress_no_entries_field(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/compress", json={"not_entries": []}
        )
        assert resp.status_code == 400
        assert "entries" in resp.get_json()["error"]

    def test_compress_empty_ipa(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/compress",
            json={"entries": [{"lexeme": "test", "ipa": ""}]},
        )
        assert resp.status_code == 200
        assert resp.get_json()["results"][0]["variants"] == []

    def test_compress_no_parentheses(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/compress",
            json={"entries": [{"lexeme": "tree", "ipa": "triː"}]},
        )
        assert resp.status_code == 200
        assert resp.get_json()["results"][0]["variants"] == ["triː"]


class TestDeduplicateEndpoint:
    """Tests for POST /api/pronunciation/deduplicate."""

    def test_no_duplicates(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate",
            json={
                "entries": [
                    {"lexeme": "cat", "ipa": "kæt"},
                    {"lexeme": "dog", "ipa": "dɒɡ"},
                ]
            },
        )
        assert resp.status_code == 200
        assert len(resp.get_json()["duplicates"]) == 0

    def test_detects_exact_duplicates(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate",
            json={
                "entries": [
                    {"lexeme": "record", "ipa": "ˈrekɔːd"},
                    {"lexeme": "record", "ipa": "ˈrekɔːd"},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["duplicates"]) >= 1
        assert data["duplicates"][0]["type"] == "exact"

    def test_detects_stress_variants(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate",
            json={
                "entries": [
                    {"lexeme": "record", "ipa": "ˈrekɔːd"},
                    {"lexeme": "record", "ipa": "ˌrekɔːd"},
                ]
            },
        )
        assert resp.status_code == 200
        types = {d["type"] for d in resp.get_json()["duplicates"]}
        assert "stress_variant" in types

    def test_detects_optional_sound_equivalents(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate",
            json={
                "entries": [
                    {"lexeme": "lactation", "ipa": "(ˌ)lækˈteɪʃ(ə)n"},
                    {"lexeme": "lactation", "ipa": "lækˈteɪʃən"},
                ]
            },
        )
        assert resp.status_code == 200
        assert len(resp.get_json()["duplicates"]) >= 1

    def test_missing_entries_field(self, authed_client):
        resp = authed_client.post("/api/pronunciation/deduplicate", json={})
        assert resp.status_code == 400

    def test_stats_in_response(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate",
            json={"entries": [{"lexeme": "test", "ipa": "test"}]},
        )
        assert resp.status_code == 200
        assert "stats" in resp.get_json()
        assert resp.get_json()["stats"]["total_entries"] == 1


class TestDeduplicateApplyEndpoint:
    """Tests for POST /api/pronunciation/deduplicate/apply."""

    def test_apply_valid_actions(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate/apply",
            json={
                "actions": [
                    {"type": "remove", "entry_id": "entry_1", "ipa": "ˈrekɔːd"},
                    {
                        "type": "merge_to_compressed",
                        "entry_id": "entry_2",
                        "ipa": "ˈskɒtɪˌsɪz(ə)m",
                    },
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["applied"] == 2
        assert len(resp.get_json()["errors"]) == 0

    def test_apply_missing_entry_id(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate/apply",
            json={"actions": [{"type": "remove", "ipa": "ˈrekɔːd"}]},
        )
        assert resp.status_code == 200
        assert resp.get_json()["applied"] == 0
        assert len(resp.get_json()["errors"]) == 1

    def test_apply_unknown_action_type(self, authed_client):
        resp = authed_client.post(
            "/api/pronunciation/deduplicate/apply",
            json={
                "actions": [
                    {
                        "type": "nonexistent_action",
                        "entry_id": "entry_1",
                        "ipa": "triː",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["applied"] == 0
        assert len(resp.get_json()["errors"]) == 1

    def test_apply_no_actions_field(self, authed_client):
        resp = authed_client.post("/api/pronunciation/deduplicate/apply", json={})
        assert resp.status_code == 400


class TestApiKeyEndpoints:
    """Tests for API key CRUD endpoints — these test auth rejection."""

    def test_list_keys_requires_auth(self, client):
        resp = client.get("/api/keys/")
        assert resp.status_code in (401, 302)

    def test_create_key_requires_auth(self, client):
        resp = client.post("/api/keys/", json={"project_id": 1, "label": "test key"})
        assert resp.status_code in (401, 302)

    def test_revoke_key_requires_auth(self, client):
        resp = client.delete("/api/keys/1")
        assert resp.status_code in (401, 302)
