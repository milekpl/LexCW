# TTS Engine Plugin — implementation plan

Date: 2026-08-11

**Status: implemented.** All steps below are done (see the git diff: `app/services/tts/`,
the generate endpoint, storage rework, settings UI, LIFT persistence fix, export
packaging, tests). Comma-delimited pronunciation lists (e.g. ``"triː, ˈtɹiː"``) are
expanded before synthesis — one audio per variant, all attached to the pronunciation.
`delete_audio` is now auth-gated. **Batch generation added:** a background job
(`app/services/tts/batch.py`, `POST /api/pronunciation/batch` + status/cancel endpoints)
generates and attaches audio for a workset or for all entries missing audio, with
progress polling and a "Generate Audio" button + modal on the workset curation page.
Verified: full unit suite green (the single failure `test_xml_update_clears_cache` is
pre-existing), 252 JS tests pass. Known limitation carried over from the data model:
per-pronunciation↔media association is by order and only applied when counts match or
there is a single pronunciation (see Open follow-ups).

## Context

The "Generate Audio" feature (`POST /api/pronunciations/generate` in `app/views.py:2170`)
is a **stub**: it returns a placeholder `/audio/pronunciation_<timestamp>.mp3` URL and
never creates a file (comment at `views.py:2186-2187`: *"This would typically generate
audio using TTS. For now, just return a placeholder."*). The UI button
(`app/static/js/entry-form.js:1742` `generateAudio`) sets the player `src` to that URL,
which 404s.

A working Google-TTS reference script exists outside this repo
(`/mnt/d/Dokumenty/slownik-wielki/flextools-main/cloud_api/IPA_TTS.py`). It is **not
general**: it hardcodes a credentials path, a fixed word→IPA dict, voice params, and a
local output directory. We generalize it.

Decisions (user-confirmed):
1. **Engine scope**: ship the IPA-capable Google Cloud TTS engine only; design a plugin
   interface so other engines can be added later (most TTS engines synthesize from text,
   not IPA — Google's SSML `<phoneme alphabet="ipa">` is the special case).
2. **Credentials**: project-settings DB (Settings UI) with environment-variable fallback,
   following the existing `openai_api_key` pattern.
3. **Storage**: honor the already-declared-but-unused `AUDIO_STORAGE_PATH`
   (`config.py:52`), store **bare relative filenames** in LIFT `<media href>` (LIFT
   convention), and fix the bug where audio is currently **dropped** from saved LIFT XML.
4. **Deliverable**: this plan + full implementation in this session.

## Current state (verified)

**Storage**
- Uploads land in `app/static/audio/` (`app/api/pronunciation.py:95-107`).
- `/audio/<filename>` serves `instance/audio` — a **different, empty** dir
  (`app/views.py:2105-2115`), so `/audio/...` URLs 404 for uploaded files.
- `config.py:52` declares `AUDIO_STORAGE_PATH` (default `instance/audio`) — **never read
  anywhere** in `app/`.
- `app/__init__.py:193-199` creates both `instance/audio` and `static/audio` at startup.

**Persistence (broken round-trip)**
- LIFT serializer writes `<media href>` only from `pronData.media`
  (`app/static/js/lift-xml-serializer.js:927-934`).
- But the Alpine adapter maps `p.audioPath → out.audio_path`
  (`app/static/js/alpine/alpine-to-serializer.js:271`) — never `media`. **Save drops audio.**
- On load, `normalizePronunciation` reads `raw.audio_path || raw.audioPath`
  (`app/static/js/alpine/normalize-entry.js:243`) — but the server sends
  `pronunciation_media: [{href, ...}]` (parsed at `app/parsers/lift_parser.py:738-753`,
  serialized via `Entry.to_dict`, `app/models/entry.py:584`). **Load drops audio too.**
- Net effect today: audio never survives a save/load cycle.

**Frontend URL patterns**
- `/static/audio/<filename>` — works (used by `entry-form.js:706`,
  `pronunciation-forms.js:417-418`, info API `pronunciation.py:258`).
- `/audio/<filename>` — 404s (used by dead `entry-view.js:18` + the stub's fake URL).
- `data.audio_url` from the stub (`entry-form.js:1784-1788`).

**Auth** — `/api/*` routes are gated by the auth gate (`app/auth_gate.py`,
`REQUIRE_AUTH` default on); pronunciation endpoints additionally use
`@_require_auth("pronunciation:read|write")` scoped to the API-key system
(`app/api/pronunciation.py:277,286,321,349,403`).

**Plugin precedent** — `ValidatorPlugin(ABC)` + `register_plugin()` in
`app/services/unified_validation_pipeline.py:174,324-334` is the canonical ABC+registry
pattern to mirror.

## Architecture

### 1. Plugin framework — `app/services/tts/`

New package:

```
app/services/tts/
  __init__.py        # re-exports registry + engines
  base.py            # TTSEngine ABC, TTSOptions dataclass, TTSResult
  registry.py        # TTSEngineRegistry (register / get / list), engine_config helper
  engines/
    __init__.py      # imports builtin engines so registration happens on import
    google_cloud.py  # GoogleCloudTTSEngine
  audio_storage.py   # storage path resolution + per-project dirs + filename helpers
  config.py          # resolve engine config from ProjectSettings + env (per-engine)
```

`base.py`:

```python
@dataclass
class TTSOptions:
    text: str                       # word / text to speak
    ipa: Optional[str] = None       # IPA transcription (used when engine.supports_ipa)
    language_code: Optional[str] = None   # e.g. "en-GB" (default from config)
    voice: Optional[str] = None           # engine-specific voice id (default from config)
    output_path: Optional[Path] = None    # where to write; None = engine returns bytes

@dataclass
class TTSResult:
    audio_content: bytes            # synthesized audio
    content_type: str = "audio/mpeg"
    engine_id: str = ""

class TTSEngine(ABC):
    engine_id: ClassVar[str]        # stable id, e.g. "google_cloud"
    display_name: ClassVar[str]     # "Google Cloud TTS"
    supports_ipa: ClassVar[bool]    # True if engine honors ipa via SSML/phoneme
    supports_text: ClassVar[bool]   # True if engine can synthesize from plain text

    def __init__(self, config: Dict[str, Any]): ...   # engine-specific config dict
    @abstractmethod
    def synthesize(self, options: TTSOptions) -> TTSResult: ...
    def validate_config(self) -> Optional[str]:
        """Return an error string if the engine is misconfigured, else None."""
        return None
    @classmethod
    def default_config(cls) -> Dict[str, Any]: ...     # keys shown in Settings UI
```

`registry.py`:

```python
class TTSEngineRegistry:
    _engines: Dict[str, Type[TTSEngine]] = {}
    @classmethod
    def register(cls, engine_cls) -> None      # keyed by engine_cls.engine_id
    @classmethod
    def get(cls, engine_id) -> Optional[Type[TTSEngine]]
    @classmethod
    def all(cls) -> List[Type[TTSEngine]]       # sorted by display_name

def get_engine(engine_id: str) -> Optional[TTSEngine]:  # instantiate with resolved config
```

Config resolution (`config.py`) — the "DB settings + env fallback" chain, mirroring
`app/api/ai_api.py:26-52`:

1. Per-project `ProjectSettings.settings_json["tts"][engine_id]` (Settings UI),
2. then environment variables (`TTS_GOOGLE_*`), 
3. then defaults (engine `default_config()`).

Google-specific env vars, in order: `TTS_GOOGLE_CREDENTIALS_JSON` (inline service-account
JSON), `GOOGLE_APPLICATION_CREDENTIALS` (path to service-account JSON, the standard Google
var — already in `config.py:51`), otherwise default application credentials. Voice and
language default to `en-GB-Standard-D` / `en-GB` (same as the reference script).

### 2. Google engine — `engines/google_cloud.py`

- Dependencies: `google-cloud-texttospeech` (add to `requirements.txt`; lazy-import inside
  the engine so the rest of the app works without it installed).
- `supports_ipa = True`; `supports_text = True` (plain text fallback when no IPA given).
- Credentials: prefer inline JSON via `TextToSpeechClient.from_service_account_info` when
  `TTS_GOOGLE_CREDENTIALS_JSON` set; else `from_service_account_file` when
  `GOOGLE_APPLICATION_CREDENTIALS` set; else default constructor (ADC).
- Synthesis, from the reference script, cleaned up:
  - IPA: `ssml = f'<speak><phoneme alphabet="ipa" ph="{ipa}">{text}</phoneme></speak>'`
  - else plain text input.
  - `VoiceSelectionParams(language_code=..., name=...)`, `AudioConfig(MP3)`.
- `validate_config()`: return error unless credentials/ADC resolvable (lazy — only checked
  when the user actually generates, so a missing library/credentials doesn't break boot).

### 3. Storage — `audio_storage.py`

- Resolve storage root once: `AUDIO_STORAGE_PATH` (config/env); absolute path used as-is,
  relative path resolved against the repo root (app runs from repo root today).
- Per-project subdirectory: `<root>/<project_db_name>/`, where `project_db_name` =
  `g.project_db_name` or session project → `basex_db_name` (fallback `dictionary`), so
  multi-project instances don't mix audio.
- Filename for generated audio is **content-addressed & readable**:
  `f"{lang}_{slug}_{hash12}.mp3"` where `hash = sha1(text|ipa|voice|lang)` — regenerating
  the same word+ipa+voice returns the existing file (no duplicate cloud calls/cost).
  Uploads keep their current uuid-based names.
- API: `get_audio_dir()`, `resolve_audio_path(project_db, filename)` (with
  `os.path.realpath` containment check against the root — no path traversal),
  `save_audio(project_db, filename, content)`, `audio_exists(...)`,
  `package_audio_for_export(project_db, hrefs, dest_dir)`.
- Serving: change `/audio/<filename>` (`views.py:2105`) to serve
  `<root>/<project_db>/<filename>` (project from session/`g`). This **fixes** the mismatch
  and makes the existing frontend `/audio/` URLs correct.
- Migration: at startup, copy any files from the old `app/static/audio/` into
  `<root>/dictionary/` (one-time, idempotent) so existing uploads keep working. The
  frontend URLs for those change from `/static/audio/` to `/audio/`.

### 4. LIFT persistence (fix the dropped-audio bug)

- **Save path**: `alpine-to-serializer.js:271` — emit the serializer's native shape:
  `if (p.audioPath) out.media = [{ href: p.audioPath }];` (keep `audio_path` too for
  backward compat). The serializer already writes `<media href>` from `media`
  (`lift-xml-serializer.js:927-934`).
- **Load path**: `normalize-entry.js` — when the server sends `pronunciation_media`
  (flat list of `{href}`), correlate by order with the pronunciation forms
  (dict-shape branch at `normalizePronunciations:221-233` assigns
  `audioPath: media[idx]?.href` when counts allow; array-shape branch at
  `normalizePronunciation:243` reads `raw.media?.[0]?.href || raw.pronunciation_media?.[0]?.href`).
  Limitation (documented): exact per-pronunciation media association when an entry has
  several pronunciations with several audios is approximated by order — full
  per-pronunciation association is a follow-up (see Open follow-ups).
- **Server-side round trip**: XML sent by the browser is stored verbatim in BaseX
  (`app/api/xml_entries.py:62-96`), so `<media href>` persists once the JS emits it; the
  parser already reads it back into `pronunciation_media`
  (`lift_parser.py:738-753`) and the model already round-trips it
  (`app/models/entry.py:173-177`).

### 5. Credentials & Settings UI

- No DB schema change: store under `settings_json["tts"][engine_id]`
  (JSON column exists; `spell_check` precedent at `app/api/dictionary_api.py:204-206`).
- `app/forms/settings_form.py`: new fields (populated from `settings_json["tts"]` in
  `populate_from_config`, emitted as `"tts": {...}` from `to_dict`):
  - `tts_enabled` (BooleanField) — master switch per engine set
  - `tts_google_credentials_json` (TextAreaField) — inline service-account JSON
  - `tts_google_voice` (StringField, default `en-GB-Standard-D`)
  - `tts_google_language_code` (StringField, default `en-GB`)
- `app/config_manager.py` `update_current_settings`: add a `"tts"` handler (assign into
  `settings.settings_json` with `flag_modified`, mirroring the `backup_settings` block at
  `config_manager.py:160-182`).
- `app/templates/settings.html`: new "Text-to-Speech" section (mirror the AI-settings
  block), showing engine state (enabled, voice, language, credentials field with a hint
  that the env var `GOOGLE_APPLICATION_CREDENTIALS` / `TTS_GOOGLE_CREDENTIALS_JSON` can be
  used instead).
- Security note (same as existing `smtp_password`/`openai_api_key` precedent): secrets at
  rest are stored in the DB in plaintext. Production deployments should prefer the env-var
  route. Credentials are never returned by the settings API to non-admins (settings page
  is admin-only via the auth gate + `admin_required` where applicable).

### 6. API — real generate endpoint

- New route in `app/api/pronunciation.py`:
  `POST /api/pronunciation/generate` with `@_require_auth("pronunciation:write")`.
  Body: `{word, ipa?, language_code?, voice?}`.
  Behavior:
  1. Resolve config; if the engine is disabled/misconfigured → `400/503` with an
     actionable message ("TTS not configured — add a service-account JSON in Settings or
     set TTS_GOOGLE_CREDENTIALS_JSON / GOOGLE_APPLICATION_CREDENTIALS").
  2. `language_code`/`voice` default from settings.
  3. Build content-addressed filename; if the file already exists, return it (dedup).
  4. Call `engine.synthesize`, write via `audio_storage.save_audio`.
  5. Validate output with the existing `validate_audio_file`
     (`app/utils/validators.py`) — fail loudly rather than persist junk.
  6. Return `{success, filename, audio_url: f"/audio/{filename}", engine}`.
- Frontend `entry-form.js` `generateAudio` (`:1765`) switches to the new URL and uses the
  returned `filename` for the hidden `audio_path` input (not just the player URL), so the
  generated audio is attached to the pronunciation and persists on save.
- Delete the stub from `app/views.py:2170-2197` (and its now-unused import of `datetime`
  if nothing else uses it — check first).

### 7. Export packaging

- In `ExportService` (`app/services/export_service.py`), after building the LIFT XML in
  `_export_lift_single` / `_export_lift_dual`:
  - regex-collect `href="..."` from `<media>` elements,
  - for each relative bare filename, copy `<root>/<project_db>/<href>` next to the export:
    single → zip containing the `.lift` + `audio/*` files; dual → zip gains `audio/*`.
  - absolute/URL hrefs are skipped (external).
- This makes exports self-contained (LIFT convention: media referenced relative to the
  `.lift` file).

## Data flow (after)

**Generate:** button → `POST /api/pronunciation/generate` → config resolve → engine →
content-addressed file in `<root>/<project_db>/` → `{audio_url, filename}` → player +
hidden `audio_path`.

**Save:** Alpine state → `alpine-to-serializer` (media) → `lift-xml-serializer`
(`<media href="...">`) → XML stored in BaseX.

**Load:** BaseX XML → `lift_parser` (`pronunciation_media`) → `Entry.to_dict` → form
`normalize-entry` (`audioPath`) → player at `/audio/<filename>` (served from
`<root>/<project_db>/`).

**Export:** `dict_service.export_lift` XML → ExportService packages `audio/*` into the
zip/download.

## Implementation steps

1. `app/services/tts/` package: `base.py`, `registry.py`, `config.py`, `audio_storage.py`,
   `engines/google_cloud.py`, `__init__.py` wiring; register in `app/__init__.py`.
2. Storage: honor `AUDIO_STORAGE_PATH`; fix `/audio/<filename>`; startup migration from
   `static/audio`; update upload + `get_audio_info` (`pronunciation.py:91-107,240-258`) to
   the new dir and `/audio/` URLs.
3. Settings: form fields + `config_manager` `"tts"` handler + `settings.html` section.
4. API: real generate endpoint; frontend caller update; remove `views.py` stub.
5. Persistence: `alpine-to-serializer.js` + `normalize-entry.js` + JS test
   (`tests/unit/alpine-adapter.test.js` style) + `entry-form.js:706` URL.
6. Export packaging in `ExportService`.
7. `requirements.txt`: `google-cloud-texttospeech`.
8. Tests: new `tests/unit/test_tts_engine.py` (registry, config resolution with mocked
   settings/env, filename dedup, storage containment, generate endpoint with a fake
   engine — no network), extend existing pronunciation API tests; run JS tests via
   `tests/js_test_runner.py`; run the affected unit tests; manual smoke of the generate
   flow (no real Google credentials → expect a clean "not configured" error).

## Files touched

- New: `app/services/tts/*` (6 files), `tests/unit/test_tts_engine.py`
- Modified: `app/views.py` (stub removal, `/audio/` route), `app/api/pronunciation.py`,
  `app/forms/settings_form.py`, `app/config_manager.py`, `app/templates/settings.html`,
  `app/static/js/entry-form.js`, `app/static/js/alpine/alpine-to-serializer.js`,
  `app/static/js/alpine/normalize-entry.js`, `app/static/js/pronunciation-forms.js`,
  `app/services/export_service.py`, `app/__init__.py`, `requirements.txt`,
  `tests/unit/alpine-adapter.test.js` (+ any JS tests for normalize),
  this plan doc.

## Verification

- `venv/bin/python -m pytest tests/unit/test_tts_engine.py tests/unit/test_api_key_auth.py
  tests/unit/test_autosave.py -x` (targeted), then the broader unit suite.
- JS: `venv/bin/python tests/js_test_runner.py tests/unit/alpine-adapter.test.js`
  (or the repo's JS test invocation).
- Manual: generate without credentials → clean error; with a fake engine → file appears in
  `<root>/<project_db>/`, `/audio/<filename>` serves it, save → XML contains `<media
  href>`, reload → player works.

## Open follow-ups (out of scope)

- Exact per-pronunciation ↔ per-media association (model change: pronunciations as a list
  of `{form, media}` instead of flattened dict+list).
- Additional engines (text-only cloud/local: e.g. Piper, eSpeak-ng, Azure, ElevenLabs) —
  the registry makes this a new `engines/*.py` + settings section.
- Encrypting secrets at rest / masking credentials in the settings form.
- Audio retention/GC (delete audio orphaned when entries change), rate/cost limiting.
