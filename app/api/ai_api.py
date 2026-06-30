"""
API endpoints for AI-powered dictionary operations.

Provides proofreading, entry drafting, prompt template management,
and batch AI operations.
"""

import logging
from typing import Any
from flask import Blueprint, request, jsonify, current_app, g

from app.services.ai_service import (
    AIService,
    AIServiceError,
    AIConfigurationError,
    AIAPIError,
)

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")
logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """Resolve API key: request body > project settings (by project_id, then first project) > env var."""
    data = request.get_json(silent=True) or {}
    if data.get("api_key"):
        return data["api_key"]

    # Try project settings by project_id in session/request context
    try:
        from app.models.project_settings import ProjectSettings
        import os
        from flask import session
        project_id = g.get("project_id") or session.get("project_id") or os.environ.get("PROJECT_ID")
        if project_id:
            settings = ProjectSettings.query.get(int(project_id))
            if settings and settings.openai_api_key:
                return settings.openai_api_key
    except Exception as e:
        logger.debug(f"Caught exception: {e}")

    # Fallback: try the first (default) project
    try:
        from app.models.project_settings import ProjectSettings
        settings = ProjectSettings.query.first()
        if settings and settings.openai_api_key:
            return settings.openai_api_key
    except Exception as e:
        logger.debug(f"Caught exception: {e}")

    # Last resort: env var
    return os.environ.get("OPENAI_API_KEY", "")


def _get_model(data: dict) -> str:
    """Resolve model: request body > project settings > default."""
    if data.get("model"):
        return data["model"]

    try:
        from app.models.project_settings import ProjectSettings
        import os
        from flask import session
        project_id = g.get("project_id") or session.get("project_id") or os.environ.get("PROJECT_ID")
        if project_id:
            settings = ProjectSettings.query.get(int(project_id))
            if settings and settings.ai_model:
                return settings.ai_model
    except Exception as e:
        logger.debug(f"Caught exception: {e}")

    try:
        from app.models.project_settings import ProjectSettings
        settings = ProjectSettings.query.first()
        if settings and settings.ai_model:
            return settings.ai_model
    except Exception as e:
        logger.debug(f"Caught exception: {e}")

    return os.environ.get("LLM_MODEL") or "gpt-4o"


def _get_api_base() -> str:
    """Resolve API base URL: project settings > default."""
    try:
        from app.models.project_settings import ProjectSettings
        import os
        from flask import session
        project_id = g.get("project_id") or session.get("project_id") or os.environ.get("PROJECT_ID")
        if project_id:
            settings = ProjectSettings.query.get(int(project_id))
            if settings and settings.ai_api_base:
                return settings.ai_api_base
    except Exception as e:
        logger.debug(f"Caught exception: {e}")

    try:
        from app.models.project_settings import ProjectSettings
        settings = ProjectSettings.query.first()
        if settings and settings.ai_api_base:
            return settings.ai_api_base
    except Exception as e:
        logger.debug(f"Caught exception: {e}")

    return os.environ.get("AI_API_BASE") or "https://api.openai.com/v1"


def _get_service() -> AIService:
    """Get AIService instance from app context."""
    try:
        return current_app.injector.get(AIService)
    except Exception:
        return AIService()


# ── Proofreading ────────────────────────────────────────────────────────────

