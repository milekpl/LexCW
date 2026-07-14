"""The CSRF policy is one rule, applied uniformly. These tests keep it that way.

    A state-changing request must carry a CSRF token, unless it authenticates
    with `Authorization: Bearer` (an API key).

No endpoint is exempt. The policy used to be a patchwork of per-blueprint
`csrf.exempt(...)` calls, which left 29 session-authenticated write routes with
no CSRF protection at all, while simultaneously making API keys unusable for
writes. Both failure modes are pinned below.

See docs/CSRF_POLICY.md.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.models.api_key import ApiKey
from app.models.project_settings import ProjectSettings
from app.models.workset_models import db


def _csrf_blocked(response) -> bool:
    return response.status_code == 400 and b"CSRF" in response.data


@pytest.fixture(scope="module")
def csrf_app():
    """App with CSRF on, as in development/production (TestingConfig disables it)."""
    application = create_app("development")
    application._tests_anonymous = True  # asserts CSRF/auth refusals
    return application


@pytest.fixture(scope="module")
def api_key(csrf_app):
    from app.api.api_keys import _generate_api_key

    with csrf_app.app_context():
        project = ProjectSettings.query.first()
        if project is None:
            pytest.skip("development database has no project to mint a key for")

        raw_key, key_hash, key_prefix = _generate_api_key()
        db.session.add(
            ApiKey(
                project_id=project.id,
                label="pytest-csrf-policy",
                key_hash=key_hash,
                key_prefix=key_prefix,
                scopes=["pronunciation:read"],
                is_active=True,
            )
        )
        db.session.commit()

    yield raw_key

    with csrf_app.app_context():
        ApiKey.query.filter_by(label="pytest-csrf-policy").delete()
        db.session.commit()


def test_no_endpoint_is_csrf_exempt(csrf_app):
    """The rule is uniform: nothing opts out.

    Guards the regression directly — `csrf.exempt(validation_bp)` and friends once
    left 29 write routes unprotected, and `csrf.exempt(api_bp)` sat one refactor
    away from exempting the entire /api surface.
    """
    csrf = csrf_app.extensions["csrf"]

    assert not csrf._exempt_blueprints, (
        "a blueprint was made CSRF-exempt; the policy allows no exemptions — "
        "the browser side is handled once in static/js/csrf.js"
    )
    assert not csrf._exempt_views, (
        "a view was made CSRF-exempt; the policy allows no exemptions"
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/validation/validate-entry",   # was exempt via validation_bp
        "/api/dashboard/clear-cache",       # was exempt via dashboard_bp
        "/api/entries/",                    # never exempt; must stay protected
    ],
)
def test_session_write_requires_csrf_token(csrf_app, path):
    """Cookie auth is ambient, so every state-changing route demands a token."""
    client = csrf_app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1

    response = client.post(path, json={})

    assert _csrf_blocked(response), f"{path} accepted a session write with no CSRF token"


def test_bearer_write_is_exempt_without_a_token(csrf_app, api_key):
    """A Bearer token is not an ambient credential, so CSRF does not apply."""
    client = csrf_app.test_client()  # no session cookie at all
    response = client.post(
        "/api/pronunciation/draft",
        json={"headword": "water"},
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert not _csrf_blocked(response), "Bearer request was rejected by CSRF"
    assert response.status_code == 200


def test_bearer_exemption_does_not_bypass_authentication(csrf_app):
    """Skipping CSRF for Bearer must not let an invalid key through."""
    client = csrf_app.test_client()
    response = client.post(
        "/api/pronunciation/draft",
        json={"headword": "water"},
        headers={"Authorization": "Bearer sw_not_a_real_key"},
    )

    assert response.status_code == 401
