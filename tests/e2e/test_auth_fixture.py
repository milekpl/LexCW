"""The e2e suite authenticates by default. These tests prove it.

Nearly all 439 e2e tests obtain their browser from the `page` fixture, which now
carries a real logged-in session (see tests/e2e/conftest.py). If that quietly
degraded to an anonymous browser, the suite would keep passing today — the app
does not yet require auth — and then collapse the moment the auth gate lands,
with no clue why. So the property is asserted directly.
"""

import json

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.playwright
def test_page_fixture_is_authenticated(page: Page, app_url: str):
    """The default browser is signed in, via a real /auth/login round-trip."""
    page.goto(f"{app_url}/api/auth/check", wait_until="domcontentloaded")
    body = json.loads(page.inner_text("pre") if page.query_selector("pre") else page.content())

    assert body["authenticated"] is True, "the `page` fixture is not logged in"
    assert body["user"]["username"] == "e2e_tester"


@pytest.mark.e2e
@pytest.mark.playwright
def test_anonymous_page_fixture_is_not_authenticated(anonymous_page: Page, app_url: str):
    """`anonymous_page` is the opt-out, for tests asserting unauthenticated behaviour."""
    anonymous_page.goto(f"{app_url}/api/auth/check", wait_until="domcontentloaded")
    content = (
        anonymous_page.inner_text("pre")
        if anonymous_page.query_selector("pre")
        else anonymous_page.content()
    )
    body = json.loads(content)

    assert body["authenticated"] is False, "`anonymous_page` carried a session"


@pytest.mark.e2e
@pytest.mark.playwright
def test_authenticated_page_reaches_a_login_only_route(page: Page, app_url: str):
    """A route behind @login_required renders, rather than bouncing to the login page."""
    page.goto(f"{app_url}/auth/profile", wait_until="domcontentloaded")

    assert "/auth/login" not in page.url, "authenticated page was redirected to login"


@pytest.mark.e2e
@pytest.mark.playwright
def test_anonymous_page_is_redirected_from_a_login_only_route(anonymous_page: Page, app_url: str):
    """The same route bounces an anonymous browser, preserving the deep link."""
    anonymous_page.goto(f"{app_url}/auth/profile", wait_until="domcontentloaded")

    assert "/auth/login" in anonymous_page.url
    assert "next=" in anonymous_page.url, "the deep link was not preserved"
