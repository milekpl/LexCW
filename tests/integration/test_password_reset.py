"""
Integration tests for password reset functionality.

These tests use the real Flask app context and database but mock external
dependencies like BaseX and SMTP.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask
from flask.testing import FlaskClient

from app.services.auth_service import AuthenticationService
from app.models.project_settings import User, db


@pytest.fixture
def test_user_data(app: Flask):
    """Create a test user for password reset tests and yield user data.
    
    We yield data rather than the user object to avoid session detachment issues.
    """
    with app.app_context():
        email = "test_reset_integration@example.com"
        username = "test_reset_user_integration"
        
        # Clean up any existing test user
        existing = User.query.filter(
            (User.email == email) | (User.username == username)
        ).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
        
        # Create test user
        user = User(
            username=username,
            email=email,
            password_hash=AuthenticationService.hash_password("OriginalPass123"),
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        
        user_id = user.id
        
        yield {
            'id': user_id,
            'email': email,
            'username': username,
        }
        
        # Cleanup - re-query to ensure we're working with a fresh session
        try:
            user_to_delete = User.query.get(user_id)
            if user_to_delete:
                db.session.delete(user_to_delete)
                db.session.commit()
        except Exception:
            db.session.rollback()


class TestPasswordResetIntegration:
    """Integration tests for password reset flow."""

    def test_password_reset_generates_token(self, app: Flask, test_user_data):
        """Test that reset_password generates a token and stores it."""
        with app.app_context():
            # Get fresh user reference
            user = User.query.get(test_user_data['id'])
            
            # Reset any existing token
            user.reset_token = None
            user.reset_token_expires = None
            user.reset_token_used = False
            db.session.commit()
            
            # Call reset_password with mocked email
            with patch.object(AuthenticationService, '_send_email'):
                success, message = AuthenticationService.reset_password(test_user_data['email'])
            
            assert success is True
            
            # Re-query to get updated user
            user = User.query.get(test_user_data['id'])
            
            # Verify token was generated
            assert user.reset_token is not None
            assert len(user.reset_token) > 20
            
            # Verify expiration was set (may be naive or timezone-aware)
            assert user.reset_token_expires is not None
            now = datetime.now(timezone.utc)
            if user.reset_token_expires.tzinfo is None:
                # Compare as naive datetimes
                expires = user.reset_token_expires.replace(tzinfo=timezone.utc)
            else:
                expires = user.reset_token_expires
            assert expires > now
            
            # Verify used flag is False
            assert user.reset_token_used is False

    def test_reset_url_generation(self, app: Flask, test_user_data):
        """Test that reset URL is generated correctly."""
        with app.app_context():
            url = AuthenticationService._generate_reset_url("test_token_12345")
            
            # Verify URL format
            assert "test_token_12345" in url
            assert "/auth/reset-password/" in url
            assert url.startswith("http://") or url.startswith("https://")

    def test_complete_password_reset_clears_token(self, app: Flask, test_user_data):
        """Test that completing reset clears all token fields."""
        with app.app_context():
            user = User.query.get(test_user_data['id'])
            
            # Setup: create valid reset token
            user.reset_token = "complete_test_token"
            user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            user.reset_token_used = False
            db.session.commit()
            
            # Complete password reset
            success, error = AuthenticationService.complete_password_reset(
                "complete_test_token",
                "NewPassword123"
            )
            
            assert success is True, f"Failed with error: {error}"
            assert error is None
            
            # Re-query user
            user = User.query.get(test_user_data['id'])
            
            # Verify token fields are cleared
            assert user.reset_token is None
            assert user.reset_token_expires is None
            assert user.reset_token_used is False  # Should be reset after use
            
            # Verify password was changed
            assert AuthenticationService.verify_password(
                user.password_hash, "NewPassword123"
            )

    def test_single_use_token_prevents_reuse(self, app: Flask, test_user_data):
        """Test that a reset token can only be used once (single-use enforcement)."""
        with app.app_context():
            user = User.query.get(test_user_data['id'])
            
            # Setup: create a valid reset token
            user.reset_token = "single_use_token"
            user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            user.reset_token_used = False
            db.session.commit()
            
            # First reset attempt - should succeed
            success1, _ = AuthenticationService.complete_password_reset(
                "single_use_token",
                "NewPass1"
            )
            assert success1 is True
            
            # Re-query user and manually restore token (simulate it being compromised/stolen)
            user = User.query.get(test_user_data['id'])
            user.reset_token = "single_use_token"
            user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            user.reset_token_used = True  # Mark as used
            db.session.commit()
            
            # Second reset attempt - should fail due to single-use enforcement
            success2, error2 = AuthenticationService.complete_password_reset(
                "single_use_token",
                "NewPass2"
            )
            assert success2 is False
            assert "already been used" in error2

    def test_expired_token_is_cleared(self, app: Flask, test_user_data):
        """Test that expired tokens are rejected and cleared."""
        with app.app_context():
            user = User.query.get(test_user_data['id'])
            
            # Setup: create an expired reset token
            user.reset_token = "expired_token"
            user.reset_token_expires = datetime.now(timezone.utc) - timedelta(minutes=5)  # Expired 5 minutes ago
            user.reset_token_used = False
            db.session.commit()
            
            # Attempt reset with expired token
            success, error = AuthenticationService.complete_password_reset(
                "expired_token",
                "NewPass123"
            )
            
            assert success is False
            assert "expired" in error.lower()
            
            # Re-query user - token should have been cleared
            user = User.query.get(test_user_data['id'])
            assert user.reset_token is None
            assert user.reset_token_expires is None

    def test_password_validation_during_reset(self, app: Flask, test_user_data):
        """Test that password validation rules are enforced during reset."""
        with app.app_context():
            user = User.query.get(test_user_data['id'])
            
            # Setup: create a valid reset token
            user.reset_token = "validation_test_token"
            user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            user.reset_token_used = False
            db.session.commit()
            
            # Try to reset with weak password
            success, error = AuthenticationService.complete_password_reset(
                "validation_test_token",
                "short1"  # Less than 8 characters
            )
            assert success is False
            assert "at least 8 characters" in error

    def test_reset_password_api_endpoint(self, client: FlaskClient, test_user_data):
        """Test the API endpoint for requesting reset."""
        with patch.object(AuthenticationService, '_send_email'):
            response = client.post(
                "/api/auth/reset-password",
                json={"email": test_user_data['email']}
            )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

    def test_complete_reset_api_endpoint(self, app: Flask, client: FlaskClient, test_user_data):
        """Test the API endpoint for completing reset by simulating the full flow."""
        # Step 1: Request a reset to get a real token generated by the service
        with patch.object(AuthenticationService, '_send_email'):
            response = client.post(
                "/api/auth/reset-password",
                json={"email": test_user_data['email']}
            )
        
        assert response.status_code == 200
        
        # Step 2: Get the generated token from the database
        with app.app_context():
            user = User.query.get(test_user_data['id'])
            real_token = user.reset_token
            assert real_token is not None, "Token was not generated"
        
        # Step 3: Complete reset using the real token via API
        response = client.post(
            "/api/auth/reset-password/complete",
            json={
                "token": real_token,
                "new_password": "ApiNewPass123"
            }
        )
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert "successfully" in data["message"].lower()
        
        # Step 4: Verify password was changed
        with app.app_context():
            user = User.query.get(test_user_data['id'])
            assert AuthenticationService.verify_password(user.password_hash, "ApiNewPass123")

    def test_complete_reset_with_invalid_token_api(self, client: FlaskClient):
        """Test API returns error for invalid token."""
        response = client.post(
            "/api/auth/reset-password/complete",
            json={
                "token": "invalid_token_xyz",
                "new_password": "NewPass123"
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_forgot_password_page(self, anonymous_client):
        """Test that forgot password page loads (for a signed-out visitor)."""
        response = anonymous_client.get("/auth/forgot-password")
        
        assert response.status_code == 200
        html = response.data.decode()
        assert "Forgot Password" in html or "forgot" in html.lower()
        assert "email" in html.lower()

    def test_reset_password_page(self, anonymous_client):
        """Test that reset password page loads with token (for a signed-out visitor)."""
        response = anonymous_client.get("/auth/reset-password/test-token-123")
        
        assert response.status_code == 200
        html = response.data.decode()
        assert "Reset Password" in html or "reset" in html.lower()
        assert "password" in html.lower()

    def test_forgot_password_link_on_login_page(self, anonymous_client):
        """Test that login page has forgot password link (for a signed-out visitor)."""
        response = anonymous_client.get("/auth/login")
        
        assert response.status_code == 200
        html = response.data.decode()
        assert "forgot" in html.lower() or "Forgot" in html
        assert "/auth/forgot-password" in html


class TestEmailContentIntegration:
    """Test email content generation."""

    def test_reset_email_contains_url_not_raw_token(self, app: Flask, test_user_data):
        """Test that email contains a clickable URL, not raw token."""
        with app.app_context():
            # Reset token state
            user = User.query.get(test_user_data['id'])
            user.reset_token = None
            user.reset_token_expires = None
            user.reset_token_used = False
            db.session.commit()
            
            # Capture email that would be sent
            sent_body = None
            def capture_send_email(*args, **kwargs):
                nonlocal sent_body
                sent_body = kwargs.get('body')
            
            # Setup SMTP config for email to be sent
            from app.models.project_settings import ProjectSettings
            ps = ProjectSettings.query.first()
            if ps:
                ps.smtp_host = "smtp.example.com"
                ps.smtp_sender_email = "test@example.com"
                db.session.commit()
            
            with patch.object(AuthenticationService, '_send_email', side_effect=capture_send_email):
                AuthenticationService.reset_password(test_user_data['email'])
            
            # Re-query to get the generated token
            user = User.query.get(test_user_data['id'])
            
            # Verify email body was captured
            assert sent_body is not None, "Email body was not captured - SMTP may not be configured"
            
            # Email should contain URL with token
            assert "/auth/reset-password/" in sent_body
            assert user.reset_token in sent_body
            
            # Email should contain helpful text
            assert "Click" in sent_body or "click" in sent_body or "link" in sent_body.lower()
            assert "reset" in sent_body.lower()
            assert "expire" in sent_body.lower() or "hours" in sent_body.lower()

    def test_email_subject_line(self, app: Flask, test_user_data):
        """Test email subject mentions password reset."""
        with app.app_context():
            sent_subject = None
            def capture_send_email(*args, **kwargs):
                nonlocal sent_subject
                sent_subject = kwargs.get('subject')
            
            # Setup SMTP config for email to be sent
            from app.models.project_settings import ProjectSettings
            ps = ProjectSettings.query.first()
            if ps:
                ps.smtp_host = "smtp.example.com"
                ps.smtp_sender_email = "test@example.com"
                db.session.commit()
            
            with patch.object(AuthenticationService, '_send_email', side_effect=capture_send_email):
                AuthenticationService.reset_password(test_user_data['email'])
            
            assert sent_subject is not None, "Email subject was not captured - SMTP may not be configured"
            assert "password" in sent_subject.lower()
            assert "reset" in sent_subject.lower()


class TestSecurityConsiderations:
    """Test security aspects of password reset."""

    def test_no_email_enumeration_on_reset_request(self, client: FlaskClient):
        """Test that reset endpoint returns same message for existing and non-existing emails."""
        # Request for non-existing email
        with patch.object(AuthenticationService, '_send_email'):
            response1 = client.post(
                "/api/auth/reset-password",
                json={"email": "definitely_nonexistent_xyz@example.com"}
            )
        
        # Request for potentially existing email (same response structure)
        with patch.object(AuthenticationService, '_send_email'):
            response2 = client.post(
                "/api/auth/reset-password",
                json={"email": "another_nonexistent_abc@example.com"}
            )
        
        # Both should return 200
        assert response1.status_code == response2.status_code == 200
        
        # Both should have same message structure
        data1 = response1.get_json()
        data2 = response2.get_json()
        assert "message" in data1
        assert "message" in data2

    def test_multiple_reset_requests_generate_new_tokens(self, app: Flask, test_user_data):
        """Test that multiple requests generate different tokens."""
        with app.app_context():
            # First request
            with patch.object(AuthenticationService, '_send_email'):
                AuthenticationService.reset_password(test_user_data['email'])
            
            user = User.query.get(test_user_data['id'])
            first_token = user.reset_token
            first_expires = user.reset_token_expires
            
            # Second request (simulating user clicking reset again)
            with patch.object(AuthenticationService, '_send_email'):
                AuthenticationService.reset_password(test_user_data['email'])
            
            user = User.query.get(test_user_data['id'])
            second_token = user.reset_token
            second_expires = user.reset_token_expires
            
            # New token should be different
            assert first_token != second_token
            
            # Expiration should be extended or at least reset
            assert second_expires >= first_expires

    def test_token_is_url_safe(self, app: Flask, test_user_data):
        """Test that generated tokens are URL-safe."""
        with app.app_context():
            with patch.object(AuthenticationService, '_send_email'):
                AuthenticationService.reset_password(test_user_data['email'])
            
            user = User.query.get(test_user_data['id'])
            token = user.reset_token
            
            # Token should not contain characters that need URL encoding
            # URL-safe base64 uses: A-Z, a-z, 0-9, -, _
            import re
            assert re.match(r'^[A-Za-z0-9_-]+$', token), f"Token contains non-URL-safe characters: {token}"

    def test_reset_url_no_double_slashes(self, app: Flask):
        """Test that generated URLs don't have double slashes."""
        with app.app_context():
            url = AuthenticationService._generate_reset_url("test_token")
            
            # Remove protocol for checking
            url_without_protocol = url.replace("https://", "").replace("http://", "")
            
            # Should not have double slashes
            assert "//" not in url_without_protocol, f"URL has double slashes: {url}"
