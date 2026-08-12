"""
TTS engine registry — engines register themselves by ``engine_id``.

Usage::

    TTSEngineRegistry.register(MyEngine)
    engine_cls = TTSEngineRegistry.get("google_cloud")
    engine = get_engine("google_cloud")   # instantiated with resolved config
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from app.services.tts.base import TTSEngine
from app.services.tts.config import get_engine_config


class TTSEngineRegistry:
    """Class-level registry of TTS engine implementations."""

    _engines: Dict[str, Type[TTSEngine]] = {}

    @classmethod
    def register(cls, engine_cls: Type[TTSEngine]) -> None:
        """Register an engine class keyed by ``engine_cls.engine_id``."""
        if not engine_cls.engine_id:
            raise ValueError(f"Engine {engine_cls.__name__} must define a non-empty engine_id")
        cls._engines[engine_cls.engine_id] = engine_cls

    @classmethod
    def get(cls, engine_id: str) -> Optional[Type[TTSEngine]]:
        """Return the engine class for ``engine_id``, or None."""
        return cls._engines.get(engine_id)

    @classmethod
    def all(cls) -> List[Type[TTSEngine]]:
        """Return all registered engine classes, sorted by display name."""
        return sorted(cls._engines.values(), key=lambda e: e.display_name.lower())


def get_engine(engine_id: str) -> Optional[TTSEngine]:
    """Instantiate the engine ``engine_id`` with its resolved configuration.

    Returns None when the engine id is unknown. Config resolution never raises:
    unknown/disabled engines degrade to their defaults.
    """
    engine_cls = TTSEngineRegistry.get(engine_id)
    if engine_cls is None:
        return None
    config = get_engine_config(engine_id)
    return engine_cls(config)


def list_engines() -> List[Dict[str, Any]]:
    """Return lightweight descriptors for all registered engines (for UIs)."""
    out = []
    for cls in TTSEngineRegistry.all():
        out.append(
            {
                "engine_id": cls.engine_id,
                "display_name": cls.display_name,
                "supports_ipa": cls.supports_ipa,
                "supports_text": cls.supports_text,
                "default_config": cls.default_config(),
            }
        )
    return out
