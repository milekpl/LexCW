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
            backup_directory=self.temp_dir
        )
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('app.database.basex_connector.BaseXConnector.execute_command')
    def test_backup_database_success(self, mock_execute_command):
        """Test successful database backup."""
        # Mock the execute_command method to return success
        mock_execute_command.return_value = "Backup successful"
        
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
        mock_execute_command.assert_called_once()
        
        # Clean up the file
        os.remove(backup_file)
    
    @patch('app.database.basex_connector.BaseXConnector.execute_command')
    def test_backup_database_failure(self, mock_execute_command):
        """Test database backup failure."""
        # Mock the execute_command method to raise an exception
        mock_execute_command.side_effect = DatabaseError("Backup failed")
        
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
    
    @patch('app.database.basex_connector.BaseXConnector.execute_command')
    def test_restore_database_success(self, mock_execute_command):
        """Test successful database restore."""
        # Mock the execute_command method to return success for both commands
        mock_execute_command.side_effect = ["Drop successful", "Create successful"]
        
        # Create a mock backup file
        backup_file = os.path.join(self.temp_dir, 'restore_test.lift')
        with open(backup_file, 'w') as f:
            f.write('<lift version="0.13"></lift>')
        
        db_name = 'test_db'
        result = self.backup_manager.restore_database(db_name, 'backup_id123', backup_file)
        
        assert result is True
        
        # Verify the commands were called
        assert mock_execute_command.call_count == 2
        # First call should be to drop the database
        mock_execute_command.assert_any_call(f"DROP DB {db_name}")
        # Second call should be to create the database from the backup file
        mock_execute_command.assert_called_with(f"CREATE DB {db_name} {backup_file}")
    
    @patch('app.database.basex_connector.BaseXConnector.execute_command')
    def test_restore_database_failure(self, mock_execute_command):
        """Test database restore failure."""
        # Mock the execute_command method to raise an exception
        mock_execute_command.side_effect = DatabaseError("Restore failed")
        
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
