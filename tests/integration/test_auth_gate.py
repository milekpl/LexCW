"""The auth gate: everything requires identity unless it is on the allowlist.

The gate is the security boundary for 441 routes, so the properties that matter are
pinned here — above all that it **fails closed**. A route nobody remembered to
protect must be protected anyway; that is the whole reason the gate exists instead
of 441 decorators.

Enabled per-app via REQUIRE_AUTH (see app/auth_gate.py). These tests switch it on
explicitly; the rest of the suite is unaffected until the flag is flipped by default.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.api.api_keys import _generate_api_key
from app.auth_gate import PUBLIC_ENDPOINTS, REGISTRATION_ENDPOINTS
from app.models.api_key import ApiKey
from app.models.project_settings import ProjectSettings
from app.models.workset_models import db

KEY_ROUTE = "/api/pronunciation/draft"     # opted into API keys via @require_auth
SESSION_ONLY_ROUTE = "/api/entries/"       # no @require_auth -> session only
LABEL = "pytest-auth-gate"


def _gated_app(**config):
    app = create_app("development")
    app._tests_anonymous = True  # this suite asserts the door is locked
    app.config["WTF_CSRF_ENABLED"] = False   # CSRF is covered by test_csrf_policy
    app.config["REQUIRE_AUTH"] = True
    app.config.update(config)
    return app


@pytest.fixture(scope="module")
def app():
    return _gated_app()


@pytest.fixture(scope="module")
def api_key(app):
    """A real key scoped for the draft endpoint."""
    with app.app_context():
        project = ProjectSettings.query.first()
        if project is None:
            pytest.skip("development database has no project to mint a key for")

        raw_key, key_hash, key_prefix = _generate_api_key()
        db.session.add(
            ApiKey(
                project_id=project.id,
                label=LABEL,
                key_hash=key_hash,
                key_prefix=key_prefix,
                scopes=["pronunciation:read"],
                is_active=True,
            )
        )
        db.session.commit()

    yield raw_key

    with app.app_context():
        ApiKey.query.filter_by(label=LABEL).delete()
        db.session.commit()


def _anon(app):
    return app.test_client()


def _session(app, user_id=1):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = user_id
    return client


# --------------------------------------------------------------------------- #
# The allowlist
# --------------------------------------------------------------------------- #

def test_allowlisted_endpoints_all_exist(app):
    """A typo in the allowlist is a silently protected route (or a stale name)."""
    known = {rule.endpoint for rule in app.url_map.iter_rules()}
    unknown = (PUBLIC_ENDPOINTS | REGISTRATION_ENDPOINTS) - known

    assert not unknown, f"allowlist names endpoints that do not exist: {sorted(unknown)}"


@pytest.mark.parametrize("path", ["/health", "/auth/login"])
def test_public_routes_are_reachable_anonymously(app, path):
    assert _anon(app).get(path).status_code == 200


def test_auth_check_is_public_and_answers_no(app):
    """Its whole job is to be callable when you are *not* signed in."""
    response = _anon(app).get("/api/auth/check")

    assert response.status_code == 200
    assert response.get_json()["authenticated"] is False


# --------------------------------------------------------------------------- #
# Everything else
# --------------------------------------------------------------------------- #

def test_anonymous_api_call_is_401_json(app):
    response = _anon(app).post(SESSION_ONLY_ROUTE, json={})

    assert response.status_code == 401
    assert response.get_json()["code"] == "authentication_required"


def test_anonymous_page_redirects_to_login_preserving_the_deep_link(app):
    response = _anon(app).get("/", headers={"Accept": "text/html"})

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"]


def test_session_user_passes_the_gate(app):
    response = _session(app).get("/", headers={"Accept": "text/html"})

    assert response.status_code == 200


def test_gate_fails_closed_for_a_route_nobody_protected():
    """The point of the gate: a new, undecorated route is protected by default.

    With 441 routes across 47 blueprints, the decorator you forget is a silent
    hole. Here nothing was done to this route at all — no decorator, no allowlist
    entry, no thought — and it is still shut.

    (Fresh app: Flask refuses to add routes once a request has been handled.)
    """
    probe_app = _gated_app()
    probe_app.add_url_rule(
        "/__gate_probe__",
        endpoint="_gate_probe",
        view_func=lambda: "secret",
    )

    response = probe_app.test_client().get("/__gate_probe__")

    assert response.status_code in (401, 302), "an unprotected route was reachable"
    assert b"secret" not in response.data


# --------------------------------------------------------------------------- #
# API keys reach only what opted in (auth matrix, rule 1)
# --------------------------------------------------------------------------- #

def test_api_key_reaches_a_route_that_opted_in(app, api_key):
    response = _anon(app).post(
        KEY_ROUTE,
        json={"headword": "water"},
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200


def test_api_key_is_refused_on_a_session_only_route(app, api_key):
    """A leaked key must not wander into endpoints nobody exposed to machines."""
    response = _anon(app).post(
        SESSION_ONLY_ROUTE,
        json={},
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 403
    assert response.get_json()["code"] == "api_key_not_permitted"


def test_api_key_cannot_mint_another_key(app, api_key):
    response = _anon(app).post(
        "/api/keys/",
        json={"label": "escalation", "project_id": 1, "scopes": ["entries:write"]},
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# Registration policy (decision D1)
# --------------------------------------------------------------------------- #

def test_registration_is_closed_by_default(app):
    response = _anon(app).get("/auth/register", headers={"Accept": "text/html"})

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_registration_is_public_when_enabled():
    open_app = _gated_app(ALLOW_REGISTRATION=True)

    response = open_app.test_client().get("/auth/register")

    assert response.status_code == 200
