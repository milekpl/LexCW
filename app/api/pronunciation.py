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
# Auth helper for API-key-protected endpoints
# ---------------------------------------------------------------------------


def _check_api_key_auth(required_scope: str) -> bool:
    """Authenticate request via API key (Bearer) or session fallback.

    Sets ``g.api_key`` or ``g.current_user`` accordingly.
    Returns ``True`` if authenticated, ``False`` if response was sent.
    """
    from datetime import datetime, timezone
    from werkzeug.security import check_password_hash
    from app.models.api_key import ApiKey
    from app.models.workset_models import db as _db
    from app.utils.auth_decorators import get_current_user

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_key = auth_header[7:]
        if not raw_key.startswith("sw_") or len(raw_key) < 11:
            return False  # caller will see g.current_user is None

        prefix = raw_key[:11]
        key_record = ApiKey.query.filter_by(key_prefix=prefix, is_active=True).first()
        if not key_record or not check_password_hash(key_record.key_hash, raw_key):
            return False

        key_scopes = key_record.scopes or []
        if key_scopes and required_scope not in key_scopes:
            return False

        key_record.last_used_at = datetime.now(timezone.utc)
        safe_commit(_db, "pronunciation")
        g.api_key = key_record
        g.current_user = None
        return True

    # Session fallback
    user = get_current_user()
    if user:
        g.current_user = user
        g.api_key = None
        return True

    return False


def _require_auth(required_scope: str):
    """Decorator factory: authenticate via API key or session.

    Returns 401/403 JSON if authentication fails.
    """
    from functools import wraps

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ok = _check_api_key_auth(required_scope)
            if not ok:
                return jsonify({"error": "Authentication required"}), 401
            # Check scope if API key was used
            api_key = getattr(g, "api_key", None)
            if api_key is not None:
                key_scopes = api_key.scopes or []
                if key_scopes and required_scope not in key_scopes:
                    return jsonify(
                        {"error": f"Scope '{required_scope}' required"}
                    ), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator


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
