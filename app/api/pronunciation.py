"""
Pronunciation audio upload and management API endpoints.
Handles MP3 file uploads for pronunciation entries.
"""

import os
import uuid
from typing import Optional
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import mimetypes

from app.utils.validators import validate_audio_file
from app.utils.db_utils import safe_commit
from app.utils.auth_decorators import require_auth as _require_auth

pronunciation_bp = Blueprint('pronunciation', __name__, url_prefix='/api/pronunciation')

# Audio file configuration
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'opus', 'm4a'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@pronunciation_bp.route('/upload', methods=['POST'])
@_require_auth("pronunciation:write")
def upload_audio():
    """
    Upload an audio file for a pronunciation entry.
    
    Expected form data:
    - audio_file: The audio file to upload
    - ipa_value: The IPA transcription for this pronunciation
    - index: The pronunciation index in the form
    
    Returns:
        JSON response with upload result and filename
    """
    try:
        # Check if file is present
        if 'audio_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No audio file provided'
            }), 400
        
        file = request.files['audio_file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400
        
        # Validate file type
        if file.filename and not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': f'File type not allowed. Supported formats: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Validate MIME type
        if file.content_type and not file.content_type.startswith('audio/'):
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Please upload an audio file.'
            }), 400
        
        # Get additional form data
        ipa_value = request.form.get('ipa_value', '').strip()
        index = request.form.get('index', '0')
        
        if not ipa_value:
            return jsonify({
                'success': False,
                'message': 'IPA transcription is required'
            }), 400
        
        # Generate secure filename
        if not file.filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400
            
        file_extension = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}_{index}.{file_extension}"

        # Resolve the target path inside the per-project audio storage
        from app.services.tts.audio_storage import resolve_audio_path

        file_path = resolve_audio_path(unique_filename)
        if file_path is None:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400

        # Ensure the audio directory exists and save the file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file.save(str(file_path))
        
        # Validate the uploaded audio file
        try:
            if not validate_audio_file(file_path):
                os.remove(file_path)  # Clean up invalid file
                return jsonify({
                    'success': False,
                    'message': 'Invalid audio file format or corrupted file'
                }), 400
        except Exception as e:
            # Clean up if validation fails
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({
                'success': False,
                'message': f'Audio validation failed: {str(e)}'
            }), 400
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        # Log the upload (optional)
        current_app.logger.info(
            f"Audio uploaded: {unique_filename}, IPA: {ipa_value}, Size: {file_size} bytes"
        )
        
        return jsonify({
            'success': True,
            'message': 'Audio file uploaded successfully',
            'filename': unique_filename,
            'ipa_value': ipa_value,
            'index': index,
            'file_size': file_size
        })
        
    except RequestEntityTooLarge:
        return jsonify({
            'success': False,
            'message': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB'
        }), 413
        
    except Exception as e:
        current_app.logger.error(f"Audio upload error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during upload'
        }), 500


@pronunciation_bp.route('/delete/<filename>', methods=['DELETE'])
@_require_auth("pronunciation:write")
def delete_audio(filename: str):
    """
    Delete an uploaded audio file.
    
    Args:
        filename: The filename to delete
        
    Returns:
        JSON response with deletion result
    """
    try:
        # Validate filename to prevent directory traversal
        from app.services.tts.audio_storage import resolve_audio_path

        file_path = resolve_audio_path(filename)
        if file_path is None:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400
        
        if not os.path.exists(str(file_path)):
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Delete the file
        os.remove(str(file_path))
        
        current_app.logger.info(f"Audio file deleted: {file_path.name}")
        
        return jsonify({
            'success': True,
            'message': 'Audio file deleted successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Audio deletion error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during deletion'
        }), 500


