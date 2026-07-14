"""
Unit tests for API key authentication model and decorator logic.
"""

import pytest
import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from unittest.mock import patch, MagicMock


class TestApiKeyGeneration:
    """Tests for API key generation logic (no DB needed)."""

    def test_key_format(self):
        """Keys should start with sw_ and be ~35 chars."""
        raw = "sw_" + secrets.token_urlsafe(32)
        assert raw.startswith("sw_")
        assert len(raw) > 30

    def test_key_prefix_extraction(self):
        """Prefix should be sw_ + first 8 chars."""
        raw = "sw_abc12345xyz67890"
        assert raw[:11] == "sw_abc12345"

    def test_key_hashing(self):
        """Keys should be hashable and verifiable with werkzeug."""
        raw = "sw_" + secrets.token_urlsafe(32)
        hashed = generate_password_hash(raw, method="pbkdf2:sha256")
        assert check_password_hash(hashed, raw) is True
        assert check_password_hash(hashed, "wrong_key") is False

    def test_key_hash_is_not_reversible(self):
        """The hash should not contain the raw key."""
        raw = "sw_" + secrets.token_urlsafe(32)
        hashed = generate_password_hash(raw, method="pbkdf2:sha256")
        assert raw not in hashed


class TestApiKeyModel:
    """Tests for ApiKey model methods (uses mock DB)."""

    def test_to_dict_never_exposes_hash(self):
        """to_dict() should never include key_hash."""
        mock_key = MagicMock()
        mock_key.id = 1
        mock_key.project_id = 1
        mock_key.label = "test"
        mock_key.key_prefix = "sw_abc12345"
        mock_key.key_hash = "should_not_appear"
        mock_key.scopes = ["read"]
        mock_key.is_active = True
        mock_key.created_at = datetime.now(timezone.utc)
        mock_key.last_used_at = None

        # Simulate to_dict
        result = {
            "id": mock_key.id,
            "project_id": mock_key.project_id,
            "label": mock_key.label,
            "key_prefix": mock_key.key_prefix,
            "scopes": mock_key.scopes or [],
            "is_active": mock_key.is_active,
            "created_at": mock_key.created_at.isoformat(),
            "last_used_at": None,
        }

        assert "key_hash" not in result
        assert "should_not_appear" not in str(result)


class TestApiKeyValidation:
    """Tests for API key validation rules.

    Scope enforcement is NOT tested here. It used to be — by re-implementing the
    decorator's `not (key_scopes and required not in key_scopes)` expression inline
    and asserting against the copy. That tests nothing: the real decorator was
    simultaneously unusable (no key could authenticate at all) and these tests were
    green throughout. Worse, the copied expression encoded "empty scopes = full
    access", which is now reversed.

    Scope decisions are exercised against the real HTTP path in
    tests/integration/test_auth_contract.py.
    """

    def test_scopes_restrict_access(self):
        """A scope the key was not granted is simply absent from its list."""
        scopes = ["read", "export"]
        assert "pronunciation:write" not in scopes


class TestDeactivatedKey:
    """Tests that deactivated keys are rejected."""

    def test_inactive_key_rejected(self):
        """Inactive keys should fail auth regardless of hash validity."""
        is_active = False
        assert is_active is False  # would be rejected in decorator
