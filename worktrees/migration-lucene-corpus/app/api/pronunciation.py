"""
Pronunciation audio upload and management API endpoints.
Handles MP3 file uploads for pronunciation entries.
"""

import os
import uuid
from typing import Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import mimetypes

from app.utils.validators import validate_audio_file

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
