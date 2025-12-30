import pytest
from app import create_app
from app.services.backup_scheduler import BackupScheduler
from app.config_manager import ConfigManager


@pytest.mark.integration
def test_backup_scheduler_schedules_on_start():
    """Integration test: starting the app should schedule backups by default."""
    app = create_app('testing')

    try:
        with app.app_context():
            scheduler: BackupScheduler = app.injector.get(BackupScheduler)

            # There should be at least one scheduled backup (default config provides 'daily')
            scheduled = scheduler.get_scheduled_backups()
            assert isinstance(scheduled, list)
            assert len(scheduled) >= 1, "Expected at least one scheduled backup"

            # Basic sanity check on job data
            assert any('Backup job for' in s.get('job_name', '') for s in scheduled)
    finally:
        # Ensure background scheduler thread is stopped to avoid test pollution
        try:
            with app.app_context():
                app.injector.get(BackupScheduler).stop()
        except Exception:
            pass


@pytest.mark.integration
def test_backup_scheduler_sync_disables_and_enables():
    """Integration test: updating backup_settings should sync with BackupScheduler"""
    app = create_app('testing')

    try:
        with app.app_context():
            config_manager: ConfigManager = app.injector.get(ConfigManager)
            scheduler: BackupScheduler = app.injector.get(BackupScheduler)

            # Ensure we start from a clean state by removing any pre-existing scheduled jobs
            for s in list(scheduler.get_scheduled_backups()):
                scheduler.cancel_backup(s['schedule_id'])
            assert len(scheduler.get_scheduled_backups()) == 0

            # Disable backups (should remain no jobs)
            config_manager.update_current_settings({'backup_settings': {'schedule': 'none'}})
            assert len(scheduler.get_scheduled_backups()) == 0

            # Enable an hourly backup and verify scheduling
            config_manager.update_current_settings({'backup_settings': {'schedule': 'hourly', 'time': '00:01'}})
            scheduled_after = scheduler.get_scheduled_backups()
            assert len(scheduled_after) >= 1
            assert any('Backup job for' in s.get('job_name', '') for s in scheduled_after)
    finally:
        try:
            with app.app_context():
                app.injector.get(BackupScheduler).stop()
        except Exception:
            pass
