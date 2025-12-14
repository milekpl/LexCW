"""
Unit tests for backup models.
"""

import pytest
from datetime import datetime
from app.models.backup_models import Backup, ScheduledBackup, OperationHistory


class TestBackupModels:
    """Test backup models functionality."""
    
    def test_backup_model_creation(self):
        """Test creating a backup model instance."""
        backup = Backup(
            db_name='test_db',
            type_='full',
            file_path='/path/to/backup.lift',
            file_size=1024,
            description='Test backup'
        )
        
        assert backup.db_name == 'test_db'
        assert backup.type == 'full'
        assert backup.file_path == '/path/to/backup.lift'
        assert backup.file_size == 1024
        assert backup.description == 'Test backup'
        assert backup.timestamp is not None
        assert backup.status == 'created'
        
    def test_backup_to_dict(self):
        """Test converting backup to dictionary."""
        backup = Backup(
            db_name='test_db',
            type_='full',
            file_path='/path/to/backup.lift',
            file_size=1024,
            description='Test backup'
        )
        
        backup_dict = backup.to_dict()
        
        assert backup_dict['db_name'] == 'test_db'
        assert backup_dict['type'] == 'full'
        assert backup_dict['file_path'] == '/path/to/backup.lift'
        assert backup_dict['file_size'] == 1024
        assert backup_dict['description'] == 'Test backup'
        assert 'timestamp' in backup_dict
        
    def test_backup_from_dict(self):
        """Test creating backup from dictionary."""
        backup_dict = {
            'db_name': 'test_db',
            'type': 'full',
            'file_path': '/path/to/backup.lift',
            'file_size': 1024,
            'description': 'Test backup'
        }

        backup = Backup.from_dict(backup_dict)

        assert backup.db_name == 'test_db'
        assert backup.type == 'full'
        assert backup.file_path == '/path/to/backup.lift'
        assert backup.file_size == 1024
        assert backup.description == 'Test backup'
        
    def test_scheduled_backup_model_creation(self):
        """Test creating a scheduled backup model instance."""
        next_run = datetime(2025, 1, 1, 12, 0)
        scheduled_backup = ScheduledBackup(
            db_name='test_db',
            interval='daily',
            time_='12:00',
            type_='full',
            next_run=next_run,
            active=True
        )
        
        assert scheduled_backup.db_name == 'test_db'
        assert scheduled_backup.interval == 'daily'
        assert scheduled_backup.time == '12:00'
        assert scheduled_backup.type == 'full'
        assert scheduled_backup.next_run == next_run
        assert scheduled_backup.active is True
        
    def test_scheduled_backup_to_dict(self):
        """Test converting scheduled backup to dictionary."""
        next_run = datetime(2025, 1, 1, 12, 0)
        scheduled_backup = ScheduledBackup(
            db_name='test_db',
            interval='daily',
            time_='12:00',
            type_='full',
            next_run=next_run,
            active=True
        )
        
        backup_dict = scheduled_backup.to_dict()
        
        assert backup_dict['db_name'] == 'test_db'
        assert backup_dict['interval'] == 'daily'
        assert backup_dict['time'] == '12:00'
        assert backup_dict['type'] == 'full'
        assert backup_dict['active'] is True
        
    def test_operation_history_model_creation(self):
        """Test creating an operation history model instance."""
        operation = OperationHistory(
            type_='create',
            data='{"entry_id": "test_entry", "content": "test"}',
            entry_id='test_entry',
            user_id='test_user'
        )
        
        assert operation.type == 'create'
        assert operation.data == '{"entry_id": "test_entry", "content": "test"}'
        assert operation.entry_id == 'test_entry'
        assert operation.user_id == 'test_user'
        assert operation.timestamp is not None
        assert operation.status == 'completed'
        
    def test_operation_history_to_dict(self):
        """Test converting operation history to dictionary."""
        operation = OperationHistory(
            type_='create',
            data='{"entry_id": "test_entry", "content": "test"}',
            entry_id='test_entry',
            user_id='test_user'
        )
        
        op_dict = operation.to_dict()
        
        assert op_dict['type'] == 'create'
        assert op_dict['data'] == '{"entry_id": "test_entry", "content": "test"}'
        assert op_dict['entry_id'] == 'test_entry'
        assert op_dict['user_id'] == 'test_user'
        assert 'timestamp' in op_dict
        assert op_dict['status'] == 'completed'
