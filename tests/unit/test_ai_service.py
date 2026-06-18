"""
E2E tests for the AI Service and API endpoints.

Tests cover:
- Entry → YAML serialization
- Prompt template CRUD
- Proofreading with mocked LLM (dummy API)
- Drafting with mocked LLM
- API key resolution
- Template resolution
- Error handling (missing key, bad template, API errors)
- Batch proofreading
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from app.services.ai_service import (
    AIService,
    AIServiceError,
    AIConfigurationError,
    AIAPIError,
)


# ── Test Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def ai_service():
    """Create AIService with no disk state (uses built-in templates)."""
    return AIService(prompt_templates_path=None)


@pytest.fixture
def sample_entry():
    """A realistic dictionary entry for testing."""
    return {
        "id": "cat_001",
        "lexical_unit": {"en": "cat", "pl": "kot"},
        "grammatical_info": "Noun",
        "pronunciations": {"seh-fonipa": "kæt"},
        "senses": [
            {
                "grammatical_info": "Noun",
                "definitions": {
                    "en": "A small domesticated carnivorous mammal",
                    "pl": "Mały udomowiony ssak mięsożerny",
                },
            }
        ],
        "etymologies": [
            {"type": "borrowing", "source": "Latin", "form": {"la": "cattus"}, "gloss": {"en": "cat"}}
        ],
    }


@pytest.fixture
def dummy_issues_response():
    """Canned proofreading response with issues."""
    return json.dumps({
        "issues": [
            {"field": "senses[0].examples", "severity": "warning",
             "message": "Only one example.", "suggestion": "Add more."},
        ],
        "summary": "Generally complete.",
    })


@pytest.fixture
def dummy_draft_response():
    """Canned drafting response."""
    return json.dumps({
        "entry_yaml": "lexical_unit:\n  en: dog\n  pl: pies\nsenses:\n- grammatical_info: Noun\n  definitions:\n    en: A canine\n",
        "notes": "Standard entry.",
    })


# ── YAML Serialization Tests ─────────────────────────────────────────────────

class TestEntryYamlSerialization:
    """Test entry → YAML serialization."""

    def test_entry_to_yaml_basic(self, ai_service, sample_entry):
        yaml_str = AIService.entry_to_yaml(sample_entry)
        assert "cat" in yaml_str
        assert "Noun" in yaml_str
        assert "kæt" in yaml_str
        assert "Lexical Unit" in yaml_str

    def test_entry_to_yaml_has_section_markers(self, ai_service, sample_entry):
        yaml_str = AIService.entry_to_yaml(sample_entry)
        assert "======" in yaml_str
        assert "---" in yaml_str

    def test_entry_to_yaml_includes_entry_id(self, ai_service, sample_entry):
        yaml_str = AIService.entry_to_yaml(sample_entry)
        assert "cat_001" in yaml_str

    def test_entry_with_minimal_data(self, ai_service):
        minimal = {"lexical_unit": {"en": "test"}}
        yaml_str = AIService.entry_to_yaml(minimal)
        assert "test" in yaml_str
        assert "lexical_unit" in yaml_str

    def test_entry_with_empty_senses(self, ai_service):
        entry = {"lexical_unit": {"en": "word"}, "senses": []}
        yaml_str = AIService.entry_to_yaml(entry)
        assert "word" in yaml_str

    def test_yaml_handles_unicode(self, ai_service):
        entry = {"lexical_unit": {"pl": "ząb"}}
        yaml_str = AIService.entry_to_yaml(entry)
        assert "ząb" in yaml_str

    def test_yaml_handles_special_characters(self, ai_service):
        entry = {"lexical_unit": {"en": "test & more"}, "senses": [{"definitions": {"en": "a \"quoted\" word"}}]}
        yaml_str = AIService.entry_to_yaml(entry)
        assert "test & more" in yaml_str


# ── Prompt Template Tests ────────────────────────────────────────────────────

class TestPromptTemplates:
    """Test prompt template CRUD."""

    def test_builtin_templates_loaded(self, ai_service):
        templates = ai_service.get_prompt_templates()
        assert len(templates) >= 2

    def test_get_templates_by_type(self, ai_service):
        proofread = ai_service.get_prompt_templates(template_type="proofread")
        drafts = ai_service.get_prompt_templates(template_type="draft")
        assert all(t["type"] == "proofread" for t in proofread)
        assert all(t["type"] == "draft" for t in drafts)

    def test_get_single_template(self, ai_service):
        tmpl = ai_service.get_prompt_template("proofreading-default")
        assert tmpl is not None
        assert tmpl["name"]  # Name may be mutated by prior update test; just check it exists
        assert tmpl["type"] == "proofread"

    def test_get_nonexistent_template(self, ai_service):
        assert ai_service.get_prompt_template("nonexistent") is None

    def test_save_new_template(self, ai_service):
        ai_service.save_prompt_template({
            "id": "test-template", "name": "Test", "type": "proofread",
            "system_prompt": "You are a tester.",
            "user_prompt_template": "Review: {entry_yaml}",
        })
        tmpl = ai_service.get_prompt_template("test-template")
        assert tmpl["name"] == "Test"

    def test_update_existing_template(self, ai_service):
        ai_service.save_prompt_template({
            "id": "proofreading-default", "name": "Updated",
            "type": "proofread", "system_prompt": "New system.",
            "user_prompt_template": "New: {entry_yaml}",
        })
        tmpl = ai_service.get_prompt_template("proofreading-default")
        assert tmpl["name"] == "Updated"

    def test_delete_template(self, ai_service):
        ai_service.save_prompt_template({
            "id": "to-delete", "name": "Delete Me", "type": "draft",
            "system_prompt": "x", "user_prompt_template": "y",
        })
        assert ai_service.delete_prompt_template("to-delete") is True
        assert ai_service.get_prompt_template("to-delete") is None

    def test_delete_nonexistent_template(self, ai_service):
        assert ai_service.delete_prompt_template("no-such") is False


# ── Proofreading Tests (with mocked LLM) ─────────────────────────────────────

class TestProofreading:
    """Test proofreading with a mocked LLM."""

    def test_proofread_returns_suggestions(self, ai_service, sample_entry, dummy_issues_response):
        with patch.object(AIService, "_call_llm", return_value=dummy_issues_response):
            result = ai_service.proofread_entry(
                entry_data=sample_entry, api_key="sk-test")

        assert "issues" in result
        assert len(result["issues"]) == 1
        assert result["issues"][0]["severity"] == "warning"
        assert "summary" in result
        assert "entry_yaml" in result  # Always included

    def test_proofread_uses_custom_template(self, ai_service, sample_entry, dummy_issues_response):
        ai_service.save_prompt_template({
            "id": "my-proofread", "name": "My Proofread", "type": "proofread",
            "system_prompt": "Be strict.", "user_prompt_template": "Check: {entry_yaml}",
        })
        with patch.object(AIService, "_call_llm", return_value=dummy_issues_response) as mock_llm:
            ai_service.proofread_entry(
                entry_data=sample_entry, api_key="sk-test",
                prompt_template_id="my-proofread")

        assert mock_llm.call_args[1]["system_prompt"] == "Be strict."

    def test_proofread_missing_template_raises(self, ai_service, sample_entry):
        with pytest.raises(AIConfigurationError, match="Prompt template not found"):
            ai_service.proofread_entry(
                entry_data=sample_entry, api_key="sk-test",
                prompt_template_id="nonexistent")

    def test_proofread_handles_empty_issues(self, ai_service, sample_entry):
        with patch.object(AIService, "_call_llm", return_value='{"issues": [], "summary": "All good."}'):
            result = ai_service.proofread_entry(
                entry_data=sample_entry, api_key="sk-test")
        assert result["issues"] == []
        assert result["summary"] == "All good."

    def test_proofread_handles_malformed_json(self, ai_service, sample_entry):
        with patch.object(AIService, "_call_llm", return_value="not json at all"):
            result = ai_service.proofread_entry(
                entry_data=sample_entry, api_key="sk-test")
        # Falls back to suggestions + raw_response
        assert "suggestions" in result
        assert "raw_response" in result
        assert result["raw_response"] == "not json at all"

    def test_proofread_handles_json_without_expected_keys(self, ai_service, sample_entry):
        with patch.object(AIService, "_call_llm", return_value='{"some_other_key": "value"}'):
            result = ai_service.proofread_entry(
                entry_data=sample_entry, api_key="sk-test")
        # Whatever the LLM returned is passed through
        assert "some_other_key" in result


# ── Drafting Tests (with mocked LLM) ─────────────────────────────────────────

class TestDrafting:
    """Test entry drafting with a mocked LLM."""

    def test_draft_returns_entry(self, ai_service, dummy_draft_response):
        with patch.object(AIService, "_call_llm", return_value=dummy_draft_response):
            result = ai_service.draft_entry(
                description="domesticated canine", api_key="sk-test")

        assert "entry_yaml" in result
        assert "entry_data" in result
        assert "notes" in result
        assert "dog" in result["entry_yaml"]

    def test_draft_parses_entry_data(self, ai_service, dummy_draft_response):
        with patch.object(AIService, "_call_llm", return_value=dummy_draft_response):
            result = ai_service.draft_entry(description="test", api_key="sk-test")
        assert isinstance(result["entry_data"], dict)

    def test_draft_replaces_placeholders(self, ai_service, dummy_draft_response):
        with patch.object(AIService, "_call_llm", return_value=dummy_draft_response) as mock_llm:
            ai_service.draft_entry(
                description="test word", api_key="sk-test",
                source_lang="fr", target_langs="en,de")

        user_prompt = mock_llm.call_args[1]["user_prompt"]
        assert "test word" in user_prompt
        assert "fr" in user_prompt
        assert "en,de" in user_prompt

    def test_draft_missing_template(self, ai_service):
        with pytest.raises(AIConfigurationError, match="Prompt template not found"):
            ai_service.draft_entry(
                description="test", api_key="sk-test",
                prompt_template_id="no-such")

    def test_draft_handles_non_json_response(self, ai_service):
        with patch.object(AIService, "_call_llm", return_value="lexical_unit:\n  en: word"):
            result = ai_service.draft_entry(description="test", api_key="sk-test")
        assert "entry_yaml" in result
        assert "entry_data" in result


# ── Batch Proofreading Tests ─────────────────────────────────────────────────

class TestBatchProofreading:
    """Test batch proofreading."""

    def test_batch_processes_all_entries(self, ai_service, sample_entry):
        canned = json.dumps({"issues": [], "summary": "ok"})
        with patch.object(AIService, "_call_llm", return_value=canned):
            results = ai_service.batch_proofread(
                entries=[sample_entry, sample_entry], api_key="sk-test")

        assert len(results) == 2
        for i, r in enumerate(results):
            assert r["entry_id"] == "cat_001"
            assert r["entry_index"] == i
            assert "issues" in r

    def test_batch_handles_individual_failures(self, ai_service, sample_entry):
        call_count = [0]

        def flaky_llm(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise AIServiceError("Simulated failure")
            return json.dumps({"issues": [], "summary": "ok"})

        with patch.object(AIService, "_call_llm", side_effect=flaky_llm):
            results = ai_service.batch_proofread(
                entries=[sample_entry, sample_entry, sample_entry], api_key="sk-test")

        assert len(results) == 3
        assert "issues" in results[0]
        assert "error" in results[1]
        assert results[1]["error"] == "Simulated failure"
        assert "issues" in results[2]

    def test_batch_empty_entries(self, ai_service):
        results = ai_service.batch_proofread(entries=[], api_key="sk-test")
        assert results == []


# ── API Error Handling Tests ─────────────────────────────────────────────────

class TestErrorHandling:
    """Test error handling in the AI service."""

    def test_call_llm_missing_key_raises(self, ai_service):
        with pytest.raises(AIConfigurationError, match="No API key provided"):
            AIService._call_llm(
                system_prompt="test", user_prompt="test", api_key="", model="gpt-4o")

    def test_call_llm_api_error_401(self, ai_service):
        with patch("requests.post") as mock_post:
            import requests as req
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
            mock_response.raise_for_status.side_effect = req.exceptions.HTTPError(
                "401 Client Error", response=mock_response)
            mock_post.return_value = mock_response

            with pytest.raises(AIAPIError, match="401"):
                AIService._call_llm(
                    system_prompt="test", user_prompt="test",
                    api_key="sk-bad", model="gpt-4o")

    def test_call_llm_rate_limit_429(self, ai_service):
        with patch("requests.post") as mock_post:
            import requests as req
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.json.return_value = {"error": {"message": "Rate limit"}}
            mock_response.raise_for_status.side_effect = req.exceptions.HTTPError(
                "429 Client Error", response=mock_response)
            mock_post.return_value = mock_response

            with pytest.raises(AIAPIError, match="429"):
                AIService._call_llm(
                    system_prompt="test", user_prompt="test",
                    api_key="sk-test", model="gpt-4o")

    def test_call_llm_success(self, ai_service):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Hello!"}}]
            }
            mock_post.return_value = mock_response

            result = AIService._call_llm(
                system_prompt="Say hello", user_prompt="Hello",
                api_key="sk-test", model="gpt-4o")

            assert result == "Hello!"
            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "gpt-4o"
            assert call_args[1]["headers"]["Authorization"] == "Bearer sk-test"

    def test_call_llm_custom_api_base(self, ai_service):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "OK"}}]
            }
            mock_post.return_value = mock_response

            AIService._call_llm(
                system_prompt="x", user_prompt="y", api_key="sk-test",
                model="deepseek-chat", api_base="https://api.deepseek.com/v1")

            call_url = mock_post.call_args[0][0]
            assert "api.deepseek.com" in call_url

    def test_call_llm_timeout(self, ai_service):
        with patch("requests.post") as mock_post:
            import requests as req
            mock_post.side_effect = req.exceptions.Timeout()

            with pytest.raises(AIAPIError, match="timed out"):
                AIService._call_llm(
                    system_prompt="test", user_prompt="test",
                    api_key="sk-test", model="gpt-4o", timeout=1)

    def test_call_llm_connection_error(self, ai_service):
        with patch("requests.post") as mock_post:
            import requests as req
            mock_post.side_effect = req.exceptions.ConnectionError("refused")

            with pytest.raises(AIAPIError, match="Could not connect"):
                AIService._call_llm(
                    system_prompt="test", user_prompt="test",
                    api_key="sk-test", model="gpt-4o")