@pronunciation_bp.route('/info/<filename>', methods=['GET'])
def get_audio_info(filename: str):
    """
    Get information about an uploaded audio file.
    
    Args:
        filename: The filename to get info for
        
    Returns:
        JSON response with file information
    """
    try:
        # Validate filename
        from app.services.tts.audio_storage import resolve_audio_path

        file_path = resolve_audio_path(filename)
        if file_path is None:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400
        
        if not os.path.exists(str(file_path)):
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Get file info
        file_size = os.path.getsize(str(file_path))
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        return jsonify({
            'success': True,
            'filename': file_path.name,
            'file_size': file_size,
            'mime_type': mime_type or 'audio/mpeg',
            'url': f'/audio/{file_path.name}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Audio info error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while getting file info'
        }), 500


# ---------------------------------------------------------------------------
# Auth for API-key-protected endpoints
# ---------------------------------------------------------------------------
# These endpoints authenticate with a session *or* an API key. The decorator is
# shared (app/utils/auth_decorators.py) — this module used to carry a private copy
# whose scope check returned 401 instead of 403 and treated an empty scope list as
# full access. Imported at the top of this module so all routes can use it.


# ---------------------------------------------------------------------------
# TTS audio generation (engine plugin framework)
# ---------------------------------------------------------------------------


@pronunciation_bp.route("/generate", methods=["POST"])
@_require_auth("pronunciation:write")
def generate_audio():
    """Generate pronunciation audio via the configured TTS engine.

    Expects JSON body::

        {"word": "tree", "ipa": "triː, ˈtɹiː", "language_code": "en-GB", "voice": "..."}

    ``word`` is required; ``ipa`` is optional (the engine uses it when it supports
    IPA, otherwise it synthesizes from text). ``language_code``/``voice`` default to
    the engine configuration.

    Comma-delimited IPA lists (as most dictionaries store them) are expanded before
    synthesis — each variant is spoken correctly on its own instead of feeding the
    raw list to the engine. One audio file is generated per expanded variant.

    Returns::

        {
          "success": true,
          "results": [{"ipa": "triː", "filename": "...", "audio_url": "/audio/...", "cached": false}, ...],
          "filename": "<first filename>", "audio_url": "/audio/<first>",
          "engine": "google_cloud", "cached": false
        }

    ``filename``/``audio_url`` are kept as the first result for backward compatibility.
    Each filename is content-addressed (word+ipa+voice+lang), so regenerating the same
    pronunciations returns the existing files without calling the engine again.
    """
    from app.services.tts import get_engine
    from app.services.tts.batch import synthesize_variants
    from app.services.tts.base import TTSEngineError

    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip()
    if not word:
        return jsonify({"success": False, "message": "A 'word' is required"}), 400
    ipa = (data.get("ipa") or "").strip() or None
    language_code = (data.get("language_code") or "").strip() or None
    voice = (data.get("voice") or "").strip() or None

    engine = get_engine("google_cloud")
    if engine is None:
        return jsonify({"success": False, "message": "No TTS engine is available"}), 503

    if not engine.config.get("enabled"):
        return jsonify({
            "success": False,
            "message": (
                "Text-to-speech is not enabled. Enable it in Settings → "
                "Text-to-Speech, or set TTS_GOOGLE_ENABLED=true and provide credentials."
            ),
        }), 400

    config_error = engine.validate_config()
    if config_error:
        return jsonify({"success": False, "message": config_error}), 400

    try:
        results = synthesize_variants(word, ipa, engine, language_code, voice)
    except TTSEngineError as e:
        current_app.logger.error("TTS synthesis failed for %r: %s", word, e)
        return jsonify({"success": False, "message": str(e)}), 502

    primary = results[0] if results else None
    payload = {
        "success": True,
        "results": results,
        "engine": engine.engine_id,
        "cached": all(r.get("cached") for r in results) if results else False,
    }
    if primary:
        payload["filename"] = primary["filename"]
        payload["audio_url"] = primary["audio_url"]
    current_app.logger.info(
        "TTS generated %d audio file(s) for %r via %s",
        len(results), word, engine.engine_id,
    )
    return jsonify(payload)


# ---------------------------------------------------------------------------
# Batch pronunciation generation (background job)
# ---------------------------------------------------------------------------


