"""
API key authentication decorator for machine-to-machine API access.

Provides a decorator that accepts either a valid API key (via Authorization: Bearer
header) or falls back to session-based authentication. API keys are scoped to
projects and may be further restricted by scope (e.g., "read", "export").

Usage:
    @app.route('/api/entries')
    @require_api_key(scope='read')
    def list_entries():
        ...

    @app.route('/api/pronunciation/deduplicate/apply')
    @require_api_key(scope='pronunciation:write')
    def apply_dedup():
        ...
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from flask import request, jsonify, g
from werkzeug.security import check_password_hash

from app.models.api_key import ApiKey
from app.utils.auth_decorators import get_current_user


def require_api_key(scope: Optional[str] = None) -> Callable:
    """
    Decorator that authenticates via API key (Bearer token) or falls back to
    session-based login.

    API keys are checked by extracting the prefix (first 8 chars after ``sw_``),
    looking up the key record, and verifying the hash. If the key has a non-empty
    ``scopes`` list, the requested ``scope`` must be present.

    When no ``Authorization: Bearer`` header is present, falls through to
    session-based ``login_required``-style auth (sets ``g.current_user``).

    Args:
        scope: Optional scope string the key must have (e.g. ``"export"``).

    Returns:
        The decorated function, which receives ``g.api_key`` (if key auth was used)
        or ``g.current_user`` (if session auth was used).
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")

            if auth_header.startswith("Bearer "):
                raw_key = auth_header[7:]

                # Extract prefix: "sw_" + first 8 chars
                if not raw_key.startswith("sw_") or len(raw_key) < 11:
                    return jsonify({"error": "Invalid API key format"}), 401

                prefix = raw_key[:11]  # "sw_" + 8 chars

                key_record = ApiKey.query.filter_by(
                    key_prefix=prefix, is_active=True
                ).first()

                if not key_record:
                    return jsonify({"error": "Invalid API key"}), 401

                if not check_password_hash(key_record.key_hash, raw_key):
                    return jsonify({"error": "Invalid API key"}), 401

                # Check scope if the key has restrictions
                key_scopes = key_record.scopes or []
                if key_scopes and scope and scope not in key_scopes:
                    return jsonify(
                        {
                            "error": (
                                f"API key does not have required scope '{scope}'. "
                                f"Key scopes: {key_scopes}"
                            )
                        }
                    ), 403

                # Update last used timestamp
                from datetime import datetime, timezone

                key_record.last_used_at = datetime.now(timezone.utc)
                from app.models.workset_models import db
from app.utils.db_utils import safe_commit

                safe_commit(db, 'api_key_auth')

                g.api_key = key_record
                g.current_user = None  # No session user when using API key
                return f(*args, **kwargs)

            # No API key — fall back to session auth
            user = get_current_user()
            if not user:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                from flask import redirect, url_for

                return redirect(url_for("auth.login", next=request.url))

            g.current_user = user
            g.api_key = None
            return f(*args, **kwargs)

        return decorated_function

    return decorator
