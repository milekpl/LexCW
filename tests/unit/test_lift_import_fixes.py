"""
Unit tests for LIFT import fixes.
Tests range file discovery and lexical relation handling.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from app.services.dictionary_service import DictionaryService


class TestLIFTImportFixes:
    """Test LIFT import functionality fixes."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dictionary service for testing."""
        with patch('app.services.dictionary_service.BaseXConnector') as mock_connector:
            mock_connector.return_value = MagicMock()
            service = DictionaryService(db_connector=mock_connector.return_value)
            return service

    def test_find_ranges_file_simple(self, mock_service):
        """Test simple range file discovery."""
        # Create temporary LIFT file
        with tempfile.NamedTemporaryFile(suffix='.lift', delete=False) as lift_file:
            lift_path = lift_file.name
            
            # Create corresponding ranges file
            ranges_path = lift_path.replace('.lift', '.lift-ranges')
            with open(ranges_path, 'w') as f:
                f.write('<lift-ranges></lift-ranges>')
            
            try:
                # Test the method
                found_path = mock_service.find_ranges_file(lift_path)
                assert found_path == ranges_path, f"Expected {ranges_path}, got {found_path}"
            finally:
                # Cleanup
                if os.path.exists(lift_path):
                    os.unlink(lift_path)
                if os.path.exists(ranges_path):
                    os.unlink(ranges_path)

    def test_find_ranges_file_windows_path(self, mock_service):
        """Test Windows path handling."""
        # Simulate Windows path
        windows_path = 'file:///C:/path/to/file.lift'
        # The method should return the path with file:/// prefix removed
        expected_ranges = 'C:/path/to/file.lift-ranges'
        
        # Mock os.path.exists to return True for the expected path
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            found_path = mock_service.find_ranges_file(windows_path)
            # Windows path should have file:/// removed, so it becomes C:/...
            assert found_path == expected_ranges

    def test_find_ranges_file_file_uri_normalization(self, mock_service):
        """Explicitly test file:/// URI normalization."""
        uri = 'file:///C:/path/to/somefile.lift'
        expected = 'C:/path/to/somefile.lift-ranges'

        # Patch os.path.exists to only return True for the normalized expected path
        with patch('os.path.exists') as mock_exists:
            def exists_side_effect(p):
                # Ensure we return True only for the normalized path
                return p == expected
            mock_exists.side_effect = exists_side_effect

            found = mock_service.find_ranges_file(uri)
            assert found == expected

    def test_find_ranges_file_not_found(self, mock_service):
        """Test when ranges file is not found."""
        with tempfile.NamedTemporaryFile(suffix='.lift', delete=False) as lift_file:
            lift_path = lift_file.name
            
            try:
                # Mock os.path.exists to return False
                with patch('os.path.exists') as mock_exists:
                    mock_exists.return_value = False
                    
                    found_path = mock_service.find_ranges_file(lift_path)
                    assert found_path is None, "Should return None when file not found"
            finally:
                if os.path.exists(lift_path):
                    os.unlink(lift_path)


    def test_range_file_discovery_fallback(self, mock_service, tmp_path, monkeypatch):
        """Test that config ranges are used as fallback (deterministic, no fragile mocks)."""
        # Use a temporary working directory so os.path.join('config', ...) resolves here
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        config_file = config_dir / 'recommended_ranges.lift-ranges'
        config_file.write_text('<lift-ranges></lift-ranges>', encoding='utf-8')

        # Create a LIFT file in the temp dir and ensure no ranges file exists alongside it
        # IMPORTANT: avoid the substring 'ranges' in the filename so directory scanning
        # doesn't accidentally detect the LIFT file itself as a candidate.
        lift_file = tmp_path / 'entry.lift'
        lift_file.write_text('<lift></lift>', encoding='utf-8')

        found_path = mock_service.find_ranges_file(str(lift_file))
        # Should find the config file as fallback (function returns relative path here)
        expected = os.path.join('config', 'recommended_ranges.lift-ranges')
        assert found_path == expected


if __name__ == '__main__':
    pytest.main([__file__, '-v'])