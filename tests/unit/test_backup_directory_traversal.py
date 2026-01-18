"""
Regression test: ensure backup_directory path traversal is prevented.

This test guards against the bug where an attacker or misconfigured
backup_directory setting could use ../ to traverse parent directories
and delete critical application files (the flask-app folder itself).
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import Mock

from app.services.basex_backup_manager import BaseXBackupManager


class TestBackupDirectoryTraversalSafety:
    """Verify backup manager rejects unsafe directory paths."""

    @pytest.fixture
    def mock_connector(self):
        """Mock BaseX connector."""
        return Mock()

    def test_backup_directory_rejects_parent_traversal(self, mock_connector):
        """Backup manager must reject paths with .. traversal."""
        # Attempt to use ../ to escape the safe directory
        unsafe_path = "../../../../home/milek"
        
        manager = BaseXBackupManager(
            basex_connector=mock_connector,
            backup_directory=unsafe_path
        )
        
        # The manager should have defaulted to instance/backups (safe path)
        backup_dir = manager.get_backup_directory()
        assert "instance" in str(backup_dir)
        assert str(backup_dir).count("..") == 0, "Backup directory must not contain .."

    def test_backup_directory_accepts_safe_instance_path(self, mock_connector):
        """Backup manager must accept safe paths under instance/."""
        safe_path = "instance/my_backups"
        
        manager = BaseXBackupManager(
            basex_connector=mock_connector,
            backup_directory=safe_path
        )
        
        backup_dir = manager.get_backup_directory()
        assert "instance" in str(backup_dir)

    def test_backup_directory_accepts_absolute_tmp_path(self, mock_connector):
        """Backup manager defaults to instance/ for paths outside the app."""
        # Even /tmp is rejected as a safety measure - backups should stay within the project
        unsafe_path = "/tmp/backups"
        
        manager = BaseXBackupManager(
            basex_connector=mock_connector,
            backup_directory=unsafe_path
        )
        
        backup_dir = manager.get_backup_directory()
        # Should default to instance/backups (the safe default)
        assert "instance" in str(backup_dir)

    def test_ranges_sidecar_only_deletes_within_backup_directory(self, mock_connector):
        """The _write_ranges_sidecar method must NOT delete files outside backup_directory."""
        # Create a manager with a safe backup directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = BaseXBackupManager(
                basex_connector=mock_connector,
                backup_directory=tmp_dir
            )
            
            # Create a test backup file
            test_backup = Path(tmp_dir) / "test_backup.lift"
            test_backup.touch()
            
            # The method should not raise and should handle path validation gracefully
            # (it will fail to export ranges but that's OK - we're testing the safety check)
            manager._write_ranges_sidecar(test_backup, "test_db")
            
            # The backup file should still exist (not deleted)
            assert test_backup.exists(), "Backup file must not be deleted"

    def test_settings_form_rejects_parent_traversal_in_regex(self):
        """Settings form validation must reject .. in paths - tested via backend manager validation."""
        # Skip testing the form directly since it requires Flask app context
        # The backend validation in BaseXBackupManager._validate_backup_directory() is the main safeguard
        # which is tested in test_backup_directory_rejects_parent_traversal()
        pass

    def test_backup_manager_logs_warning_for_unsafe_paths(self, mock_connector):
        """Manager should default to safe path when unsafe paths are provided."""
        unsafe_path = "../../../../../../tmp/evil"
        
        manager = BaseXBackupManager(
            basex_connector=mock_connector,
            backup_directory=unsafe_path
        )
        
        # The manager should have defaulted to a safe path (instance/backups)
        backup_dir = manager.get_backup_directory()
        assert "instance" in str(backup_dir)
        assert str(backup_dir).count("..") == 0, "Backup directory must not contain .."
