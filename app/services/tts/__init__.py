"""
Text-to-speech engine plugin framework.

Engines are plugins registered in :class:`TTSEngineRegistry`; each implements the
:class:`TTSEngine` ABC (see ``base.py``). Config is resolved per engine from project
settings (``settings_json["tts"]``) with environment-variable fallback (see ``config.py``).
Audio files are stored under ``AUDIO_STORAGE_PATH`` in per-project subdirectories
(see ``audio_storage.py``).
"""

from app.services.tts.base import TTSEngine, TTSOptions, TTSResult, TTSEngineError
from app.services.tts.registry import TTSEngineRegistry, get_engine, list_engines
from app.services.tts import audio_storage  # noqa: F401  (module-level helpers)

# Import built-in engines so they register themselves on import.
from app.services.tts.engines import google_cloud  # noqa: F401

__all__ = [
    "TTSEngine",
    "TTSOptions",
    "TTSResult",
    "TTSEngineError",
    "TTSEngineRegistry",
    "get_engine",
    "list_engines",
    "audio_storage",
]
