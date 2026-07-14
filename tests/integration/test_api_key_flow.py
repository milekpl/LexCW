"""The API key lifecycle, end to end over HTTP: mint -> use -> revoke -> reactivate.

This is the path that nothing tested, and all three original API-key bugs lived in
it:

* `key_prefix` was VARCHAR(8) while prefixes are 11 chars, so **no key could ever
  be created** (Postgres StringDataRightTruncation).
* Creation hashed `raw` but stored the prefix as `"sw_" + raw[:8]`, while
  verification hashed the `sw_`-prefixed string — so even a key that *was* created
  could never authenticate.
* CSRF rejected every Bearer write before auth even ran.

`tests/unit/test_api_key_auth.py` was green throughout, because it tested hashing
and scope logic in isolation with hand-built prefixes: it never called
`_generate_api_key()`, never inserted a row, and never made a request. Hence this
file — every test here goes through the real endpoints.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.models.api_key import ApiKey
from app.models.project_settings import ProjectSettings
from app.models.workset_models import db

DRAFT = "/api/pronunciation/draft"   # @require_auth("pronunciation:read")
LABEL = "pytest-key-flow"


@pytest.fixture(scope="module")
def app():
    application = create_app("development")
    application._tests_anonymous = True  # session is set explicitly where needed
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture(scope="module")
def project_id(app):
    with app.app_context():
        project = ProjectSettings.query.first()
        if project is None:
            pytest.skip("development database has no project to mint keys for")
        return project.id


@pytest.fixture
def admin_client(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
    return client


@pytest.fixture
def created_key(app, admin_client, project_id):
    """Mint a key through the real endpoint, and clean up after."""
    response = admin_client.post(
        "/api/keys/",
        json={"label": LABEL, "project_id": project_id, "scopes": ["pronunciation:read"]},
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    payload = response.get_json()["key"]

    yield payload

    with app.app_context():
        ApiKey.query.filter_by(label=LABEL).delete()
        db.session.commit()


def _draft_with(app, raw_key):
    """Call a protected endpoint with the key, from a client with no session."""
    return app.test_client().post(
        DRAFT,
        json={"headword": "water"},
        headers={"Authorization": f"Bearer {raw_key}"},
    )


def test_creating_a_key_returns_the_raw_key_exactly_once(created_key, admin_client):
    """The raw key is shown at creation and never again."""
    assert created_key["raw_key"].startswith("sw_")
    assert created_key["key_prefix"] == created_key["raw_key"][:11]

    listed = admin_client.get("/api/keys/").get_json()["keys"]
    mine = next(key for key in listed if key["label"] == LABEL)

    assert "raw_key" not in mine, "the raw key was returned again after creation"
    assert "key_hash" not in mine, "the key hash was exposed over the API"


def test_a_minted_key_authenticates_from_a_session_less_client(app, created_key):
    """The whole point: a script with only the key can call the API."""
    response = _draft_with(app, created_key["raw_key"])

    assert response.status_code == 200
    assert response.get_json()["available"] is True


def test_using_a_key_records_last_used_at(app, created_key):
    with app.app_context():
        before = ApiKey.query.filter_by(label=LABEL).first().last_used_at
    assert before is None, "a freshly minted key should never have been used"

    _draft_with(app, created_key["raw_key"])

    with app.app_context():
        after = ApiKey.query.filter_by(label=LABEL).first().last_used_at
    assert after is not None, "last_used_at was not recorded — no audit trail for keys"


def test_revoking_a_key_stops_it_working(app, admin_client, created_key):
    assert _draft_with(app, created_key["raw_key"]).status_code == 200

    revoke = admin_client.delete(f"/api/keys/{created_key['id']}")
    assert revoke.status_code == 200, revoke.get_data(as_text=True)

    response = _draft_with(app, created_key["raw_key"])
    assert response.status_code == 401, "a revoked key still worked"
    assert response.get_json()["code"] == "invalid_api_key"


def test_reactivating_a_key_restores_it(app, admin_client, created_key):
    admin_client.delete(f"/api/keys/{created_key['id']}")
    assert _draft_with(app, created_key["raw_key"]).status_code == 401

    reactivate = admin_client.post(f"/api/keys/{created_key['id']}/reactivate")
    assert reactivate.status_code == 200, reactivate.get_data(as_text=True)

    assert _draft_with(app, created_key["raw_key"]).status_code == 200


def test_offered_scopes_are_the_ones_the_app_actually_enforces(app, admin_client):
    """The management page must not offer scopes that do nothing.

    It used to advertise `read`, `export` and `pronunciation:validate` — none of
    which any endpoint has ever checked, so a key granted them could do exactly
    nothing. The list is now read off the routes themselves.
    """
    offered = set(admin_client.get("/api/keys/scopes").get_json()["scopes"])

    enforced = {
        view._required_scope
        for view in app.view_functions.values()
        if getattr(view, "_required_scope", None)
    }

    assert offered == enforced
    assert "pronunciation:read" in offered, "a scope the app enforces was not offered"
    assert "export" not in offered, "a scope no endpoint checks was offered"


def test_key_events_are_audited(app, admin_client, created_key):
    """A key outlives the session that made it; issuing and revoking are recorded."""
    from app.models.user_models import ActivityLog

    admin_client.delete(f"/api/keys/{created_key['id']}")

    with app.app_context():
        actions = {
            log.action
            for log in ActivityLog.query.filter_by(
                entity_type="api_key", entity_id=str(created_key["id"])
            ).all()
        }

    assert "api_key_created" in actions
    assert "api_key_revoked" in actions


def test_a_tampered_key_is_rejected(app, created_key):
    """The prefix identifies the key; the hash proves it. Changing the secret fails."""
    raw = created_key["raw_key"]
    tampered = raw[:11] + "x" * (len(raw) - 11)   # right prefix, wrong secret

    response = _draft_with(app, tampered)

    assert response.status_code == 401
    assert response.get_json()["code"] == "invalid_api_key"
