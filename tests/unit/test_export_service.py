"""
Unit tests for ExportService

Tests the unified export service that consolidates export functionality
from app/api/export.py and app/views.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import zipfile
import io
from datetime import datetime
from pathlib import Path

from app.services.export_service import ExportService, get_export_service
from app.services.dictionary_service import DictionaryService
from app.services.css_mapping_service import CSSMappingService
from app.utils.exceptions import ExportError, DatabaseError


class TestExportServiceInitialization:
    """Test ExportService initialization and setup"""

    def test_service_initialization_with_dependencies(self):
        """ExportService should initialize with dictionary and CSS services."""
        mock_dict_service = Mock(spec=DictionaryService)
        mock_css_service = Mock(spec=CSSMappingService)
        
        service = ExportService(mock_dict_service, mock_css_service)
        
        assert service.dict_service is mock_dict_service
        assert service.css_service is mock_css_service
    
    def test_service_initialization_without_css_service(self):
        """ExportService should create default CSS service if not provided."""
        mock_dict_service = Mock(spec=DictionaryService)
        
        with patch('app.services.export_service.CSSMappingService') as mock_css_class:
            mock_css_instance = Mock()
            mock_css_class.return_value = mock_css_instance
            
            service = ExportService(mock_dict_service)
            
            assert service.dict_service is mock_dict_service
            assert service.css_service is mock_css_instance


class TestExportLift:
    """Test LIFT export functionality"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        return mock_dict, mock_css

    def test_export_lift_single_file(self, mock_services):
        """Should export LIFT as single file."""
        mock_dict, mock_css = mock_services
        
        # Setup mock return value
        sample_lift = '<?xml version="1.0"?><lift></lift>'
        mock_dict.export_lift.return_value = sample_lift
        
        service = ExportService(mock_dict, mock_css)
        result = service.export_lift(dual_file=False, as_download=False)
        
        assert result == sample_lift
        mock_dict.export_lift.assert_called_once_with(dual_file=False)

    def test_export_lift_dual_file_as_zip(self, mock_services):
        """Should export LIFT as dual files in ZIP."""
        mock_dict, mock_css = mock_services
        
        # Setup mock return values
        lift_content = '<?xml version="1.0"?><lift></lift>'
        ranges_content = '<?xml version="1.0"?><lift-ranges></lift-ranges>'
        mock_dict.export_lift.return_value = lift_content
        mock_dict.export_lift_ranges.return_value = ranges_content
        
        service = ExportService(mock_dict, mock_css)
        response = service.export_lift(dual_file=True, as_download=True)
        
        # Verify it's a Response object with ZIP content
        assert hasattr(response, 'data')
        assert response.content_type == 'application/zip'
        
        # Verify ZIP contents
        zip_buffer = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_buffer, 'r') as zipf:
            files = zipf.namelist()
            assert len(files) == 2
            assert any('.lift' in f for f in files)
            assert any('.lift-ranges' in f for f in files)

    def test_export_lift_adds_xml_declaration(self, mock_services):
        """Should add XML declaration if missing."""
        mock_dict, mock_css = mock_services
        
        # Return content without XML declaration
        mock_dict.export_lift.return_value = '<lift></lift>'
        
        service = ExportService(mock_dict, mock_css)
        result = service.export_lift(dual_file=False, as_download=False)
        
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_export_lift_database_error_propagation(self, mock_services):
        """Should propagate DatabaseError."""
        mock_dict, mock_css = mock_services
        mock_dict.export_lift.side_effect = DatabaseError("DB Error")
        
        service = ExportService(mock_dict, mock_css)
        
        with pytest.raises(DatabaseError):
            service.export_lift()

    def test_export_lift_handles_generic_error(self, mock_services):
        """Should wrap generic errors in ExportError."""
        mock_dict, mock_css = mock_services
        mock_dict.export_lift.side_effect = Exception("Generic error")
        
        service = ExportService(mock_dict, mock_css)
        
        with pytest.raises(ExportError) as exc_info:
            service.export_lift()
        
        assert "Generic error" in str(exc_info.value)


