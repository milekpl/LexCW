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

pronunciation_bp = Blueprint('pronunciation', __name__, url_prefix='/api/pronunciation')

# Audio file configuration
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'opus', 'm4a'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@pronunciation_bp.route('/upload', methods=['POST'])
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
        
        # Ensure audio directory exists
        static_folder = current_app.static_folder
        if not static_folder:
            return jsonify({
                'success': False,
                'message': 'Static folder not configured'
            }), 500
            
        audio_dir = os.path.join(static_folder, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(audio_dir, unique_filename)
        file.save(file_path)
        
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
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400
        
        # Check if file exists
        static_folder = current_app.static_folder
        if not static_folder:
            return jsonify({
                'success': False,
                'message': 'Static folder not configured'
            }), 500
            
        audio_dir = os.path.join(static_folder, 'audio')
        file_path = os.path.join(audio_dir, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Delete the file
        os.remove(file_path)
        
        current_app.logger.info(f"Audio file deleted: {safe_filename}")
        
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
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400
        
        # Check if file exists
        static_folder = current_app.static_folder
        if not static_folder:
            return jsonify({
                'success': False,
                'message': 'Static folder not configured'
            }), 500
            
        audio_dir = os.path.join(static_folder, 'audio')
        file_path = os.path.join(audio_dir, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Get file info
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return jsonify({
            'success': True,
            'filename': safe_filename,
            'file_size': file_size,
            'mime_type': mime_type or 'audio/mpeg',
            'url': f'/static/audio/{safe_filename}'
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
# full access.

from app.utils.auth_decorators import require_auth as _require_auth


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
