"""
Authentication service for user login, registration, and password management.
"""

from typing import Optional
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, url_for
import secrets
import re

from app.models.workset_models import db
from app.utils.db_utils import safe_commit
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
    def _send_email(host, port, username, password, use_tls, sender, recipient, subject, body):
        """Send an email via SMTP. Uses stdlib smtplib — no extra dependencies."""
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient

        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        try:
            if username and password:
                server.login(username, password)
            server.sendmail(sender, [recipient], msg.as_string())
        finally:
            server.quit()

    @staticmethod
    def _generate_reset_url(token: str, base_url: Optional[str] = None) -> str:
        """
        Generate a secure password reset URL with the token.
        
        Args:
            token: The reset token
            base_url: Optional base URL override (uses config.BASE_URL by default)
            
        Returns:
            Full password reset URL
        """
        # Get base URL from config or use provided value
        if base_url is None:
            base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
        
        # Ensure no trailing slash in base_url
        base_url = base_url.rstrip('/')
        
        # Generate the token verification URL
        # Token is URL-safe (from secrets.token_urlsafe), so no additional encoding needed
        reset_url = f"{base_url}/auth/reset-password/{token}"
        
        return reset_url

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
        safe_commit(db, "auth_service")

        # Log the registration
        log = ActivityLog(
            user_id=user.id,
            action="register",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {username} registered",
        )
        db.session.add(log)
        safe_commit(db, "auth_service")

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
        safe_commit(db, "auth_service")

        # Log the login
        log = ActivityLog(
            user_id=user.id,
            action="login",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {user.username} logged in",
        )
        db.session.add(log)
        safe_commit(db, "auth_service")

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
        safe_commit(db, "auth_service")

        # Log the password change
        log = ActivityLog(
            user_id=user.id,
            action="change_password",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {user.username} changed password",
        )
        db.session.add(log)
        safe_commit(db, "auth_service")

        return True, None

    @staticmethod
    def reset_password(email: str) -> tuple[bool, Optional[str]]:
        """
        Initiate password reset process (generates and stores token).

        The reset token is valid for 1 hour. In production, wire an email
        sender to deliver the token (e.g. Flask-Mail, SendGrid, SMTP).

        Args:
            email: User's email address

        Returns:
            Tuple of (success, message)
        """
        user = User.query.filter_by(email=email).first()

        if not user:
            # Don't reveal whether email exists
            return True, "If the email exists, a reset link has been sent"

        # Generate and store reset token with 1-hour expiration.
        # reset_token_used is cleared here, not just after a successful reset: if a
        # reset is interrupted between marking the token used and clearing it, the
        # flag would otherwise stay set forever and every *future* token would be
        # refused as "already used" — locking the account out of password reset
        # permanently, with no way back except the database.
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        user.reset_token_used = False
        safe_commit(db, "auth_service")

        # Log the password reset request
        log = ActivityLog(
            user_id=user.id,
            action="password_reset_request",
            entity_type="user",
            entity_id=str(user.id),
            description=f"Password reset requested for {user.email} (token expires in 1h)",
        )
        db.session.add(log)
        safe_commit(db, "auth_service")

        # Generate the reset URL with the token embedded
        reset_url = AuthenticationService._generate_reset_url(reset_token)
        
        # Calculate expiration time for display (1 hour from now)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        expires_str = expires_at.strftime('%Y-%m-%d %H:%M UTC')

        # Try to send email if SMTP is configured
        try:
            from app.models.project_settings import ProjectSettings
            ps = ProjectSettings.query.first()
            if ps and ps.smtp_host and ps.smtp_sender_email:
                email_body = (
                    f'You requested a password reset for your account.\n\n'
                    f'Click the link below to reset your password:\n\n'
                    f'{reset_url}\n\n'
                    f'This link will expire at {expires_str}.\n\n'
                    f'If you did not request this password reset, please ignore this email.\n\n'
                    f'For security reasons, this link can only be used once.'
                )
                
                AuthenticationService._send_email(
                    host=ps.smtp_host,
                    port=ps.smtp_port or 587,
                    username=ps.smtp_username,
                    password=ps.smtp_password,
                    use_tls=ps.smtp_use_tls if ps.smtp_use_tls is not None else True,
                    sender=ps.smtp_sender_email,
                    recipient=user.email,
                    subject='Password Reset Request',
                    body=email_body
                )
                current_app.logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            current_app.logger.warning(f'Failed to send password reset email to {user.email}: {e}')

        return True, "If the email exists, a reset link has been sent"

    @staticmethod
    def complete_password_reset(token: str, new_password: str) -> tuple[bool, Optional[str]]:
        """
        Complete a password reset using a valid token.
        
        Security features:
        - Single-use token enforcement (token marked as used immediately)
        - Expiration validation with timezone awareness
        - Immediate token invalidation after successful reset
        - Atomic database operations

        Args:
            token: Reset token from email link
            new_password: New password to set

        Returns:
            Tuple of (success, error_message)
        """
        user = User.query.filter_by(reset_token=token).first()

        if not user:
            return False, "Invalid or expired reset token"

        # Check if token has already been used (single-use enforcement)
        if user.reset_token_used:
            return False, "This reset link has already been used. Please request a new password reset."

        if user.reset_token_expires is None:
            return False, "Invalid or expired reset token"

        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        expires = user.reset_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if now > expires:
            # Clear expired token
            user.reset_token = None
            user.reset_token_expires = None
            user.reset_token_used = False
            safe_commit(db, "auth_service")
            return False, "Reset token has expired. Please request a new password reset."

        # Validate new password
        is_valid, error = AuthenticationService.validate_password(new_password)
        if not is_valid:
            return False, error

        # Mark token as used immediately (single-use enforcement)
        # This prevents race conditions where the same token is used twice
        user.reset_token_used = True
        safe_commit(db, "auth_service")

        # Update password and clear token
        user.password_hash = AuthenticationService.hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        user.reset_token_used = False  # Reset for future use
        safe_commit(db, "auth_service")

        # Log the password reset completion
        log = ActivityLog(
            user_id=user.id,
            action="password_reset_complete",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {user.username} completed password reset",
        )
        db.session.add(log)
        safe_commit(db, "auth_service")

        return True, None

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

        safe_commit(db, "auth_service")

        # Log the profile update
        log = ActivityLog(
            user_id=user.id,
            action="update_profile",
            entity_type="user",
            entity_id=str(user.id),
            description=f"User {user.username} updated profile",
        )
        db.session.add(log)
        safe_commit(db, "auth_service")

        return True, None
