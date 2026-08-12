"""
TTS engine plugin base types.

An engine is a class implementing :class:`TTSEngine`. The framework only knows the
ABC — each engine brings its own config keys (credentials, voice, language) and its
own synthesis transport (cloud API, local binary, …).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional


class TTSEngineError(Exception):
    """Raised when a TTS engine cannot synthesize or is misconfigured."""


@dataclass
class TTSOptions:
    """Inputs for a single synthesis call.

    Attributes:
        text: The text (usually the headword) to speak.
        ipa: Optional IPA transcription. Engines with ``supports_ipa=True`` use it
            (Google renders it verbatim via SSML phoneme); others ignore it.
        language_code: BCP-47-ish language code (e.g. ``"en-GB"``). Defaults to the
            engine config when None.
        voice: Engine-specific voice id (e.g. ``"en-GB-Standard-D"``). Defaults to the
            engine config when None.
        output_path: Optional filesystem path to write the audio to. When None the
            caller is expected to persist :attr:`TTSResult.audio_content` itself.
    """

    text: str
    ipa: Optional[str] = None
    language_code: Optional[str] = None
    voice: Optional[str] = None
    output_path: Optional[Path] = None


@dataclass
class TTSResult:
    """Output of a synthesis call."""

    audio_content: bytes
    content_type: str = "audio/mpeg"
    engine_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class TTSEngine(abc.ABC):
    """Base class for all TTS engines.

    Subclasses must set ``engine_id``/``display_name``/capabilities and implement
    :meth:`synthesize`. ``config`` is the resolved per-engine configuration dict
    (see :func:`app.services.tts.config.get_engine_config`).
    """

    engine_id: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    supports_ipa: ClassVar[bool] = False
    supports_text: ClassVar[bool] = False
    #: Env-var prefix used for the environment fallback of this engine's config,
    #: e.g. ``"TTS_GOOGLE_"``. Keys become ``<prefix><KEY_UPPER>``.
    env_prefix: ClassVar[str] = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = dict(config or {})

    @classmethod
    def default_config(cls) -> Dict[str, Any]:
        """Default config keys/values surfaced in the Settings UI."""
        return {}

    @abc.abstractmethod
    def synthesize(self, options: TTSOptions) -> TTSResult:
        """Synthesize audio for ``options`` and return it.

        Raises:
            TTSEngineError: on any failure (missing library, bad credentials,
                upstream API error, …).
        """

    def validate_config(self) -> Optional[str]:
        """Return a human-readable error string if the engine is not usable, else None.

        The default returns None (usable). Engines that lazily acquire clients should
        override this to surface credential/library problems with a helpful message.
        """
        return None
