"""
Authentication routes for web UI.

This module provides web-based authentication routes (login, register, profile).
It complements the REST API in app/api/auth_api.py.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g,
)
from app.services.auth_service import AuthenticationService
from app.services.user_service import UserManagementService
from app.utils.auth_decorators import login_required, get_current_user
from app.models.project_settings import db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Display login page and handle login form submission."""
    # Redirect if already logged in
    if get_current_user():
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember", False)

        if not username or not password:
            flash("Please provide both username and password.", "error")
            return render_template("auth/login.html")

        # Authenticate user
        user, error = AuthenticationService.authenticate_user(username, password)

        if user:
            # Set session
            session["user_id"] = user.id
            session["username"] = user.username
            if remember:
                session.permanent = True

            # Log activity
            from app.models.user_models import ActivityLog

            log = ActivityLog(
                user_id=user.id,
                action="login",
                entity_type="auth",
                entity_id=str(user.id),
                description=f"User {user.username} logged in",
                ip_address=request.remote_addr,
            )
            db.session.add(log)
            db.session.commit()

            flash(f"Welcome back, {user.first_name or user.username}!", "success")

            # Redirect to next page or home
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.index"))
        else:
            flash(error or "Authentication failed", "error")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Display registration page and handle registration form submission."""
    # Redirect if already logged in
    if get_current_user():
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        # Validate passwords match
        if password != password_confirm:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")

        # Register user
        user, error = AuthenticationService.register_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        if user:
            # Auto-login after registration
            session["user_id"] = user.id
            session["username"] = user.username

            flash(
                "Registration successful! Welcome to the Lexicographic Curation Workbench.",
                "success",
            )
            return redirect(url_for("main.index"))
        else:
            flash(error or "Registration failed", "error")

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    username = session.get("username", "User")

    # Log activity
    if g.current_user:
        from app.models.user_models import ActivityLog

        log = ActivityLog(
            user_id=g.current_user.id,
            action="logout",
            resource_type="auth",
            details={"ip_address": request.remote_addr},
        )
        db.session.add(log)
        db.session.commit()

    # Clear session
    session.clear()

    flash(f"Goodbye, {username}!", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    """Display user profile page."""
    user = g.current_user

    # Get user's projects
    user_service = UserManagementService()
    projects = user_service.get_user_projects(user.id)

    # Get recent activity
    from app.models.user_models import ActivityLog

    recent_activity = (
        ActivityLog.query.filter_by(user_id=user.id)
        .order_by(ActivityLog.timestamp.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "auth/profile.html",
        user=user,
        projects=projects,
        recent_activity=recent_activity,
    )


@auth_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit user profile."""
    user = g.current_user

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        bio = request.form.get("bio", "").strip()

        # Update profile
        result = AuthenticationService.update_profile(
            user_id=user.id, first_name=first_name, last_name=last_name, bio=bio
        )

        if result["success"]:
            flash("Profile updated successfully.", "success")
            return redirect(url_for("auth.profile"))
        else:
            flash(result["message"], "error")

    return render_template("auth/edit_profile.html", user=user)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change user password."""
    user = g.current_user

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate passwords match
        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return render_template("auth/change_password.html")

        # Change password
        result = AuthenticationService.change_password(
            user_id=user.id, old_password=current_password, new_password=new_password
        )

        if result["success"]:
            flash("Password changed successfully.", "success")
            return redirect(url_for("auth.profile"))
        else:
            flash(result["message"], "error")

    return render_template("auth/change_password.html")
