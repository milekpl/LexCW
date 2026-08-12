"""
Display-profile API-key auth.

The old ``require_authentication`` decorator in ``app/api/display.py`` accepted ANY
non-empty API key when ``REQUIRE_API_AUTHENTICATION`` was set — a stub. It is replaced
with the real ``@require_auth("profiles:read"|"profiles:write")`` (same decorator the
pronunciation endpoints use): session user *or* a valid Bearer key holding the scope.
These tests pin the contract against the real HTTP path with real (hashed) keys.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.api.api_keys import _generate_api_key
from app.models.api_key import ApiKey
from app.models.workset_models import db


@pytest.fixture
def dclient(db_app):
    """Client for the db_app (SQLite) with the auth gate disabled."""
    db_app.config["REQUIRE_AUTH"] = False
    db_app.config["WTF_CSRF_ENABLED"] = False
    return db_app.test_client()


@pytest.fixture
def make_api_key(db_app):
    """Mint a real (hashed) API key with the given scopes; clean up afterwards."""
    created = []

    def _make(scopes):
        raw_key, key_hash, key_prefix = _generate_api_key()
        from app.models.project_settings import ProjectSettings

        project = ProjectSettings.query.first()
        if project is None:
            project = db_app.config_manager.create_settings(
                "Display Auth Test",
                basex_db_name="display_auth_test",
                settings_json={"source_language": {"code": "en", "name": "English"}},
            )
        key = ApiKey(
            project_id=project.id,
            label=f"display-auth-test-{key_prefix}",
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            is_active=True,
        )
        db.session.add(key)
        db.session.commit()
        created.append(key)
        return raw_key

    yield _make

    for key in created:
        db.session.delete(key)
    db.session.commit()


PUT_URL = "/api/display-profiles/999999"
PREVIEW_URL = "/api/display-profiles/entries/whatever/preview?profile_id=1"


class TestDisplayRoutesAuth:
    def test_anonymous_is_401(self, dclient):
        assert dclient.put(PUT_URL, json={"name": "x"}).status_code == 401
        assert dclient.delete(PUT_URL).status_code == 401
        assert dclient.get(PREVIEW_URL).status_code == 401

    def test_unknown_key_is_401(self, dclient):
        headers = {"Authorization": "Bearer sw_not_a_real_key"}
        assert dclient.put(PUT_URL, json={"name": "x"}, headers=headers).status_code == 401

    def test_x_api_key_header_no_longer_authenticates(self, dclient, make_api_key):
        """The old stub accepted any non-empty X-API-KEY; that must be gone."""
        make_api_key(["profiles:write"])
        headers = {"X-API-KEY": "anything-at-all"}
        resp = dclient.put(PUT_URL, json={"name": "x"}, headers=headers)
        assert resp.status_code == 401

    def test_key_without_scope_is_403(self, dclient, make_api_key):
        raw = make_api_key(["profiles:read"])
        headers = {"Authorization": f"Bearer {raw}"}
        resp = dclient.put(PUT_URL, json={"name": "x"}, headers=headers)
        assert resp.status_code == 403
        assert resp.get_json()["code"] == "insufficient_scope"

    def test_key_with_write_scope_passes(self, dclient, make_api_key):
        raw = make_api_key(["profiles:write"])
        headers = {"Authorization": f"Bearer {raw}"}
        # Auth passed → we reach the handler → profile simply doesn't exist.
        resp = dclient.put(PUT_URL, json={"name": "x"}, headers=headers)
        assert resp.status_code == 404

    def test_delete_with_write_scope_passes(self, dclient, make_api_key):
        raw = make_api_key(["profiles:write"])
        headers = {"Authorization": f"Bearer {raw}"}
        assert dclient.delete(PUT_URL, headers=headers).status_code == 404

    def test_preview_needs_read_scope(self, dclient, make_api_key):
        raw_write = make_api_key(["profiles:write"])
        assert dclient.get(
            PREVIEW_URL, headers={"Authorization": f"Bearer {raw_write}"}
        ).status_code == 403

        raw_read = make_api_key(["profiles:read"])
        # Auth passed → handler runs → profile does not exist.
        resp = dclient.get(PREVIEW_URL, headers={"Authorization": f"Bearer {raw_read}"})
        assert resp.status_code == 404

    def test_session_user_passes(self, dclient):
        dummy = MagicMock()
        dummy.id = 1
        dummy.username = "tester"
        dummy.is_admin = True
        with patch("app.utils.auth_decorators.get_current_user", return_value=dummy):
            # Auth passed → handler runs → profile does not exist.
            assert dclient.put(PUT_URL, json={"name": "x"}).status_code == 404


class TestAuthGateBoundary:
    def test_bearer_key_only_admitted_on_opted_in_routes(self, db_app, make_api_key):
        """The gate lets Bearer keys through ONLY routes flagged _accepts_api_key.

        update_profile is opted in (require_auth); get_audio_info is not — a Bearer
        key there is rejected by the gate itself with api_key_not_permitted.
        """
        raw = make_api_key(["profiles:write"])
        headers = {"Authorization": f"Bearer {raw}"}

        db_app.config["REQUIRE_AUTH"] = True
        client = db_app.test_client()

        # Flagged route: gate admits the key, decorator validates it → 404 (no profile).
        resp = client.put(PUT_URL, json={"name": "x"}, headers=headers)
        assert resp.status_code == 404

        # Unflagged route with a Bearer key → gate refuses, even with a valid key.
        resp_info = client.get("/api/pronunciation/info/whatever.mp3", headers=headers)
        assert resp_info.status_code == 403
        assert resp_info.get_json()["code"] == "api_key_not_permitted"


class TestLegacyReadRoutesGated:
    """display.py read routes are gated with profiles:read (parity with /api/profiles)."""

    def test_anonymous_is_401(self, dclient):
        assert dclient.get("/api/display-profiles").status_code == 401
        assert dclient.get("/api/display-profiles/1").status_code == 401
        assert dclient.get("/api/display-profiles/templates").status_code == 401
        assert dclient.post("/api/display-profiles/validate-css", json={}).status_code == 401
        assert dclient.post("/api/display-profiles/preview", json={}).status_code == 401

    def test_read_scope_can_list(self, dclient, make_api_key):
        raw = make_api_key(["profiles:read"])
        headers = {"Authorization": f"Bearer {raw}"}
        assert dclient.get("/api/display-profiles", headers=headers).status_code == 200
        assert dclient.get("/api/display-profiles/templates", headers=headers).status_code == 200

    def test_write_only_key_rejected_on_read(self, dclient, make_api_key):
        raw = make_api_key(["profiles:write"])
        resp = dclient.get(
            "/api/display-profiles", headers={"Authorization": f"Bearer {raw}"}
        )
        assert resp.status_code == 403
        assert resp.get_json()["code"] == "insufficient_scope"


class TestRemainingWriteRoutesGated:
    """The same blueprint's other write routes must not rely on the global gate."""

    def test_create_profile_requires_auth(self, dclient):
        body = {"name": "Unauth Profile", "elements": []}
        assert dclient.post("/api/display-profiles", json=body).status_code == 401

    def test_create_profile_requires_write_scope(self, dclient, make_api_key):
        body = {"name": "Scoped Profile", "elements": []}
        raw_read = make_api_key(["profiles:read"])
        resp = dclient.post(
            "/api/display-profiles", json=body,
            headers={"Authorization": f"Bearer {raw_read}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["code"] == "insufficient_scope"

        raw_write = make_api_key(["profiles:write"])
        resp = dclient.post(
            "/api/display-profiles", json=body,
            headers={"Authorization": f"Bearer {raw_write}"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "Scoped Profile"

    def test_apply_template_requires_auth(self, dclient):
        assert dclient.post(
            "/api/display-profiles/999999/apply-template", json={"template_id": "x"}
        ).status_code == 401

    def test_apply_template_requires_write_scope(self, dclient, make_api_key):
        raw = make_api_key(["profiles:write"])
        resp = dclient.post(
            "/api/display-profiles/999999/apply-template",
            json={"template_id": "x"},
            headers={"Authorization": f"Bearer {raw}"},
        )
        # Auth passed → handler runs → profile does not exist.
        assert resp.status_code == 404


class TestProfilesBlueprintAuth:
    """The /api/profiles blueprint (display_profiles.py) is gated the same way."""

    def test_anonymous_is_401(self, dclient):
        assert dclient.get("/api/profiles").status_code == 401
        assert dclient.post("/api/profiles", json={"name": "x"}).status_code == 401
        assert dclient.delete("/api/profiles/1").status_code == 401
        assert dclient.post("/api/profiles/import", json={}).status_code == 401

    def test_read_scope_can_list_but_not_write(self, dclient, make_api_key):
        raw = make_api_key(["profiles:read"])
        headers = {"Authorization": f"Bearer {raw}"}
        assert dclient.get("/api/profiles", headers=headers).status_code == 200
        resp = dclient.post("/api/profiles", json={"name": "x"}, headers=headers)
        assert resp.status_code == 403
        assert resp.get_json()["code"] == "insufficient_scope"

    def test_write_scope_can_create(self, dclient, make_api_key):
        raw = make_api_key(["profiles:write"])
        headers = {"Authorization": f"Bearer {raw}"}
        resp = dclient.post(
            "/api/profiles", json={"name": "Profiles BP Test", "elements": []}, headers=headers
        )
        assert resp.status_code in (200, 201)
        assert dclient.delete("/api/profiles/999999", headers=headers).status_code == 404
        assert dclient.post(
            "/api/profiles/999999/apply-template", json={"template_id": "x"}, headers=headers
        ).status_code == 404


class TestEntryIdInjectionGuard:
    """entry_id is never whitelisted — the XQuery builder escapes it centrally.

    Route guards were removed so space-containing GUIDs (the corpus format) are
    accepted; injection safety is enforced by build_entry_by_id_query (quotes
    doubled). These tests pin that: odd ids reach the lookup instead of a 400,
    and the escaping is verified at the builder level.
    """

    def test_preview_entry_accepts_space_containing_guid(self, db_app, make_api_key):
        from unittest.mock import MagicMock

        raw = make_api_key(["profiles:read"])
        headers = {"Authorization": f"Bearer {raw}"}
        db_app.config["REQUIRE_AUTH"] = False

        # No BaseX in unit tests: stub the injector so get_entry returns None.
        css = MagicMock()
        css.get_profile.return_value = MagicMock()
        dict_svc = MagicMock()
        dict_svc.get_entry.return_value = None
        real_injector = db_app.injector

        def _get(cls):
            name = getattr(cls, "__name__", str(cls))
            return css if name == "CSSMappingService" else dict_svc

        fake_injector = MagicMock()
        fake_injector.get.side_effect = _get
        db_app.injector = fake_injector
        try:
            resp = db_app.test_client().get(
                "/api/display-profiles/entries/00008ca0%2080a0%204d10%2091d1%20eb4bfff5db10"
                "/preview?profile_id=1",
                headers=headers,
            )
        finally:
            db_app.injector = real_injector

        # Auth passed, lookup reached with the space-containing id (no 400).
        assert resp.status_code == 404

    def test_preview_entry_injection_payload_reaches_escaped_lookup(self, db_app, make_api_key):
        from unittest.mock import MagicMock

        raw = make_api_key(["profiles:read"])
        headers = {"Authorization": f"Bearer {raw}"}
        db_app.config["REQUIRE_AUTH"] = False

        css = MagicMock()
        css.get_profile.return_value = MagicMock()
        dict_svc = MagicMock()
        dict_svc.get_entry.return_value = None
        real_injector = db_app.injector

        def _get(cls):
            name = getattr(cls, "__name__", str(cls))
            return css if name == "CSSMappingService" else dict_svc

        fake_injector = MagicMock()
        fake_injector.get.side_effect = _get
        db_app.injector = fake_injector
        try:
            resp = db_app.test_client().get(
                '/api/display-profiles/entries/x%22%20or%201%3D1%20--/preview?profile_id=1',
                headers=headers,
            )
            # The payload reached get_entry (escaped by the query builder), which
            # found nothing → 404. It is NOT a 400 and NOT a 500 leak.
            assert resp.status_code == 404
            got_id = dict_svc.get_entry.call_args[0][0]
            assert '"' in got_id  # the raw quote payload flowed through unblocked
        finally:
            db_app.injector = real_injector

    def test_preview_profile_accepts_space_and_quote_ids(self, dclient, make_api_key):
        raw = make_api_key(["profiles:read"])
        headers = {"Authorization": f"Bearer {raw}"}
        # Space GUID: no match in DB → sample fallback renders HTML (no 400).
        resp = dclient.post(
            "/api/profiles/preview",
            json={"elements": [], "entry_id": "00008ca0 80a0 4d10 91d1 eb4bfff5db10"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "html" in resp.get_json()
        # Quote payload: escaped by the builder, no match → sample fallback (no 400/500).
        resp2 = dclient.post(
            "/api/profiles/preview",
            json={"elements": [], "entry_id": '" or 1=1 --'},
            headers=headers,
        )
        assert resp2.status_code == 200
        assert "html" in resp2.get_json()


class TestPreviewAliasDelegation:
    """/api/display-profiles/preview delegates to the shared impl (auth once)."""

    def test_display_alias_preview_works_with_read_key(self, dclient, make_api_key):
        raw = make_api_key(["profiles:read"])
        resp = dclient.post(
            "/api/display-profiles/preview",
            json={"elements": [], "entry_id": "entry-123"},
            headers={"Authorization": f"Bearer {raw}"},
        )
        assert resp.status_code == 200
        assert "html" in resp.get_json()