class TestExportHTML:
    """Test HTML export functionality"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        return mock_dict, mock_css

    @patch('app.exporters.html_exporter.HTMLExporter')
    def test_export_html_basic(self, mock_exporter_class, mock_services):
        """Should export HTML with basic parameters."""
        mock_dict, mock_css = mock_services
        
        # Setup mock exporter
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        
        service = ExportService(mock_dict, mock_css)
        
        with patch('os.makedirs'):
            result_path, filename = service.export_html(
                output_path='/tmp/exports',
                title='Test Dictionary',
                profile_id=123,
                column_layout='single',
                show_subentries=True
            )
        
        # Verify exporter was called
        mock_exporter_class.assert_called_once_with(mock_dict, mock_css)
        mock_exporter.export.assert_called_once()
        
        # Verify export parameters
        call_kwargs = mock_exporter.export.call_args[1]
        assert call_kwargs['title'] == 'Test Dictionary'
        assert call_kwargs['profile_id'] == 123
        assert call_kwargs['column_layout'] == 'single'
        assert call_kwargs['show_subentries'] == True

    @patch('app.exporters.html_exporter.HTMLExporter')
    def test_export_html_validates_column_layout(self, mock_exporter_class, mock_services):
        """Should validate and correct column_layout parameter."""
        mock_dict, mock_css = mock_services
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        
        service = ExportService(mock_dict, mock_css)
        
        with patch('os.makedirs'):
            # Pass invalid column_layout
            service.export_html(
                output_path='/tmp/exports',
                title='Test',
                column_layout='invalid'
            )
        
        # Should use 'single' as default
        call_kwargs = mock_exporter.export.call_args[1]
        assert call_kwargs['column_layout'] == 'single'

    @patch('app.exporters.html_exporter.HTMLExporter')
    def test_export_html_creates_directory(self, mock_exporter_class, mock_services):
        """Should create output directory if it doesn't exist."""
        mock_dict, mock_css = mock_services
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        
        service = ExportService(mock_dict, mock_css)
        
        with patch('os.makedirs') as mock_makedirs:
            service.export_html(output_path='/tmp/exports')
            mock_makedirs.assert_called_once_with('/tmp/exports', exist_ok=True)

    @patch('app.exporters.html_exporter.HTMLExporter')
    def test_export_html_error_handling(self, mock_exporter_class, mock_services):
        """Should wrap HTML export errors in ExportError."""
        mock_dict, mock_css = mock_services
        mock_exporter = Mock()
        mock_exporter.export.side_effect = Exception("Export failed")
        mock_exporter_class.return_value = mock_exporter
        
        service = ExportService(mock_dict, mock_css)
        
        with pytest.raises(ExportError) as exc_info:
            with patch('os.makedirs'):
                service.export_html(output_path='/tmp/exports')
        
        assert "Export failed" in str(exc_info.value)


class TestFileHandling:
    """Test file handling utilities"""

    def test_get_export_path_simple_filename(self):
        """Should construct path for simple filename."""
        mock_dict = Mock(spec=DictionaryService)
        service = ExportService(mock_dict)
        
        path = service.get_export_path('test.lift', '/instance')
        
        assert str(path).endswith('exports/test.lift')
        assert 'instance' in str(path)

    def test_get_export_path_with_subdirectory(self):
        """Should construct path with subdirectory."""
        mock_dict = Mock(spec=DictionaryService)
        service = ExportService(mock_dict)
        
        path = service.get_export_path('backup/test.lift', '/instance')
        
        assert 'exports/backup' in str(path)
        assert str(path).endswith('test.lift')

    def test_get_export_path_with_explicit_subdir(self):
        """Should use explicit subdirectory parameter."""
        mock_dict = Mock(spec=DictionaryService)
        service = ExportService(mock_dict)
        
        path = service.get_export_path('test.lift', '/instance', 'backups')
        
        assert 'exports/backups' in str(path)

    def test_determine_mime_type_known_extensions(self):
        """Should return correct MIME type for known extensions."""
        mock_dict = Mock(spec=DictionaryService)
        service = ExportService(mock_dict)
        
        assert service.determine_mime_type('file.lift') == 'application/xml'
        assert service.determine_mime_type('file.lift-ranges') == 'application/xml'
        assert service.determine_mime_type('file.db') == 'application/x-sqlite3'
        assert service.determine_mime_type('file.mobi') == 'application/x-mobipocket-ebook'
        assert service.determine_mime_type('file.opf') == 'application/oebps-package+xml'
        assert service.determine_mime_type('file.html') == 'text/html'
        assert service.determine_mime_type('file.zip') == 'application/zip'
        assert service.determine_mime_type('file.json') == 'application/json'
        assert service.determine_mime_type('file.txt') == 'text/plain'

    def test_determine_mime_type_unknown_extension(self):
        """Should return octet-stream for unknown extensions."""
        mock_dict = Mock(spec=DictionaryService)
        service = ExportService(mock_dict)
        
        assert service.determine_mime_type('file.xyz') == 'application/octet-stream'

    def test_file_exists_true(self, tmp_path):
        """Should return True if file exists."""
        mock_dict = Mock(spec=DictionaryService)
        service = ExportService(mock_dict)
        
        # Create exports directory and test file
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        test_file = exports_dir / "test.lift"
        test_file.write_text("test content")
        
        assert service.file_exists("test.lift", str(tmp_path)) == True

    def test_file_exists_false(self, tmp_path):
        """Should return False if file doesn't exist."""
        mock_dict = Mock(spec=DictionaryService)
        service = ExportService(mock_dict)
        
        # Create exports directory but no file
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        
        assert service.file_exists("nonexistent.lift", str(tmp_path)) == False


