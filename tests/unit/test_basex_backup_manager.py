from __future__ import annotations
import json
from pathlib import Path
from app.services.basex_backup_manager import BaseXBackupManager


class FakeConnector:
    def __init__(self):
        self.database = None
        self._lock = None  # Add missing lock attribute

    def execute_command(self, cmd: str):
        # Simulate EXPORT command creating the indicated path
        if cmd.startswith('OPEN '):
            # set database name
            self.database = cmd.split(' ', 1)[1]
            return True
        if cmd.startswith('EXPORT '):
            # Extract path from EXPORT command: format is "EXPORT db TO 'path'"
            parts = cmd.split(' TO ')
            if len(parts) >= 2:
                path_part = parts[1]
                # Remove quotes if present
                path = path_part.strip("'\"")
                p = Path(path)
                # create a simple .lift file
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0"?><lift version="0.13"><entry id="x"></entry></lift>')
                return True
            return False
        return True


def test_backup_writes_ranges_and_display_profiles(tmp_path):
    connector = FakeConnector()
    manager = BaseXBackupManager(connector, config_manager=None, backup_directory=str(tmp_path))

    backup = manager.backup_database(db_name='testdb', backup_type='manual', description='desc', include_media=False)
    # Confirm backup file exists
    file_path = Path(backup.file_path)
    assert file_path.exists()

    # Check ranges export (legacy .ranges.xml should exist)
    ranges_legacy = Path(str(file_path) + '.ranges.xml')
    assert ranges_legacy.exists()
    contents = ranges_legacy.read_text(encoding='utf-8')
    assert '<range' in contents
    assert '<range-element' in contents

    # Check display profiles default exists
    dp = Path(str(file_path) + '.display_profiles.json')
    assert dp.exists()
    dp_json = json.loads(dp.read_text(encoding='utf-8'))
    assert 'profiles' in dp_json and len(dp_json['profiles']) >= 1
"""
Unit tests for BaseXBackupManager.
"""

import os
import tempfile
import json
from pathlib import Path
from datetime import datetime
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from app.services.basex_backup_manager import BaseXBackupManager
from app.utils.exceptions import DatabaseError, ValidationError


