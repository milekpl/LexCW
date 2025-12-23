from flask import Blueprint, jsonify, request, current_app, Response, send_from_directory
from datetime import datetime
import os
import logging
import zipfile
import io

from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import DatabaseError

# Set up logging
logger = logging.getLogger(__name__)

# Create export blueprint
export_bp = Blueprint('export', __name__)


def get_dictionary_service():
    """Get the dictionary service instance."""
    # Get BaseX connector from Flask app
    connector = current_app.injector.get(DictionaryService).db_connector
    
    # Create and return a dictionary service
    return DictionaryService(connector)


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
        # Get query parameters
        dual_file = request.args.get('dual_file', 'false').lower() == 'true'
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"dictionary_export_{timestamp}"
        
        if dual_file:
            # Export as dual files and create ZIP archive
            return _export_dual_file_lift(dict_service, base_filename)
        else:
            # Export as single file (original behavior)
            return _export_single_file_lift(dict_service, base_filename)
        
    except Exception as e:
        logger.error("Error exporting to LIFT format: %s", str(e))
        return jsonify({
            'success': False,
            'message': f"Error exporting to LIFT format: {str(e)}"
        }), 500


def _export_single_file_lift(dict_service, base_filename):
    """Export LIFT as single file (original behavior)."""
    filename = f"{base_filename}.lift"
    
    # Get the LIFT XML content
    lift_xml = None
    if hasattr(dict_service, 'export_lift'):
        try:
            # Get LIFT content from service (single file mode)
            lift_xml = dict_service.export_lift(dual_file=False)
            
            # Ensure XML declaration is present
            if not lift_xml.startswith('<?xml'):
                lift_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + lift_xml
        except DatabaseError:
            # Re-raise database errors instead of falling back
            raise
        except Exception as e:
            # Fallback only for non-database errors
            lift_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<lift version="0.13">\n</lift>'
    else:
        # Create a placeholder LIFT XML with proper XML declaration
        lift_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<lift version="0.13">\n</lift>'
    
    # Return LIFT XML content directly with proper content type
    return Response(
        lift_xml,
        content_type='application/xml; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


def _export_dual_file_lift(dict_service, base_filename):
    """Export LIFT as dual files (main + ranges) in a ZIP archive."""
    # Generate filenames
    lift_filename = f"{base_filename}.lift"
    ranges_filename = f"{base_filename}.lift-ranges"
    zip_filename = f"{base_filename}.zip"
    
    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()
    
    try:
        # Export main LIFT file with range references
        lift_xml = dict_service.export_lift(dual_file=True)
        
        # Ensure XML declaration is present
        if not lift_xml.startswith('<?xml'):
            lift_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + lift_xml
        
        # Export ranges file
        ranges_xml = dict_service.export_lift_ranges()
        
        # Ensure XML declaration is present for ranges
        if not ranges_xml.startswith('<?xml'):
            ranges_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ranges_xml
        
        # Create ZIP archive with both files
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add main LIFT file
            zipf.writestr(lift_filename, lift_xml)
            
            # Add ranges file
            zipf.writestr(ranges_filename, ranges_xml)
        
        # Return ZIP file
        return Response(
            zip_buffer.getvalue(),
            content_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{zip_filename}"'
            }
        )
        
    except Exception as e:
        # If any error occurs, try to export as single file as fallback
        return _export_single_file_lift(dict_service, base_filename)


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
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No request data provided'
            }), 400

        # Extract parameters
        output_path = data.get('output_path', 'instance/exports')
        title = data.get('title', 'Dictionary')
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'pl')
        author = data.get('author', 'Lexicographic Curation Workbench')
        kindlegen_path = data.get('kindlegen_path')
        
        # Export to Kindle format
        result_path = dict_service.export_to_kindle(
            output_path=output_path,
            title=title,
            source_lang=source_lang,
            target_lang=target_lang,
            author=author,
            kindlegen_path=kindlegen_path
        )
        
        return jsonify({
            'success': True,
            'message': 'Kindle export completed successfully',
            'result_path': result_path
        })
        
    except Exception as e:
        logger.error("Error exporting to Kindle format: %s", str(e))
        return jsonify({
            'success': False,
            'message': f"Error exporting to Kindle format: {str(e)}"
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
        # Get exports directory
        exports_dir = os.path.join(current_app.instance_path, 'exports')
        filepath = os.path.join(exports_dir, filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Return file for download
        return send_from_directory(
            directory=exports_dir,
            path=filename,
            as_attachment=True
        )
        
    except Exception as e:
        logger.error("Error downloading export file: %s", str(e))
        return jsonify({
            'success': False,
            'message': f"Error downloading export file: {str(e)}"
        }), 500