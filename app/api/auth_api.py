"""
Authentication API blueprint for user registration, login, and password management.
"""

from flask import Blueprint, request, jsonify, session, g
from app.services.auth_service import AuthenticationService
from app.utils.auth_decorators import login_required, get_current_user

auth_api_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@auth_api_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              example: john_doe
            email:
              type: string
              example: john@example.com
            password:
              type: string
              example: SecurePass123
            first_name:
              type: string
              example: John
            last_name:
              type: string
              example: Doe
    responses:
      201:
        description: User created successfully
      400:
        description: Validation error
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    user, error = AuthenticationService.register_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    if error:
        return jsonify({"error": error}), 400

    # Auto-login after registration
    session["user_id"] = user.id
    session["username"] = user.username

    return jsonify(
        {
            "message": "User registered successfully",
            "user": user.to_dict(include_private=True),
        }
    ), 201


@auth_api_bp.route("/login", methods=["POST"])
def login():
    """
    Login with username/email and password.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: Username or email
              example: john_doe
            password:
              type: string
              example: SecurePass123
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username_or_email = data.get("username")
    password = data.get("password")

    if not username_or_email or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user, error = AuthenticationService.authenticate_user(username_or_email, password)

    if error:
        return jsonify({"error": error}), 401

    # Set session
    session["user_id"] = user.id
    session["username"] = user.username
    session.permanent = True  # Use permanent session

    return jsonify(
        {"message": "Login successful", "user": user.to_dict(include_private=True)}
    ), 200


@auth_api_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    Logout current user.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Logout successful
    """
    session.clear()
    return jsonify({"message": "Logout successful"}), 200


@auth_api_bp.route("/me", methods=["GET"])
@login_required
def get_current_user_info():
    """
    Get current logged-in user information.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Current user info
      401:
        description: Not authenticated
    """
    return jsonify({"user": g.current_user.to_dict(include_private=True)}), 200


@auth_api_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """
    Change current user's password.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - old_password
            - new_password
          properties:
            old_password:
              type: string
            new_password:
              type: string
    responses:
      200:
        description: Password changed successfully
      400:
        description: Validation error
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "Old password and new password are required"}), 400

    success, error = AuthenticationService.change_password(
        g.current_user, old_password, new_password
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Password changed successfully"}), 200


@auth_api_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Request password reset (sends reset token).
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              example: john@example.com
    responses:
      200:
        description: Reset email sent (if email exists)
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    success, message = AuthenticationService.reset_password(email)

    # Always return success to avoid email enumeration
    return jsonify({"message": "If the email exists, a reset link has been sent"}), 200


@auth_api_bp.route("/check", methods=["GET"])
def check_auth():
    """
    Check if user is authenticated.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Authentication status
    """
    user = get_current_user()

    if user:
        return jsonify({"authenticated": True, "user": user.to_dict()}), 200
    else:
        return jsonify({"authenticated": False}), 200
