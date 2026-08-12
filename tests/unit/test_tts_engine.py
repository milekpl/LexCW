"""
Unit tests for the TTS engine plugin framework.

Covers: registry, per-engine config resolution (settings_json → env → defaults),
audio storage (safe filenames, containment, save/exists, legacy migration), the
Google Cloud engine's SSML IPA construction (no network), and the
POST /api/pronunciation/generate endpoint using a fake engine (no network).
"""

import os

import pytest
from unittest.mock import MagicMock, patch

from app.services.tts.base import TTSEngine, TTSOptions, TTSResult, TTSEngineError
from app.services.tts.registry import TTSEngineRegistry, get_engine, list_engines
from app.services.tts.config import get_engine_config, engine_enabled
from app.services.tts import audio_storage
from app.services.tts.engines.google_cloud import GoogleCloudTTSEngine


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_google_cloud_registered(self):
        cls = TTSEngineRegistry.get("google_cloud")
        assert cls is not None
        assert cls.engine_id == "google_cloud"
        assert cls.supports_ipa is True
        assert cls.supports_text is True

    def test_list_engines_descriptors(self):
        engines = list_engines()
        assert any(e["engine_id"] == "google_cloud" for e in engines)

    def test_unknown_engine_returns_none(self):
        assert TTSEngineRegistry.get("does_not_exist") is None
        assert get_engine("does_not_exist") is None

    def test_register_requires_engine_id(self):
        class BadEngine(TTSEngine):
            engine_id = ""

            def synthesize(self, options):
                raise NotImplementedError

        with pytest.raises(ValueError):
            TTSEngineRegistry.register(BadEngine)


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


class TestConfigResolution:
    def test_defaults_when_nothing_configured(self, monkeypatch):
        for var in ("TTS_GOOGLE_ENABLED", "TTS_GOOGLE_VOICE", "TTS_GOOGLE_LANGUAGE_CODE",
                    "TTS_GOOGLE_CREDENTIALS_JSON"):
            monkeypatch.delenv(var, raising=False)
        cfg = get_engine_config("google_cloud")
        assert cfg["enabled"] is False
        assert cfg["voice"] == "en-GB-Standard-D"
        assert cfg["language_code"] == "en-GB"

    def test_env_overrides_defaults(self, monkeypatch):
        monkeypatch.setenv("TTS_GOOGLE_ENABLED", "true")
        monkeypatch.setenv("TTS_GOOGLE_VOICE", "en-US-Studio-Q")
        monkeypatch.setenv("TTS_GOOGLE_LANGUAGE_CODE", "en-US")
        cfg = get_engine_config("google_cloud")
        assert cfg["enabled"] is True
        assert cfg["voice"] == "en-US-Studio-Q"
        assert cfg["language_code"] == "en-US"
        assert engine_enabled("google_cloud") is True

    def test_env_false_bool(self, monkeypatch):
        monkeypatch.setenv("TTS_GOOGLE_ENABLED", "false")
        assert engine_enabled("google_cloud") is False

    def test_project_settings_stored_override_defaults(self, db_app):
        from flask import current_app
        from app.models.project_settings import ProjectSettings

        with db_app.app_context():
            cm = current_app.config_manager
            settings = cm.create_settings(
                project_name="TTS Test",
                basex_db_name="tts_test_db",
                settings_json={"source_language": {"code": "en", "name": "English"}},
            )
            raw = settings.settings_json or {}
            raw["tts"] = {
                "google_cloud": {
                    "enabled": True,
                    "credentials_json": '{"type": "service_account"}',
                    "voice": "en-GB-Standard-D",
                    "language_code": "en-GB",
                }
            }
            settings.settings_json = raw
            from app.models.workset_models import db

            db.session.commit()
            assert settings.id is not None

            cfg = get_engine_config("google_cloud")
            assert cfg["enabled"] is True
            assert cfg["credentials_json"] == '{"type": "service_account"}'

    def test_config_manager_update_current_settings_stores_tts(self, db_app):
        from flask import current_app

        with db_app.app_context():
            cm = current_app.config_manager
            saved = cm.update_current_settings({
                "tts": {
                    "google_cloud": {
                        "enabled": True,
                        "credentials_json": "",
                        "voice": "en-GB-Standard-D",
                        "language_code": "en-GB",
                    }
                }
            })
            raw = saved.settings_json or {}
            assert raw["tts"]["google_cloud"]["enabled"] is True
            # Round-trips through get_engine_config
            assert get_engine_config("google_cloud")["enabled"] is True


