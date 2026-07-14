"""The auth contract: one decorator, one set of answers.

401 means "I don't know who you are". 403 means "I know who you are, and no".
Conflating them — as the old private `_require_auth` in app/api/pronunciation.py
did, returning 401 when a valid key merely lacked a scope — tells a caller to
retry with fresh credentials when the credentials were never the problem.

Also pins least privilege: an API key grants exactly the scopes it was issued.
An empty scope list used to mean *full access*.

See specs/auth_overhaul/auth_matrix.md and app/utils/auth_decorators.py.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.api.api_keys import _generate_api_key
from app.models.api_key import ApiKey
from app.models.project_settings import ProjectSettings
from app.models.workset_models import db

READ_ENDPOINT = "/api/pronunciation/draft"      # @require_auth("pronunciation:read")
READ_SCOPE = "pronunciation:read"

LABEL_PREFIX = "pytest-auth-contract"


@pytest.fixture(scope="module")
def app():
    application = create_app("development")
    application._tests_anonymous = True  # asserts 401/403 for anonymous callers
    application.config["WTF_CSRF_ENABLED"] = False  # CSRF is covered by test_csrf_policy
    return application


@pytest.fixture(scope="module")
def project_id(app):
    with app.app_context():
        project = ProjectSettings.query.first()
        if project is None:
            pytest.skip("development database has no project to mint keys for")
        return project.id


@pytest.fixture
def make_key(app, project_id):
    """Mint a real key with the given scopes; clean up afterwards."""
    created: list[str] = []

    def _make(scopes: list[str]) -> str:
        raw_key, key_hash, key_prefix = _generate_api_key()
        label = f"{LABEL_PREFIX}-{key_prefix}"
        with app.app_context():
            db.session.add(
                ApiKey(
                    project_id=project_id,
                    label=label,
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    scopes=scopes,
                    is_active=True,
                )
            )
            db.session.commit()
        created.append(label)
        return raw_key

    yield _make

    with app.app_context():
        ApiKey.query.filter(ApiKey.label.in_(created)).delete(synchronize_session=False)
        db.session.commit()


def _post(app, headers=None, session_user=None):
    client = app.test_client()
    if session_user is not None:
        with client.session_transaction() as session:
            session["user_id"] = session_user
    return client.post(READ_ENDPOINT, json={"headword": "water"}, headers=headers or {})


def test_no_credential_is_401(app):
    response = _post(app)

    assert response.status_code == 401
    assert response.get_json()["code"] == "authentication_required"


def test_unknown_key_is_401(app):
    response = _post(app, headers={"Authorization": "Bearer sw_not_a_real_key"})

    assert response.status_code == 401
    assert response.get_json()["code"] == "invalid_api_key"


def test_key_without_the_scope_is_403_not_401(app, make_key):
    """The regression: a real key lacking a scope is an authorization failure."""
    raw_key = make_key(["corpus:read"])  # valid key, wrong scope

    response = _post(app, headers={"Authorization": f"Bearer {raw_key}"})

    assert response.status_code == 403, "scope failure must not masquerade as 401"
    assert response.get_json()["code"] == "insufficient_scope"


def test_key_with_no_scopes_grants_nothing(app, make_key):
    """An empty scope list used to mean 'full access' — the opposite of least privilege."""
    raw_key = make_key([])

    response = _post(app, headers={"Authorization": f"Bearer {raw_key}"})

    assert response.status_code == 403
    assert response.get_json()["code"] == "insufficient_scope"


def test_revoked_key_is_401(app, make_key):
    raw_key = make_key([READ_SCOPE])
    with app.app_context():
        key = ApiKey.query.filter_by(key_prefix=raw_key[:11]).first()
        key.is_active = False
        db.session.commit()

    response = _post(app, headers={"Authorization": f"Bearer {raw_key}"})

    assert response.status_code == 401
    assert response.get_json()["code"] == "invalid_api_key"


def test_key_with_the_scope_succeeds(app, make_key):
    raw_key = make_key([READ_SCOPE])

    response = _post(app, headers={"Authorization": f"Bearer {raw_key}"})

    assert response.status_code == 200
    assert response.get_json()["available"] is True


def test_session_user_succeeds(app):
    response = _post(app, session_user=1)

    assert response.status_code == 200


def test_browser_navigation_redirects_to_login(app):
    """HTML callers get a login redirect that preserves the deep link, not JSON."""
    client = app.test_client()
    response = client.get("/auth/profile", headers={"Accept": "text/html"})

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_api_key_cannot_reach_management_endpoints(app, make_key):
    """Rule 1: a leaked key must not be able to mint further keys.

    Refused either by the gate (403 `api_key_not_permitted`, when REQUIRE_AUTH is on
    — the route never opted into key access) or by `login_required` (401, when it is
    off). What must never happen is that the key gets in.
    """
    raw_key = make_key([READ_SCOPE])

    client = app.test_client()
    response = client.get("/api/keys/", headers={"Authorization": f"Bearer {raw_key}"})

    assert response.status_code in (401, 403), "an API key authenticated to /api/keys"
    assert "keys" not in (response.get_json() or {}), "an API key listed the API keys"


def test_creating_a_key_requires_explicit_scopes(app):
    """Least privilege starts at issuance: no scopes chosen, no key."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1

    response = client.post("/api/keys/", json={"label": "no-scopes", "project_id": 1})

    assert response.status_code == 400
    assert "scopes" in response.get_json()["error"]
