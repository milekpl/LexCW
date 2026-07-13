"""
API key management endpoints.

Allows users with session auth to create, list, and revoke API keys
for their projects. The raw key is shown exactly once at creation.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash

from app.models.workset_models import db
from app.utils.db_utils import safe_commit
from app.models.api_key import ApiKey
from app.utils.auth_decorators import login_required

api_keys_bp = Blueprint("api_keys", __name__, url_prefix="/api/keys")


def _generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    The ``sw_`` marker is part of the raw key itself, so that the hash covers
    exactly the string a client sends as ``Authorization: Bearer <raw_key>``
    and the prefix is a literal slice of it (see ``_check_api_key_auth``).

    Returns:
        Tuple of (raw_key, key_hash, key_prefix).
    """
    raw = "sw_" + secrets.token_urlsafe(32)
    prefix = raw[:11]
    hashed = generate_password_hash(raw, method="pbkdf2:sha256")
    return raw, hashed, prefix


@api_keys_bp.route("/", methods=["GET"])
@login_required
def list_keys():
    """List all active API keys for the current user's projects."""
    # Find keys for projects the user owns or is a member of
    from app.models.project_settings import ProjectSettings

    # Get all projects the user is associated with
    owned = ProjectSettings.query.filter_by(owner_id=g.current_user.id).all()
    owned_ids = [p.id for p in owned]

    # Also check member_projects
    member_ids = [p.id for p in (g.current_user.member_projects or [])]

    project_ids = list(set(owned_ids + member_ids))
    if not project_ids:
        return jsonify({"keys": []}), 200

    keys = (
        ApiKey.query.filter(ApiKey.project_id.in_(project_ids))
        .order_by(ApiKey.created_at.desc())
        .all()
    )

    return jsonify({"keys": [k.to_dict() for k in keys]}), 200


@api_keys_bp.route("/", methods=["POST"])
@login_required
def create_key():
    """Create a new API key for a project.

    The raw key is returned only in this response. Store it securely.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    project_id = data.get("project_id")
    label = data.get("label", "").strip()
    scopes = data.get("scopes", [])

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    if not label:
        return jsonify({"error": "label is required"}), 400

    # Verify the user has access to this project
    from app.models.project_settings import ProjectSettings

    project = ProjectSettings.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    is_owner = project.owner_id == g.current_user.id
    is_member = g.current_user in (project.members or [])
    if not is_owner and not is_member and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized for this project"}), 403

    # Generate key
    raw_key, key_hash, key_prefix = _generate_api_key()

    key = ApiKey(
        project_id=project_id,
        label=label,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes or [],
        is_active=True,
    )
    db.session.add(key)
    safe_commit(db, "api_keys")

    result = key.to_dict()
    result["raw_key"] = raw_key  # Shown once!

    return jsonify({"message": "API key created", "key": result}), 201


@api_keys_bp.route("/<int:key_id>", methods=["DELETE"])
@login_required
def revoke_key(key_id: int):
    """Revoke an API key (soft delete — sets is_active=False)."""
    key = ApiKey.query.get(key_id)
    if not key:
        return jsonify({"error": "API key not found"}), 404

    # Verify ownership via project access
    from app.models.project_settings import ProjectSettings

    project = ProjectSettings.query.get(key.project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    is_owner = project.owner_id == g.current_user.id
    if not is_owner and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized to revoke this key"}), 403

    key.is_active = False
    safe_commit(db, "api_keys")

    return jsonify({"message": "API key revoked"}), 200


@api_keys_bp.route("/<int:key_id>/reactivate", methods=["POST"])
@login_required
def reactivate_key(key_id: int):
    """Reactivate a previously revoked API key."""
    key = ApiKey.query.get(key_id)
    if not key:
        return jsonify({"error": "API key not found"}), 404

    from app.models.project_settings import ProjectSettings
    project = ProjectSettings.query.get(key.project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    is_owner = project.owner_id == g.current_user.id
    if not is_owner and not g.current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    key.is_active = True
    safe_commit(db, "api_keys")

    return jsonify({"message": "API key reactivated"}), 200
