import pytest
from app.services.dictionary_service import DictionaryService
from app.services.operation_history_service import OperationHistoryService
from app.models.entry import Entry
from datetime import datetime

class TestDashboardIntegration:
    @pytest.fixture
    def dict_service(self, app):
        return app.injector.get(DictionaryService)

    @pytest.fixture
    def history_service(self, app):
        return app.injector.get(OperationHistoryService)

    def test_activity_recording(self, dict_service, history_service):
        # 1. Check initial activity
        initial_activity = dict_service.get_recent_activity()
        
        # 2. Perform operations
        test_entry_id = f"test_activity_{datetime.now().strftime('%H%M%S')}"
        from app.models.sense import Sense
        entry = Entry(
            id_=test_entry_id, 
            lexical_unit={"pl": "test activity"},
            senses=[Sense(id="test_sense_1", glosses={"pl": "test gloss"})]
        )
        
        dict_service.create_entry(entry)
        
        # 3. Verify activity recorded
        activities = dict_service.get_recent_activity()
        assert len(activities) > len(initial_activity)
        assert activities[0]['action'] == 'Entry Created'
        assert test_entry_id in activities[0]['description']
        
        # 4. Perform update
        entry.lexical_unit = {"pl": "updated activity"}
        dict_service.update_entry(entry)
        
        activities = dict_service.get_recent_activity()
        assert activities[0]['action'] == 'Entry Updated'
        assert test_entry_id in activities[0]['description']
        
        # 5. Perform delete
        dict_service.delete_entry(test_entry_id)
        
        activities = dict_service.get_recent_activity()
        assert activities[0]['action'] == 'Entry Deleted'
        assert test_entry_id in activities[0]['description']

    def test_system_status_data(self, dict_service):
        status = dict_service.get_system_status()
        
        assert 'db_connected' in status
        assert 'last_backup' in status
        assert 'next_backup' in status
        assert 'total_backups' in status
        assert 'backup_count' in status
        assert 'storage_percent' in status
        
        # backup_count and total_backups should match
        assert status['backup_count'] == status['total_backups']
        
        # Should have reasonable defaults even if no backups
        assert status['last_backup'] in ['Never', 'N/A'] or status['last_backup'].startswith('202')
        assert status['next_backup'] in ['Not scheduled', 'Error'] or status['next_backup'].startswith('202')
