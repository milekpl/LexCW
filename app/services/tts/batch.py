"""
Batch TTS pronunciation generation.

Reuses the single-entry synthesis logic (:func:`synthesize_variants`, extracted so
the HTTP route and the batch job share one implementation) to generate audio for
many entries at once and attach it to their LIFT XML (``<media href>`` inside each
``<pronunciation>``).

Entry selection:
- a workset (``workset_entries`` table in Postgres), or
- all entries that have pronunciations but no audio yet (XQuery over BaseX).

Runs as an in-process background job (daemon thread) with a job store polled by the
client — the same pattern as the embedding index rebuild (``app/api/embedding_api.py``).
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import uuid
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional

from app.services.ipa_service import expand_pronunciations
from app.services.tts import audio_storage
from app.services.tts.base import TTSEngineError, TTSOptions
from app.services.tts.registry import get_engine

logger = logging.getLogger(__name__)

DEFAULT_ENGINE_ID = "google_cloud"
MAX_BATCH_ENTRIES = 5000

# ---------------------------------------------------------------------------
# Shared single-word synthesis (used by both the HTTP route and the batch job)
# ---------------------------------------------------------------------------


def synthesize_variants(
    word: str,
    ipa: Optional[str],
    engine,
    language_code: Optional[str] = None,
    voice: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate audio for every expanded pronunciation variant of ``ipa``.

    Comma-delimited IPA lists are expanded first; one content-addressed audio file
    is generated (or reused from cache) per variant. Returns a list of
    ``{ipa, filename, audio_url, cached}``. Raises :class:`TTSEngineError` on
    synthesis or persistence failure.
    """
    lang = language_code or engine.config.get("language_code") or "en-GB"
    voice_name = voice or engine.config.get("voice") or "en-GB-Standard-D"

    variants = expand_pronunciations(ipa) if ipa else []
    results: List[Dict[str, Any]] = []

    for variant in (variants or [None]):
        variant_ipa = variant or None

        fingerprint = hashlib.sha1(
            f"{word}\x00{variant_ipa or ''}\x00{lang}\x00{voice_name}".encode("utf-8")
        ).hexdigest()[:12]
        slug = re.sub(r"[^A-Za-z0-9]+", "_", word).strip("_")[:40] or "word"
        filename = f"{lang}_{slug}_{fingerprint}.mp3"

        if audio_storage.audio_exists(filename):
            results.append({
                "ipa": variant_ipa or "",
                "filename": filename,
                "audio_url": f"/audio/{filename}",
                "cached": True,
            })
            continue

        result = engine.synthesize(
            TTSOptions(text=word, ipa=variant_ipa, language_code=lang, voice=voice_name)
        )

        path = audio_storage.resolve_audio_path(filename)
        if path is None:
            raise TTSEngineError(f"Refusing unsafe audio filename: {filename}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.audio_content)

        from app.utils.validators import validate_audio_file

        if not validate_audio_file(str(path)):
            path.unlink(missing_ok=True)
            raise TTSEngineError("Generated audio failed validation")

        results.append({
            "ipa": variant_ipa or "",
            "filename": filename,
            "audio_url": f"/audio/{filename}",
            "cached": False,
        })

    return results


# ---------------------------------------------------------------------------
# Entry selection
# ---------------------------------------------------------------------------


def iter_workset_entry_ids(workset_id: int) -> List[str]:
    """Return the entry IDs of a workset (from the Postgres workset_entries table)."""
    from flask import current_app

    conn = current_app.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT entry_id FROM workset_entries WHERE workset_id = %s",
                (workset_id,),
            )
            return [str(row[0]) for row in cur.fetchall()]
    finally:
        current_app.pg_pool.putconn(conn)


def iter_entries_missing_audio(dict_service) -> List[str]:
    """Return entry IDs that have pronunciations but no audio media yet (XQuery)."""
    db_name = dict_service.db_connector.database
    xquery = (
        f"let $entries := collection('{db_name}')//*[local-name()='entry' "
        "and .//*[local-name()='pronunciation'] "
        "and not(.//*[local-name()='media'])] "
        "return string-join(for $e in $entries return data($e/@id), '|||')"
    )
    result = dict_service.db_connector.execute_query(xquery)
    if not result or not result.strip():
        return []
    return [eid for eid in result.split("|||") if eid]


