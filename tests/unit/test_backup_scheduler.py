"""
Unit tests for BackupScheduler.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from app.services.backup_scheduler import BackupScheduler
from app.services.basex_backup_manager import BaseXBackupManager
from app.models.backup_models import ScheduledBackup


class TestBackupScheduler:
    """Test BackupScheduler functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock backup manager
        self.mock_backup_manager = Mock(spec=BaseXBackupManager)
        
        # Create the scheduler with the mock
        self.scheduler = BackupScheduler(backup_manager=self.mock_backup_manager)
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Stop the scheduler if it was started
        if self.scheduler._running:
            self.scheduler.stop()
    
    def test_get_cron_schedule_hourly(self):
        """Test getting cron schedule for hourly backups."""
        cron = self.scheduler._get_cron_schedule('hourly', '30')
        assert cron == '30 * * * *'  # 30 minutes past every hour
        
        cron = self.scheduler._get_cron_schedule('hourly', '15:45')
        assert cron == '45 * * * *'  # 45 minutes past every hour (using minutes from 15:45)
        
    def test_get_cron_schedule_daily(self):
        """Test getting cron schedule for daily backups."""
        cron = self.scheduler._get_cron_schedule('daily', '02:30')
        assert cron == '30 02 * * *'  # 2:30 AM daily
        
        cron = self.scheduler._get_cron_schedule('daily', '22:15')
        assert cron == '15 22 * * *'  # 10:15 PM daily
    
    def test_get_cron_schedule_weekly(self):
        """Test getting cron schedule for weekly backups."""
        cron = self.scheduler._get_cron_schedule('weekly', '03:00')
        assert cron == '00 03 * * 0'  # 3:00 AM on Sunday weekly
    
    def test_get_cron_schedule_invalid_interval(self):
        """Test getting cron schedule with invalid interval."""
        with pytest.raises(ValueError):
            self.scheduler._get_cron_schedule('invalid', '02:00')
    
    @patch('app.services.backup_scheduler.BackgroundScheduler')
    @patch('app.services.backup_scheduler.CronTrigger')
    def test_schedule_backup(self, mock_cron_trigger, mock_scheduler_class):
        """Test scheduling a backup."""
        # Mock the scheduler instance
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_scheduler.add_job.return_value = Mock()
        mock_scheduler.add_job.return_value.next_run_time = datetime(2025, 1, 1, 12, 0)
        
        # Create a scheduled backup
        scheduled_backup = ScheduledBackup(
            db_name='test_db',
            interval='daily',
            time_='02:00',
            type_='full',
            next_run=datetime(2025, 1, 1, 12, 0)
        )
        
        self.scheduler.start()
        result = self.scheduler.schedule_backup(scheduled_backup)
        
        assert result is True
        mock_scheduler.add_job.assert_called_once()
        # Check that the job was stored
        assert scheduled_backup.schedule_id in self.scheduler._scheduled_backup_jobs
    
    @patch('app.services.backup_scheduler.BackgroundScheduler')
    def test_cancel_backup(self, mock_scheduler_class):
        """Test canceling a scheduled backup."""
        # Mock the scheduler instance
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        # Add a mock job to the scheduler
        mock_job = Mock()
        mock_scheduler.add_job.return_value = mock_job
        
        # Create and schedule a backup
        scheduled_backup = ScheduledBackup(
            db_name='test_db',
            interval='daily',
            time_='02:00',
            type_='full',
            next_run=datetime(2025, 1, 1, 12, 0)
        )
        
        self.scheduler.start()
        self.scheduler.schedule_backup(scheduled_backup)
        
        # Cancel the scheduled backup
        result = self.scheduler.cancel_backup(scheduled_backup.id)
        
        assert result is True
        mock_job.remove.assert_called_once()
        assert scheduled_backup.id not in self.scheduler._scheduled_backup_jobs
    
    def test_cancel_nonexistent_backup(self):
        """Test canceling a non-existent scheduled backup."""
        result = self.scheduler.cancel_backup('nonexistent_id')
        assert result is False
    
    def test_execute_scheduled_backup_success(self):
        """Test executing a scheduled backup successfully."""
        scheduled_backup = ScheduledBackup(
            db_name='test_db',
            interval='daily',
            time_='02:00',
            type_='full',
            next_run=datetime(2025, 1, 1, 12, 0)
        )
        
        # Mock the backup manager to return success
        self.mock_backup_manager.backup_database.return_value = Mock()
        
        # Execute the scheduled backup
        self.scheduler._execute_scheduled_backup(scheduled_backup)
        
        # Verify the backup was called
        self.mock_backup_manager.backup_database.assert_called_once_with(
            db_name='test_db',
            backup_type='full',
            description='Scheduled daily backup'
        )
        assert scheduled_backup.last_status == 'success'
    
    def test_execute_scheduled_backup_failure(self):
        """Test executing a scheduled backup with failure."""
        scheduled_backup = ScheduledBackup(
            db_name='test_db',
            interval='daily',
            time_='02:00',
            type_='full',
            next_run=datetime(2025, 1, 1, 12, 0)
        )
        
        # Mock the backup manager to raise an exception
        self.mock_backup_manager.backup_database.side_effect = Exception("Backup failed")
        
        # Execute the scheduled backup
        self.scheduler._execute_scheduled_backup(scheduled_backup)
        
        # Verify the backup was called
        self.mock_backup_manager.backup_database.assert_called_once_with(
            db_name='test_db',
            backup_type='full',
            description='Scheduled daily backup'
        )
        assert scheduled_backup.last_status == 'failed'
    
    @patch('app.services.backup_scheduler.BackgroundScheduler')
    def test_get_scheduled_backups(self, mock_scheduler_class):
        """Test getting scheduled backups info."""
        # Mock the scheduler
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        # Create mock jobs
        mock_job1 = Mock()
        mock_job1.id = 'job1'
        mock_job1.name = 'Backup job for db1'
        mock_job1.next_run_time = datetime(2025, 1, 1, 12, 0)
        mock_job1.trigger = '0 2 * * *'
        
        mock_job2 = Mock()
        mock_job2.id = 'job2'
        mock_job2.name = 'Backup job for db2'
        mock_job2.next_run_time = datetime(2025, 1, 1, 13, 0)
        mock_job2.trigger = '0 3 * * *'
        
        # Add jobs to scheduler
        self.scheduler._scheduled_backup_jobs = {
            'id1': mock_job1,
            'id2': mock_job2
        }
        
        scheduled_info = self.scheduler.get_scheduled_backups()
        
        assert len(scheduled_info) == 2
        assert scheduled_info[0]['job_id'] == 'job1'
        assert scheduled_info[1]['job_id'] == 'job2'
