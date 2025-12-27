"""Simple unit test for backup scheduler functionality."""

import pytest
from datetime import datetime, timedelta
from app.services.backup_scheduler import BackupScheduler
from app.models.backup_models import ScheduledBackup


class TestBackupSchedulerSimple:
    """Simple tests for backup scheduler."""
    
    def test_schedule_backup_basic(self):
        """Test that we can schedule a basic backup."""
        # Create a mock backup manager
        class MockBackupManager:
            def backup_database(self, **kwargs):
                return {"success": True, "backup_id": "test123"}
        
        # Create scheduler
        scheduler = BackupScheduler(MockBackupManager())
        scheduler.start()  # Need to start scheduler first
        
        # Create a scheduled backup
        next_run = datetime.utcnow() + timedelta(hours=1)
        scheduled_backup = ScheduledBackup(
            db_name="test_db",
            interval="daily",
            time_="02:00",
            type_="full",
            next_run=next_run
        )
        
        # Schedule the backup
        result = scheduler.schedule_backup(scheduled_backup)
        
        # Verify it was scheduled
        assert result is True, "Backup should be scheduled successfully"
        
        # Verify it appears in scheduled backups
        scheduled = scheduler.get_scheduled_backups()
        assert len(scheduled) == 1, f"Expected 1 scheduled backup, got {len(scheduled)}"
        
        # Verify the scheduled backup details
        scheduled_backup_data = scheduled[0]
        assert 'schedule_id' in scheduled_backup_data
        assert 'job_id' in scheduled_backup_data
        assert 'next_run_time' in scheduled_backup_data
        
        print(f"SUCCESS: Scheduled backup: {scheduled_backup_data}")
    
    def test_scheduler_starts(self):
        """Test that scheduler can be started."""
        class MockBackupManager:
            def backup_database(self, **kwargs):
                return {"success": True}
        
        scheduler = BackupScheduler(MockBackupManager())
        
        # Scheduler should start without error
        scheduler.start()
        
        # Verify it's running
        assert scheduler._running is True, "Scheduler should be running after start"
        assert scheduler.scheduler is not None, "Scheduler should have a scheduler instance"
        
        print("SUCCESS: Scheduler started successfully")
    
    def test_get_scheduled_backups_empty(self):
        """Test getting scheduled backups when none exist."""
        class MockBackupManager:
            def backup_database(self, **kwargs):
                return {"success": True}
        
        scheduler = BackupScheduler(MockBackupManager())
        
        # Should return empty list when no backups scheduled
        scheduled = scheduler.get_scheduled_backups()
        assert isinstance(scheduled, list), "Should return a list"
        assert len(scheduled) == 0, "Should be empty when no backups scheduled"
        
        print("SUCCESS: Empty scheduled backups list returned correctly")
