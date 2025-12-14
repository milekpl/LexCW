"""
Illustration image upload and management API endpoints.

Mirrors audio pronunciation endpoints but for image files stored under `/static/images/`.
"""

import os
import uuid
from typing import Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import mimetypes


illustration_bp = Blueprint('illustration', __name__, url_prefix='/api/illustration')

# Image file configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@illustration_bp.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image_file' not in request.files:
            return jsonify({'success': False, 'message': 'No image file provided'}), 400

        file = request.files['image_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if file.filename and not allowed_file(file.filename):
            return jsonify({'success': False, 'message': f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

        # Validate MIME type loosely
        if file.content_type and not file.content_type.startswith('image/'):
            return jsonify({'success': False, 'message': 'Invalid file type. Please upload an image.'}), 400

        # Generate secure unique filename
        file_extension = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

        static_folder = current_app.static_folder
        if not static_folder:
            return jsonify({'success': False, 'message': 'Static folder not configured'}), 500

        images_dir = os.path.join(static_folder, 'images')
        os.makedirs(images_dir, exist_ok=True)

        file_path = os.path.join(images_dir, unique_filename)
        file.save(file_path)

        # Simple file size check
        file_size = os.path.getsize(file_path)
        if file_size == 0 or file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            return jsonify({'success': False, 'message': 'Invalid image file size'}), 400

        current_app.logger.info(f"Image uploaded: {unique_filename} Size: {file_size}")
        return jsonify({'success': True, 'filename': unique_filename, 'file_size': file_size}), 201

    except RequestEntityTooLarge:
        return jsonify({'success': False, 'message': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB'}), 413
    except Exception as e:
        current_app.logger.error(f"Image upload error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during upload'}), 500


@illustration_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_image(filename: str):
    try:
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({'success': False, 'message': 'Invalid filename'}), 400

        static_folder = current_app.static_folder
        if not static_folder:
            return jsonify({'success': False, 'message': 'Static folder not configured'}), 500

        images_dir = os.path.join(static_folder, 'images')
        file_path = os.path.join(images_dir, safe_filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found'}), 404

        os.remove(file_path)
        current_app.logger.info(f"Image deleted: {safe_filename}")
        return jsonify({'success': True, 'message': 'Image deleted successfully'})

    except Exception as e:
        current_app.logger.error(f"Image deletion error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during deletion'}), 500


@illustration_bp.route('/info/<filename>', methods=['GET'])
def get_image_info(filename: str):
    try:
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({'success': False, 'message': 'Invalid filename'}), 400

        static_folder = current_app.static_folder
        if not static_folder:
            return jsonify({'success': False, 'message': 'Static folder not configured'}), 500

        images_dir = os.path.join(static_folder, 'images')
        file_path = os.path.join(images_dir, safe_filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found'}), 404

        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)

        return jsonify({'success': True, 'filename': safe_filename, 'file_size': file_size, 'mime_type': mime_type or 'image/png', 'url': f'/static/images/{safe_filename}'})

    except Exception as e:
        current_app.logger.error(f"Image info error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while getting file info'}), 500