# ---------------------------------------------------------------------------
# Entry XML manipulation (attach generated audio)
# ---------------------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _ns(tag: str, name: str) -> str:
    if "}" in tag:
        return tag.split("}")[0] + "}" + name
    return name


def _entry_headword(root: ET.Element) -> str:
    """First lexical-unit form text, or empty string."""
    for lu in root.iter():
        if _local(lu.tag) == "lexical-unit":
            for form in lu:
                if _local(form.tag) != "form":
                    continue
                text = form.findtext(f"{form.tag.split('}')[0] + '}' if '}' in form.tag else ''}text")
                if text and text.strip():
                    return text.strip()
    return ""


def _pronunciation_ipa_texts(pron: ET.Element) -> List[str]:
    """Non-empty form texts of a pronunciation (the IPA value)."""
    texts: List[str] = []
    for form in pron:
        if _local(form.tag) != "form":
            continue
        text = form.findtext(_ns(form.tag, "text"))
        if text and text.strip():
            texts.append(text.strip())
    return texts


def _existing_media_hrefs(pron: ET.Element) -> set:
    hrefs = set()
    for media in pron:
        if _local(media.tag) == "media":
            href = media.get("href")
            if href:
                hrefs.add(href)
    return hrefs


def add_audio_to_entry_xml(
    entry_xml: str,
    engine,
    entry_id: str = "",
) -> tuple[str, int, List[Dict[str, Any]]]:
    """Generate audio for an entry's pronunciations and inject ``<media href>``.

    Args:
        entry_xml: Raw LIFT XML for one entry.
        engine: A TTS engine instance (already validated/enabled).
        entry_id: Entry id, used as the synthesis word fallback.

    Returns:
        ``(new_xml, generated_count, details)`` where ``details`` is a list of
        ``{ipa, filename}`` per generated/cached audio.
    """
    root = ET.fromstring(entry_xml)
    word = _entry_headword(root) or entry_id

    all_details: List[Dict[str, Any]] = []
    changed = False

    for pron in root.iter():
        if _local(pron.tag) != "pronunciation":
            continue

        ipa_texts = _pronunciation_ipa_texts(pron)
        if not ipa_texts:
            continue

        # Expand all form texts (comma-delimited lists included) and dedupe.
        variants: List[str] = []
        for text in ipa_texts:
            for v in expand_pronunciations(text):
                if v not in variants:
                    variants.append(v)

        if not variants:
            continue

        try:
            results = synthesize_variants(word, ", ".join(variants), engine)
        except TTSEngineError as e:
            logger.warning("TTS failed for entry %s (%s): %s", entry_id, word, e)
            continue

        existing = _existing_media_hrefs(pron)
        for res in results:
            filename = res["filename"]
            if filename in existing:
                continue
            media = ET.SubElement(pron, _ns(pron.tag, "media"))
            media.set("href", filename)
            existing.add(filename)
            all_details.append({"ipa": res["ipa"], "filename": filename})
            changed = True

    new_xml = ET.tostring(root, encoding="unicode")
    return new_xml, len(all_details), all_details


# ---------------------------------------------------------------------------
# Background job store + runner (embedding-api pattern)
# ---------------------------------------------------------------------------

_batch_jobs: Dict[str, Dict[str, Any]] = {}
_batch_jobs_lock = threading.Lock()


def _update_job(job_id: str, data: Dict[str, Any]) -> None:
    with _batch_jobs_lock:
        if job_id not in _batch_jobs:
            _batch_jobs[job_id] = {}
        _batch_jobs[job_id].update(data)


def get_batch_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _batch_jobs_lock:
        return dict(_batch_jobs.get(job_id, {}))


def cancel_batch_job(job_id: str) -> bool:
    with _batch_jobs_lock:
        job = _batch_jobs.get(job_id)
        if not job:
            return False
        job["cancelled"] = True
        job["message"] = "Stopping batch job..."
    return True


