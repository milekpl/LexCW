"""
Project Members API blueprint for managing user access to projects.
"""

from flask import Blueprint, request, jsonify, g
from app.services.user_service import UserManagementService
from app.models.user_models import UserRole
from app.utils.auth_decorators import (
    login_required,
    project_access_required,
    role_required,
)

project_members_api_bp = Blueprint(
    "project_members_api", __name__, url_prefix="/api/projects"
)


@project_members_api_bp.route("/<int:project_id>/members", methods=["GET"])
@project_access_required
def get_project_members(project_id):
    """
    Get all members of a project.
    ---
    tags:
      - Project Members
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
    responses:
      200:
        description: List of project members
    """
    members = UserManagementService.get_project_members(project_id)

    return jsonify({"members": members, "count": len(members)}), 200


@project_members_api_bp.route("/<int:project_id>/members", methods=["POST"])
@role_required(UserRole.ADMIN)
def add_project_member(project_id):
    """
    Add a user to a project (requires admin role).
    ---
    tags:
      - Project Members
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - role
          properties:
            user_id:
              type: integer
            role:
              type: string
              enum: [admin, member, viewer]
    responses:
      201:
        description: Member added
      400:
        description: Validation error
      403:
        description: Not authorized
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    user_id = data.get("user_id")
    role_str = data.get("role", "member").lower()

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # Parse role
    try:
        role = UserRole[role_str.upper()]
    except KeyError:
        return jsonify(
            {"error": f"Invalid role: {role_str}. Must be admin, member, or viewer"}
        ), 400

    success, error = UserManagementService.add_user_to_project(
        user_id=user_id,
        project_id=project_id,
        role=role,
        granted_by_user_id=g.current_user.id,
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "User added to project successfully"}), 201


@project_members_api_bp.route(
    "/<int:project_id>/members/<int:user_id>", methods=["PUT"]
)
@role_required(UserRole.ADMIN)
def update_project_member_role(project_id, user_id):
    """
    Update a user's role in a project (requires admin role).
    ---
    tags:
      - Project Members
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - role
          properties:
            role:
              type: string
              enum: [admin, member, viewer]
    responses:
      200:
        description: Role updated
      400:
        description: Validation error
      403:
        description: Not authorized
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    role_str = data.get("role", "").lower()

    if not role_str:
        return jsonify({"error": "Role is required"}), 400

    # Parse role
    try:
        role = UserRole[role_str.upper()]
    except KeyError:
        return jsonify(
            {"error": f"Invalid role: {role_str}. Must be admin, member, or viewer"}
        ), 400

    success, error = UserManagementService.update_user_project_role(
        user_id=user_id,
        project_id=project_id,
        new_role=role,
        updated_by_user_id=g.current_user.id,
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "User role updated successfully"}), 200


@project_members_api_bp.route(
    "/<int:project_id>/members/<int:user_id>", methods=["DELETE"]
)
@role_required(UserRole.ADMIN)
def remove_project_member(project_id, user_id):
    """
    Remove a user from a project (requires admin role).
    ---
    tags:
      - Project Members
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: Member removed
      400:
        description: Validation error
      403:
        description: Not authorized
    """
    success, error = UserManagementService.remove_user_from_project(
        user_id=user_id, project_id=project_id, removed_by_user_id=g.current_user.id
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "User removed from project successfully"}), 200


@project_members_api_bp.route(
    "/<int:project_id>/members/<int:user_id>/role", methods=["GET"]
)
@project_access_required
def get_user_project_role(project_id, user_id):
    """
    Get a user's role in a project.
    ---
    tags:
      - Project Members
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: User role
      404:
        description: User has no access to project
    """
    role = UserManagementService.get_user_role_in_project(user_id, project_id)

    if not role:
        return jsonify({"error": "User does not have access to this project"}), 404

    return jsonify(
        {"user_id": user_id, "project_id": project_id, "role": role.value}
    ), 200


@project_members_api_bp.route("/<int:project_id>/check-access", methods=["GET"])
@login_required
def check_project_access(project_id):
    """
    Check if current user has access to a project.
    ---
    tags:
      - Project Members
    parameters:
      - in: path
        name: project_id
        type: integer
        required: true
    responses:
      200:
        description: Access status
    """
    has_access = UserManagementService.has_project_access(g.current_user.id, project_id)
    role = UserManagementService.get_user_role_in_project(g.current_user.id, project_id)

    return jsonify(
        {"has_access": has_access, "role": role.value if role else None}
    ), 200