@ai_bp.route("/proofread", methods=["POST"])
def proofread_entry():
    """Proofread a single entry.
    ---
    tags: [AI]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [entry_data]
            properties:
              entry_data: {type: object}
              prompt_template_id: {type: string}
              api_key: {type: string}
              model: {type: string}
    responses:
      200: {description: Proofreading results with issues array}
      400: {description: Missing entry_data}
      402: {description: API key required}
      500: {description: AI API error}
    """
    try:
        data = request.get_json(silent=True) or {}
        entry_data = data.get("entry_data")
        if not entry_data:
            return jsonify({"error": "entry_data is required"}), 400

        api_key = _get_api_key()
        if not api_key:
            return jsonify({"error": "API key is required. Set it in project settings or pass it in the request."}), 402

        model = _get_model(data)
        api_base = _get_api_base()
        template_id = data.get("prompt_template_id") or "proofreading-default"
        service = _get_service()

        result = service.proofread_entry(
            entry_data=entry_data,
            api_key=api_key,
            model=model,
            api_base=api_base,
            prompt_template_id=template_id,
        )
        return jsonify(result)

    except AIConfigurationError as e:
        return jsonify({"error": str(e)}), 402
    except AIAPIError as e:
        logger.error("AI API error: %s", e)
        return jsonify({"error": str(e)}), 502
    except AIServiceError as e:
        logger.error("AI service error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── Drafting ────────────────────────────────────────────────────────────────

@ai_bp.route("/draft", methods=["POST"])
def draft_entry():
    """Draft a new entry from a description.
    ---
    tags: [AI]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [description]
            properties:
              description: {type: string, description: "Word/phrase to draft an entry for"}
              source_lang: {type: string, default: "en"}
              target_langs: {type: string, default: "en"}
              prompt_template_id: {type: string}
              api_key: {type: string}
              model: {type: string}
    responses:
      200: {description: Drafted entry in YAML and parsed dict}
      400: {description: Missing description}
      402: {description: API key required}
    """
    try:
        data = request.get_json(silent=True) or {}
        description = data.get("description")
        if not description:
            return jsonify({"error": "description is required"}), 400

        api_key = _get_api_key()
        if not api_key:
            return jsonify({"error": "API key is required."}), 402

        model = _get_model(data)
        api_base = _get_api_base()
        template_id = data.get("prompt_template_id") or "drafting-default"
        source_lang = data.get("source_lang", "en")
        target_langs = data.get("target_langs", "en")
        service = _get_service()

        result = service.draft_entry(
            description=description,
            source_lang=source_lang,
            target_langs=target_langs,
            api_key=api_key,
            model=model,
            api_base=api_base,
            prompt_template_id=template_id,
        )
        return jsonify(result)

    except AIConfigurationError as e:
        return jsonify({"error": str(e)}), 402
    except AIAPIError as e:
        logger.error("AI API error: %s", e)
        return jsonify({"error": str(e)}), 502
    except AIServiceError as e:
        logger.error("AI service error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── Batch Proofreading ──────────────────────────────────────────────────────

@ai_bp.route("/batch-proofread", methods=["POST"])
def batch_proofread():
    """Proofread multiple entries in batch.
    ---
    tags: [AI]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [entries]
            properties:
              entries: {type: array, items: {type: object}}
              prompt_template_id: {type: string}
              api_key: {type: string}
              model: {type: string}
    responses:
      200: {description: Batch results per entry}
      400: {description: Missing entries}
    """
    try:
        data = request.get_json(silent=True) or {}
        entries = data.get("entries", [])
        if not entries:
            return jsonify({"error": "entries array is required"}), 400

        api_key = _get_api_key()
        if not api_key:
            return jsonify({"error": "API key is required."}), 402

        model = _get_model(data)
        api_base = _get_api_base()
        template_id = data.get("prompt_template_id") or "proofreading-default"
        service = _get_service()

        results = service.batch_proofread(
            entries=entries,
            api_key=api_key,
            model=model,
            api_base=api_base,
            prompt_template_id=template_id,
        )
        return jsonify({"results": results})

    except AIServiceError as e:
        logger.error("Batch proofread error: %s", e)
        return jsonify({"error": str(e)}), 500


# ── Prompt Templates ────────────────────────────────────────────────────────

@ai_bp.route("/prompt-templates", methods=["GET"])
def list_prompt_templates():
    """List available prompt templates.
    ---
    tags: [AI]
    parameters:
      - name: type
        in: query
        schema: {type: string, enum: [proofread, draft]}
    responses:
      200: {description: List of prompt templates}
    """
    try:
        template_type = request.args.get("type")
        service = _get_service()
        templates = service.get_prompt_templates(template_type=template_type)
        return jsonify({"templates": templates})
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/prompt-templates", methods=["POST"])
def save_prompt_template():
    """Create or update a prompt template.
    ---
    tags: [AI]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [id, name, type, system_prompt, user_prompt_template]
            properties:
              id: {type: string}
              name: {type: string}
              type: {type: string, enum: [proofread, draft]}
              system_prompt: {type: string}
              user_prompt_template: {type: string}
              description: {type: string}
    responses:
      200: {description: Template saved}
      400: {description: Missing required fields}
    """
    try:
        data = request.get_json(silent=True) or {}
        required = ["id", "name", "type", "system_prompt", "user_prompt_template"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"'{field}' is required"}), 400

        service = _get_service()
        template = service.save_prompt_template(data)
        return jsonify(template)

    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/prompt-templates/<string:template_id>", methods=["DELETE"])
def delete_prompt_template(template_id: str):
    """Delete a prompt template.
    ---
    tags: [AI]
    parameters:
      - name: template_id
        in: path
        required: true
        schema: {type: string}
    responses:
      200: {description: Deleted}
      404: {description: Not found}
    """
    try:
        service = _get_service()
        if service.delete_prompt_template(template_id):
            return jsonify({"deleted": template_id})
        return jsonify({"error": "Template not found"}), 404
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500


# ── Available Models ────────────────────────────────────────────────────────

@ai_bp.route("/models", methods=["GET"])
def list_models():
    """List available AI models.
    ---
    tags: [AI]
    responses:
      200: {description: List of available models}
    """
    return jsonify({"models": AIService.get_available_models()})


@ai_bp.route("/test-connection", methods=["POST"])
def test_connection():
    """Test the AI API connection with current settings.
    ---
    tags: [AI]
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              api_key: {type: string}
              api_base: {type: string}
              model: {type: string}
    responses:
      200: {description: Connection successful with model info}
      402: {description: API key required}
      502: {description: Connection failed}
    """
    try:
        data = request.get_json(silent=True) or {}
        api_key = data.get("api_key") or _get_api_key()
        if not api_key:
            return jsonify({"error": "API key is required"}), 402

        api_base = data.get("api_base") or _get_api_base()
        model = data.get("model") or _get_model(data)

        # Make a minimal test call
        result = AIService._call_llm(
            system_prompt="Reply with exactly: OK",
            user_prompt="Say OK",
            api_key=api_key,
            model=model,
            api_base=api_base,
            max_tokens=10,
            temperature=0,
            timeout=15,
        )

        return jsonify({
            "success": True,
            "model": model,
            "api_base": api_base,
            "response": result.strip()[:200],
        })

    except AIConfigurationError as e:
        return jsonify({"error": str(e)}), 402
    except AIAPIError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        logger.error("Test connection error: %s", e)
        return jsonify({"error": str(e)}), 500
