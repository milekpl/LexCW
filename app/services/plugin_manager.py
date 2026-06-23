"""
Plugin Manager for the Lexicographic Curation Workbench.

Discovers and loads plugins from instance/plugins/. Each plugin is a
subdirectory containing manifest.json and plugin.py.

Security:
- Plugins execute arbitrary Python code — only install trusted plugins.
- The allowlist file `enabled.json` in the plugins directory controls which
  plugins load. If present, ONLY listed plugins are loaded. If absent, all
  discovered plugins are loaded (backward compatible).
- Plugin directories must be readable by the Flask process.
- The instance/ directory must exist and be writable (plugins can create
  files there).

manifest.json format:
{
    "name": "Plugin Name",
    "version": "1.0",
    "description": "What it does",
    "entrypoint": "plugin.py",
    "type": "exporter"
}

plugin.py must expose:
    def register(app):
        '''Called on startup. Use app.injector to access services.'''
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask

logger = logging.getLogger(__name__)


class PluginManager:
    """Discovers and loads plugins from the filesystem.

    Args:
        plugins_dir: Path to the plugins directory (typically instance/plugins/).
        allowlist: Optional set of plugin names to allow. If None, reads from
                   enabled.json in plugins_dir. If the file doesn't exist, all
                   discovered plugins are loaded.
    """

    def __init__(self, plugins_dir: Path, allowlist: Optional[set] = None):
        self.plugins_dir = Path(plugins_dir)
        self._allowlist = allowlist
        self._plugins: Dict[str, Dict[str, Any]] = {}

    @property
    def allowlist(self) -> Optional[set]:
        """Resolve the allowlist: explicit > enabled.json > None (allow all)."""
        if self._allowlist is not None:
            return self._allowlist
        enabled_file = self.plugins_dir / "enabled.json"
        if enabled_file.is_file():
            try:
                with open(enabled_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                names = data.get("plugins", [])
                if isinstance(names, list):
                    return set(names)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not read plugin allowlist: {e}")
        return None  # None means "allow all"

    def _is_allowed(self, manifest: Dict[str, Any]) -> bool:
        """Check if a plugin is in the allowlist (if one is active)."""
        allowed = self.allowlist
        if allowed is None:
            return True
        return manifest.get("name", "") in allowed or manifest.get("name", "") in allowed

    def discover(self) -> List[Dict[str, Any]]:
        """Scan plugins_dir for valid plugin directories.

        Returns a list of plugin manifest dicts.
        """
        if not self.plugins_dir.is_dir():
            logger.info(f"Plugins directory does not exist: {self.plugins_dir}")
            return []

        discovered = []
        for entry in sorted(self.plugins_dir.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.json"
            if not manifest_path.is_file():
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Invalid manifest in {entry.name}: {e}")
                continue

            required = ["name", "version", "entrypoint", "type"]
            if not all(k in manifest for k in required):
                logger.warning(f"Manifest in {entry.name} missing required keys: {required}")
                continue

            manifest["_dir"] = str(entry)
            discovered.append(manifest)

        return discovered

    def load_plugin(self, manifest: Dict[str, Any], app: Flask) -> bool:
        """Load a plugin from its manifest and call register(app).

        Args:
            manifest: Plugin manifest dict (with _dir key added by discover).
            app: Flask application instance.

        Returns:
            True if loaded successfully, False otherwise.
        """
        plugin_dir = Path(manifest["_dir"])
        entrypoint = manifest["entrypoint"]
        module_path = plugin_dir / entrypoint

        if not module_path.is_file():
            logger.error(f"Plugin entrypoint not found: {module_path}")
            return False

        module_name = f"plugin_{manifest['name'].lower().replace(' ', '_').replace('-', '_')}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, str(module_path))
            if spec is None or spec.loader is None:
                logger.error(f"Could not create module spec for {module_path}")
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if not hasattr(module, "register"):
                logger.error(f"Plugin {manifest['name']} has no register() function")
                return False

            module.register(app)
            self._plugins[manifest["name"]] = manifest
            logger.info(f"Loaded plugin: {manifest['name']} v{manifest['version']}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {manifest['name']}: {e}", exc_info=True)
            return False

    def load_all(self, app: Flask) -> int:
        """Discover and load plugins, respecting the allowlist.

        Args:
            app: Flask application instance.

        Returns:
            Number of plugins loaded.
        """
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        discovered = self.discover()
        allowed = self.allowlist
        skipped = 0
        loaded = 0

        for manifest in discovered:
            name = manifest.get("name", "unknown")
            if allowed is not None and name not in allowed:
                logger.info(f"Plugin '{name}' not in allowlist — skipped")
                skipped += 1
                continue
            if self.load_plugin(manifest, app):
                loaded += 1

        logger.info(
            f"Plugin manager: {loaded} loaded, {skipped} skipped, "
            f"{len(discovered) - loaded - skipped} failed"
        )
        return loaded

    def get_loaded_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Return all successfully loaded plugins."""
        return dict(self._plugins)

    def get_exporters(self) -> List[Dict[str, Any]]:
        """Return loaded exporter-type plugins with their endpoints.

        Each plugin declares its own API endpoint in manifest.json under the
        ``endpoint`` key. This replaces the earlier hard-coded name-to-endpoint
        mapping, so renames and new plugins work without code changes.

        For backward compatibility, if a plugin's manifest lacks an explicit
        ``endpoint`` field, a fallback is generated from its name.
        """
        return [
            {
                "name": m["name"],
                "description": m.get("description", ""),
                "version": m["version"],
                "endpoint": m.get("endpoint", f"/api/export/{m['name'].lower().replace(' ', '-')}"),
            }
            for m in self._plugins.values()
            if m.get("type") == "exporter"
        ]