@pronunciation_bp.route("/batch", methods=["POST"])
@_require_auth("pronunciation:write")
def batch_generate():
    """Start a background job that generates and attaches pronunciation audio.

    Body::

        {"mode": "workset", "workset_id": 3}
        {"mode": "missing_audio"}

    ``mode`` selects the entry set: ``workset`` (entry IDs from the workset table)
    or ``missing_audio`` (every entry that has pronunciations but no audio yet).
    The job runs asynchronously; poll ``/batch/status/<job_id>`` for progress.

    Returns::

        202 {"success": true, "job_id": "...", "total": 123, "message": "..."}
    """
    from app.services.tts.batch import (
        MAX_BATCH_ENTRIES,
        get_ready_engine,
        iter_entries_missing_audio,
        iter_workset_entry_ids,
        start_batch_job,
    )
    from app.services.tts.base import TTSEngineError

    data = request.get_json(silent=True) or {}
    mode = data.get("mode") or "workset"
    workset_id = data.get("workset_id")

    try:
        if mode == "missing_audio":
            from app.services.dictionary_service import DictionaryService

            dict_service = current_app.injector.get(DictionaryService)
            entry_ids = iter_entries_missing_audio(dict_service)
        elif mode == "workset" and workset_id:
            entry_ids = iter_workset_entry_ids(int(workset_id))
        else:
            return jsonify({
                "success": False,
                "message": "Provide workset_id (mode='workset') or use mode='missing_audio'",
            }), 400
    except Exception as e:
        current_app.logger.error("Batch entry selection failed: %s", e, exc_info=True)
        return jsonify({"success": False, "message": f"Entry selection failed: {e}"}), 500

    if not entry_ids:
        return jsonify({
            "success": True,
            "job_id": None,
            "total": 0,
            "message": "No entries to process",
        })

    if len(entry_ids) > MAX_BATCH_ENTRIES:
        entry_ids = entry_ids[:MAX_BATCH_ENTRIES]

    try:
        engine = get_ready_engine()
    except TTSEngineError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    job_id = start_batch_job(entry_ids, engine)
    return jsonify({
        "success": True,
        "job_id": job_id,
        "total": len(entry_ids),
        "message": "Batch job started",
    }), 202


@pronunciation_bp.route("/batch/status/<job_id>", methods=["GET"])
@_require_auth("pronunciation:read")
def batch_status(job_id: str):
    """Poll progress of a background pronunciation batch job."""
    from app.services.tts.batch import get_batch_job

    job = get_batch_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404
    return jsonify({"success": True, "job": job})


@pronunciation_bp.route("/batch/cancel/<job_id>", methods=["POST"])
@_require_auth("pronunciation:write")
def batch_cancel(job_id: str):
    """Cancel a running background pronunciation batch job."""
    from app.services.tts.batch import cancel_batch_job

    if not cancel_batch_job(job_id):
        return jsonify({"success": False, "error": "Job not found"}), 404
    return jsonify({"success": True, "message": "Cancel request sent"})


# ---------------------------------------------------------------------------
# IPA compression and deduplication endpoints
# ---------------------------------------------------------------------------


@pronunciation_bp.route("/compress", methods=["POST"])
@_require_auth("pronunciation:read")
def compress_ipa():
    """Expand parenthesised optional sounds in IPA transcriptions.

    Expects JSON body::

        {"entries": [{"lexeme": "...", "ipa": "..."}, ...]}
    """
    data = request.get_json()
    if not data or "entries" not in data:
        return jsonify({"error": "Request body must contain 'entries' list"}), 400

    from app.services.ipa_service import process_and_split

    results = []
    for entry in data["entries"]:
        lexeme = entry.get("lexeme", "")
        ipa = entry.get("ipa", "")
        if not ipa:
            results.append({"lexeme": lexeme, "ipa_raw": ipa, "variants": []})
            continue

        variants = process_and_split(ipa)
        results.append(
            {
                "lexeme": lexeme,
                "ipa_raw": ipa,
                "variants": variants,
            }
        )

    return jsonify({"results": results}), 200


