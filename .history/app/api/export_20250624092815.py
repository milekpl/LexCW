"""
Export API endpoints for the Dictionary Writing System.

This module provides API endpoints for exporting dictionary data in various formats.
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file

from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector

# Create blueprint
export_bp = Blueprint('export_api', __name__, url_prefix='/api/export')
logger = logging.getLogger(__name__)


def get_dictionary_service():
    """
    Get an instance of the dictionary service.
    
    Returns:
        DictionaryService instance.
    """
    # Create a BaseX connector using app config
    connector = BaseXConnector(
        host=current_app.config['BASEX_HOST'],
        port=current_app.config['BASEX_PORT'],
        username=current_app.config['BASEX_USERNAME'],
        password=current_app.config['BASEX_PASSWORD'],
        database=current_app.config['BASEX_DATABASE'],
    )
    
    # Create and return a dictionary service
    return DictionaryService(connector)


@export_bp.route('/lift', methods=['GET'])
def export_lift():
    """
    Export the dictionary to LIFT format.
    
    Returns:
        JSON response with the path to the exported file.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(current_app.instance_path, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"dictionary_export_{timestamp}.lift"
          # Export to LIFT (placeholder - needs implementation)
        if hasattr(dict_service, 'export_to_lift'):
            dict_service.export_to_lift(output_path)
        else:
            # Create a placeholder file for now
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n<lift version="0.13">\n</lift>')
        
        # Return path to the exported file
        return jsonify({
            'success': True,
            'message': 'Dictionary exported to LIFT format',
            'filename': filename,
            'path': output_path
        }), 200
        
    except Exception as e:
        logger.error("Error exporting to LIFT format: %s", str(e))
        return jsonify({
            'success': False,
            'message': f"Error exporting to LIFT format: {str(e)}"
        }), 500


@export_bp.route('/kindle', methods=['POST'])
def export_kindle():
    """
    Export the dictionary to Kindle format.
    
    Returns:
        JSON response with the path to the exported files.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get request parameters
        data = request.get_json() or {}
        title = data.get('title', 'Dictionary')
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'pl')
        author = data.get('author', 'Dictionary Writing System')
        
        # Get kindlegen path from config if available
        kindlegen_path = current_app.config.get('KINDLEGEN_PATH')
        
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(current_app.instance_path, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate directory name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_name = f"kindle_export_{timestamp}"
        
        # Export to Kindle format
        output_path = os.path.join(exports_dir, dir_name)
        output_dir = dict_service.export_to_kindle(
            output_path, 
            title=title,
            source_lang=source_lang,
            target_lang=target_lang,
            author=author,
            kindlegen_path=kindlegen_path
        )
        
        # Check if MOBI file was created
        mobi_path = os.path.join(output_dir, 'dictionary.mobi')
        mobi_created = os.path.exists(mobi_path)
        
        # Return path to the exported files
        return jsonify({
            'success': True,
            'message': 'Dictionary exported to Kindle format',
            'directory': dir_name,
            'path': output_dir,
            'mobi_created': mobi_created,
            'files': {
                'opf': os.path.join(output_dir, 'dictionary.opf'),
                'html': os.path.join(output_dir, 'dictionary.html'),
                'mobi': mobi_path if mobi_created else None
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting to Kindle format: {e}")
        return jsonify({
            'success': False,
            'message': f"Error exporting to Kindle format: {str(e)}"
        }), 500


@export_bp.route('/sqlite', methods=['POST'])
def export_sqlite():
    """
    Export the dictionary to SQLite format for mobile apps.
    
    Returns:
        JSON response with the path to the exported file.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get request parameters
        data = request.get_json() or {}
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'pl')
        batch_size = int(data.get('batch_size', 500))
        
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(current_app.instance_path, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"dictionary_export_{timestamp}.db"
        
        # Export to SQLite
        output_path = os.path.join(exports_dir, filename)
        dict_service.export_to_sqlite(
            output_path, 
            source_lang=source_lang,
            target_lang=target_lang,
            batch_size=batch_size
        )
        
        # Return path to the exported file
        return jsonify({
            'success': True,
            'message': 'Dictionary exported to SQLite format',
            'filename': filename,
            'path': output_path
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting to SQLite format: {e}")
        return jsonify({
            'success': False,
            'message': f"Error exporting to SQLite format: {str(e)}"
        }), 500


@export_bp.route('/download/<path:filename>', methods=['GET'])
def download_export(filename):
    """
    Download an exported file.
    
    Args:
        filename: Name of the file to download.
        
    Returns:
        File download response.
    """
    try:
        # Validate filename
        if '..' in filename or filename.startswith('/'):
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400
        
        # Get exports directory
        exports_dir = os.path.join(current_app.instance_path, 'exports')
        
        # Check if file exists
        file_path = os.path.join(exports_dir, filename)
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Determine MIME type based on file extension
        mime_type = 'application/octet-stream'  # Default
        if filename.endswith('.lift'):
            mime_type = 'application/xml'
        elif filename.endswith('.db'):
            mime_type = 'application/x-sqlite3'
        elif filename.endswith('.mobi'):
            mime_type = 'application/x-mobipocket-ebook'
        elif filename.endswith('.opf'):
            mime_type = 'application/oebps-package+xml'
        elif filename.endswith('.html'):
            mime_type = 'text/html'
        
        # Send file
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({
            'success': False,
            'message': f"Error downloading file: {str(e)}"
        }), 500