# ---------------------------------------------------------------------------
# Audio storage
# ---------------------------------------------------------------------------


class TestAudioStorage:
    def test_safe_filename_rejects_paths(self):
        assert audio_storage.safe_filename("file.mp3") == "file.mp3"
        assert audio_storage.safe_filename("../../etc/passwd") is None
        assert audio_storage.safe_filename("/abs/path.mp3") is None
        assert audio_storage.safe_filename("") is None
        assert audio_storage.safe_filename("..") is None
        assert audio_storage.safe_filename("a/b.mp3") is None
        assert audio_storage.safe_filename("..\\evil.mp3") is None

    def test_resolve_rejects_nested_filenames(self, tmp_path, monkeypatch):
        monkeypatch.setattr(audio_storage, "get_storage_root", lambda: tmp_path)
        assert audio_storage.resolve_audio_path("nested/x.mp3") is None
        assert audio_storage.resolve_audio_path("../../etc/passwd") is None

    def test_save_and_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(audio_storage, "get_storage_root", lambda: tmp_path)
        saved = audio_storage.save_audio("probe.mp3", b"\xff\xfb data", project_db="unit")
        assert saved is not None and saved.is_file()
        assert audio_storage.audio_exists("probe.mp3", project_db="unit")
        assert not audio_storage.audio_exists("missing.mp3", project_db="unit")

    def test_migrate_legacy_audio(self, tmp_path, monkeypatch):
        legacy = tmp_path / "legacy_audio"
        legacy.mkdir()
        (legacy / "old1.mp3").write_bytes(b"\xff\xfb legacy")
        (legacy / "old2.mp3").write_bytes(b"\xff\xfb legacy2")
        (legacy / "skip_me.txt").write_bytes(b"not audio")
        monkeypatch.setattr(audio_storage, "get_storage_root", lambda: tmp_path / "root")

        copied = audio_storage.migrate_legacy_audio(static_audio_dir=legacy)
        assert copied == 2
        assert (tmp_path / "root" / "dictionary" / "old1.mp3").is_file()
        assert (tmp_path / "root" / "dictionary" / "old2.mp3").is_file()
        # Idempotent: second run copies nothing new
        assert audio_storage.migrate_legacy_audio(static_audio_dir=legacy) == 0


# ---------------------------------------------------------------------------
# Google engine (no network)
# ---------------------------------------------------------------------------


