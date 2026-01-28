"""
User Preferences API blueprint for managing user-specific settings like field visibility.
"""

from flask import Blueprint, request, jsonify, g
from app.services.user_preferences_service import UserPreferencesService
from app.services.user_service import UserManagementService
from app.utils.auth_decorators import login_required, admin_required
from app.models.project_settings import User, ProjectSettings

user_preferences_bp = Blueprint("user_preferences", __name__, url_prefix="/api/users")


@user_preferences_bp.route("/<int:user_id>/preferences/field-visibility", methods=["GET"])
@login_required
def get_field_visibility(user_id):
    """
    Get field visibility settings for a user.

    Returns user's saved preferences, or project defaults if user has no saved settings.

    ---
    tags:
      - User Preferences
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: query
        name: project_id
        type: integer
        description: Project ID for getting project defaults
    responses:
      200:
        description: Field visibility settings
      401:
        description: Not authenticated
      403:
        description: Not authorized to view this user's preferences
      404:
        description: User not found
    """
    # Only allow users to view their own preferences (or admin)
    if g.current_user.id != user_id and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized to view these preferences"}), 403

    user = UserManagementService.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    project_id = request.args.get("project_id", type=int)

    settings = UserPreferencesService.get_field_visibility(user_id, project_id)

    return jsonify({
        "fieldVisibility": settings
    }), 200


@user_preferences_bp.route("/<int:user_id>/preferences/field-visibility", methods=["PUT"])
@login_required
def save_field_visibility(user_id):
    """
    Save field visibility settings for a user.

    ---
    tags:
      - User Preferences
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            project_id:
              type: integer
              description: Project context for the settings
            sections:
              type: object
              description: Section visibility settings
            fields:
              type: object
              description: Field visibility settings per section
    responses:
      200:
        description: Settings saved successfully
      400:
        description: Invalid data provided
      401:
        description: Not authenticated
      403:
        description: Not authorized to modify this user's preferences
      404:
        description: User not found
    """
    # Only allow users to modify their own preferences (or admin)
    if g.current_user.id != user_id and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized to modify these preferences"}), 403

    user = UserManagementService.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    if "sections" not in data and "fields" not in data:
        return jsonify({"error": "Must provide 'sections' or 'fields' settings"}), 400

    project_id = data.get("project_id")

    success, error = UserPreferencesService.save_field_visibility(
        user_id=user_id,
        project_id=project_id,
        settings={
            "sections": data.get("sections"),
            "fields": data.get("fields")
        }
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Settings saved successfully"}), 200


@user_preferences_bp.route("/<int:user_id>/preferences/field-visibility/reset", methods=["POST"])
@login_required
def reset_field_visibility(user_id):
    """
    Reset field visibility settings to project defaults (or hardcoded defaults).

    ---
    tags:
      - User Preferences
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            project_id:
              type: integer
              description: Project ID for project defaults (optional)
    responses:
      200:
        description: Settings reset successfully
      401:
        description: Not authenticated
      403:
        description: Not authorized
      404:
        description: User not found
    """
    # Only allow users to reset their own preferences (or admin)
    if g.current_user.id != user_id and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    user = UserManagementService.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    project_id = data.get("project_id")

    success, error = UserPreferencesService.reset_to_project_defaults(
        user_id=user_id,
        project_id=project_id
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Settings reset to defaults"}), 200


# Project-level defaults endpoints (admin only)

@user_preferences_bp.route("/<int:user_id>/preferences", methods=["GET"])
@login_required
def get_all_preferences(user_id):
    """
    Get all preferences for a user.

    ---
    tags:
      - User Preferences
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: All user preferences
      403:
        description: Not authorized
    """
    # Only allow users to view their own preferences (or admin)
    if g.current_user.id != user_id and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    user = UserManagementService.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "preferences": user.preferences or {}
    }), 200


@user_preferences_bp.route("/<int:user_id>/preferences", methods=["PUT"])
@login_required
def save_preferences(user_id):
    """
    Save all preferences for a user (merge with existing).

    ---
    tags:
      - User Preferences
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          description: Preferences to merge (partial update supported)
    responses:
      200:
        description: Preferences saved successfully
      403:
        description: Not authorized
    """
    # Only allow users to modify their own preferences (or admin)
    if g.current_user.id != user_id and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    user = UserManagementService.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Initialize preferences if not exists
    if user.preferences is None:
        user.preferences = {}

    # Merge new preferences
    user.preferences.update(data)
    db.session.commit()

    return jsonify({
        "message": "Preferences saved successfully",
        "preferences": user.preferences
    }), 200


# Project defaults endpoints (separate blueprint for better routing)

project_defaults_bp = Blueprint("project_defaults", __name__, url_prefix="/api/projects")


@project_defaults_bp.route("/<int:project_id>/field-visibility/defaults", methods=["GET"])
@login_required
def get_project_defaults(project_id):
    """
    Get field visibility defaults for a project (admin or project member).

    ---
    tags:
      - Project Settings
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
    responses:
      200:
        description: Project field visibility defaults
      404:
        description: Project not found
    """
    # Check if user has access to project
    has_access = UserManagementService.has_project_access(g.current_user.id, project_id)
    if not has_access and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized to view this project"}), 403

    defaults = UserPreferencesService.get_project_defaults(project_id)

    return jsonify({
        "fieldVisibilityDefaults": defaults
    }), 200


@project_defaults_bp.route("/<int:project_id>/field-visibility/defaults", methods=["PUT"])
@admin_required
def save_project_defaults(project_id):
    """
    Save field visibility defaults for a project (admin only).

    ---
    tags:
      - Project Settings
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            sections:
              type: object
              description: Section visibility defaults
            fields:
              type: object
              description: Field visibility defaults per section
    responses:
      200:
        description: Project defaults saved successfully
      400:
        description: Invalid data provided
      404:
        description: Project not found
    """
    project = ProjectSettings.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    if "sections" not in data and "fields" not in data:
        return jsonify({"error": "Must provide 'sections' or 'fields' defaults"}), 400

    success, error = UserPreferencesService.save_project_defaults(
        project_id=project_id,
        settings={
            "sections": data.get("sections"),
            "fields": data.get("fields")
        },
        admin_user_id=g.current_user.id
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Project defaults saved successfully"}), 200


@project_defaults_bp.route("/<int:project_id>/field-visibility/defaults", methods=["DELETE"])
@admin_required
def clear_project_defaults(project_id):
    """
    Clear field visibility defaults for a project (admin only).

    This will cause users to fall back to hardcoded defaults.

    ---
    tags:
      - Project Settings
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
    responses:
      200:
        description: Project defaults cleared successfully
      404:
        description: Project not found
    """
    project = ProjectSettings.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    project.field_visibility_defaults = None
    db.session.commit()

    return jsonify({"message": "Project defaults cleared"}), 200


# Import db for commit in save_preferences
from app.models.workset_models import db
