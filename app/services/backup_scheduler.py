"""
Service for scheduling cyclical backups of BaseX databases.
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

from app.services.basex_backup_manager import BaseXBackupManager
from app.models.backup_models import ScheduledBackup
from app.services.event_bus import EventBus


class BackupScheduler:
    """
    Service for scheduling cyclical backups of BaseX databases.
    
    This service uses APScheduler to manage recurring backup jobs based on configurable
    intervals (hourly, daily, weekly). It supports different backup types and maintains
    scheduling metadata.
    """

    def __init__(self, backup_manager: BaseXBackupManager,
                 event_bus: Optional[EventBus] = None):
        """
        Initialize the backup scheduler.

        Args:
            backup_manager: BaseXBackupManager instance to perform actual backups
            event_bus: Optional EventBus instance for receiving entry update events
        """
        self.backup_manager = backup_manager
        # Defer scheduler initialization to `start()` so tests can patch
        # BackgroundScheduler before it is instantiated in unit tests.
        self.scheduler = None
        self.logger = logging.getLogger(__name__)
        self._scheduled_backup_jobs: Dict[str, Job] = {}
        self._running = False
        # First run always performs a backup
        self._dirty = True

        # Subscribe to entry_updated events if event_bus is provided
        if event_bus:
            event_bus.on('entry_updated', self._on_entry_updated)

    def start(self):
        """Start the backup scheduler."""
        if not self._running:
            # Initialize scheduler lazily to allow test patches
            if self.scheduler is None:
                self.scheduler = BackgroundScheduler()
            self.scheduler.start()
            self._running = True
            self.logger.info("Backup scheduler started")

    def stop(self):
        """Stop the backup scheduler."""
        if self._running and self.scheduler is not None:
            self.scheduler.shutdown()
            self.scheduler = None
            self._running = False
            self.logger.info("Backup scheduler stopped")

    def schedule_backup(self, scheduled_backup: ScheduledBackup) -> bool:
        """
        Schedule a recurring backup job based on the scheduled backup configuration.

        Args:
            scheduled_backup: ScheduledBackup model instance with scheduling config

        Returns:
            True if scheduling was successful, False otherwise
        """
        try:
            # Define cron schedule based on interval
            cron_schedule = self._get_cron_schedule(scheduled_backup.interval, scheduled_backup.time)
            
            # Create the backup job function
            def backup_job():
                self._execute_scheduled_backup(scheduled_backup)
            
            # Schedule the job using cron fields (avoid direct CronTrigger construction
            # to increase testability when CronTrigger is patched in unit tests)
            minute, hour, day, month, dow = cron_schedule.split()
            job = self.scheduler.add_job(
                func=backup_job,
                trigger='cron',
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=dow,
                id=f"backup_{scheduled_backup.id}",
                name=f"Backup job for {scheduled_backup.db_name}",
                replace_existing=True
            )

            # Store reference to the job
            self._scheduled_backup_jobs[scheduled_backup.id] = job
            # Record schedule id on the ScheduledBackup model for easy lookup
            setattr(scheduled_backup, 'schedule_id', scheduled_backup.id)
            
            # Update the scheduled backup's next run time
            scheduled_backup.next_run = job.next_run_time
            
            self.logger.info(f"Scheduled backup for {scheduled_backup.db_name} with interval {scheduled_backup.interval}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule backup for {scheduled_backup.db_name}: {str(e)}")
            return False

    def _get_cron_schedule(self, interval: str, time_str: str) -> str:
        """
        Convert interval and time specification to cron format.
        
        Args:
            interval: Backup interval ('hourly', 'daily', 'weekly')
            time_str: Time specification in HH:MM format or cron format
            
        Returns:
            Cron schedule string
        """
        if interval == 'hourly':
            # If time_str is HH:MM format, use the minute; otherwise use 0
            if ':' in time_str:
                minute = time_str.split(':')[1].zfill(2)
                return f"{minute} * * * *"
            else:
                return f"{time_str} * * * *"  # Assume it's already in cron format for minute
        
        elif interval == 'daily':
            if ':' in time_str:
                hour, minute = time_str.split(':')
                return f"{minute.zfill(2)} {hour.zfill(2)} * * *"
            else:
                return time_str  # Assume it's already in cron format
        
        elif interval == 'weekly':
            # Default to Sunday at specified time if no day specified
            if ':' in time_str:
                hour, minute = time_str.split(':')
                # Assuming Sunday is day 0; you might want to extend this to support specific days
                return f"{minute.zfill(2)} {hour.zfill(2)} * * 0"
            else:
                return time_str  # Assume it's already in cron format
        
        else:
            raise ValueError(f"Unsupported interval: {interval}")

    def _execute_scheduled_backup(self, scheduled_backup: ScheduledBackup):
        """
        Execute a scheduled backup job.

        Args:
            scheduled_backup: ScheduledBackup model instance to execute
        """
        # Check if any changes occurred since last backup
        if not getattr(self, '_dirty', True):
            self.logger.info(f"No changes since last backup for {scheduled_backup.db_name}, skipping")
            return

        try:
            # Reset dirty flag after checking
            self._dirty = False

            # Update last run time
            scheduled_backup.last_run = datetime.utcnow()

            # Perform the backup - wrap in app context for background thread safety
            from flask import current_app
            with current_app.app_context():
                backup_result = self.backup_manager.backup_database(
                    db_name=scheduled_backup.db_name,
                    backup_type=scheduled_backup.type,
                    description=f"Scheduled {scheduled_backup.interval} backup"
                )

            # Update last status
            scheduled_backup.last_status = 'success'

            self.logger.info(f"Scheduled backup completed for {scheduled_backup.db_name}")

        except Exception as e:
            scheduled_backup.last_status = 'failed'
            error_msg = f"Scheduled backup failed for {scheduled_backup.db_name}: {str(e)}"
            self.logger.error(error_msg)

    def _on_entry_updated(self, data: Dict[str, Any]) -> None:
        """
        Handle entry_updated events - mark backup as needed.

        Args:
            data: Event data containing entry_id
        """
        self._dirty = True
        self.logger.debug(f"Entry {data.get('entry_id')} updated, backup needed")

    def cancel_backup(self, schedule_id: str) -> bool:
        """
        Cancel a scheduled backup job.

        Args:
            schedule_id: ID of the scheduled backup to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            if schedule_id in self._scheduled_backup_jobs:
                job = self._scheduled_backup_jobs[schedule_id]
                job.remove()
                del self._scheduled_backup_jobs[schedule_id]

                self.logger.info(f"Scheduled backup cancelled for ID: {schedule_id}")
                return True
            else:
                self.logger.warning(f"No scheduled backup found with ID: {schedule_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to cancel scheduled backup {schedule_id}: {str(e)}")
            return False

    def get_scheduled_backups(self) -> List[Dict[str, any]]:
        """
        Get information about all currently scheduled backups.

        Returns:
            List of scheduled backup information
        """
        scheduled_info = []
        
        for schedule_id, job in self._scheduled_backup_jobs.items():
            info = {
                'schedule_id': schedule_id,
                'job_id': job.id,
                'job_name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            scheduled_info.append(info)
        
        return scheduled_info

    def run_scheduled_backups(self):
        """
        Manually trigger all scheduled backups.
        This is mainly for testing or on-demand execution.
        """
        self.logger.info("Manually triggering all scheduled backups")
        
        for schedule_id, job in self._scheduled_backup_jobs.items():
            # Execute the job immediately
            try:
                job.func()  # Execute the backup function directly
                self.logger.info(f"Manual backup executed for schedule ID: {schedule_id}")
            except Exception as e:
                self.logger.error(f"Manual backup failed for schedule ID {schedule_id}: {str(e)}")

    def update_scheduled_backup(self, scheduled_backup: ScheduledBackup) -> bool:
        """
        Update an existing scheduled backup.

        Args:
            scheduled_backup: Updated ScheduledBackup model instance

        Returns:
            True if update was successful, False otherwise
        """
        # First cancel the existing job
        self.cancel_backup(scheduled_backup.id)

        # Then schedule the updated configuration
        return self.schedule_backup(scheduled_backup)

    def sync_backup_schedule(self, db_name: str, backup_settings: Dict[str, any]) -> bool:
        """
        Sync scheduled backups with project settings.
        
        This method will:
        1. Find any existing jobs for the given database and cancel them
        2. If schedule is enabled, create and schedule a new backup job
        
        Args:
            db_name: Name of the database (e.g., 'dictionary')
            backup_settings: Dictionary containing backup settings (schedule, time, etc.)
            
        Returns:
            True if sync resulted in active schedule, False if disabled/failed
        """
        try:
            self.logger.info(f"Syncing backup schedule for {db_name} with settings: {backup_settings}")
            
            # 1. Find and cancel existing jobs for this database
            jobs_to_cancel = []
            for schedule_id, job in self._scheduled_backup_jobs.items():
                if job.name == f"Backup job for {db_name}":
                    jobs_to_cancel.append(schedule_id)
            
            for schedule_id in jobs_to_cancel:
                self.cancel_backup(schedule_id)
                self.logger.info(f"Cancelled existing backup job {schedule_id} for {db_name}")
                
            # 2. Check if scheduling is enabled
            schedule_interval = backup_settings.get('schedule', 'daily')
            if not schedule_interval or schedule_interval == 'none':
                self.logger.info(f"Backup schedule disabled for {db_name}")
                return False
                
            # 3. Create new schedule
            # Import here to avoid circular dependencies if any
            from app.models.backup_models import ScheduledBackup
            
            # Default to 2:00 AM if not specified
            time_str = backup_settings.get('time', '02:00')
            
            scheduled_backup = ScheduledBackup(
                db_name=db_name,
                interval=schedule_interval,
                time_=time_str,
                type_='full', # Default to full backup
                active=True,
                next_run=datetime.now() + timedelta(days=1) # Initial dummy value, updated by scheduler
            )
            
            # 4. Schedule the job
            result = self.schedule_backup(scheduled_backup)
            if result:
                self.logger.info(f"Successfully synced new backup schedule for {db_name}: {schedule_interval} at {time_str}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to sync backup schedule for {db_name}: {e}")
            return False
