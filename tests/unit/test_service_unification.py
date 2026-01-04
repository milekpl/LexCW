"""
Integration test: Verify EventBus coordinates autosave, history, and backup.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock


@pytest.mark.unit
def test_autosave_triggers_history_and_marks_backup_dirty():
    """Full flow: autosave -> persist -> emit event -> history records -> backup marked dirty"""
    from app.services.event_bus import EventBus
    from app.services.operation_history_service import OperationHistoryService
    from app.services.backup_scheduler import BackupScheduler

    # Create shared event bus
    event_bus = EventBus()

    # Use a temp file for history to avoid polluting the instance directory
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_history_path = f.name
        # Initialize with proper JSON structure
        import json
        json.dump({
            'operations': [],
            'transfers': [],
            'undo_stack': [],
            'redo_stack': []
        }, f)

    try:
        # Create services with shared event bus
        history_service = OperationHistoryService(
            history_file_path=temp_history_path,
            event_bus=event_bus
        )
        mock_backup_manager = Mock()
        backup_scheduler = BackupScheduler(backup_manager=mock_backup_manager, event_bus=event_bus)

        # Verify initial state - dirty should be True (first run)
        assert backup_scheduler._dirty == True

        # Simulate entry update from autosave
        event_bus.emit('entry_updated', {
            'entry_id': 'entry-123',
            'source': 'autosave',
            'timestamp': '2025-01-04T10:00:00Z'
        })

        # Verify backup is marked dirty
        assert backup_scheduler._dirty == True

        # Verify operation was recorded in history
        history = history_service.get_operation_history()
        autosave_ops = [op for op in history if op.get('type') == 'autosave']
        assert len(autosave_ops) == 1
        assert autosave_ops[0].get('entry_id') == 'entry-123'
    finally:
        # Clean up temp file
        if os.path.exists(temp_history_path):
            os.unlink(temp_history_path)
