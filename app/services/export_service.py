"""
Unified Export Service

Consolidates export functionality from:
- app/api/export.py (API routes)
- app/views.py (UI routes)

This eliminates duplication between API and UI layers, ensuring consistent
export behavior regardless of how exports are triggered.
"""

import io
import os
import zipfile
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, Union
from flask import Response, send_from_directory, jsonify
from pathlib import Path

from app.services.dictionary_service import DictionaryService
from app.services.css_mapping_service import CSSMappingService
from app.utils.exceptions import DatabaseError, ExportError

# Import HTMLExporter at module level for better testability
try:
    from app.exporters.html_exporter import HTMLExporter
except ImportError:
    HTMLExporter = None  # Will be checked at runtime

logger = logging.getLogger(__name__)


class ExportService:
    """
    Unified service for all export operations.
    
    Provides consistent export functionality used by both API and UI routes.
    Handles format conversions, file generation, and download preparation.
    """
    
    def __init__(
        self,
        dictionary_service: DictionaryService,
        css_service: Optional[CSSMappingService] = None
    ):
        """
        Initialize the export service.
        
        Args:
            dictionary_service: Service for accessing dictionary data
            css_service: Optional CSS service for HTML rendering
        """
        self.dict_service = dictionary_service
        self.css_service = css_service or CSSMappingService()
        
    def export_lift(
        self,
        dual_file: bool = False,
        format: str = 'single',
        as_download: bool = True
    ) -> Union[Response, Tuple[Response, int], str]:
        """
        Export dictionary to LIFT format.
        
        Args:
            dual_file: If True, exports as dual files (main + ranges) in ZIP
            format: Export format ('single' or 'dual')
            as_download: If True, returns Response for download; if False, returns XML string
            
        Returns:
            Response for download, or XML string if as_download=False
            
        Raises:
            ExportError: If export fails
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"dictionary_export_{timestamp}"
            
            if dual_file or format == 'dual':
                return self._export_lift_dual(base_filename, as_download)
            else:
                return self._export_lift_single(base_filename, as_download)
                
        except DatabaseError:
            raise
        except Exception as e:
            logger.error("Error exporting to LIFT format: %s", str(e))
            raise ExportError(f"Failed to export to LIFT: {str(e)}")
    
    def _export_lift_single(
        self,
        base_filename: str,
        as_download: bool
    ) -> Union[Response, str]:
        """Export LIFT as single file."""
        filename = f"{base_filename}.lift"
        
        # Get LIFT content from service
        lift_xml = self.dict_service.export_lift(dual_file=False)
        
        # Ensure XML declaration
        if not lift_xml.startswith('<?xml'):
            lift_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + lift_xml
        
        if not as_download:
            return lift_xml
        
        return Response(
            lift_xml,
            content_type='application/xml; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    
    def _export_lift_dual(
        self,
        base_filename: str,
        as_download: bool
    ) -> Union[Response, Tuple[Response, int]]:
        """Export LIFT as dual files (main + ranges) in ZIP archive."""
        lift_filename = f"{base_filename}.lift"
        ranges_filename = f"{base_filename}.lift-ranges"
        zip_filename = f"{base_filename}.zip"
        
        zip_buffer = io.BytesIO()
        
        try:
            # Export main LIFT with range references
            lift_xml = self.dict_service.export_lift(dual_file=True)
            if not lift_xml.startswith('<?xml'):
                lift_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + lift_xml
            
            # Export ranges file
            ranges_xml = self.dict_service.export_lift_ranges()
            if not ranges_xml.startswith('<?xml'):
                ranges_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ranges_xml
            
            # Create ZIP
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(lift_filename, lift_xml)
                zipf.writestr(ranges_filename, ranges_xml)
            
            return Response(
                zip_buffer.getvalue(),
                content_type='application/zip',
                headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'}
            )
            
        except Exception as e:
            logger.error("Error in dual-file LIFT export: %s", str(e))
            # Fallback to single file
            logger.info("Falling back to single file export")
            return self._export_lift_single(base_filename, as_download)
    
    def export_html(
        self,
        output_path: str,
        title: str = "Dictionary",
        profile_id: Optional[int] = None,
        column_layout: str = "single",
        show_subentries: bool = True,
        return_path_only: bool = False
    ) -> Union[str, Tuple[str, str], Dict[str, Any]]:
        """
        Export dictionary to HTML format.
        
        Args:
            output_path: Directory to save the export
            title: Title of the dictionary
            profile_id: Optional display profile ID for rendering
            column_layout: Layout style ('single' or 'two')
            show_subentries: Whether to show subentries
            return_path_only: If True, returns just the path; if False, returns (path, filename)
            
        Returns:
            Full path to exported file, or (path, filename) tuple
            
        Raises:
            ExportError: If export fails
        """
        try:
            from app.exporters.html_exporter import HTMLExporter
            
            # Validate column_layout
            if column_layout not in ("single", "two"):
                column_layout = "single"
            
            # Ensure output directory exists
            os.makedirs(output_path, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dictionary_export_{timestamp}.zip"
            full_path = os.path.join(output_path, filename)
            
            # Create exporter and run export
            exporter = HTMLExporter(self.dict_service, self.css_service)
            exporter.export(
                output_path=full_path,
                title=title,
                profile_id=profile_id,
                column_layout=column_layout,
                show_subentries=show_subentries
            )
            
            if return_path_only:
                return full_path
            return full_path, filename
            
        except Exception as e:
            logger.error("Error exporting to HTML format: %s", str(e), exc_info=True)
            raise ExportError(f"Failed to export to HTML: {str(e)}")
    
    def export_kindle(
        self,
        output_path: str,
        title: str = "Dictionary",
        source_lang: str = "en",
        target_lang: str = "pl",
        author: str = "Lexicographic Curation Workbench",
        kindlegen_path: Optional[str] = None
    ) -> str:
        """
        Export dictionary to Kindle format.
        
        Note: Kindle export has been moved to a plugin. This method will attempt
        to use the dictionary service if available, otherwise raises an error
        directing users to the plugin.
        
        Args:
            output_path: Directory to save the export
            title: Title of the dictionary
            source_lang: Source language code
            target_lang: Target language code
            author: Author name
            kindlegen_path: Path to kindlegen executable
            
        Returns:
            Path to the exported file
            
        Raises:
            ExportError: If export fails or plugin not available
        """
        try:
            # Check if dictionary service has export_to_kindle method
            if hasattr(self.dict_service, 'export_to_kindle'):
                result_path = self.dict_service.export_to_kindle(
                    output_path=output_path,
                    title=title,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    author=author,
                    kindlegen_path=kindlegen_path
                )
                return result_path
            else:
                # Kindle export moved to plugin
                raise ExportError(
                    "Kindle export has been moved to a plugin. "
                    "Please install the kindle-exporter plugin from instance/plugins/kindle-exporter/"
                )
            
        except ExportError:
            raise
        except Exception as e:
            logger.error("Error exporting to Kindle format: %s", str(e))
            raise ExportError(f"Failed to export to Kindle: {str(e)}")
    
    def get_export_path(
        self,
        filename: str,
        instance_path: str,
        subdirectory: Optional[str] = None
    ) -> Path:
        """
        Construct the full path to an exported file.
        
        Args:
            filename: Name of the file
            instance_path: Flask instance path
            subdirectory: Optional subdirectory within exports
            
        Returns:
            Full Path object to the file
        """
        if "/" in filename:
            parts = filename.split("/", 1)
            if subdirectory:
                subdirectory = os.path.join(subdirectory, parts[0])
                filename = parts[1]
            else:
                subdirectory = parts[0]
                filename = parts[1]
        
        base_path = Path(instance_path) / "exports"
        if subdirectory:
            base_path = base_path / subdirectory
        
        return base_path / filename
    
    def determine_mime_type(self, filename: str) -> str:
        """
        Determine MIME type based on file extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            MIME type string
        """
        mime_types = {
            '.lift': 'application/xml',
            '.lift-ranges': 'application/xml',
            '.db': 'application/x-sqlite3',
            '.mobi': 'application/x-mobipocket-ebook',
            '.opf': 'application/oebps-package+xml',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.zip': 'application/zip',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.txt': 'text/plain',
        }
        
        ext = os.path.splitext(filename)[1].lower()
        return mime_types.get(ext, 'application/octet-stream')
    
    def file_exists(
        self,
        filename: str,
        instance_path: str,
        subdirectory: Optional[str] = None
    ) -> bool:
        """
        Check if an exported file exists.
        
        Args:
            filename: Name of the file
            instance_path: Flask instance path
            subdirectory: Optional subdirectory within exports
            
        Returns:
            True if file exists, False otherwise
        """
        file_path = self.get_export_path(filename, instance_path, subdirectory)
        return file_path.is_file()
    
    def prepare_download_response(
        self,
        filename: str,
        instance_path: str,
        subdirectory: Optional[str] = None,
        as_attachment: bool = True
    ) -> Response:
        """
        Prepare a download response for an exported file.
        
        Args:
            filename: Name of the file
            instance_path: Flask instance path
            subdirectory: Optional subdirectory
            as_attachment: Whether to send as attachment
            
        Returns:
            Flask Response object for download
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.get_export_path(filename, instance_path, subdirectory)
        
        if not file_path.is_file():
            raise FileNotFoundError(f"Export file not found: {filename}")
        
        mime_type = self.determine_mime_type(filename)
        
        return send_from_directory(
            directory=str(file_path.parent),
            path=file_path.name,
            mimetype=mime_type,
            as_attachment=as_attachment
        )


# Convenience function for quick access
def get_export_service(dictionary_service: Optional[DictionaryService] = None) -> ExportService:
    """
    Get an ExportService instance.
    
    Args:
        dictionary_service: Optional pre-configured dictionary service
        
    Returns:
        ExportService instance
    """
    if dictionary_service is None:
        from flask import current_app
        connector = current_app.injector.get(DictionaryService).db_connector
        dictionary_service = DictionaryService(connector)
    
    return ExportService(dictionary_service)
