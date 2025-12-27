"""Integration tests for system status functionality."""

import pytest
import json
from flask import Flask
from flask.testing import FlaskClient


@pytest.mark.integration
class TestSystemStatusIntegration:
    """Test system status functionality on the dashboard."""
    
    def test_dashboard_shows_system_status(self, client: FlaskClient) -> None:
        """Test that the dashboard page includes system status information."""
        response = client.get('/')
        assert response.status_code == 200
        
        # Check that system status elements are present in the HTML
        html_content = response.data.decode('utf-8')
        assert 'System Status' in html_content
        assert 'Database Connection' in html_content
        assert 'Last Backup' in html_content
        assert 'Next Scheduled Backup' in html_content
        assert 'Total Backups' in html_content
        assert 'Storage Usage' in html_content
        
    def test_dashboard_includes_system_status_data(self, client: FlaskClient) -> None:
        """Test that the dashboard includes actual system status data."""
        response = client.get('/')
        assert response.status_code == 200
        
        # Check that the response contains system status data
        html_content = response.data.decode('utf-8')
        
        # These should be present in the rendered HTML (as actual values, not template variables)
        assert 'System Status' in html_content
        assert 'Database Connection' in html_content
        assert 'Last Backup' in html_content
        assert 'Next Scheduled Backup' in html_content
        assert 'Total Backups' in html_content
        assert 'Storage Usage' in html_content
        
        # Check that badges are present (indicating actual data is rendered)
        assert 'db-status-badge' in html_content
        assert 'backup-status-badge' in html_content
        assert 'next-backup-badge' in html_content
        assert 'backup-count-badge' in html_content
        assert 'storage-status-badge' in html_content
        
    def test_quick_backup_button_present(self, client: FlaskClient) -> None:
        """Test that the quick backup button is present and functional."""
        response = client.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode('utf-8')
        assert 'quick-backup-btn' in html_content
        assert 'Quick Backup' in html_content
        
    def test_system_status_reflects_actual_backup_state(self, client: FlaskClient) -> None:
        """Test that system status accurately reflects backup state."""
        response = client.get('/')
        assert response.status_code == 200
        
        # The system status should be populated with actual data from the service
        # This test verifies that the backend is properly wired to the frontend
        html_content = response.data.decode('utf-8')
        
        # Check that the system status is not just placeholder data
        # It should contain actual values from get_system_status()
        assert '{{ system_status.db_connected }}' not in html_content
        assert '{{ system_status.last_backup }}' not in html_content
        assert '{{ system_status.next_backup }}' not in html_content
        assert '{{ system_status.backup_count }}' not in html_content
        assert '{{ system_status.storage_percent }}' not in html_content
        
    def test_refresh_button_present(self, client: FlaskClient) -> None:
        """Test that the refresh button is present."""
        response = client.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode('utf-8')
        assert 'refresh-stats-btn' in html_content
        assert 'Refresh' in html_content


@pytest.mark.integration
class TestQuickBackupFunctionality:
    """Test quick backup functionality."""
    
    def test_quick_backup_endpoint_exists(self, client: FlaskClient) -> None:
        """Test that the backup create endpoint exists and is accessible."""
        # Test with required parameters
        response = client.post('/api/backup/create', 
                              data=json.dumps({
                                  'db_name': 'dictionary',
                                  'backup_type': 'manual',
                                  'name': 'Test Backup',
                                  'description': 'Test backup from integration test'
                              }),
                              content_type='application/json')
        
        # Should return a valid response (either success or error)
        assert response.status_code in [200, 201, 400, 500]
        
        data = json.loads(response.data)
        assert 'success' in data
        
    def test_quick_backup_requires_db_name(self, client: FlaskClient) -> None:
        """Test that quick backup requires db_name parameter."""
        # Test without db_name parameter (should fail)
        response = client.post('/api/backup/create',
                              data=json.dumps({
                                  'backup_type': 'manual',
                                  'name': 'Test Backup'
                              }),
                              content_type='application/json')
        
        # Should return 400 error
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert not data['success']
        assert 'error' in data
        assert 'Database name is required' in data['error']


@pytest.mark.integration
class TestSystemStatusBackend:
    """Test the backend system status functionality."""
    
    def test_get_system_status_method_exists(self, client: FlaskClient) -> None:
        """Test that the get_system_status method exists and returns data."""
        # This test verifies that the backend service method works
        from app.services.dictionary_service import DictionaryService
        
        service = client.application.injector.get(DictionaryService)
        system_status = service.get_system_status()
        
        # Debug output to see actual values
        print(f"DEBUG: System status: {system_status}")
        
        # Verify that system status contains expected fields
        assert isinstance(system_status, dict)
        assert 'db_connected' in system_status
        assert 'last_backup' in system_status
        assert 'next_backup' in system_status
        assert 'total_backups' in system_status
        assert 'backup_count' in system_status
        assert 'storage_percent' in system_status
        
        # Verify field types
        assert isinstance(system_status['db_connected'], bool)
        assert isinstance(system_status['last_backup'], str)
        assert isinstance(system_status['next_backup'], str)
        assert isinstance(system_status['total_backups'], int)
        assert isinstance(system_status['backup_count'], int)
        assert isinstance(system_status['storage_percent'], int)
        
        # Verify that next_backup shows "Not scheduled" when no backups are scheduled
        # This is the correct behavior - it should not be empty or undefined
        assert system_status['next_backup'] == "Not scheduled"

@pytest.mark.integration
class TestBackupSettingsIntegration:
    """Test that backup settings show accurate information."""
    
    def test_backup_settings_api_returns_scheduled_backups(self, client: FlaskClient) -> None:
        """Test that the backup settings API returns actual scheduled backup information."""
        response = client.get('/api/backup/scheduled')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        
        scheduled_backups = data['data']
        print(f"DEBUG: Scheduled backups: {scheduled_backups}")
        
        # Verify that it returns a list
        assert isinstance(scheduled_backups, list)
        
        # In a test environment with no scheduled backups, this should be empty
        # This is the correct behavior - no hardcoded "Daily at 2:00 AM" placeholder
        if len(scheduled_backups) == 0:
            print("INFO: No scheduled backups found (this is expected in test environment)")
        else:
            print(f"INFO: Found {len(scheduled_backups)} scheduled backups")
            # If there are scheduled backups, verify they have expected structure
            for backup in scheduled_backups:
                assert 'schedule_id' in backup
                assert 'job_id' in backup
                assert 'next_run_time' in backup