@pronunciation_bp.route("/deduplicate", methods=["POST"])
@_require_auth("pronunciation:read")
def deduplicate_pronunciations():
    """Find duplicate or near-duplicate pronunciations.

    Expects JSON body::

        {"entries": [{"lexeme": "...", "ipa": "..."}, ...]}
    """
    data = request.get_json()
    if not data or "entries" not in data:
        return jsonify({"error": "Request body must contain 'entries' list"}), 400

    from app.services.ipa_service import find_duplicates

    duplicates = find_duplicates(data["entries"])

    return jsonify(
        {
            "duplicates": duplicates,
            "stats": {
                "total_entries": len(data["entries"]),
                "duplicate_groups": len(duplicates),
            },
        }
    ), 200


@pronunciation_bp.route("/draft", methods=["POST"])
@_require_auth("pronunciation:read")
def draft_ipa():
    """Draft IPA pronunciation(s) for a headword using the deployed ByT5 model.

    Expects JSON body::

        {"headword": "...", "writing_system": "seh-fonipa", "num_candidates": 1}

    Returns::

        {"available": true, "writing_system": "...", "candidates": ["ˈkæt", ...]}

    If no ByT5 model is deployed for the requested writing system, ``available``
    is ``false`` and ``candidates`` is empty (this is not an error).
    """
    data = request.get_json(silent=True) or {}
    headword = (data.get("headword") or "").strip()
    if not headword:
        return jsonify({"error": "Request body must contain a non-empty 'headword'"}), 400

    ws = data.get("writing_system") or "seh-fonipa"
    try:
        num_candidates = int(data.get("num_candidates", 1) or 1)
    except (TypeError, ValueError):
        num_candidates = 1
    num_candidates = max(1, min(num_candidates, 5))

    from app.services.ipa_byt5_service import IPAByT5Service

    svc = IPAByT5Service.get_instance(ipa_ws=ws)
    if not svc.is_available():
        return jsonify(
            {
                "available": False,
                "writing_system": ws,
                "candidates": [],
                "message": "No ByT5 IPA model is deployed for this writing system.",
            }
        ), 200

    candidates = svc.draft_ipa(headword, num_return_sequences=num_candidates)
    return (
        jsonify(
            {
                "available": True,
                "writing_system": ws,
                "candidates": candidates,
            }
        ),
        200,
    )


@pronunciation_bp.route("/deduplicate/apply", methods=["POST"])
@_require_auth("pronunciation:write")
def apply_deduplication():
    """Apply deduplication actions (remove or merge pronunciation entries).

    Expects JSON body::

        {
            "actions": [
                {"type": "remove", "entry_id": "...", "ipa": "..."},
                {"type": "merge_to_compressed", "entry_id": "...", "ipa": "..."}
            ]
        }
    """
    data = request.get_json()
    if not data or "actions" not in data:
        return jsonify({"error": "Request body must contain 'actions' list"}), 400

    applied = 0
    errors = []
    for i, action in enumerate(data["actions"]):
        action_type = action.get("type")
        entry_id = action.get("entry_id")

        if not action_type or not entry_id:
            errors.append(
                {"index": i, "error": "action must have 'type' and 'entry_id'"}
            )
            continue

        if action_type == "remove":
            try:
                from app.services.dictionary_service import DictionaryService
                dictionary_service = current_app.injector.get(DictionaryService)
                dictionary_service.delete_pronunciation(entry_id, action.get("writing_system", "seh-fonipa"))
                applied += 1
            except Exception as e:
                errors.append({"index": i, "error": f"Failed to remove pronunciation: {str(e)}"})
        elif action_type == "merge_to_compressed":
            try:
                from app.services.dictionary_service import DictionaryService
                dictionary_service = current_app.injector.get(DictionaryService)
                ipa_value = action.get("ipa", "")
                dictionary_service.update_pronunciation(entry_id, action.get("writing_system", "seh-fonipa"), ipa_value)
                applied += 1
            except Exception as e:
                errors.append({"index": i, "error": f"Failed to merge pronunciation: {str(e)}"})
        else:
            errors.append({"index": i, "error": f"Unknown action type: {action_type}"})

    return jsonify({"applied": applied, "errors": errors}), 200
