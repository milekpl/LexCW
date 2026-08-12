"""
Google Cloud Text-to-Speech engine.

One of the few TTS providers that can speak IPA directly: it accepts SSML
``<phoneme alphabet="ipa" ph="...">`` and renders the phonemes verbatim, which is why
this is the flagship engine for pronunciation audio. Modeled on the working reference
script ``flextools-main/cloud_api/IPA_TTS.py``, generalized:

- credentials from project settings (inline service-account JSON) or the standard
  ``GOOGLE_APPLICATION_CREDENTIALS`` env var (path) or default application credentials;
- configurable voice + language (defaults ``en-GB-Standard-D`` / ``en-GB``);
- plain-text synthesis fallback when no IPA is provided.

The ``google-cloud-texttospeech`` package is imported lazily so the rest of the app
works even when it (or the credentials) is absent.
"""

from __future__ import annotations

import html
import json
import logging
import os
from typing import Any, Dict, Optional

from app.services.tts.base import TTSEngine, TTSEngineError, TTSOptions, TTSResult

logger = logging.getLogger(__name__)


class GoogleCloudTTSEngine(TTSEngine):
    engine_id = "google_cloud"
    display_name = "Google Cloud TTS"
    supports_ipa = True
    supports_text = True
    env_prefix = "TTS_GOOGLE_"

    @classmethod
    def default_config(cls) -> Dict[str, Any]:
        return {
            "enabled": False,
            "credentials_json": "",
            "voice": "en-GB-Standard-D",
            "language_code": "en-GB",
        }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._client = None
        self._tts = None  # the google.cloud.texttospeech module (set by _get_client)

    # -- client ----------------------------------------------------------------

    def _get_client(self):
        """Lazily build the TextToSpeechClient from the resolved config."""
        if self._client is not None:
            return self._client
        try:
            from google.cloud import texttospeech

            self._tts = texttospeech
        except ImportError as e:  # pragma: no cover - exercised only w/o the package
            raise TTSEngineError(
                "The 'google-cloud-texttospeech' package is not installed. "
                "Install it (pip install google-cloud-texttospeech) or use another engine."
            ) from e

        credentials_json = (self.config.get("credentials_json") or "").strip()
        env_credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or ""

        try:
            if credentials_json:
                self._client = texttospeech.TextToSpeechClient.from_service_account_info(
                    json.loads(credentials_json)
                )
            elif env_credentials_path and os.path.isfile(env_credentials_path):
                self._client = texttospeech.TextToSpeechClient.from_service_account_file(
                    env_credentials_path
                )
            else:
                # Default application credentials (ADC).
                self._client = texttospeech.TextToSpeechClient()
        except Exception as e:
            raise TTSEngineError(
                "Google Cloud TTS credentials are invalid or unusable. Configure a "
                "service-account JSON in Settings, or set TTS_GOOGLE_CREDENTIALS_JSON / "
                f"GOOGLE_APPLICATION_CREDENTIALS. ({e})"
            ) from e
        return self._client

    def validate_config(self) -> Optional[str]:
        if not self.config.get("enabled"):
            return "Google Cloud TTS is disabled."
        try:
            self._get_client()
        except TTSEngineError as e:
            return str(e)
        except Exception as e:  # pragma: no cover
            return f"Google Cloud TTS is not usable: {e}"
        return None

    # -- synthesis -------------------------------------------------------------

    def synthesize(self, options: TTSOptions) -> TTSResult:
        client = self._get_client()
        if self._tts is None:  # pragma: no cover - _get_client always sets it
            raise TTSEngineError("Google Cloud TTS client is unavailable.")
        tts = self._tts

        language_code = options.language_code or self.config.get("language_code") or "en-GB"
        voice = options.voice or self.config.get("voice") or "en-GB-Standard-D"

        try:
            if options.ipa and options.ipa.strip():
                # IPA phonemes rendered verbatim; escape XML attribute/text content.
                ph = html.escape(options.ipa.strip(), quote=True)
                text = html.escape(options.text)
                ssml = f'<speak><phoneme alphabet="ipa" ph="{ph}">{text}</phoneme></speak>'
                synthesis_input = tts.SynthesisInput(ssml=ssml)
            else:
                synthesis_input = tts.SynthesisInput(text=options.text)

            voice_params = tts.VoiceSelectionParams(
                language_code=language_code, name=voice
            )
            audio_config = tts.AudioConfig(
                audio_encoding=tts.AudioEncoding.MP3
            )

            response = client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )
        except TTSEngineError:
            raise
        except Exception as e:
            raise TTSEngineError(
                f"Google Cloud TTS synthesis failed for {options.text!r}: {e}"
            ) from e

        if not response.audio_content:
            raise TTSEngineError(
                f"Google Cloud TTS returned no audio for {options.text!r}"
            )

        result = TTSResult(
            audio_content=response.audio_content,
            content_type="audio/mpeg",
            engine_id=self.engine_id,
        )
        if options.output_path is not None:
            try:
                options.output_path.write_bytes(result.audio_content)
            except OSError as e:
                raise TTSEngineError(
                    f"Could not write audio file {options.output_path}: {e}"
                ) from e
        return result
