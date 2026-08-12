"""
Per-engine configuration resolution.

Resolution chain for every engine config key (mirrors the ``openai_api_key`` pattern in
``app/api/ai_api.py``):

1. project settings: ``ProjectSettings.settings_json["tts"][engine_id]`` (Settings UI),
2. environment variables ``<env_prefix><KEY_UPPER>`` (e.g. ``TTS_GOOGLE_VOICE``),
3. engine ``default_config()``.

Credentials are never logged and never returned by any API that the frontend consumes.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def _project_tts_settings() -> Dict[str, Any]:
    """Return the per-project ``settings_json["tts"]`` dict (or {})."""
    try:
        from app.models.project_settings import ProjectSettings

        settings = ProjectSettings.query.first()
        if settings is None:
            return {}
        raw = getattr(settings, "settings_json", None) or {}
        tts = raw.get("tts") if isinstance(raw, dict) else None
        return tts if isinstance(tts, dict) else {}
    except Exception:
        return {}


def _env_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    return value.strip().lower() in ("1", "true", "yes", "on")


def get_engine_config(engine_id: str) -> Dict[str, Any]:
    """Resolve the merged configuration dict for ``engine_id``.

    Never raises: any lookup failure degrades to the engine's defaults.
    """
    from app.services.tts.registry import TTSEngineRegistry  # avoid import cycle

    engine_cls = TTSEngineRegistry.get(engine_id)
    if engine_cls is None:
        return {}

    defaults = dict(engine_cls.default_config())
    prefix = getattr(engine_cls, "env_prefix", "") or ""

    # 1. Project settings (UI)
    stored = _project_tts_settings().get(engine_id)
    if not isinstance(stored, dict):
        stored = {}

    # 2. Environment overrides
    env_overrides: Dict[str, Any] = {}
    for key in list(defaults.keys()) + [k for k in stored.keys() if isinstance(k, str)]:
        env_key = f"{prefix}{key.upper()}"
        raw = os.environ.get(env_key)
        if raw is None:
            continue
        if isinstance(defaults.get(key), bool):
            val = _env_bool(raw)
            if val is not None:
                env_overrides[key] = val
        else:
            env_overrides[key] = raw

    # Merge: defaults < stored < env
    merged = dict(defaults)
    for key, value in stored.items():
        if value is None or value == "":
            continue
        merged[key] = value
    merged.update(env_overrides)
    return merged


def engine_enabled(engine_id: str) -> bool:
    """Whether ``engine_id`` is enabled (settings or env), default False."""
    cfg = get_engine_config(engine_id)
    return bool(cfg.get("enabled", False))
