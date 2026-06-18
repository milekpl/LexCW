"""
Integration tests for the AI API endpoints.

Tests the Flask endpoints end-to-end with a mocked LLM backend.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from app import create_app
from app.services.ai_service import AIService


@pytest.fixture
def app():
    """Create Flask app for testing with AI blueprint registered."""
    os.environ["FLASK_CONFIG"] = "testing"
    os.environ["TESTING"] = "true"
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def dummy_response():
    return json.dumps(
        {
            "issues": [
                {
                    "field": "lexical_unit",
                    "severity": "info",
                    "message": "Looks good.",
                    "suggestion": None,
                }
            ],
            "summary": "All clear.",
        }
    )


@pytest.fixture
def sample_entry_data():
    return {
        "lexical_unit": {"en": "test"},
        "grammatical_info": "Noun",
        "senses": [
            {"definitions": {"en": "A test entry"}, "grammatical_info": "Noun"}
        ],
    }


# ── Proofreading Endpoint ────────────────────────────────────────────────────

class TestProofreadEndpoint:
    def test_proofread_with_api_key_in_body(self, client, dummy_response, sample_entry_data):
        with patch.object(AIService, "_call_llm", return_value=dummy_response):
            resp = client.post(
                "/api/ai/proofread",
                data=json.dumps(
                    {
                        "entry_data": sample_entry_data,
                        "api_key": "sk-test-body",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "issues" in data
        assert data["summary"] == "All clear."

    def test_proofread_without_api_key_returns_402(self, client, sample_entry_data):
        # Clear env var so no fallback
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            resp = client.post(
                "/api/ai/proofread",
                data=json.dumps({"entry_data": sample_entry_data}),
                content_type="application/json",
            )
        assert resp.status_code == 402
        assert "API key" in resp.get_json()["error"]

    def test_proofread_without_entry_data_returns_400(self, client):
        resp = client.post(
            "/api/ai/proofread",
            data=json.dumps({"api_key": "sk-test"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "entry_data" in resp.get_json()["error"]

    def test_proofread_with_custom_template(self, client, dummy_response, sample_entry_data):
        # First save a template
        with patch.object(AIService, "_call_llm", return_value=dummy_response):
            client.post(
                "/api/ai/prompt-templates",
                data=json.dumps(
                    {
                        "id": "e2e-proofread",
                        "name": "E2E Proofread",
                        "type": "proofread",
                        "system_prompt": "Be e2e.",
                        "user_prompt_template": "Review: {entry_yaml}",
                    }
                ),
                content_type="application/json",
            )

            resp = client.post(
                "/api/ai/proofread",
                data=json.dumps(
                    {
                        "entry_data": sample_entry_data,
                        "api_key": "sk-test",
                        "prompt_template_id": "e2e-proofread",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_proofread_handles_llm_error(self, client, sample_entry_data):
        def raise_error(*args, **kwargs):
            from app.services.ai_service import AIAPIError
            raise AIAPIError("LLM unavailable")

        with patch.object(AIService, "_call_llm", side_effect=raise_error):
            resp = client.post(
                "/api/ai/proofread",
                data=json.dumps(
                    {"entry_data": sample_entry_data, "api_key": "sk-test"}
                ),
                content_type="application/json",
            )
        assert resp.status_code == 502


# ── Drafting Endpoint ────────────────────────────────────────────────────────

class TestDraftEndpoint:
    def test_draft_returns_entry(self, client):
        canned = json.dumps(
            {
                "entry_yaml": "lexical_unit:\n  en: test\nsenses: []\n",
                "notes": "Drafted.",
            }
        )
        with patch.object(AIService, "_call_llm", return_value=canned):
            resp = client.post(
                "/api/ai/draft",
                data=json.dumps(
                    {
                        "description": "a test word",
                        "api_key": "sk-test",
                        "source_lang": "en",
                        "target_langs": "pl",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "entry_yaml" in data
        assert "entry_data" in data
        assert "test" in data["entry_yaml"]

    def test_draft_without_description_returns_400(self, client):
        resp = client.post(
            "/api/ai/draft",
            data=json.dumps({"api_key": "sk-test"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "description" in resp.get_json()["error"]

    def test_draft_without_api_key_returns_402(self, client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            resp = client.post(
                "/api/ai/draft",
                data=json.dumps({"description": "test"}),
                content_type="application/json",
            )
        assert resp.status_code == 402

    def test_draft_defaults_template_when_not_specified(self, client):
        canned = json.dumps(
            {"entry_yaml": "lexical_unit:\n  en: word\n", "notes": ""}
        )
        with patch.object(AIService, "_call_llm", return_value=canned):
            resp = client.post(
                "/api/ai/draft",
                data=json.dumps(
                    {"description": "word", "api_key": "sk-test"}
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200


# ── Batch Proofreading Endpoint ──────────────────────────────────────────────

class TestBatchProofreadEndpoint:
    def test_batch_returns_results(self, client, sample_entry_data):
        canned = json.dumps({"issues": [], "summary": "ok"})
        with patch.object(AIService, "_call_llm", return_value=canned):
            resp = client.post(
                "/api/ai/batch-proofread",
                data=json.dumps(
                    {
                        "entries": [sample_entry_data, sample_entry_data],
                        "api_key": "sk-test",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert len(data["results"]) == 2

    def test_batch_empty_entries_returns_400(self, client):
        resp = client.post(
            "/api/ai/batch-proofread",
            data=json.dumps({"entries": [], "api_key": "sk-test"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── Prompt Template Endpoints ────────────────────────────────────────────────

class TestPromptTemplateEndpoints:
    def test_list_templates(self, client):
        resp = client.get("/api/ai/prompt-templates")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "templates" in data
        assert len(data["templates"]) >= 2

    def test_list_templates_filtered_by_type(self, client):
        resp = client.get("/api/ai/prompt-templates?type=proofread")
        assert resp.status_code == 200
        data = resp.get_json()
        for t in data["templates"]:
            assert t["type"] == "proofread"

    def test_save_and_delete_template(self, client):
        # Save
        resp = client.post(
            "/api/ai/prompt-templates",
            data=json.dumps(
                {
                    "id": "api-test-template",
                    "name": "API Test",
                    "type": "proofread",
                    "system_prompt": "Test system.",
                    "user_prompt_template": "Test: {entry_yaml}",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == "api-test-template"

        # Delete
        resp = client.delete("/api/ai/prompt-templates/api-test-template")
        assert resp.status_code == 200

        # Verify gone
        resp = client.delete("/api/ai/prompt-templates/api-test-template")
        assert resp.status_code == 404

    def test_save_template_missing_fields(self, client):
        resp = client.post(
            "/api/ai/prompt-templates",
            data=json.dumps({"id": "bad"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── Models Endpoint ──────────────────────────────────────────────────────────

class TestModelsEndpoint:
    def test_list_models(self, client):
        resp = client.get("/api/ai/models")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "models" in data
        assert len(data["models"]) >= 1


# ── Test Connection Endpoint ─────────────────────────────────────────────────

class TestConnectionEndpoint:
    def test_test_connection_success(self, client):
        with patch.object(AIService, "_call_llm", return_value="OK"):
            resp = client.post(
                "/api/ai/test-connection",
                data=json.dumps(
                    {"api_key": "sk-test", "model": "gpt-4o"}
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_test_connection_no_key(self, client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            resp = client.post(
                "/api/ai/test-connection",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 402

    def test_test_connection_api_error(self, client):
        def raise_error(*args, **kwargs):
            from app.services.ai_service import AIAPIError
            raise AIAPIError("Bad gateway")

        with patch.object(AIService, "_call_llm", side_effect=raise_error):
            resp = client.post(
                "/api/ai/test-connection",
                data=json.dumps({"api_key": "sk-test"}),
                content_type="application/json",
            )
        # AIAPIError renders as 502 in the proofread/draft endpoints, but
        # the test-connection endpoint catches it as a generic Exception → 500
        assert resp.status_code in (500, 502)
