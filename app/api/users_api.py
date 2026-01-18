"""
Users API blueprint for user profile and management.
"""

from flask import Blueprint, request, jsonify, g
from app.services.user_service import UserManagementService
from app.services.auth_service import AuthenticationService
from app.utils.auth_decorators import login_required, admin_required
from app.models.project_settings import User

users_api_bp = Blueprint("users_api", __name__, url_prefix="/api/users")


@users_api_bp.route("/", methods=["GET"])
@admin_required
def list_users():
    """
    List all users (admin only).
    ---
    tags:
      - Users
    parameters:
      - in: query
        name: active_only
        type: boolean
        default: true
        description: Only return active users
    responses:
      200:
        description: List of users
    """
    active_only = request.args.get("active_only", "true").lower() == "true"
    users = UserManagementService.list_users(active_only=active_only)

    return jsonify(
        {"users": [user.to_dict() for user in users], "count": len(users)}
    ), 200


@users_api_bp.route("/<int:user_id>", methods=["GET"])
@login_required
def get_user(user_id):
    """
    Get user profile.
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: User profile
      404:
        description: User not found
    """
    user = UserManagementService.get_user_by_id(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Include private info if viewing own profile or admin
    include_private = g.current_user.id == user_id or g.current_user.is_admin

    return jsonify({"user": user.to_dict(include_private=include_private)}), 200


@users_api_bp.route("/<int:user_id>", methods=["PUT"])
@login_required
def update_user(user_id):
    """
    Update user profile.
    ---
    tags:
      - Users
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
            first_name:
              type: string
            last_name:
              type: string
            bio:
              type: string
            avatar_url:
              type: string
    responses:
      200:
        description: User updated
      403:
        description: Not authorized
      404:
        description: User not found
    """
    # Only allow users to update their own profile (or admin)
    if g.current_user.id != user_id and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized to update this user"}), 403

    user = UserManagementService.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    success, error = AuthenticationService.update_user_profile(
        user=user,
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        bio=data.get("bio"),
        avatar_url=data.get("avatar_url"),
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify(
        {
            "message": "User updated successfully",
            "user": user.to_dict(include_private=True),
        }
    ), 200


@users_api_bp.route("/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_user(user_id):
    """
    Deactivate a user account (admin only).
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: User deactivated
      404:
        description: User not found
    """
    success, error = UserManagementService.deactivate_user(user_id, g.current_user.id)

    if error:
        return jsonify({"error": error}), 404

    return jsonify({"message": "User deactivated successfully"}), 200


@users_api_bp.route("/<int:user_id>/reactivate", methods=["POST"])
@admin_required
def reactivate_user(user_id):
    """
    Reactivate a user account (admin only).
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: User reactivated
      404:
        description: User not found
    """
    success, error = UserManagementService.reactivate_user(user_id, g.current_user.id)

    if error:
        return jsonify({"error": error}), 404

    return jsonify({"message": "User reactivated successfully"}), 200


@users_api_bp.route("/<int:user_id>/projects", methods=["GET"])
@login_required
def get_user_projects(user_id):
    """
    Get all projects a user has access to.
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: List of projects
      403:
        description: Not authorized
    """
    # Only allow users to view their own projects (or admin)
    if g.current_user.id != user_id and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    projects = UserManagementService.get_user_projects(user_id)

    return jsonify({"projects": projects, "count": len(projects)}), 200


@users_api_bp.route("/search", methods=["GET"])
@login_required
def search_users():
    """
    Search users by username or email.
    ---
    tags:
      - Users
    parameters:
      - in: query
        name: q
        type: string
        required: true
        description: Search query
    responses:
      200:
        description: Search results
    """
    query = request.args.get("q", "").strip()

    if not query or len(query) < 2:
        return jsonify({"error": "Query must be at least 2 characters"}), 400

    # Search by username or email
    users = (
        User.query.filter(
            (User.username.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%"))
        )
        .filter_by(is_active=True)
        .limit(20)
        .all()
    )

    return jsonify(
        {"users": [user.to_dict() for user in users], "count": len(users)}
    ), 200
