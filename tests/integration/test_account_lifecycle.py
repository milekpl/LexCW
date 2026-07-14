"""Section 5: password reset, session hardening, audit trail, key management.

All of this code existed and none of it ran. The reset flow was dead for the same
reason everything else was — `User.query` raised, so login was impossible and the
routes behind it were unreachable. Now that they are reachable, they get tested.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.models.project_settings import User
from app.models.user_models import ActivityLog
from app.models.workset_models import db
from app.services.auth_service import AuthenticationService

USERNAME = "lifecycle_tester"
EMAIL = "lifecycle@example.test"
PASSWORD = "original-password"


@pytest.fixture
def app():
    application = create_app("testing")
    application._tests_anonymous = True  # drives real login/logout
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def user(app):
    with app.app_context():
        account = User(
            username=USERNAME,
            email=EMAIL,
            password_hash=AuthenticationService.hash_password(PASSWORD),
            is_active=True,
        )
        db.session.add(account)
        db.session.commit()
        return account.id


def _token_for(app, user_id: int) -> str:
    with app.app_context():
        return User.query.get(user_id).reset_token


# --------------------------------------------------------------------------- #
# 5.1 Password reset
# --------------------------------------------------------------------------- #

def test_reset_issues_a_token_and_the_token_sets_a_new_password(app, user):
    with app.app_context():
        ok, _ = AuthenticationService.reset_password(EMAIL)
        assert ok

    token = _token_for(app, user)
    assert token, "no reset token was issued"

    with app.app_context():
        ok, error = AuthenticationService.complete_password_reset(token, "BrandNew1pass")
        assert ok, error

        assert AuthenticationService.authenticate_user(USERNAME, "BrandNew1pass")[0]
        assert AuthenticationService.authenticate_user(USERNAME, PASSWORD)[0] is None, (
            "the old password still works after a reset"
        )


def test_a_reset_token_works_only_once(app, user):
    with app.app_context():
        AuthenticationService.reset_password(EMAIL)
    token = _token_for(app, user)

    with app.app_context():
        AuthenticationService.complete_password_reset(token, "FirstPass1")

        ok, error = AuthenticationService.complete_password_reset(token, "SecondPass1")

        assert not ok, "a reset token was accepted twice"
        assert AuthenticationService.authenticate_user(USERNAME, "FirstPass1")[0]


def test_an_expired_token_is_refused(app, user):
    with app.app_context():
        AuthenticationService.reset_password(EMAIL)
        account = User.query.get(user)
        account.reset_token_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        token = account.reset_token

        ok, error = AuthenticationService.complete_password_reset(token, "TooLate1pass")

        assert not ok
        assert "expired" in (error or "").lower()


def test_a_second_reset_works_after_the_first_was_used(app, user):
    """Regression: `reset_token_used` was never cleared when issuing a new token.

    An interrupted reset would leave the flag set, and every future token would be
    refused as "already used" — locking the account out of password reset forever.
    """
    with app.app_context():
        AuthenticationService.reset_password(EMAIL)
    first = _token_for(app, user)
    with app.app_context():
        AuthenticationService.complete_password_reset(first, "PasswordOne1")

    with app.app_context():
        AuthenticationService.reset_password(EMAIL)
    second = _token_for(app, user)

    with app.app_context():
        ok, error = AuthenticationService.complete_password_reset(second, "PasswordTwo1")

        assert ok, f"a second password reset was refused: {error}"
        assert AuthenticationService.authenticate_user(USERNAME, "PasswordTwo1")[0]


def test_reset_for_an_unknown_email_does_not_reveal_that_it_is_unknown(app):
    with app.app_context():
        ok, message = AuthenticationService.reset_password("nobody@example.test")

        assert ok, "an unknown address was answered differently — that leaks the user list"
        assert "if the email exists" in (message or "").lower()


# --------------------------------------------------------------------------- #
# 5.2 Session hardening
# --------------------------------------------------------------------------- #

def test_session_cookie_is_not_readable_by_javascript(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_session_cookie_is_not_sent_cross_site(app):
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_sessions_expire(app):
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(days=14)


def test_production_requires_https_for_the_session_cookie():
    production = create_app("production")

    assert production.config["SESSION_COOKIE_SECURE"] is True, (
        "production would send the session cookie in the clear"
    )


def test_production_does_not_disable_csrf():
    """TestingConfig turns CSRF off, and config classes get copied."""
    production = create_app("production")

    assert production.config["WTF_CSRF_ENABLED"] is True


# --------------------------------------------------------------------------- #
# 5.4 Audit trail
# --------------------------------------------------------------------------- #

def test_a_failed_login_is_recorded(app, user):
    client = app.test_client()

    client.post("/auth/login", data={"username": USERNAME, "password": "wrong"})

    with app.app_context():
        logged = ActivityLog.query.filter_by(action="login_failed").all()
        assert logged, "a failed login left no trace — nothing would show a password-guessing attempt"
        assert logged[0].entity_id == USERNAME


def test_a_failed_login_for_an_unknown_user_is_still_recorded(app):
    client = app.test_client()

    client.post("/auth/login", data={"username": "ghost", "password": "x"})

    with app.app_context():
        logged = ActivityLog.query.filter_by(action="login_failed").all()
        assert logged
        assert logged[0].user_id is None
        assert logged[0].entity_id == "ghost"


def test_logout_is_recorded(app, user):
    client = app.test_client()
    client.post("/auth/login", data={"username": USERNAME, "password": PASSWORD})

    client.get("/auth/logout")

    with app.app_context():
        assert ActivityLog.query.filter_by(action="logout").all(), "logout left no trace"
