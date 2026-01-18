"""
Authentication decorators for route protection.
"""

from functools import wraps
from flask import session, jsonify, redirect, url_for, request, g
from typing import Callable, Optional

from app.models.project_settings import User
from app.models.user_models import UserRole
from app.services.user_service import UserManagementService


def get_current_user() -> Optional[User]:
    """Get the currently logged-in user from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


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
            # Check if this is an API request
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            # For web requests, redirect to login
            return redirect(url_for("auth.login", next=request.url))

        # Store user in g for access in route
        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f: Callable) -> Callable:
    """
    Decorator to require admin privileges for a route.

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
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login", next=request.url))

        if not user.is_admin:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin privileges required"}), 403
            return jsonify({"error": "Admin privileges required"}), 403

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
            return redirect(url_for("auth.login", next=request.url))

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
                return redirect(url_for("auth.login", next=request.url))

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