def _prune_batch_jobs() -> None:
    """Drop finished jobs older than 1 hour to bound memory."""
    import time

    cutoff = time.time() - 3600
    with _batch_jobs_lock:
        for jid in [j for j, job in _batch_jobs.items() if job.get("_finished_at", 0) < cutoff]:
            _batch_jobs.pop(jid, None)


def start_batch_job(
    entry_ids: List[str],
    engine,
    attach: bool = True,
) -> str:
    """Start a background job generating audio for ``entry_ids``.

    Returns the new ``job_id``. The job runs in a daemon thread and reports via
    :func:`get_batch_job`. ``engine`` must already be enabled + validated.
    """
    from flask import current_app

    job_id = str(uuid.uuid4())
    app_obj = current_app._get_current_object()

    _update_job(job_id, {
        "job_id": job_id,
        "status": "queued",
        "processed": 0,
        "total": len(entry_ids),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "message": "Queued pronunciation batch job...",
        "error": None,
        "engine": engine.engine_id,
        "attach": attach,
        "cancelled": False,
    })

    def _run() -> None:
        with app_obj.app_context():
            from app.api.xml_entries import get_xml_entry_service

            _update_job(job_id, {"status": "running", "message": "Starting..."})
            xml_service = get_xml_entry_service()
            results: List[Dict[str, Any]] = []
            total = len(entry_ids)
            processed = success = failed = skipped = 0

            try:
                for entry_id in entry_ids:
                    if get_batch_job(job_id).get("cancelled"):
                        break

                    try:
                        entry = xml_service.get_entry(entry_id)
                        new_xml, count, _details = add_audio_to_entry_xml(
                            entry["xml"], engine, entry_id=entry_id
                        )
                        if count == 0:
                            skipped += 1
                            results.append({
                                "id": entry_id, "status": "skipped",
                                "reason": "no IPA pronunciation",
                            })
                        else:
                            xml_service.update_entry(entry_id, new_xml)
                            success += 1
                            results.append({
                                "id": entry_id, "status": "success",
                                "audio_count": count,
                            })
                    except Exception as e:  # noqa: BLE001 - per-entry isolation
                        failed += 1
                        results.append({"id": entry_id, "status": "error", "error": str(e)})

                    processed += 1
                    _update_job(job_id, {
                        "processed": processed,
                        "success": success,
                        "failed": failed,
                        "skipped": skipped,
                        "message": f"Processed {processed}/{total}",
                    })

                cancelled = get_batch_job(job_id).get("cancelled")
                _update_job(job_id, {
                    "status": "cancelled" if cancelled else "completed",
                    "message": (
                        "Batch job stopped." if cancelled
                        else f"Done: {success} ok, {skipped} skipped, {failed} failed."
                    ),
                    "summary": {
                        "total": total,
                        "processed": processed,
                        "success": success,
                        "failed": failed,
                        "skipped": skipped,
                    },
                    "results": results,
                    "_finished_at": __import__("time").time(),
                })
            except Exception as e:  # noqa: BLE001
                logger.error("Batch job %s failed: %s", job_id, e, exc_info=True)
                _update_job(job_id, {
                    "status": "failed",
                    "error": str(e),
                    "message": f"Batch job failed: {e}",
                    "_finished_at": __import__("time").time(),
                })

    _prune_batch_jobs()
    t = threading.Thread(target=_run, daemon=True, name=f"tts-batch-{job_id[:8]}")
    t.start()
    return job_id


def get_ready_engine() -> Any:
    """Return a validated, enabled TTS engine or raise TTSEngineError with the reason."""
    engine = get_engine(DEFAULT_ENGINE_ID)
    if engine is None:
        raise TTSEngineError("No TTS engine is available")
    if not engine.config.get("enabled"):
        raise TTSEngineError(
            "Text-to-speech is not enabled. Enable it in Settings → Text-to-Speech, "
            "or set TTS_GOOGLE_ENABLED=true and provide credentials."
        )
    config_error = engine.validate_config()
    if config_error:
        raise TTSEngineError(config_error)
    return engine
