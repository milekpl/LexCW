"""Export API routes - delegates to ExportService for all operations."""

from flask import Blueprint, jsonify, request, current_app
import logging

from app.services.export_service import get_export_service

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__)


@export_bp.route('/lift', methods=['GET'])
def export_lift():
    """
    Export the dictionary to LIFT format.

    Query Parameters:
        dual_file: If 'true', exports as dual files (main + ranges) in a ZIP archive

    Returns:
        LIFT XML content or ZIP archive with dual files.
    """
    try:
        dual_file = request.args.get('dual_file', 'false').lower() == 'true'
        service = get_export_service()
        return service.export_lift(dual_file=dual_file, as_download=True)
    except Exception as e:
        logger.error("Error exporting to LIFT format: %s", str(e))
        return jsonify({
            'success': False,
            'message': f"Error exporting to LIFT format: {str(e)}"
        }), 500


@export_bp.route('/download/<filename>', methods=['GET'])
def download_export(filename):
    """
    Download an exported file.

    Args:
        filename: Name of the file to download

    Returns:
        File download response.
    """
    try:
        service = get_export_service()
        return service.prepare_download_response(
            filename=filename,
            instance_path=current_app.instance_path,
            as_attachment=True
        )

    except FileNotFoundError as e:
        return jsonify({
            'success': False,
            'message': 'File not found'
        }), 404
    except Exception as e:
        logger.error("Error downloading export file: %s", str(e))
        return jsonify({
            'success': False,
            'message': f"Error downloading export file: {str(e)}"
        }), 500


@export_bp.route('/html', methods=['POST'])
def export_html():
    """
    Export the dictionary to HTML format with alphabetical navigation.

    Query Parameters (JSON body):
        output_path: Directory to save the exported ZIP file (default: instance/exports)
        title: Title of the dictionary (default: Dictionary)
        profile_id: Display profile ID to use for rendering (optional)

    Returns:
        JSON response with the path to the exported ZIP file.
    """
    try:
        data = request.get_json() or {}
        output_path = data.get('output_path', 'instance/exports')
        title = data.get('title', 'Dictionary')
        profile_id = data.get('profile_id')

        service = get_export_service()
        result_path, filename = service.export_html(
            output_path=output_path,
            title=title,
            profile_id=profile_id,
            return_path_only=False
        )

        return jsonify({
            'success': True,
            'message': 'HTML export completed successfully',
            'result_path': result_path,
            'filename': filename
        })

    except Exception as e:
        logger.error("Error exporting to HTML format: %s", str(e), exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error exporting to HTML format: {str(e)}"
        }), 500


@export_bp.route('/html', methods=['GET'])
def export_html_info():
    """Get information about HTML export endpoint."""
    return jsonify({
        'name': 'HTML Export',
        'description': 'Export dictionary entries to HTML format with alphabetical navigation',
        'method': 'POST',
        'parameters': {
            'output_path': {'type': 'string', 'description': 'Directory to save exported ZIP file'},
            'title': {'type': 'string', 'description': 'Title for the dictionary'},
            'profile_id': {'type': 'integer', 'description': 'Display profile ID for rendering (optional)'}
        },
        'returns': {
            'success': 'boolean',
            'message': 'Success or error message',
            'result_path': 'Path to exported ZIP file',
            'filename': 'Name of exported file'
        }
    })