class TestGoogleEngine:
    def test_validate_config_disabled(self):
        engine = GoogleCloudTTSEngine({"enabled": False})
        assert "disabled" in (engine.validate_config() or "")

    def test_synthesize_uses_ipa_phoneme(self):
        engine = GoogleCloudTTSEngine({"enabled": True, "voice": "en-GB-Standard-D",
                                       "language_code": "en-GB"})
        client = MagicMock()
        tts = MagicMock()
        engine._client = client
        engine._tts = tts

        result = engine.synthesize(TTSOptions(text="tree", ipa="triː"))
        tts.SynthesisInput.assert_called_once_with(
            ssml='<speak><phoneme alphabet="ipa" ph="triː">tree</phoneme></speak>'
        )
        tts.VoiceSelectionParams.assert_called_once_with(
            language_code="en-GB", name="en-GB-Standard-D"
        )
        tts.AudioConfig.assert_called_once()
        assert result.engine_id == "google_cloud"

    def test_synthesize_escapes_ipa_attribute(self):
        engine = GoogleCloudTTSEngine({"enabled": True})
        client = MagicMock()
        engine._client = client
        engine._tts = MagicMock()
        engine.synthesize(TTSOptions(text='say "hi"', ipa='a"b'))
        args, kwargs = engine._tts.SynthesisInput.call_args
        ssml = kwargs.get("ssml", args[0] if args else None)
        assert 'ph="a&quot;b"' in ssml

    def test_synthesize_falls_back_to_plain_text(self):
        engine = GoogleCloudTTSEngine({"enabled": True})
        client = MagicMock()
        engine._client = client
        engine._tts = MagicMock()
        engine.synthesize(TTSOptions(text="hello"))
        args, kwargs = engine._tts.SynthesisInput.call_args
        assert kwargs.get("text") == "hello"

    def test_synthesize_missing_library_raises(self):
        engine = GoogleCloudTTSEngine({"enabled": True})
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("google"):
                raise ImportError("No module named 'google'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(TTSEngineError, match="not installed"):
                engine._get_client()


# ---------------------------------------------------------------------------
# Generate endpoint (fake engine, no network)
# ---------------------------------------------------------------------------


class FakeEngine:
    engine_id = "fake_engine"
    display_name = "Fake Engine"

    def __init__(self, config):
        self.config = dict(config)
        self.calls = 0

    def validate_config(self):
        return None

    def synthesize(self, options):
        self.calls += 1
        return TTSResult(
            audio_content=b"\xff\xfbID3 fake mp3 audio data",
            content_type="audio/mpeg",
            engine_id=self.engine_id,
        )


@pytest.fixture
def tts_env(tmp_path, monkeypatch):
    """Point audio storage at a tmp dir and register a fake engine."""
    monkeypatch.setattr(audio_storage, "get_storage_root", lambda: tmp_path)
    monkeypatch.setenv("TTS_GOOGLE_ENABLED", "true")

    fake = FakeEngine({"enabled": True, "language_code": "en-GB", "voice": "en-GB-Standard-D"})

    def _get_engine(engine_id):
        if engine_id == "google_cloud":
            return fake
        return None

    monkeypatch.setattr("app.services.tts.registry.get_engine", _get_engine)
    monkeypatch.setattr("app.services.tts.get_engine", _get_engine)
    return fake, tmp_path


@pytest.fixture
def authed_client(client, monkeypatch):
    """Test client with session auth satisfied and the auth gate disabled."""
    app = client.application
    app.config["REQUIRE_AUTH"] = False

    dummy_user = MagicMock()
    dummy_user.id = 1
    dummy_user.username = "tester"
    dummy_user.is_admin = True
    monkeypatch.setattr(
        "app.utils.auth_decorators.get_current_user", lambda: dummy_user
    )
    return client


class TestGenerateEndpoint:
    def test_generate_requires_word(self, authed_client, tts_env):
        resp = authed_client.post("/api/pronunciation/generate", json={"ipa": "triː"})
        assert resp.status_code == 400

    def test_generate_success_and_dedup(self, authed_client, tts_env):
        fake, tmp_path = tts_env
        resp = authed_client.post(
            "/api/pronunciation/generate",
            json={"word": "tree", "ipa": "triː"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["filename"].endswith(".mp3")
        assert data["audio_url"] == f"/audio/{data['filename']}"
        assert data["engine"] == "fake_engine"

        # File exists on disk in the (tmp) audio storage
        saved = tmp_path / "dictionary" / data["filename"]
        assert saved.is_file()

        # Content-addressed dedup: second call does not synthesize again
        resp2 = authed_client.post(
            "/api/pronunciation/generate",
            json={"word": "tree", "ipa": "triː"},
        )
        assert resp2.status_code == 200
        assert resp2.get_json()["cached"] is True
        assert fake.calls == 1

    def test_generate_different_utterance_new_file(self, authed_client, tts_env):
        fake, _ = tts_env
        r1 = authed_client.post("/api/pronunciation/generate", json={"word": "tree", "ipa": "triː"})
        r2 = authed_client.post("/api/pronunciation/generate", json={"word": "sea", "ipa": "siː"})
        assert r1.get_json()["filename"] != r2.get_json()["filename"]
        assert fake.calls == 2

    def test_generate_engine_error_returns_502(self, authed_client, tts_env):
        fake, _ = tts_env

        def boom(options):
            raise TTSEngineError("upstream refused")

        fake.synthesize = boom
        resp = authed_client.post("/api/pronunciation/generate", json={"word": "tree", "ipa": "triː"})
        assert resp.status_code == 502
        assert "upstream refused" in resp.get_json()["message"]

    def test_generate_disabled_returns_400(self, authed_client, tts_env, monkeypatch):
        fake, _ = tts_env
        fake.config = {"enabled": False, "language_code": "en-GB", "voice": "en-GB-Standard-D"}
        resp = authed_client.post("/api/pronunciation/generate", json={"word": "tree", "ipa": "triː"})
        assert resp.status_code == 400
        assert "not enabled" in resp.get_json()["message"]


# ---------------------------------------------------------------------------
# Export packaging (audio shipped with LIFT exports)
# ---------------------------------------------------------------------------


class TestExportMediaPackaging:
    def _make_xml(self, hrefs):
        media = "".join(f'<media href="{h}"/>' for h in hrefs)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<lift><entry id="e1"><lexical-unit><form lang="en"><text>tree</text></form>'
            f'</lexical-unit><pronunciation>{media}</pronunciation></entry></lift>'
        )

    def test_collect_media_files(self, tmp_path, monkeypatch):
        from app.services.export_service import ExportService

        monkeypatch.setattr(audio_storage, "get_storage_root", lambda: tmp_path)
        audio_storage.save_audio("en-GB_tree_abc123.mp3", b"\xff\xfb audio", project_db="dictionary")

        svc = ExportService(dictionary_service=MagicMock())
        found = svc._collect_media_files(
            self._make_xml(["en-GB_tree_abc123.mp3", "missing.mp3", "https://x/y.mp3"])
        )
        assert len(found) == 1
        assert found[0][0] == "en-GB_tree_abc123.mp3"

    def test_single_export_zips_audio_when_present(self, tmp_path, monkeypatch):
        import io
        import zipfile

        from app.services.export_service import ExportService

        monkeypatch.setattr(audio_storage, "get_storage_root", lambda: tmp_path)
        audio_storage.save_audio("en-GB_tree_abc123.mp3", b"\xff\xfb audio", project_db="dictionary")

        dict_service = MagicMock()
        dict_service.export_lift.return_value = self._make_xml(["en-GB_tree_abc123.mp3"])
        svc = ExportService(dictionary_service=dict_service)
        resp = svc._export_lift_single("dictionary_export_20260811", as_download=True)
        assert resp.content_type == "application/zip"

        zf = zipfile.ZipFile(io.BytesIO(resp.data))
        names = zf.namelist()
        assert any(n.endswith(".lift") for n in names)
        assert "audio/en-GB_tree_abc123.mp3" in names
        assert zf.read("audio/en-GB_tree_abc123.mp3") == b"\xff\xfb audio"

    def test_single_export_plain_lift_when_no_media(self):
        from app.services.export_service import ExportService

        dict_service = MagicMock()
        dict_service.export_lift.return_value = self._make_xml([])
        svc = ExportService(dictionary_service=dict_service)
        resp = svc._export_lift_single("dictionary_export_20260811", as_download=True)
        assert resp.content_type == "application/xml; charset=utf-8"
        assert b"<entry" in resp.data


# ---------------------------------------------------------------------------
# Pronunciation expansion (comma-delimited IPA lists)
# ---------------------------------------------------------------------------


class TestPronunciationExpansion:
    def test_expand_pronunciations_helper(self):
        from app.services.ipa_service import expand_pronunciations

        assert expand_pronunciations("triː, ˈtɹiː") == ["triː", "ˈtɹiː"]
        assert expand_pronunciations("ab(c), de(f)") == ["ab", "abc", "de", "def"]
        assert expand_pronunciations("a, a, b") == ["a", "b"]  # dedup, order kept
        assert expand_pronunciations("") == []
        assert expand_pronunciations(None) == []

    def test_generate_expands_comma_list(self, authed_client, tts_env):
        fake, _ = tts_env
        resp = authed_client.post(
            "/api/pronunciation/generate",
            json={"word": "tree", "ipa": "triː, ˈtɹiː"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["results"]) == 2
        assert data["results"][0]["ipa"] == "triː"
        assert data["results"][1]["ipa"] == "ˈtɹiː"
        assert data["results"][0]["filename"] != data["results"][1]["filename"]
        assert fake.calls == 2
        # Legacy single fields point at the first (primary) result
        assert data["filename"] == data["results"][0]["filename"]
        assert data["audio_url"] == data["results"][0]["audio_url"]

    def test_generate_comma_list_dedup(self, authed_client, tts_env):
        fake, _ = tts_env
        body = {"word": "tree", "ipa": "triː, ˈtɹiː"}
        r1 = authed_client.post("/api/pronunciation/generate", json=body)
        assert r1.status_code == 200
        r2 = authed_client.post("/api/pronunciation/generate", json=body)
        assert r2.status_code == 200
        assert r2.get_json()["cached"] is True
        assert fake.calls == 2  # nothing re-synthesized

    def test_generate_single_ipa_single_result(self, authed_client, tts_env):
        fake, _ = tts_env
        resp = authed_client.post(
            "/api/pronunciation/generate", json={"word": "sea", "ipa": "siː"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) == 1
        assert data["results"][0]["ipa"] == "siː"
        assert fake.calls == 1


# ---------------------------------------------------------------------------
# Delete auth surface
# ---------------------------------------------------------------------------


class TestDeleteAuth:
    def test_delete_requires_auth(self, client, tts_env, monkeypatch):
        app = client.application
        app.config["REQUIRE_AUTH"] = False
        resp = client.delete("/api/pronunciation/delete/whatever.mp3")
        assert resp.status_code == 401

    def test_delete_authed_reaches_file_check(self, authed_client, tts_env):
        resp = authed_client.delete("/api/pronunciation/delete/missing.mp3")
        assert resp.status_code == 404  # auth passed; file simply absent


# ---------------------------------------------------------------------------
# Upload auth surface
# ---------------------------------------------------------------------------


class TestUploadAuth:
    def test_upload_requires_auth(self, client, tts_env, monkeypatch):
        import io

        app = client.application
        app.config["REQUIRE_AUTH"] = False
        resp = client.post(
            "/api/pronunciation/upload",
            data={"audio_file": (io.BytesIO(b"\xff\xfb mp3"), "clip.mp3"), "ipa_value": "triː"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401

    def test_upload_authed_reaches_validation(self, authed_client, tts_env):
        import io

        resp = authed_client.post(
            "/api/pronunciation/upload",
            data={"audio_file": (io.BytesIO(b"\xff\xfb mp3 data"), "clip.mp3"), "ipa_value": "triː"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["filename"].endswith(".mp3")
        # File landed in the (tmp) audio storage
        from app.services.tts import audio_storage

        assert audio_storage.audio_exists(data["filename"])


# ---------------------------------------------------------------------------
# Batch TTS (workset / missing-audio background job)
# ---------------------------------------------------------------------------


SAMPLE_ENTRY_XML = (
    '<entry id="e1" guid="g1">'
    '<lexical-unit><form lang="en"><text>tree</text></form></lexical-unit>'
    '<pronunciation><form lang="seh-fonipa"><text>triː, ˈtɹiː</text></form></pronunciation>'
    '</entry>'
)

SAMPLE_ENTRY_XML_NS = (
    '<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="e1" guid="g1">'
    '<lexical-unit><form lang="en"><text>tree</text></form></lexical-unit>'
    '<pronunciation><form lang="seh-fonipa"><text>triː, ˈtɹiː</text></form></pronunciation>'
    '</entry>'
)


class TestSynthesizeVariants:
    def test_expands_comma_list(self, tts_env):
        fake, tmp_path = tts_env
        from app.services.tts.batch import synthesize_variants

        results = synthesize_variants("tree", "triː, ˈtɹiː", fake)
        assert len(results) == 2
        assert results[0]["ipa"] == "triː"
        assert results[1]["ipa"] == "ˈtɹiː"
        assert results[0]["filename"] != results[1]["filename"]
        assert fake.calls == 2
        # Files exist on disk
        from app.services.tts import audio_storage

        assert audio_storage.audio_exists(results[0]["filename"])
        assert audio_storage.audio_exists(results[1]["filename"])

    def test_cache_hit_second_call(self, tts_env):
        fake, _ = tts_env
        from app.services.tts.batch import synthesize_variants

        r1 = synthesize_variants("tree", "triː", fake)
        r2 = synthesize_variants("tree", "triː", fake)
        assert r1[0]["filename"] == r2[0]["filename"]
        assert r2[0]["cached"] is True
        assert fake.calls == 1


class TestAddAudioToEntryXml:
    def test_injects_media_for_each_variant(self, tts_env):
        import xml.etree.ElementTree as ET

        fake, _ = tts_env
        from app.services.tts.batch import add_audio_to_entry_xml

        new_xml, count, details = add_audio_to_entry_xml(SAMPLE_ENTRY_XML, fake, entry_id="e1")
        assert count == 2
        assert len(details) == 2
        root = ET.fromstring(new_xml)
        pron = root.find("pronunciation")
        media = [m for m in pron if m.tag.split("}")[-1] == "media"]
        assert len(media) == 2
        for m in media:
            assert m.get("href").endswith(".mp3")
        assert fake.calls == 2

    def test_handles_namespaced_xml(self, tts_env):
        import xml.etree.ElementTree as ET

        fake, _ = tts_env
        from app.services.tts.batch import add_audio_to_entry_xml

        new_xml, count, _ = add_audio_to_entry_xml(SAMPLE_ENTRY_XML_NS, fake, entry_id="e1")
        assert count == 2
        root = ET.fromstring(new_xml)
        ns = "{http://fieldworks.sil.org/schemas/lift/0.13}"
        pron = root.find(f"{ns}pronunciation")
        media = [m for m in pron if m.tag == f"{ns}media"]
        assert len(media) == 2

    def test_idempotent_rerun(self, tts_env):
        fake, _ = tts_env
        from app.services.tts.batch import add_audio_to_entry_xml

        new_xml, count, _ = add_audio_to_entry_xml(SAMPLE_ENTRY_XML, fake, entry_id="e1")
        assert count == 2
        _, count2, _ = add_audio_to_entry_xml(new_xml, fake, entry_id="e1")
        assert count2 == 0  # already attached
        assert fake.calls == 2  # nothing re-synthesized

    def test_no_pronunciation_returns_unchanged(self, tts_env):
        fake, _ = tts_env
        from app.services.tts.batch import add_audio_to_entry_xml

        xml = '<entry id="e2"><lexical-unit><form lang="en"><text>run</text></form></lexical-unit></entry>'
        new_xml, count, _ = add_audio_to_entry_xml(xml, fake, entry_id="e2")
        assert count == 0
        assert "media" not in new_xml


class TestBatchRoutes:
    def test_batch_missing_audio_starts_job(self, authed_client, tts_env, monkeypatch):
        import app.services.tts.batch as batch_mod

        fake, _ = tts_env
        fake.config = {"enabled": True, "language_code": "en-GB", "voice": "en-GB-Standard-D"}
        captured = {}

        def _fake_start(entry_ids, engine, attach=True):
            captured["entry_ids"] = entry_ids
            captured["engine"] = engine
            return "job-abc"

        def _fake_ids(dict_service):
            return ["e1", "e2", "e3"]

        monkeypatch.setattr(batch_mod, "get_ready_engine", lambda: fake)
        monkeypatch.setattr(batch_mod, "iter_entries_missing_audio", _fake_ids)
        monkeypatch.setattr(batch_mod, "start_batch_job", _fake_start)

        resp = authed_client.post(
            "/api/pronunciation/batch", json={"mode": "missing_audio"}
        )
        assert resp.status_code == 202
        data = resp.get_json()
        assert data["success"] is True
        assert data["job_id"] == "job-abc"
        assert data["total"] == 3
        assert captured["entry_ids"] == ["e1", "e2", "e3"]
        assert captured["engine"] is fake

    def test_batch_workset_starts_job(self, authed_client, tts_env, monkeypatch):
        import app.services.tts.batch as batch_mod

        fake, _ = tts_env
        fake.config = {"enabled": True, "language_code": "en-GB", "voice": "en-GB-Standard-D"}
        captured = {}

        def _fake_start(entry_ids, engine, attach=True):
            captured["entry_ids"] = entry_ids
            return "job-ws"

        monkeypatch.setattr(batch_mod, "get_ready_engine", lambda: fake)
        monkeypatch.setattr(batch_mod, "iter_workset_entry_ids", lambda ws_id: ["w1", "w2"])
        monkeypatch.setattr(batch_mod, "start_batch_job", _fake_start)

        resp = authed_client.post(
            "/api/pronunciation/batch", json={"mode": "workset", "workset_id": 7}
        )
        assert resp.status_code == 202
        assert resp.get_json()["total"] == 2
        assert captured["entry_ids"] == ["w1", "w2"]

    def test_batch_requires_mode_and_workset_id(self, authed_client, tts_env):
        resp = authed_client.post("/api/pronunciation/batch", json={})
        assert resp.status_code == 400

    def test_batch_engine_disabled_returns_400(self, authed_client, tts_env, monkeypatch):
        import app.services.tts.batch as batch_mod
        from app.services.tts.base import TTSEngineError

        monkeypatch.setattr(batch_mod, "iter_entries_missing_audio", lambda ds: ["e1"])

        def _raise_disabled():
            raise TTSEngineError(
                "Text-to-speech is not enabled. Enable it in Settings → Text-to-Speech."
            )

        monkeypatch.setattr(batch_mod, "get_ready_engine", _raise_disabled)

        resp = authed_client.post("/api/pronunciation/batch", json={"mode": "missing_audio"})
        assert resp.status_code == 400
        assert "not enabled" in resp.get_json()["message"]

    def test_batch_status_and_cancel(self, authed_client, monkeypatch):
        import app.services.tts.batch as batch_mod

        def _fake_job(job_id):
            if job_id == "job-x":
                return {"job_id": "job-x", "status": "running", "processed": 5, "total": 10}
            return None

        monkeypatch.setattr(batch_mod, "get_batch_job", _fake_job)
        monkeypatch.setattr(batch_mod, "cancel_batch_job", lambda jid: jid == "job-x")

        resp = authed_client.get("/api/pronunciation/batch/status/job-x")
        assert resp.status_code == 200
        assert resp.get_json()["job"]["processed"] == 5

        resp404 = authed_client.get("/api/pronunciation/batch/status/nope")
        assert resp404.status_code == 404

        resp_cancel = authed_client.post("/api/pronunciation/batch/cancel/job-x")
        assert resp_cancel.status_code == 200
        resp_cancel404 = authed_client.post("/api/pronunciation/batch/cancel/nope")
        assert resp_cancel404.status_code == 404
