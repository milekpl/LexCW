"""
Unit tests for OperationHistoryService.
"""

import json
import os
import tempfile
from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock
from app.services.operation_history_service import OperationHistoryService
from app.models.merge_split_operations import MergeSplitOperation, SenseTransfer


class TestOperationHistoryService:
    """Test OperationHistoryService functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.service = OperationHistoryService(history_file_path=self.temp_file.name)
        
        # Ensure the file exists with initial content
        with open(self.temp_file.name, 'w') as f:
            json.dump({
                'operations': [],
                'transfers': [],
                'undo_stack': [],
                'redo_stack': []
            }, f)
    
    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_record_operation(self):
        """Test recording an operation."""
        operation_data = {
            'entry_id': 'test_entry',
            'content': 'test content'
        }
        
        recorded_op = self.service.record_operation(
            operation_type='create',
            data=operation_data,
            entry_id='test_entry',
            user_id='test_user'
        )
        
        assert recorded_op.type == 'create'
        assert recorded_op.entry_id == 'test_entry'
        assert recorded_op.user_id == 'test_user'
        assert json.loads(recorded_op.data) == operation_data
        
        # Check that the operation was saved to the file
        history = self.service._read_history()
        assert len(history['operations']) == 1
        assert history['operations'][0]['type'] == 'create'
        
    def test_undo_redo_operations(self):
        """Test undo and redo functionality."""
        # Record an operation
        operation_data = {'test': 'data'}
        self.service.record_operation(
            operation_type='create',
            data=operation_data,
            entry_id='test_entry',
            user_id='test_user'
        )
        
        # Verify undo stack has one operation
        undo_stack = self.service.get_undo_stack()
        assert len(undo_stack) == 1
        
        # Perform undo
        undo_result = self.service.undo_last_operation()
        assert undo_result is not None
        assert undo_result['status'] == 'undone'
        
        # Check stacks after undo
        undo_stack = self.service.get_undo_stack()
        redo_stack = self.service.get_redo_stack()
        assert len(undo_stack) == 0
        assert len(redo_stack) == 1
        
        # Perform redo
        redo_result = self.service.redo_last_operation()
        assert redo_result is not None
        assert redo_result['status'] == 'completed'
        
        # Check stacks after redo
        undo_stack = self.service.get_undo_stack()
        redo_stack = self.service.get_redo_stack()
        assert len(undo_stack) == 1
        assert len(redo_stack) == 0
        
    def test_no_operations_to_undo(self):
        """Test undo when there are no operations to undo."""
        result = self.service.undo_last_operation()
        assert result is None
        
    def test_no_operations_to_redo(self):
        """Test redo when there are no operations to redo."""
        result = self.service.redo_last_operation()
        assert result is None
        
    def test_get_operation_history(self):
        """Test getting operation history."""
        # Record multiple operations
        self.service.record_operation(
            operation_type='create',
            data={'test': 'data1'},
            entry_id='entry1',
            user_id='user1'
        )
        
        self.service.record_operation(
            operation_type='update',
            data={'test': 'data2'},
            entry_id='entry2',
            user_id='user2'
        )
        
        # Get all operations
        all_ops = self.service.get_operation_history()
        assert len(all_ops) == 2
        
        # Get operations for specific entry
        entry_ops = self.service.get_operation_history(entry_id='entry1')
        assert len(entry_ops) == 1
        assert entry_ops[0]['entry_id'] == 'entry1'
        
    def test_record_merge_split_operation(self):
        """Test recording merge/split operations."""
        # Create a mock merge/split operation
        op = MergeSplitOperation(
            operation_type='split_entry',
            source_id='source_entry',
            user_id='test_user'
        )
        
        self.service.record_merge_split_operation(op)
        
        # Verify it was saved
        history = self.service._read_history()
        assert len(history['operations']) == 1
        assert history['operations'][0]['type'] == 'merge_split_split_entry'
        
    def test_record_transfer(self):
        """Test recording sense transfer."""
        # Create a mock transfer
        transfer = SenseTransfer(
            sense_id='sense1',
            original_entry_id='entry1',
            new_entry_id='entry2'
        )
        
        self.service.record_transfer(transfer)
        
        # Verify it was saved
        history = self.service._read_history()
        assert len(history['transfers']) == 1
        assert history['transfers'][0]['sense_id'] == 'sense1'
        
    def test_clear_history(self):
        """Test clearing history."""
        # Add some operations
        self.service.record_operation(
            operation_type='create',
            data={'test': 'data'},
            entry_id='entry1'
        )

        # Verify operations exist
        history = self.service._read_history()
        assert len(history['operations']) > 0

        # Clear history
        self.service.clear_history()

        # Verify history is cleared
        history = self.service._read_history()
        assert len(history['operations']) == 0
        assert len(history['transfers']) == 0
        assert len(history['undo_stack']) == 0
        assert len(history['redo_stack']) == 0

    def test_listens_to_entry_updated_event(self):
        """OperationHistoryService should record operations when entry_updated is emitted."""
        from app.services.operation_history_service import OperationHistoryService
        from unittest.mock import Mock

        mock_event_bus = Mock()
        service = OperationHistoryService(history_file_path=self.temp_file.name, event_bus=mock_event_bus)

        # Verify on() was called with 'entry_updated' and the handler
        mock_event_bus.on.assert_called_with('entry_updated', service._on_entry_updated)

    def test_on_entry_updated_handler_records_autosave(self):
        """_on_entry_updated handler should record autosave operation."""
        from app.services.operation_history_service import OperationHistoryService
        from unittest.mock import Mock

        mock_event_bus = Mock()
        service = OperationHistoryService(history_file_path=self.temp_file.name, event_bus=mock_event_bus)

        # Call the handler with sample data
        test_data = {'entry_id': 'test-entry-123', 'changes': {'field': 'value'}}
        service._on_entry_updated(test_data)

        # Verify operation was recorded with autosave type
        history = service._read_history()
        autosave_ops = [op for op in history['operations'] if op.get('type') == 'autosave']
        assert len(autosave_ops) == 1
        assert autosave_ops[0]['entry_id'] == 'test-entry-123'
        assert autosave_ops[0]['user_id'] == 'autosave'

    def test_no_event_bus_subscription_without_event_bus(self):
        """Service should work without event_bus parameter."""
        from app.services.operation_history_service import OperationHistoryService

        service = OperationHistoryService(history_file_path=self.temp_file.name)

        # Verify no event_bus attribute when not provided
        assert service.event_bus is None
