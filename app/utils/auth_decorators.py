"""
Authentication decorators for route protection.

Two ways to authenticate, one contract:

* **Session** — a logged-in browser user (`session["user_id"]`).
* **API key** — a machine client sending `Authorization: Bearer sw_…`, limited to
  the scopes granted to that key.

`require_auth(scope)` accepts either. `login_required` / `admin_required` accept
only a session, so an API key can never reach identity or management endpoints
(see specs/auth_overhaul/auth_matrix.md, rule 1).

Failures always answer the same way:

| Situation                              | Status | code                      |
|----------------------------------------|--------|---------------------------|
| No credential at all                   | 401    | `authentication_required` |
| API key unknown, inactive, or malformed| 401    | `invalid_api_key`         |
| Valid key, but the scope was not granted| 403   | `insufficient_scope`      |
| Session user without admin rights      | 403    | `admin_required`          |

401 means "I don't know who you are"; 403 means "I know who you are, and no".
Conflating them (returning 401 for a scope failure) tells a caller to retry with
new credentials when the credentials were never the problem.

Browser navigations get a redirect to the login page instead of JSON, so deep
links survive a login round-trip.
"""

from functools import wraps
from datetime import datetime, timezone
from flask import session, jsonify, redirect, url_for, request, g
from typing import Callable, Optional, Tuple

from app.models.project_settings import User
from app.models.user_models import UserRole
from app.services.user_service import UserManagementService


