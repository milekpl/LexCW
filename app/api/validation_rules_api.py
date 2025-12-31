"""
Validation Rules API.

REST API endpoints for managing project-specific validation rules.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app, send_file
from werkzeug.security import safe_join

from app.services.validation_rules_service import get_validation_rules_service, ValidationRulesService

logger = logging.getLogger(__name__)

validation_rules_bp = Blueprint(
    "validation_rules",
    __name__,
    url_prefix="/api/projects"
)


def get_service():
    """Get the validation rules service from Flask app context."""
    from flask import current_app
    try:
        # Try to get from app context first (most reliable in API requests)
        if hasattr(current_app, 'validation_rules_service'):
            return current_app.validation_rules_service
        # Try to get from injector
        if hasattr(current_app, 'injector'):
            return current_app.injector.get(ValidationRulesService)
    except (AttributeError, RuntimeError):
        pass
    # Fallback to singleton if app context not available
    return get_validation_rules_service()


@validation_rules_bp.route("/<project_id>/validation-rules", methods=["GET"])
def get_project_validation_rules(project_id: str):
    """
    Get validation rules for a project.

    Returns the project-specific rules if they exist,
    otherwise returns the default rules.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: project_id
        in: path
        type: string
        required: true
        description: Project identifier
      - name: include_defaults
        in: query
        type: boolean
        default: false
        description: Include default rules if project has no custom rules
    responses:
      200:
        description: List of validation rules
    """
    try:
        service = get_service()
        include_defaults = request.args.get('include_defaults', 'false').lower() == 'true'

        rules = service.get_project_rules(project_id)

        # If no project-specific rules, fall back to defaults
        use_defaults = len(rules) == 0 and include_defaults
        if use_defaults:
            rules = service.get_default_rules()
            return jsonify({
                "rules": rules,
                "source": "defaults",
                "count": len(rules)
            })

        return jsonify({
            "rules": rules,
            "source": "project",
            "count": len(rules)
        })

    except Exception as e:
        logger.error(f"Error getting validation rules for project {project_id}: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/<project_id>/validation-rules", methods=["PUT"])
def update_project_validation_rules(project_id: str):
    """
    Update validation rules for a project.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: project_id
        in: path
        type: string
        required: true
        description: Project identifier
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              rules:
                type: array
                items:
                  type: object
    responses:
      200:
        description: Rules updated successfully
      400:
        description: Invalid request or validation errors
    """
    try:
        data = request.get_json()

        if not data or 'rules' not in data:
            return jsonify({"error": "Request body with 'rules' array is required"}), 400

        rules = data['rules']
        created_by = data.get('created_by')

        service = get_service()
        result = service.save_project_rules(
            project_id=project_id,
            rules=rules,
            created_by=created_by
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error updating validation rules for project {project_id}: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/<project_id>/validation-rules", methods=["DELETE"])
def delete_project_validation_rules(project_id: str):
    """
    Delete all validation rules for a project.

    After deletion, the project will use default rules.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: project_id
        in: path
        type: string
        required: true
        description: Project identifier
    responses:
      200:
        description: Rules deleted successfully
    """
    try:
        service = get_service()
        count = service.delete_project_rules(project_id)

        return jsonify({
            "success": True,
            "message": f"Deleted {count} validation rules",
            "count": count
        })

    except Exception as e:
        logger.error(f"Error deleting validation rules for project {project_id}: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/<project_id>/validation-rules/export", methods=["GET"])
def export_project_validation_rules(project_id: str):
    """
    Export validation rules for a project as JSON file.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: project_id
        in: path
        type: string
        required: true
        description: Project identifier
    responses:
      200:
        description: JSON file download
      404:
        description: No rules to export
    """
    try:
        service = get_service()
        export_data = service.export_rules(project_id)

        if not export_data:
            return jsonify({"error": "No rules to export"}), 404

        # Convert to JSON and create response
        json_str = json.dumps(export_data, indent=2)

        from io import BytesIO
        buffer = BytesIO()
        buffer.write(json_str.encode('utf-8'))
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'validation_rules_{project_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )

    except Exception as e:
        logger.error(f"Error exporting validation rules for project {project_id}: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/<project_id>/validation-rules/import", methods=["POST"])
def import_project_validation_rules(project_id: str):
    """
    Import validation rules for a project from JSON file.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: project_id
        in: path
        type: string
        required: true
        description: Project identifier
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              rules:
                type: array
              replace:
                type: boolean
                default: false
    responses:
      200:
        description: Rules imported successfully
      400:
        description: Invalid import data
    """
    try:
        data = request.get_json()

        if not data or 'rules' not in data:
            return jsonify({"error": "Request body with 'rules' array is required"}), 400

        replace = data.get('replace', False)
        created_by = data.get('created_by')

        service = get_service()
        result = service.import_rules(
            project_id=project_id,
            import_data=data,
            replace=replace,
            created_by=created_by
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error importing validation rules for project {project_id}: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/<project_id>/validation-rules/initialize", methods=["POST"])
def initialize_project_validation_rules(project_id: str):
    """
    Initialize validation rules for a new project.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: project_id
        in: path
        type: string
        required: true
        description: Project identifier
    requestBody:
      required: false
      content:
        application/json:
          schema:
            type: object
            properties:
              template_id:
                type: string
                description: Template to use (optional)
    responses:
      200:
        description: Rules initialized successfully
      400:
        description: Project already has rules
    """
    try:
        data = request.get_json() or {}
        template_id = data.get('template_id')
        created_by = data.get('created_by')

        service = get_service()
        result = service.initialize_project_rules(
            project_id=project_id,
            template_id=template_id,
            created_by=created_by
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error initializing validation rules for project {project_id}: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/validation-rule-templates", methods=["GET"])
def get_validation_rule_templates():
    """
    Get available validation rule templates.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: category
        in: query
        type: string
        description: Filter by category
    responses:
      200:
        description: List of templates
    """
    try:
        category = request.args.get('category')

        service = get_service()
        templates = service.get_templates(category)

        return jsonify({
            "templates": templates,
            "count": len(templates)
        })

    except Exception as e:
        logger.error(f"Error getting validation rule templates: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/validation-rule-templates/<template_id>", methods=["GET"])
def get_validation_rule_template(template_id: str):
    """
    Get a specific validation rule template.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: template_id
        in: path
        type: string
        required: true
        description: Template identifier
    responses:
      200:
        description: Template details
      404:
        description: Template not found
    """
    try:
        service = get_service()
        template = service.get_template(template_id)

        if template:
            return jsonify(template)
        else:
            return jsonify({"error": f"Template not found: {template_id}"}), 404

    except Exception as e:
        logger.error(f"Error getting validation rule template {template_id}: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/validation-rules/test", methods=["POST"])
def test_validation_rule():
    """
    Test a validation rule against sample data.

    ---
    tags:
      - Validation Rules
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              rule:
                type: object
                description: Rule configuration to test
              test_data:
                type: object
                description: Sample data to validate against
    responses:
      200:
        description: Test result
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        rule_config = data.get('rule')
        test_data = data.get('test_data')

        if not rule_config:
            return jsonify({"error": "Rule configuration is required"}), 400
        if not test_data:
            return jsonify({"error": "Test data is required"}), 400

        service = get_service()
        result = service.test_rule(rule_config, test_data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error testing validation rule: {e}")
        return jsonify({"error": str(e)}), 500


@validation_rules_bp.route("/<project_id>/validation-rules/effective", methods=["GET"])
def get_effective_validation_rules(project_id: str):
    """
    Get effective validation rules for a project.

    Returns project rules if they exist, otherwise returns default rules.

    ---
    tags:
      - Validation Rules
    parameters:
      - name: project_id
        in: path
        type: string
        required: true
        description: Project identifier
    responses:
      200:
        description: List of effective validation rules
    """
    try:
        service = get_service()
        rules = service.get_effective_rules(project_id)

        return jsonify({
            "rules": rules,
            "count": len(rules)
        })

    except Exception as e:
        logger.error(f"Error getting effective validation rules for project {project_id}: {e}")
        return jsonify({"error": str(e)}), 500
