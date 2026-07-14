"""The IPA draft button: the feature that started this, as the worked example.

The original report was "we trained the byT5 model, but the app says it's not
available". The model was fine. The request was returning 401, and the frontend
reported *any* response without `available: true` as a missing model — so an auth
failure was indistinguishable from an absent ML model, and the hunt went to the
wrong place entirely.

Two properties are pinned here, in a real browser:

1. Signed in, the button drafts an IPA.
2. Signed out, the user is told they are **signed out** — never that the model is
   unavailable. `available: false` must mean exactly one thing: there is no model.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page


def _draft_request(page: Page, app_url: str) -> dict:
    """Call the draft endpoint the way the button does, and report what came back."""
    return page.evaluate(
        """async (url) => {
            const response = await fetch(url + '/api/pronunciation/draft', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({headword: 'water', num_candidates: 1})
            });
            let body = null;
            try { body = await response.clone().json(); } catch (e) { body = null; }
            return {status: response.status, body: body};
        }""",
        app_url,
    )


@pytest.mark.e2e
@pytest.mark.playwright
def test_signed_in_user_can_draft_an_ipa(page: Page, app_url: str):
    """The happy path the user was denied for two days."""
    page.goto(f"{app_url}/", wait_until="domcontentloaded")

    result = _draft_request(page, app_url)

    assert result["status"] == 200, f"draft failed: {result}"
    body = result["body"]

    if body.get("available") is False:
        pytest.skip("no ByT5 model deployed in this environment")

    assert body["available"] is True
    assert body["candidates"], "an available model returned no candidates"


@pytest.mark.e2e
@pytest.mark.playwright
def test_signed_out_user_is_told_they_are_signed_out_not_that_the_model_is_missing(
    anonymous_page: Page, app_url: str
):
    """The regression that cost two days: a 401 must never look like a missing model.

    A caller that skips the status check — as every one of the 36 unchecked
    `fetch(...).then(r => r.json())` sites in this codebase does — must NOT receive
    a parseable body it can mistake for a result. auth.js rejects the request
    instead, with the server's own message, and sends the user to log in.
    """
    anonymous_page.goto(f"{app_url}/", wait_until="domcontentloaded")

    outcome = anonymous_page.evaluate(
        """async (url) => {
            try {
                // The exact shape of the original bug: no status check at all.
                const data = await fetch(url + '/api/pronunciation/draft', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({headword: 'water'})
                }).then(r => r.json());
                return {rejected: false, data: data};
            } catch (err) {
                return {rejected: true, message: err.message};
            }
        }""",
        app_url,
    )

    assert outcome["rejected"], (
        "an unauthenticated draft resolved to a body the caller can misread: "
        f"{outcome.get('data')!r} — this is exactly how a 401 became "
        '"ByT5 model not available"'
    )
    assert "Authentication required" in outcome["message"]
    assert "model" not in outcome["message"].lower(), (
        "the auth failure was described in terms of the ML model"
    )

    # And the user ends up somewhere they can do something about it. (With the gate
    # on they were already sent to login on the way in, so auth.js correctly does
    # not redirect a second time — assert the destination, not the navigation.)
    anonymous_page.wait_for_timeout(1000)
    assert "/auth/login" in anonymous_page.url, (
        f"signed-out user was left on {anonymous_page.url} with no way forward"
    )
