"""
Authentication service for user login, registration, and password management.
"""

from typing import Optional
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import re

from app.models.workset_models import db
from app.models.project_settings import User
from app.models.user_models import ActivityLog


class AuthenticationService:
    """Service for user authentication and password management."""

    @staticmethod
    def validate_password(password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        return True, None

    @staticmethod
    def validate_username(username: str) -> tuple[bool, Optional[str]]:
        """
        Validate username format.

        Args:
            username: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"

        if len(username) > 80:
            return False, "Username must be less than 80 characters"

        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            return (
                False,
                "Username can only contain letters, numbers, underscores, and hyphens",
            )

        return True, None

    @staticmethod
    def validate_email(email: str) -> tuple[bool, Optional[str]]:
        """
        Validate email format.

        Args:
            email: Email to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, email):
            return False, "Invalid email format"

        return True, None

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using werkzeug's pbkdf2:sha256.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return generate_password_hash(password, method="pbkdf2:sha256")

    @staticmethod
    def verify_password(password_hash: str, password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password_hash: Stored password hash
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        return check_password_hash(password_hash, password)

    @staticmethod
    def register_user(
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> tuple[Optional[User], Optional[str]]:
        """
        Register a new user.

        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password
            first_name: User's first name
            last_name: User's last name
            is_admin: Whether user should be admin

        Returns:
            Tuple of (user, error_message)
        """
        # Validate inputs
        is_valid, error = AuthenticationService.validate_username(username)
        if not is_valid:
            return None, error

        is_valid, error = AuthenticationService.validate_email(email)
        if not is_valid:
            return None, error

        is_valid, error = AuthenticationService.validate_password(password)
        if not is_valid:
            return None, error

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return None, "Username already taken"

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return None, "Email already registered"

        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=AuthenticationService.hash_password(password),
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            is_active=True,
        )

        db.session.add(user)
        db.session.commit()

        # Log the registration
        log = ActivityLog(
            user_id=user.id,
            action="register",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {username} registered",
        )
        db.session.add(log)
        db.session.commit()

        return user, None

    @staticmethod
    def authenticate_user(
        username_or_email: str, password: str
    ) -> tuple[Optional[User], Optional[str]]:
        """
        Authenticate a user by username/email and password.

        Args:
            username_or_email: Username or email address
            password: Plain text password

        Returns:
            Tuple of (user, error_message)
        """
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if not user:
            return None, "Invalid credentials"

        if not user.is_active:
            return None, "Account is deactivated"

        if not AuthenticationService.verify_password(user.password_hash, password):
            return None, "Invalid credentials"

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        # Log the login
        log = ActivityLog(
            user_id=user.id,
            action="login",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {user.username} logged in",
        )
        db.session.add(log)
        db.session.commit()

        return user, None

    @staticmethod
    def change_password(
        user: User, old_password: str, new_password: str
    ) -> tuple[bool, Optional[str]]:
        """
        Change a user's password.

        Args:
            user: User object
            old_password: Current password
            new_password: New password

        Returns:
            Tuple of (success, error_message)
        """
        # Verify old password
        if not AuthenticationService.verify_password(user.password_hash, old_password):
            return False, "Current password is incorrect"

        # Validate new password
        is_valid, error = AuthenticationService.validate_password(new_password)
        if not is_valid:
            return False, error

        # Update password
        user.password_hash = AuthenticationService.hash_password(new_password)
        db.session.commit()

        # Log the password change
        log = ActivityLog(
            user_id=user.id,
            action="change_password",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {user.username} changed password",
        )
        db.session.add(log)
        db.session.commit()

        return True, None

    @staticmethod
    def reset_password(email: str) -> tuple[bool, Optional[str]]:
        """
        Initiate password reset process (generates token).

        Note: Email sending functionality would need to be implemented separately.

        Args:
            email: User's email address

        Returns:
            Tuple of (success, error_message or reset_token)
        """
        user = User.query.filter_by(email=email).first()

        if not user:
            # Don't reveal whether email exists
            return True, "If the email exists, a reset link has been sent"

        # Generate reset token (in production, store this with expiration)
        reset_token = secrets.token_urlsafe(32)

        # TODO: Store reset token in database with expiration
        # TODO: Send email with reset link

        # Log the password reset request
        log = ActivityLog(
            user_id=user.id,
            action="password_reset_request",
            entity_type="user",
            entity_id=str(user.id),
            description=f"Password reset requested for {user.email}",
        )
        db.session.add(log)
        db.session.commit()

        return True, reset_token  # In production, return success message only

    @staticmethod
    def update_user_profile(
        user: User,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Update user profile information.

        Args:
            user: User object
            first_name: New first name
            last_name: New last name
            bio: New bio
            avatar_url: New avatar URL

        Returns:
            Tuple of (success, error_message)
        """
        if first_name is not None:
            user.first_name = first_name

        if last_name is not None:
            user.last_name = last_name

        if bio is not None:
            user.bio = bio

        if avatar_url is not None:
            user.avatar_url = avatar_url

        db.session.commit()

        # Log the profile update
        log = ActivityLog(
            user_id=user.id,
            action="update_profile",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {user.username} updated profile",
        )
        db.session.add(log)
        db.session.commit()

        return True, None
