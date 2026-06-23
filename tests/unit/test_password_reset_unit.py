"""
Unit tests for password reset functionality.

These tests verify the password reset service methods without requiring
external services like BaseX or PostgreSQL.
"""

import pytest
import re
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.services.auth_service import AuthenticationService


class TestPasswordResetUrlGeneration:
    """Test reset URL generation functionality."""

    def test_generate_reset_url_with_default_base_url(self, app):
        """Test that reset URL is generated with default base URL from config."""
        with app.app_context():
            token = "test_token_123"
            url = AuthenticationService._generate_reset_url(token)
            
            # URL should contain the token
            assert token in url
            assert "/auth/reset-password/" in url
            
            # Should match expected pattern
            pattern = r'^http://[^/]+/auth/reset-password/[^/]+$'
            assert re.match(pattern, url), f"URL {url} doesn't match expected pattern"

    def test_generate_reset_url_with_custom_base_url(self):
        """Test that reset URL can be generated with custom base URL."""
        token = "test_token_123"
        custom_base = "https://example.com"
        
        url = AuthenticationService._generate_reset_url(token, custom_base)
        
        expected = "https://example.com/auth/reset-password/test_token_123"
        assert url == expected

    def test_generate_reset_url_removes_trailing_slash(self):
        """Test that trailing slashes are removed from base URL."""
        token = "test_token_123"
        base_with_slash = "https://example.com/"
        
        url = AuthenticationService._generate_reset_url(token, base_with_slash)
        
        # Should not have double slashes
        assert "//" not in url.replace("https://", "").replace("http://", "")


class TestPasswordValidation:
    """Test password validation during reset."""

    def test_validate_password_minimum_length(self):
        """Test that passwords must be at least 8 characters."""
        is_valid, error = AuthenticationService.validate_password("Short1")
        assert not is_valid
        assert "8 characters" in error

    def test_validate_password_requires_uppercase(self):
        """Test that passwords require uppercase letters."""
        is_valid, error = AuthenticationService.validate_password("lowercase123")
        assert not is_valid
        assert "uppercase" in error

    def test_validate_password_requires_lowercase(self):
        """Test that passwords require lowercase letters."""
        is_valid, error = AuthenticationService.validate_password("UPPERCASE123")
        assert not is_valid
        assert "lowercase" in error

    def test_validate_password_requires_digit(self):
        """Test that passwords require at least one digit."""
        is_valid, error = AuthenticationService.validate_password("NoDigitsHere")
        assert not is_valid
        assert "digit" in error

    def test_validate_password_valid(self):
        """Test that valid passwords pass validation."""
        is_valid, error = AuthenticationService.validate_password("ValidPass123")
        assert is_valid
        assert error is None


class TestEmailSending:
    """Test email sending functionality."""

    @patch('smtplib.SMTP')
    def test_send_email_with_tls(self, mock_smtp):
        """Test sending email with TLS."""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        AuthenticationService._send_email(
            host="smtp.example.com",
            port=587,
            username="user",
            password="pass",
            use_tls=True,
            sender="from@example.com",
            recipient="to@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        # Verify SMTP was created with TLS
        mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_email_without_tls(self, mock_smtp_ssl):
        """Test sending email without TLS (using SSL)."""
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server
        
        AuthenticationService._send_email(
            host="smtp.example.com",
            port=465,
            username="user",
            password="pass",
            use_tls=False,
            sender="from@example.com",
            recipient="to@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        # Verify SMTP_SSL was used
        mock_smtp_ssl.assert_called_once_with("smtp.example.com", 465, timeout=10)
        mock_server.login.assert_called_once_with("user", "pass")


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_hash(self):
        """Test that password hashing returns a hash string."""
        password = "TestPassword123"
        password_hash = AuthenticationService.hash_password(password)
        
        # Should be a string
        assert isinstance(password_hash, str)
        # Should be longer than original password
        assert len(password_hash) > len(password)
        # Should contain hashing method info
        assert "pbkdf2" in password_hash or "scrypt" in password_hash or "argon2" in password_hash

    def test_verify_password_with_correct_password(self):
        """Test password verification with correct password."""
        password = "TestPassword123"
        password_hash = AuthenticationService.hash_password(password)
        
        assert AuthenticationService.verify_password(password_hash, password) is True

    def test_verify_password_with_wrong_password(self):
        """Test password verification with wrong password."""
        password = "TestPassword123"
        wrong_password = "WrongPassword123"
        password_hash = AuthenticationService.hash_password(password)
        
        assert AuthenticationService.verify_password(password_hash, wrong_password) is False


class TestUsernameAndEmailValidation:
    """Test username and email validation."""

    def test_validate_username_minimum_length(self):
        """Test that usernames must be at least 3 characters."""
        is_valid, error = AuthenticationService.validate_username("ab")
        assert not is_valid
        assert "3 characters" in error

    def test_validate_username_maximum_length(self):
        """Test that usernames must be less than 80 characters."""
        is_valid, error = AuthenticationService.validate_username("a" * 81)
        assert not is_valid
        assert "80 characters" in error

    def test_validate_username_invalid_characters(self):
        """Test that usernames can only contain allowed characters."""
        is_valid, error = AuthenticationService.validate_username("user@name")
        assert not is_valid
        assert "letters, numbers, underscores, and hyphens" in error

    def test_validate_username_valid(self):
        """Test valid username formats."""
        valid_usernames = [
            "john_doe",
            "jane-doe",
            "user123",
            "User_Name-123",
        ]
        for username in valid_usernames:
            is_valid, error = AuthenticationService.validate_username(username)
            assert is_valid, f"Username '{username}' should be valid"
            assert error is None

    def test_validate_email_invalid_format(self):
        """Test that invalid email formats are rejected."""
        invalid_emails = [
            "not-an-email",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
            "noat.symbol",
        ]
        for email in invalid_emails:
            is_valid, error = AuthenticationService.validate_email(email)
            assert not is_valid, f"Email '{email}' should be invalid"
            assert "Invalid email" in error

    def test_validate_email_valid(self):
        """Test valid email formats."""
        valid_emails = [
            "user@example.com",
            "user.name@example.co.uk",
            "user+tag@example.com",
            "first.last@company.io",
        ]
        for email in valid_emails:
            is_valid, error = AuthenticationService.validate_email(email)
            assert is_valid, f"Email '{email}' should be valid"
            assert error is None
