from types import SimpleNamespace
from unittest.mock import Mock

from app.config_manager import ConfigManager


def test_update_current_settings_triggers_scheduler_sync(app, test_project, monkeypatch):
    """Integration: ensure updating backup_settings calls BackupScheduler.sync_backup_schedule.

    Uses the real Flask app and DB (created by `test_project`).
    """
    cm = ConfigManager(app.instance_path)

    with app.app_context():
        # attach a mock scheduler via injector (use monkeypatch to restore automatically)
        mock_scheduler = Mock()
        from types import SimpleNamespace
        monkeypatch.setattr(app, 'injector', SimpleNamespace(get=lambda cls: mock_scheduler), raising=True)

        new_backup = {
            'schedule': 'hourly',
            'time': '12:15',
            'directory': '/tmp/sync_test'
        }

        # Call update_current_settings and assert sync called with the test project's DB name
        cm.update_current_settings({'backup_settings': new_backup})

        assert mock_scheduler.sync_backup_schedule.called
        mock_scheduler.sync_backup_schedule.assert_called_once_with(test_project.basex_db_name, new_backup)

        # Restore original injector if we replaced it manually
        try:
            if 'original_injector' in locals():
                app.injector = original_injector
        except Exception:
            pass
