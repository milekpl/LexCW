"""
Audio file storage for pronunciations.

Single source of truth: the ``AUDIO_STORAGE_PATH`` config/env value (default
``instance/audio``), resolved against the repo root when relative. Files are stored in
per-project subdirectories (``<root>/<project_db>/``) so multi-project instances do not
mix media. LIFT XML stores only the **bare relative filename** in ``<media href>``;
the serving route and export packaging resolve it back to this directory.

Legacy: files uploaded before this refactor live in ``app/static/audio`` and were
served via ``/static/audio/``. :func:`migrate_legacy_audio` copies them into the new
location once at startup so existing data keeps working.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SAFE_DB_RE = re.compile(r"[^A-Za-z0-9_.-]")


def _repo_root() -> Path:
    # <repo>/app/services/tts/audio_storage.py -> parents[3]
    return Path(__file__).resolve().parents[3]


def get_storage_root() -> Path:
    """Resolve the audio storage root directory (absolute)."""
    cfg: Optional[str] = None
    try:
        from flask import current_app

        cfg = current_app.config.get("AUDIO_STORAGE_PATH")
    except Exception:
        cfg = None
    cfg = cfg or os.environ.get("AUDIO_STORAGE_PATH") or "instance/audio"
    path = Path(cfg).expanduser()
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def get_project_db() -> str:
    """Return the current project's database name (sanitized), default ``dictionary``."""
    project_db = "dictionary"
    try:
        from flask import current_app, g, session

        g_db = getattr(g, "project_db_name", None)
        if g_db:
            project_db = str(g_db)
        else:
            project_id = session.get("project_id")
            if project_id:
                from app.models.project_settings import ProjectSettings

                ps = ProjectSettings.query.get(int(project_id))
                if ps is not None and getattr(ps, "basex_db_name", None):
                    project_db = str(ps.basex_db_name)
    except Exception:
        pass
    sanitized = _SAFE_DB_RE.sub("_", project_db).strip("_") or "dictionary"
    return sanitized


def get_project_audio_dir(project_db: Optional[str] = None) -> Path:
    """Return the per-project audio directory, creating it if needed."""
    db = project_db or get_project_db()
    directory = get_storage_root() / db
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("Could not create audio directory %s: %s", directory, e)
    return directory


def safe_filename(filename: str) -> Optional[str]:
    """Return a bare, safe filename or None if the input is unusable.

    Rejects path separators and traversal attempts — LIFT hrefs must stay bare
    relative filenames (no directories, no ``..``).
    """
    if not filename:
        return None
    if "/" in filename or "\\" in filename:
        return None
    if filename in (".", "..") or ".." in filename:
        return None
    if filename.startswith("/"):
        return None
    return filename


def resolve_audio_path(
    filename: str, project_db: Optional[str] = None
) -> Optional[Path]:
    """Resolve ``filename`` to an absolute path inside the project audio dir.

    Returns None if the filename is unsafe. The result is containment-checked against
    the storage root (defence against path traversal via the DB value).
    """
    name = safe_filename(filename)
    if name is None:
        return None
    directory = get_project_audio_dir(project_db)
    root = directory.resolve()
    path = (directory / name).resolve()
    if path.parent != root:
        logger.warning("Refusing audio path outside storage root: %s", path)
        return None
    return path


def save_audio(
    filename: str, content: bytes, project_db: Optional[str] = None
) -> Optional[Path]:
    """Persist ``content`` under the project audio dir. Returns the written path."""
    path = resolve_audio_path(filename, project_db)
    if path is None:
        logger.error("Refusing to save unsafe audio filename: %r", filename)
        return None
    try:
        path.write_bytes(content)
        return path
    except OSError as e:
        logger.error("Failed to write audio file %s: %s", path, e)
        return None


def audio_exists(filename: str, project_db: Optional[str] = None) -> bool:
    path = resolve_audio_path(filename, project_db)
    return bool(path and path.is_file())


def migrate_legacy_audio(
    static_audio_dir: Optional[Union[str, Path]] = None,
) -> int:
    """Copy files from the legacy ``app/static/audio`` dir into the new storage.

    Idempotent: files that already exist in the target are skipped. Returns the number
    of files copied. ``static_audio_dir`` may be passed explicitly for testing.
    """
    if static_audio_dir is not None:
        static_audio = Path(static_audio_dir)
    else:
        try:
            from flask import current_app

            static_audio = Path(current_app.static_folder) / "audio"
        except Exception:
            static_audio = _repo_root() / "app" / "static" / "audio"

    if not static_audio.is_dir():
        return 0

    # Only carry over audio files; skip anything else that may have landed there.
    audio_extensions = {".mp3", ".wav", ".ogg", ".opus", ".m4a", ".aac", ".flac", ".webm"}
    target = get_project_audio_dir("dictionary")
    copied = 0
    for src in static_audio.iterdir():
        if not src.is_file():
            continue
        if src.suffix.lower() not in audio_extensions:
            continue
        name = safe_filename(src.name)
        if name is None:
            continue
        dst = target / name
        if dst.exists():
            continue
        try:
            shutil.copy2(src, dst)
            copied += 1
        except OSError as e:
            logger.warning("Failed to migrate legacy audio %s: %s", src, e)
    if copied:
        logger.info("Migrated %d legacy audio file(s) to %s", copied, target)
    return copied