class TestBaseXBackupManager:
    """Test BaseXBackupManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock BaseX connector
        self.mock_basex_connector = Mock()
        
        # Create a temporary directory for backups
        self.temp_dir = tempfile.mkdtemp()
        
        self.backup_manager = BaseXBackupManager(
            basex_connector=self.mock_basex_connector,
            config_manager=None,
            backup_directory=self.temp_dir
        )
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_backup_database_success(self):
        """Test successful database backup."""
        # Mock the execute_command method to return success
        self.mock_basex_connector.execute_command.return_value = "Backup successful"
        
        # Create a mock backup file
        backup_file = os.path.join(self.temp_dir, 'test_db_backup_20250101_120000.lift')
        with open(backup_file, 'w') as f:
            f.write('<lift version="0.13"></lift>')
        
        db_name = 'test_db'
        backup = self.backup_manager.backup_database(db_name, 'full', 'Test backup')
        
        # Verify the backup was created
        assert backup.db_name == db_name
        assert backup.type == 'full'
        assert backup.description == 'Test backup'
        assert backup.status == 'completed'
        assert backup.file_path == backup_file
        assert backup.file_size > 0
        
        # Verify the command was executed
        self.mock_basex_connector.execute_command.assert_called_once()

        # display_name should prefer the description
        assert backup.to_dict().get('display_name') == 'Test backup'
        
        # Clean up the file
        os.remove(backup_file)
    
    def test_backup_database_failure(self):
        """Test database backup failure."""
        # Mock the execute_command method to raise an exception
        self.mock_basex_connector.execute_command.side_effect = DatabaseError("Backup failed")
        
        db_name = 'test_db'
        
        with pytest.raises(DatabaseError):
            self.backup_manager.backup_database(db_name, 'full', 'Test backup')
    
    def test_validate_backup_valid_file(self):
        """Test validating a valid backup file."""
        # Create a temporary valid backup file
        backup_file = os.path.join(self.temp_dir, 'valid_backup.lift')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write('<lift version="0.13"><entry id="test"></entry></lift>')
        
        result = self.backup_manager.validate_backup(backup_file)
        
        assert result['is_valid_lift'] is True
        assert result['is_not_empty'] is True
        assert result['is_valid'] is True
        assert result['file_size'] > 0
    
    def test_validate_backup_invalid_file(self):
        """Test validating an invalid backup file."""
        # Create a temporary invalid backup file
        backup_file = os.path.join(self.temp_dir, 'invalid_backup.lift')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write('invalid content')
        
        result = self.backup_manager.validate_backup(backup_file)
        
        assert result['is_valid_lift'] is False
        assert result['is_not_empty'] is True
        assert result['is_valid'] is False
    
    def test_validate_backup_nonexistent_file(self):
        """Test validating a non-existent backup file."""
        backup_file = os.path.join(self.temp_dir, 'nonexistent.lift')
        
        with pytest.raises(ValidationError):
            self.backup_manager.validate_backup(backup_file)
    
    def test_list_backups(self):
        """Test listing backups."""
        # Create some mock backup files
        backup_files = [
            'db1_backup_20250101_120000.lift',
            'db2_backup_20250101_130000.lift',
            'not_a_backup.xml',
            'another_db_backup_20250101_140000.lift'
        ]
        
        for filename in backup_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write('<lift></lift>')
        
        # List all backups
        backups = self.backup_manager.list_backups()
        assert len(backups) == 3  # Should exclude 'not_a_backup.xml'
        
        # List backups for a specific database
        db1_backups = self.backup_manager.list_backups('db1')
        assert len(db1_backups) == 1
        assert db1_backups[0]['db_name'] == 'db1'
        
        # List backups for another database
        db2_backups = self.backup_manager.list_backups('db2')
        assert len(db2_backups) == 1
        assert db2_backups[0]['db_name'] == 'db2'

    def test_list_skips_empty_files_without_meta(self):
        """Empty .lift files without metadata should be skipped."""
        # Create an empty lift file
        empty_file = os.path.join(self.temp_dir, 'skip_db_backup_20250101_000000.lift')
        open(empty_file, 'w').close()

        backups = self.backup_manager.list_backups()
        filenames = [b['filename'] for b in backups]
        assert 'skip_db_backup_20250101_000000.lift' not in filenames

    def test_delete_backup_removes_files_and_meta(self):
        """Deleting a backup should remove the file and its metadata."""
        filename = 'del_db_backup_20250101_000001.lift'
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<lift></lift>')

        meta = {
            'id': 'del_db_20250101_000001',
            'db_name': 'del_db',
            'description': 'to be deleted'
        }
        meta_path = file_path + '.meta.json'
        with open(meta_path, 'w', encoding='utf-8') as mf:
            json.dump(meta, mf)

        # Ensure it's listed
        backups = self.backup_manager.list_backups()
        assert any(b['filename'] == filename for b in backups)

        # Delete and verify
        backup_id = f"del_db_20250101_000001"
        assert self.backup_manager.delete_backup(backup_id) is True
        assert not os.path.exists(file_path)
        assert not os.path.exists(meta_path)

    def test_restore_applies_settings_and_profiles(self):
        """Restore should read settings and display profiles files and apply them."""
        self.mock_basex_connector.execute_command.return_value = "OK"

        # Create a mock backup file
        filename = 'restore_test_db_backup_20250101_121212.lift'
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<lift version="0.13"></lift>')

        # Add settings and display profiles
        settings = [{'project_name': 'Restore Project', 'source_language': {'code': 'xx', 'name': 'Xx'}}]
        with open(file_path + '.settings.json', 'w', encoding='utf-8') as sf:
            json.dump(settings, sf)

        dp = {'profiles': [{'name': 'Default'}]}
        with open(file_path + '.display_profiles.json', 'w', encoding='utf-8') as df:
            json.dump(dp, df)

        backup_id = 'restore_test_db_20250101_121212'

        # Ensure restore_database does not raise
        result = self.backup_manager.restore_database('restored_db', backup_id, file_path)
        assert result is True

    def test_restore_validation_rules_schema_enforced(self):
        """Restore should validate validation_rules.json and fail if schema invalid."""
        # create mock backup file
        filename = 'vr_db_backup_20250101_121212.lift'
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<lift version="0.13"></lift>')

        # Create an invalid validation_rules.json (invalid structure)
        with open(file_path + '.validation_rules.json', 'w', encoding='utf-8') as vf:
            vf.write('{ invalid json }')

        with pytest.raises(ValidationError):
            self.backup_manager.restore_database('restored_db', 'vr_db_20250101_121212', file_path)

    def test_backup_includes_media_when_enabled(self):
        """When include_media is True, uploads are copied into .media alongside backup."""
        self.mock_basex_connector.execute_command.return_value = "OK"

        # Create a mock uploads directory in a Flask app instance path by creating
        # a temporary directory and setting current_app.instance_path within an app context
        from flask import Flask, current_app
        instance_dir = Path(self.temp_dir) / 'instance'
        instance_dir.mkdir(parents=True, exist_ok=True)
        app = Flask(__name__, instance_path=str(instance_dir))
        with app.app_context():
            # instance_path is set on app creation
            pass

            uploads = instance_dir / 'uploads'
            uploads.mkdir(parents=True, exist_ok=True)
            # add a small media file
            media_file = uploads / 'image.jpg'
            media_file.write_text('fake image data')

            # Create a mock backup file so backup_database finds it
            backup_file = os.path.join(self.temp_dir, 'media_db_backup_20250101_120000.lift')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write('<lift version="0.13"></lift>')

            # Call backup with include_media flag True
            backup = self.backup_manager.backup_database('media_db', 'manual', 'media test', include_media=True)

            # Check that .media directory exists next to the created backup file
            media_tgt = Path(backup.file_path + '.media')
            assert media_tgt.exists() and media_tgt.is_dir()
            assert (media_tgt / 'image.jpg').exists()


    def test_list_backups_with_metadata(self):
        """Test that metadata files are read and merged into list results."""
        # Create a mock backup file
        filename = 'meta_db_backup_20250101_150000.lift'
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<lift version="0.13"></lift>')

        # Create metadata file
        meta = {
            'id': 'meta_db_20250101_150000',
            'db_name': 'meta_db',
            'description': 'This is a description',
            'status': 'completed',
            'type': 'manual',
            'timestamp': '2025-01-01T15:00:00'
        }
        meta_path = file_path + '.meta.json'
        with open(meta_path, 'w', encoding='utf-8') as mf:
            json.dump(meta, mf)

        backups = self.backup_manager.list_backups()
        # Find our metadata backup
        found = [b for b in backups if b.get('filename') == filename]
        assert len(found) == 1
        b = found[0]
        assert b.get('description') == 'This is a description'
        assert b.get('status') == 'completed'
        assert b.get('type') == 'manual'
        # display_name should be present from metadata
        assert b.get('display_name') == 'This is a description'
    
    def test_restore_database_success(self):
        """Test successful database restore."""
        # Mock the execute_command method to return success for both commands
        self.mock_basex_connector.execute_command.side_effect = ["Drop successful", "Create successful"]
        
        # Create a mock backup file
        backup_file = os.path.join(self.temp_dir, 'restore_test.lift')
        with open(backup_file, 'w') as f:
            f.write('<lift version="0.13"></lift>')
        
        db_name = 'test_db'
        result = self.backup_manager.restore_database(db_name, 'backup_id123', backup_file)
        
        assert result is True
        
        # Verify the commands were called
        assert self.mock_basex_connector.execute_command.call_count == 2
        # First call should be to drop the database
        self.mock_basex_connector.execute_command.assert_any_call(f"DROP DB {db_name}")
        # Second call should be to create the database from the backup file
        self.mock_basex_connector.execute_command.assert_called_with(f"CREATE DB {db_name} {backup_file}")
    
    def test_restore_database_failure(self):
        """Test database restore failure."""
        # Mock the execute_command method to raise an exception
        self.mock_basex_connector.execute_command.side_effect = DatabaseError("Restore failed")
        
        backup_file = os.path.join(self.temp_dir, 'restore_test.lift')
        with open(backup_file, 'w') as f:
            f.write('<lift version="0.13"></lift>')
        
        db_name = 'test_db'
        
        with pytest.raises(DatabaseError):
            self.backup_manager.restore_database(db_name, 'backup_id123', backup_file)
    
    def test_cleanup_old_backups(self):
        """Test cleaning up old backups."""
        # Create some mock backup files for a specific database
        db_name = 'test_db'
        for i in range(15):  # Create 15 backups
            timestamp = f'20250101_{100000 + i:06}'  # 10:00:00, 10:00:01, etc.
            backup_file = os.path.join(self.temp_dir, f'{db_name}_backup_{timestamp}.lift')
            with open(backup_file, 'w') as f:
                f.write('<lift></lift>')
        
        # Initially should have 15 backups
        all_backups = self.backup_manager.list_backups(db_name)
        assert len(all_backups) == 15
        
        # Keep only 5 backups
        deleted_count = self.backup_manager.cleanup_old_backups(db_name, keep_count=5)
        
        assert deleted_count == 10  # Should delete 10 old backups
        
        # Now should have only 5 backups
        remaining_backups = self.backup_manager.list_backups(db_name)
        assert len(remaining_backups) == 5