def get_current_user() -> Optional[User]:
    """Get the currently logged-in user from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def _wants_json() -> bool:
    """True when the caller expects JSON rather than a login page."""
    if request.path.startswith("/api/"):
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    accept = request.accept_mimetypes
    return accept.accept_json and not accept.accept_html


def next_target() -> str:
    """Where to return the user after login: a *relative* path, never absolute.

    `request.url` would be absolute (http://host/path), and the login handler
    rejects absolute targets — accepting them is an open redirect (?next=
    http://evil.example). Relative keeps the deep link working and the door shut.
    """
    return request.full_path.rstrip("?") or "/"


def auth_error(message: str, status: int, code: str):
    """Build the one auth-failure response shape used across the app."""
    if status == 401 and not _wants_json():
        # Browser navigation: send them to log in, then back where they were.
        return redirect(url_for("auth.login", next=next_target()))
    return jsonify({"error": message, "code": code}), status


def _authenticate_api_key(required_scope: Optional[str]):
    """Authenticate a Bearer key. Returns None on success, else an error response."""
    from werkzeug.security import check_password_hash

    from app.models.api_key import ApiKey
    from app.models.workset_models import db
    from app.utils.db_utils import safe_commit

    raw_key = request.headers.get("Authorization", "")[7:]
    if not raw_key.startswith("sw_") or len(raw_key) < 11:
        return auth_error("Invalid API key", 401, "invalid_api_key")

    record = ApiKey.query.filter_by(key_prefix=raw_key[:11], is_active=True).first()
    if not record or not check_password_hash(record.key_hash, raw_key):
        return auth_error("Invalid API key", 401, "invalid_api_key")

    # Least privilege: a key grants exactly the scopes it was given. An empty scope
    # list therefore grants *nothing* — it used to mean "full access", so a key
    # created with no scopes selected could do anything the API allowed.
    granted = record.scopes or []
    if required_scope is not None and required_scope not in granted:
        return auth_error(
            f"This API key does not have the '{required_scope}' scope",
            403,
            "insufficient_scope",
        )

    record.last_used_at = datetime.now(timezone.utc)
    safe_commit(db, "api_key_auth")

    g.api_key = record
    g.current_user = None
    return None


def require_auth(scope: Optional[str] = None) -> Callable:
    """Require a session **or** an API key holding ``scope``.

    Usage:
        @bp.route("/draft", methods=["POST"])
        @require_auth("pronunciation:read")
        def draft(): ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.headers.get("Authorization", "").startswith("Bearer "):
                error = _authenticate_api_key(scope)
                if error is not None:
                    return error
                return f(*args, **kwargs)

            user = get_current_user()
            if not user:
                return auth_error(
                    "Authentication required", 401, "authentication_required"
                )

            g.current_user = user
            g.api_key = None
            return f(*args, **kwargs)

        # The gate (app/__init__.py) reads this: only a route that opted in may be
        # reached with an API key. Everything else is session-only, so a leaked key
        # cannot wander into endpoints nobody meant to expose to machines.
        decorated_function._accepts_api_key = True
        decorated_function._required_scope = scope
        return decorated_function

    return decorator


def login_required(f: Callable) -> Callable:
    """
    Decorator to require user login for a route.

    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return 'This requires login'
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return auth_error("Authentication required", 401, "authentication_required")

        # Store user in g for access in route
        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f: Callable) -> Callable:
    """
    Decorator to require admin privileges for a route.

    Session-only by design: an API key must never be able to reach management
    endpoints, or a leaked key could mint further keys and take the instance.

    Usage:
        @app.route('/admin/users')
        @admin_required
        def admin_route():
            return 'This requires admin'
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return auth_error("Authentication required", 401, "authentication_required")

        if not user.is_admin:
            return auth_error("Admin privileges required", 403, "admin_required")

        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def project_access_required(f: Callable) -> Callable:
    """
    Decorator to require project access for a route.
    Checks if user has access to the project in session or specified in request.

    Usage:
        @app.route('/projects/<int:project_id>/entries')
        @project_access_required
        def project_route(project_id):
            return 'This requires project access'
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login", next=next_target()))

        # Get project_id from kwargs, session, or request args
        project_id = (
            kwargs.get("project_id")
            or session.get("project_id")
            or request.args.get("project_id")
        )

        if not project_id:
            return jsonify({"error": "No project specified"}), 400

        # Check if user has access
        if not UserManagementService.has_project_access(user.id, int(project_id)):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Project access denied"}), 403
            return jsonify({"error": "Project access denied"}), 403

        g.current_user = user
        g.project_id = int(project_id)
        return f(*args, **kwargs)

    return decorated_function


def role_required(required_role: UserRole):
    """
    Decorator factory to require a specific role for a route.

    Usage:
        @app.route('/projects/<int:project_id>/settings')
        @role_required(UserRole.ADMIN)
        def project_settings(project_id):
            return 'This requires admin role'
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("auth.login", next=next_target()))

            # Admin users have access to everything
            if user.is_admin:
                g.current_user = user
                return f(*args, **kwargs)

            # Get project_id from kwargs, session, or request args
            project_id = (
                kwargs.get("project_id")
                or session.get("project_id")
                or request.args.get("project_id")
            )

            if not project_id:
                return jsonify({"error": "No project specified"}), 400

            # Get user's role in project
            user_role = UserManagementService.get_user_role_in_project(
                user.id, int(project_id)
            )

            if not user_role:
                return jsonify({"error": "Project access denied"}), 403

            # Check if user has required role
            # Role hierarchy: ADMIN > MEMBER > VIEWER
            role_hierarchy = {UserRole.ADMIN: 3, UserRole.MEMBER: 2, UserRole.VIEWER: 1}

            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                return jsonify({"error": f"{required_role.value} role required"}), 403

            g.current_user = user
            g.project_id = int(project_id)
            g.user_role = user_role
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def optional_auth(f: Callable) -> Callable:
    """
    Decorator that loads user if authenticated but doesn't require it.
    Useful for routes that behave differently based on authentication status.

    Usage:
        @app.route('/public')
        @optional_auth
        def public_route():
            if g.current_user:
                return 'Hello, ' + g.current_user.username
            return 'Hello, guest'
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        g.current_user = user if user else None
        return f(*args, **kwargs)

    return decorated_function
