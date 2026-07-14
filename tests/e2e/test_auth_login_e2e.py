"""Login, driven through the actual form in a real browser.

This is the test whose absence let the whole thing rot. Login was impossible for
months — `User.query` raised `UndefinedColumn` because the `users` table lacked
`reset_token_used`, so `get_current_user()` could never succeed — and nothing
noticed, because nothing ever logged in.

The `page` fixture authenticates via a real login round-trip, so in a sense the
suite exercises login constantly. But a fixture is allowed to be clever; this file
is not. It clicks the form.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from tests.e2e.conftest import E2E_PASSWORD, E2E_USERNAME

LOGIN_FORM_SUBMIT = 'form:has(input[name="password"]) button[type="submit"]'


def _log_in(page: Page, app_url: str, username: str, password: str) -> None:
    page.goto(f"{app_url}/auth/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    # Scoped to the login form on purpose: base.html renders a navbar search form
    # first, so a bare button[type="submit"] hits *that* and navigates to /search
    # without logging in — while still leaving /auth/login, which is why a
    # URL-based assertion is not enough to prove login worked.
    page.click(LOGIN_FORM_SUBMIT)
    page.wait_for_load_state("networkidle")


def _is_authenticated(page: Page, app_url: str) -> bool:
    page.goto(f"{app_url}/api/auth/check", wait_until="domcontentloaded")
    import json

    return json.loads(page.inner_text("body")).get("authenticated") is True


@pytest.mark.e2e
@pytest.mark.playwright
def test_login_with_valid_credentials_starts_a_session(anonymous_page: Page, app_url, e2e_user):
    _log_in(anonymous_page, app_url, E2E_USERNAME, E2E_PASSWORD)

    assert _is_authenticated(anonymous_page, app_url), "valid credentials did not sign the user in"


@pytest.mark.e2e
@pytest.mark.playwright
def test_login_with_wrong_password_is_refused(anonymous_page: Page, app_url, e2e_user):
    _log_in(anonymous_page, app_url, E2E_USERNAME, "definitely-not-the-password")

    assert "/auth/login" in anonymous_page.url, "a bad password navigated away from the login page"
    assert not _is_authenticated(anonymous_page, app_url), "a bad password signed the user in"


@pytest.mark.e2e
@pytest.mark.playwright
def test_login_with_unknown_user_is_refused(anonymous_page: Page, app_url, e2e_user):
    _log_in(anonymous_page, app_url, "no-such-person", "whatever")

    assert not _is_authenticated(anonymous_page, app_url)


@pytest.mark.e2e
@pytest.mark.playwright
def test_disabled_account_cannot_log_in(anonymous_page: Page, app_url, configured_flask_app, e2e_user):
    """is_active=False must actually keep someone out."""
    app, _ = configured_flask_app
    disabled_username = "disabled_tester"
    password = "disabled-pw"

    with app.app_context():
        from app.models.project_settings import User
        from app.models.workset_models import db
        from app.services.auth_service import AuthenticationService

        user = User.query.filter_by(username=disabled_username).first()
        if user is None:
            user = User(username=disabled_username, email="disabled@example.test")
            db.session.add(user)
        user.password_hash = AuthenticationService.hash_password(password)
        user.is_active = False
        db.session.commit()

    _log_in(anonymous_page, app_url, disabled_username, password)

    assert not _is_authenticated(anonymous_page, app_url), "a disabled account was allowed in"


@pytest.mark.e2e
@pytest.mark.playwright
def test_logout_ends_the_session(anonymous_page: Page, app_url, e2e_user):
    _log_in(anonymous_page, app_url, E2E_USERNAME, E2E_PASSWORD)
    assert _is_authenticated(anonymous_page, app_url)

    anonymous_page.goto(f"{app_url}/auth/logout", wait_until="networkidle")

    assert not _is_authenticated(anonymous_page, app_url), "the session survived logout"


@pytest.mark.e2e
@pytest.mark.playwright
def test_deep_link_survives_the_login_round_trip(anonymous_page: Page, app_url, e2e_user):
    """Visit a protected page while signed out; come back to it after signing in."""
    anonymous_page.goto(f"{app_url}/auth/profile", wait_until="domcontentloaded")

    assert "/auth/login" in anonymous_page.url, "protected page did not redirect"
    assert "next=" in anonymous_page.url, "the deep link was dropped"

    anonymous_page.fill('input[name="username"]', E2E_USERNAME)
    anonymous_page.fill('input[name="password"]', E2E_PASSWORD)
    anonymous_page.click(LOGIN_FORM_SUBMIT)
    anonymous_page.wait_for_load_state("networkidle")

    assert "/auth/profile" in anonymous_page.url, (
        f"after login the user landed on {anonymous_page.url}, not the page they asked for"
    )


@pytest.mark.e2e
@pytest.mark.playwright
def test_losing_the_session_cookie_sends_you_back_to_login(anonymous_page: Page, app_url, e2e_user):
    """Session expiry, as the browser experiences it: the cookie is gone."""
    _log_in(anonymous_page, app_url, E2E_USERNAME, E2E_PASSWORD)
    assert _is_authenticated(anonymous_page, app_url)

    anonymous_page.context.clear_cookies()

    anonymous_page.goto(f"{app_url}/auth/profile", wait_until="domcontentloaded")

    assert "/auth/login" in anonymous_page.url, "an expired session still reached a protected page"
