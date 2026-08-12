"""Built-in TTS engines. Importing this package registers them."""

from app.services.tts.engines.google_cloud import GoogleCloudTTSEngine
from app.services.tts.registry import TTSEngineRegistry

# Register built-in engines. Engines from user plugins can call
# TTSEngineRegistry.register(...) anywhere at import time.
TTSEngineRegistry.register(GoogleCloudTTSEngine)

__all__ = ["GoogleCloudTTSEngine"]