class TestGetExportService:
    """Test the convenience factory function"""

    def test_get_export_service_with_preconfigured_service(self):
        """Should use provided dictionary service."""
        mock_dict = Mock(spec=DictionaryService)
        
        service = get_export_service(mock_dict)
        
        assert isinstance(service, ExportService)
        assert service.dict_service is mock_dict

    @patch('app.services.export_service.DictionaryService')
    def test_get_export_service_creates_new_service(self, mock_dict_class, mock_app):
        """Should create new dictionary service if not provided."""
        from flask import current_app
        mock_connector = Mock()
        mock_dict_instance = Mock()
        mock_dict_instance.db_connector = mock_connector
        mock_dict_class.return_value = mock_dict_instance
        current_app.injector.get.return_value = mock_dict_instance

        service = get_export_service()

        assert isinstance(service, ExportService)
        assert service.dict_service is not None
        current_app.injector.get.assert_called_once()
        mock_dict_class.assert_called_once()


class TestExportIntegration:
    """Integration-style tests for export workflows"""

    def test_complete_lift_export_workflow(self):
        """Test complete LIFT export workflow."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        
        # Setup realistic LIFT content
        lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test1">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        </lift>'''
        ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges></lift-ranges>'''
        
        mock_dict.export_lift.return_value = lift_xml
        mock_dict.export_lift_ranges.return_value = ranges_xml
        
        service = ExportService(mock_dict, mock_css)
        
        # Test dual-file export
        response = service.export_lift(dual_file=True)
        
        assert response.content_type == 'application/zip'
        assert 'Content-Disposition' in response.headers
        assert '.zip' in response.headers['Content-Disposition']

    @patch('app.exporters.html_exporter.HTMLExporter')
    def test_complete_html_export_workflow(self, mock_exporter_class):
        """Test complete HTML export workflow with all options."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        
        service = ExportService(mock_dict, mock_css)
        
        with patch('os.makedirs'):
            result_path, filename = service.export_html(
                output_path='/tmp/exports',
                title='My Dictionary',
                profile_id=42,
                column_layout='two',
                show_subentries=False
            )
        
        # Verify all parameters passed correctly
        call_args = mock_exporter.export.call_args[1]
        assert call_args['output_path'] == result_path
        assert call_args['title'] == 'My Dictionary'
        assert call_args['profile_id'] == 42
        assert call_args['column_layout'] == 'two'
        assert call_args['show_subentries'] == False


class TestExportErrorHandling:
    """Test error handling and edge cases"""

    def test_export_lift_empty_content_handling(self):
        """Should handle empty LIFT content gracefully."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        
        # Return empty content
        mock_dict.export_lift.return_value = ''
        mock_dict.export_lift_ranges.return_value = ''
        
        service = ExportService(mock_dict, mock_css)
        
        # Should handle gracefully (not crash)
        # Service adds XML declaration even to empty content
        result = service.export_lift(dual_file=False, as_download=False)
        # Result contains XML declaration added by the service
        assert '<?xml' in result or result == ''

    @patch('app.exporters.html_exporter.HTMLExporter')
    def test_export_html_invalid_layout_defaults_to_single(self, mock_exporter_class):
        """Should default to single column for invalid layout."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        
        service = ExportService(mock_dict, mock_css)
        
        with patch('os.makedirs'):
            # Pass invalid layout
            service.export_html(
                output_path='/tmp/exports',
                title='Test',
                column_layout='triple'  # Invalid
            )
        
        # Should default to 'single'
        call_args = mock_exporter.export.call_args[1]
        assert call_args['column_layout'] == 'single'


class TestBackwardCompatibility:
    """Test that consolidated service maintains backward compatibility"""

    def test_export_lift_api_compatibility(self):
        """API export should work the same as before."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        mock_dict.export_lift.return_value = '<lift></lift>'
        
        service = ExportService(mock_dict, mock_css)
        
        # Simulate API call behavior
        response = service.export_lift(dual_file=False)
        
        # Should return Response object for download
        assert hasattr(response, 'data')
        assert response.content_type == 'application/xml; charset=utf-8'

    @patch('app.exporters.html_exporter.HTMLExporter')
    def test_export_html_ui_compatibility(self, mock_exporter_class):
        """UI export should work the same as before."""
        mock_dict = Mock(spec=DictionaryService)
        mock_css = Mock(spec=CSSMappingService)
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        
        service = ExportService(mock_dict, mock_css)
        
        with patch('os.makedirs'):
            result_path, filename = service.export_html(
                output_path='/tmp/exports',
                title='Dictionary',
                column_layout='single',
                show_subentries=True
            )
        
        # Should return path and filename tuple
        assert isinstance(result_path, str)
        assert isinstance(filename, str)
        assert filename.endswith('.zip')
