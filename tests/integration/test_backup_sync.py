
import pytest
from flask.testing import FlaskClient
from app.config_manager import ConfigManager
from app.services.backup_scheduler import BackupScheduler

@pytest.mark.integration
def test_backup_schedule_updates_on_settings_change(client: FlaskClient):
    """Test that updating settings triggers a scheduler update."""
    app = client.application
    
    # Get services
    config_manager = app.injector.get(ConfigManager)
    scheduler = app.injector.get(BackupScheduler)
    
    # Ensure scheduler is started
    if not scheduler._running:
        scheduler.start()
        
    # Check initial state (should be daily from defaults/startup)
    initial_backups = scheduler.get_scheduled_backups()
    print(f"Initial backups: {initial_backups}")
    
    # Update settings to 'hourly'
    new_settings = {
        'backup_settings': {
            'schedule': 'hourly',
            'time': '15:30',
            'directory': '/tmp/backup_test',
            'retention': 5,
            'compression': True
        }
    }
    
    print("Updating settings to hourly...")
    config_manager.update_current_settings(new_settings)
    
    # Verify scheduler was updated
    updated_backups = scheduler.get_scheduled_backups()
    print(f"Updated backups: {updated_backups}")
    
    assert len(updated_backups) > 0, "Scheduler should have active jobs"
    
    # Check if the trigger is correct for hourly
    # The scheduler may contain multiple jobs (other projects); find any job that matches our expected minute
    matching_jobs = [j for j in updated_backups if ("minute='30'" in str(j['trigger'])) or ("minute=\"30\"" in str(j['trigger']))]
    print(f"Matching jobs with minute=30: {matching_jobs}")
    assert matching_jobs, f"No scheduled job found with minute=30 in updated backups: {updated_backups}"

    job_info = matching_jobs[0]
    trigger_str = str(job_info['trigger'])
    print(f"Trigger string: {trigger_str}")

    # Assert that the trigger includes minute=30 and hour is wildcard
    assert ("minute='30'" in trigger_str) or ("minute=\"30\"" in trigger_str)
    assert ("hour='*'" in trigger_str) or ("hour=\"*\"" in trigger_str)

    # Remember the schedule id for the job we care about
    my_schedule_id = job_info['schedule_id']

    # Now update to 'none' to disable
    disable_settings = {
        'backup_settings': {
            'schedule': 'none',
            'directory': '/tmp/backup_test'
        }
    }
    print("Disabling backup schedule...")
    config_manager.update_current_settings(disable_settings)
    
    final_backups = scheduler.get_scheduled_backups()
    print(f"Final backups: {final_backups}")
    
    # Ensure the job for our test DB was removed (other projects may still have jobs)
    assert not any(b.get('schedule_id') == my_schedule_id for b in final_backups), "Scheduled job for test DB should be removed after disabling"
