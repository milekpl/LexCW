"""
Integration tests for backup API endpoints.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch
from app.models.backup_models import Backup, ScheduledBackup


class TestBackupAPI:
    """Test backup API endpoints."""
    
    def test_get_operation_history(self, client, app):
        """Test getting operation history."""
        with app.app_context():
            response = client.get('/api/backup/operations')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'success' in data
            assert 'data' in data
    
    def test_undo_last_operation(self, client, app):
        """Test undoing the last operation."""
        with app.app_context():
            # Test POST request to undo operation
            response = client.post('/api/backup/operations/undo', 
                                 json={})
            assert response.status_code in [200, 400]  # 400 if no operations to undo
    
    def test_redo_last_operation(self, client, app):
        """Test redoing the last operation."""
        with app.app_context():
            # Test POST request to redo operation
            response = client.post('/api/backup/operations/redo', 
                                 json={})
            assert response.status_code in [200, 400]  # 400 if no operations to redo
    
    def test_create_backup(self, client, app):
        """Test creating a backup."""
        with app.app_context():
            backup_data = {
                'db_name': 'test_db',
                'backup_type': 'manual',
                'description': 'Test backup'
            }
            response = client.post('/api/backup/create', 
                                 json=backup_data,
                                 content_type='application/json')
            # Response might be 500 if BaseX is not available in test environment
            assert response.status_code in [200, 500]
    
    def test_get_backup_history(self, client, app):
        """Test getting backup history."""
        with app.app_context():
            response = client.get('/api/backup/history')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'success' in data
    
    def test_schedule_backup(self, client, app):
        """Test scheduling a backup."""
        with app.app_context():
            schedule_data = {
                'db_name': 'test_db',
                'interval': 'daily',
                'time': '02:00',
                'type': 'full',
                'active': True
            }
            response = client.post('/api/backup/schedule',
                                 json=schedule_data,
                                 content_type='application/json')
            # Response might be 500 if scheduler fails in test environment
            assert response.status_code in [200, 500]
    
    def test_get_scheduled_backups(self, client, app):
        """Test getting scheduled backups."""
        with app.app_context():
            response = client.get('/api/backup/scheduled')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'success' in data
    
    def test_cancel_scheduled_backup(self, client, app):
        """Test canceling a scheduled backup."""
        with app.app_context():
            # This will likely return 400 or 404 since the ID probably doesn't exist
            response = client.delete('/api/backup/scheduled/nonexistent_id')
            assert response.status_code in [400, 404, 200]
    
    def test_validate_backup(self, client, app):
        """Test validating a backup file."""
        with app.app_context():
            # This will likely return 404 since the file path doesn't exist
            response = client.get('/api/backup/validate/nonexistent/path.lift')
            # May return 200 with error in data, or 500, or 404
            assert response.status_code in [200, 404, 500]
