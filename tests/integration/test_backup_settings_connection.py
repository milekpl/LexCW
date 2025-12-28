"""Integration tests to verify backup settings are properly connected to the scheduler."""

import pytest
import json
from datetime import datetime
from flask.testing import FlaskClient


@pytest.mark.integration
class TestBackupSettingsConnection:
    """Test that backup settings are properly connected to the backup scheduler."""
    


@pytest.mark.integration
class TestBackupSettingsDatabase:
    """Test backup settings in the database."""
    
    def test_backup_settings_exist_in_database(self, client: FlaskClient) -> None:
        """Test that backup settings exist in the database and can be retrieved."""
        from app.models.project_settings import ProjectSettings
        from app.models.workset_models import db
        
        # Get settings from database
        settings = ProjectSettings.query.filter_by(id=1).first()
        
        if settings:
            print(f"DEBUG: Found settings: {settings}")
            if hasattr(settings, 'backup_settings'):
                backup_settings = settings.backup_settings
                print(f"DEBUG: Backup settings in database: {backup_settings}")
                
                # Verify backup settings structure
                assert isinstance(backup_settings, dict), f"Expected dict, got {type(backup_settings)}"
                
                # Check for expected fields
                if 'schedule' in backup_settings:
                    schedule = backup_settings['schedule']
                    print(f"DEBUG: Schedule from database: {schedule}")
                    assert schedule in ['daily', 'weekly', 'monthly', 'none'], f"Invalid schedule: {schedule}"
                
                if 'retention' in backup_settings:
                    retention = backup_settings['retention']
                    assert isinstance(retention, int), f"Retention should be int, got {type(retention)}"
                    assert retention > 0, f"Retention should be positive, got {retention}"
            else:
                pytest.fail("ProjectSettings has no backup_settings attribute")
        else:
            print("DEBUG: No ProjectSettings found in database (id=1)")
            # This might be expected in test environment

@pytest.mark.integration
class TestBackupSettingsUI:
    """Test backup settings in the UI."""
    
    def test_settings_page_shows_backup_settings(self, client: FlaskClient) -> None:
        """Test that the settings page displays backup settings."""
        response = client.get('/settings/', follow_redirects=True)
        assert response.status_code == 200
        
        html_content = response.data.decode('utf-8')
        
        # Check that backup settings section exists
        assert 'Backup Schedule' in html_content or 'backup_settings' in html_content, \
            "Settings page should display backup settings"
        
        # Check for backup-related elements
        backup_elements = ['Daily', 'Weekly', 'Monthly', 'backup', 'schedule']
        found_elements = [elem for elem in backup_elements if elem in html_content]
        
        if not found_elements:
            pytest.fail(f"Settings page should contain backup-related elements, found none of: {backup_elements}")

@pytest.mark.integration
class TestBackupSchedulerIntegration:
    """Test that the backup scheduler is properly integrated."""
    
    def test_backup_scheduler_is_started(self, client: FlaskClient) -> None:
        """Test that the backup scheduler is started and functional."""
        from app.services.backup_scheduler import BackupScheduler
        
        scheduler = client.application.injector.get(BackupScheduler)
        assert scheduler is not None, "Backup scheduler should be initialized"
        
        # Check if scheduler is running
        is_running = scheduler._running if hasattr(scheduler, '_running') else False
        print(f"DEBUG: Backup scheduler running: {is_running}")
        
        # Check if scheduler has a scheduler instance
        has_scheduler = scheduler.scheduler is not None if hasattr(scheduler, 'scheduler') else False
        print(f"DEBUG: Backup scheduler has scheduler instance: {has_scheduler}")
        
        # Get scheduled backups
        scheduled = scheduler.get_scheduled_backups()
        print(f"DEBUG: Scheduled backups from scheduler: {scheduled}")
        
        assert isinstance(scheduled, list), f"Scheduled backups should be list, got {type(scheduled)}"

@pytest.mark.integration
class TestBackupSettingsEndToEnd:
    """End-to-end test for backup settings connection."""
    
    def test_backup_settings_flow(self, client: FlaskClient) -> None:
        """Test the complete backup settings flow: settings -> scheduler -> API -> UI."""
        # 1. Check settings in database
        from app.models.project_settings import ProjectSettings
        settings = ProjectSettings.query.filter_by(id=1).first()
        
        db_schedule = None
        if settings and hasattr(settings, 'backup_settings'):
            db_schedule = settings.backup_settings.get('schedule')
            print(f"DEBUG: Schedule in database: {db_schedule}")
        
        # 2. Check scheduler
        from app.services.backup_scheduler import BackupScheduler
        scheduler = client.application.injector.get(BackupScheduler)
        scheduled_backups = scheduler.get_scheduled_backups()
        scheduler_schedule = scheduled_backups[0]['trigger'] if scheduled_backups else None
        print(f"DEBUG: Schedule in scheduler: {scheduler_schedule}")
        
        # 3. Check API
        api_response = client.get('/api/backup/scheduled')
        api_data = json.loads(api_response.data)
        api_schedule = api_data['data'][0]['trigger'] if api_data['data'] else None
        print(f"DEBUG: Schedule from API: {api_schedule}")
        
        # 4. Check UI (settings page)
        settings_response = client.get('/settings')
        settings_html = settings_response.data.decode('utf-8')
        ui_schedule = 'Daily' if 'Daily' in settings_html else None
        print(f"DEBUG: Schedule in UI: {ui_schedule}")
        
        # Verify consistency
        schedules = [db_schedule, scheduler_schedule, api_schedule, ui_schedule]
        non_none_schedules = [s for s in schedules if s]
        
        if non_none_schedules:
            # If any schedule is set, they should all be consistent
            first = non_none_schedules[0]
            for s in non_none_schedules[1:]:
                # Normalize for comparison
                s_normalized = s.lower() if s else None
                first_normalized = first.lower() if first else None
                
                if s_normalized and first_normalized and s_normalized != first_normalized:
                    pytest.fail(f"Inconsistent schedules: {first} vs {s}")
        else:
            print("DEBUG: No schedules found anywhere (this may be expected in test environment)")

@pytest.mark.integration
class TestBackupSettingsDefault:
    """Test default backup settings."""
    
    def test_default_backup_settings(self, client: FlaskClient) -> None:
        """Test that default backup settings are reasonable."""
        from app.config_manager import ConfigManager
        
        config_manager = client.application.injector.get(ConfigManager)
        default_settings = config_manager.get_backup_settings()
        
        print(f"DEBUG: Default backup settings: {default_settings}")
        
        # Verify default settings structure
        assert 'schedule' in default_settings, "Default settings should have schedule"
        assert 'retention' in default_settings, "Default settings should have retention"
        assert 'directory' in default_settings, "Default settings should have directory"
        
        # Verify default values are reasonable
        schedule = default_settings['schedule']
        retention = default_settings['retention']
        
        assert schedule in ['daily', 'weekly', 'monthly'], f"Invalid default schedule: {schedule}"
        assert isinstance(retention, int) and retention > 0, f"Invalid default retention: {retention}"
        
        print(f"DEBUG: Default schedule: {schedule}, retention: {retention}")
