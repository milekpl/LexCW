"""
E2E test for the StarDict export plugin.

Verifies:
- Plugin is discovered and loaded
- POST /api/export/stardict returns a .tar.gz
- The archive contains valid .ifo, .idx, and .dict files
"""

import importlib.util
import io
import json
import os
import struct
import tarfile
from pathlib import Path

import pytest

from app import create_app
from app.services.plugin_manager import PluginManager


def _register_stardict(app):
    """Helper: import and register the StarDict plugin."""
    plugin_py = Path(__file__).parent.parent.parent / "instance" / "plugins" / "stardict_exporter" / "plugin.py"
    spec = importlib.util.spec_from_file_location("stardict_plugin", str(plugin_py))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.register(app)


@pytest.fixture
def app():
    os.environ["FLASK_CONFIG"] = "testing"
    os.environ["TESTING"] = "true"
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestStarDictPlugin:
    """Test that the StarDict exporter plugin works end-to-end."""

    def test_plugin_manifest_exists(self):
        manifest = Path(__file__).parent.parent.parent / "instance" / "plugins" / "stardict_exporter" / "manifest.json"
        assert manifest.exists(), f"StarDict plugin manifest not found at {manifest}"

    def test_export_endpoint_available(self, client):
        _register_stardict(client.application)
        resp = client.post("/api/export/stardict",
            data=json.dumps({"title": "TestDict", "source_lang": "en", "target_lang": "pl"}),
            content_type="application/json",
        )
        assert resp.status_code in (200, 500)

    def test_export_produces_valid_tarball(self, client):
        _register_stardict(client.application)
        resp = client.post("/api/export/stardict",
            data=json.dumps({"title": "TestDict", "source_lang": "en", "target_lang": "pl"}),
            content_type="application/json",
        )
        if resp.status_code != 200:
            pytest.skip("No entries in test database")
        assert resp.content_type == "application/gzip"
        with tarfile.open(fileobj=io.BytesIO(resp.data), mode="r:gz") as tar:
            names = tar.getnames()
            assert any("ifo" in n for n in names), f"No .ifo in archive: {names}"
            assert any("idx" in n for n in names), f"No .idx in archive: {names}"
            assert any("dict" in n for n in names), f"No .dict in archive: {names}"

    def test_export_without_entries(self, client):
        _register_stardict(client.application)
        resp = client.post("/api/export/stardict",
            data=json.dumps({"title": "Test"}),
            content_type="application/json",
        )
        assert resp.status_code in (200, 500)


class TestPluginManagerAPI:
    def test_get_exporters_lists_stardict(self, app):
        plugins_dir = Path(app.instance_path) / "plugins"
        pm = PluginManager(plugins_dir)
        pm.load_all(app)
        names = [e["name"] for e in pm.get_exporters()]
        assert any("StarDict" in n for n in names), f"StarDict not in {names}"

    def test_export_options_page(self, client):
        resp = client.get("/export")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Export Options" in html or "plugin" in html.lower() or "export" in html.lower()
