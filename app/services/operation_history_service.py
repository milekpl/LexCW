"""
Service for persisting and retrieving comprehensive operation history for undo/redo functionality.
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.merge_split_operations import MergeSplitOperation, SenseTransfer
from app.models.backup_models import OperationHistory as OperationHistoryModel

class OperationHistoryService:
    """
    Enhanced service for persisting and retrieving comprehensive operation history
    supporting undo/redo functionality for all editor operations including create,
    update, delete, merge, and split operations on dictionary entries.
    """

    def __init__(self, history_file_path: str = 'instance/operation_history.json', max_history: int = 100):
        self.history_file_path = history_file_path
        self.max_history = max_history  # Maximum number of operations to keep in history
        self._ensure_history_file_exists()

    def _ensure_history_file_exists(self):
        if not os.path.exists(os.path.dirname(self.history_file_path)):
            os.makedirs(os.path.dirname(self.history_file_path))
        if not os.path.exists(self.history_file_path):
            with open(self.history_file_path, 'w') as f:
                json.dump({
                    'operations': [],
                    'transfers': [],
                    'undo_stack': [],
                    'redo_stack': []
                }, f)

    def _read_history(self):
        with open(self.history_file_path, 'r') as f:
            data = json.load(f)
        # Ensure backward-compatible keys exist
        data.setdefault('operations', [])
        data.setdefault('transfers', [])
        data.setdefault('undo_stack', [])
        data.setdefault('redo_stack', [])
        return data

    def _write_history(self, data):
        with open(self.history_file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def record_operation(self, operation_type: str, data: Dict[str, Any], entry_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Record an operation in the history for potential undo/redo.

        Args:
            operation_type: Type of operation ('create', 'update', 'delete', 'merge', 'split')
            data: Dictionary containing operation details needed for undo/redo
            entry_id: ID of the affected entry (if applicable)
            user_id: ID of the user who performed the operation
        """
        history = self._read_history()

        # Create an OperationHistory model instance
        operation = OperationHistoryModel(
            type_=operation_type,
            data=json.dumps(data),
            entry_id=entry_id,
            user_id=user_id
        )

        # Add to operations list
        history['operations'].append(operation.to_dict())

        # Maintain history size limit
        if len(history['operations']) > self.max_history:
            history['operations'] = history['operations'][-self.max_history:]

        # Add to undo stack
        history['undo_stack'].append(operation.to_dict())

        # Clear redo stack since we're adding a new operation
        history['redo_stack'] = []

        self._write_history(history)

        # Return the recorded operation
        return operation

    def record_merge_split_operation(self, operation: MergeSplitOperation):
        """
        Record a merge/split operation in the history (maintaining backward compatibility).
        """
        history = self._read_history()
        history['operations'].append({
            **operation.to_dict(),
            'type': f'merge_split_{operation.operation_type}'  # Add type for classification
        })
        self._write_history(history)

    # Backwards-compatible aliases for older callers/tests
    def save_operation(self, operation: MergeSplitOperation):
        """Alias for recording a merge/split operation (backwards compatibility)."""
        return self.record_merge_split_operation(operation)

    def record_transfer(self, transfer: SenseTransfer):
        """
        Record a sense transfer in the history (maintaining backward compatibility).
        """
        history = self._read_history()
        history['transfers'].append(transfer.to_dict())
        self._write_history(history)

    def save_transfer(self, transfer: SenseTransfer):
        """Alias for recording a sense transfer (backwards compatibility)."""
        return self.record_transfer(transfer)

    def undo_last_operation(self) -> Optional[Dict[str, Any]]:
        """
        Undo the last operation in the history.

        Returns:
            Dictionary containing undo information or None if no operations to undo
        """
        history = self._read_history()

        if not history['undo_stack']:
            return None

        # Move last operation from undo to redo stack
        last_operation = history['undo_stack'].pop()

        # Mark the operation as undone in the main operations list
        for op in history['operations']:
            if op['id'] == last_operation['id']:
                op['status'] = 'undone'
                op['timestamp_undone'] = datetime.utcnow().isoformat()

        history['redo_stack'].append(last_operation)

        # Update the status of the operation to indicate it was undone
        last_operation['status'] = 'undone'
        last_operation['timestamp_undone'] = datetime.utcnow().isoformat()

        self._write_history(history)

        return last_operation

    def redo_last_operation(self) -> Optional[Dict[str, Any]]:
        """
        Redo the last undone operation.

        Returns:
            Dictionary containing redo information or None if no operations to redo
        """
        history = self._read_history()

        if not history['redo_stack']:
            return None

        # Move last operation from redo to undo stack
        last_operation = history['redo_stack'].pop()

        # Mark the operation as redone in the main operations list
        for op in history['operations']:
            if op['id'] == last_operation['id']:
                op['status'] = 'completed'  # Back to completed
                if 'timestamp_undone' in op:
                    del op['timestamp_undone']

        history['undo_stack'].append(last_operation)

        # Update the status of the operation to indicate it was redone
        last_operation['status'] = 'completed'
        last_operation['timestamp_redone'] = datetime.utcnow().isoformat()

        self._write_history(history)

        return last_operation

    def get_operation_history(self, entry_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get operation history, optionally filtered by entry ID.

        Args:
            entry_id: Optional entry ID to filter operations

        Returns:
            List of operation history entries
        """
        history = self._read_history()

        operations = history['operations']

        if entry_id:
            operations = [op for op in operations if op.get('entry_id') == entry_id]

        # Sort by timestamp, newest first
        operations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return operations

    def get_undo_stack(self) -> List[Dict[str, Any]]:
        """
        Get the undo stack (operations that can be undone).

        Returns:
            List of operations in the undo stack
        """
        history = self._read_history()
        return history['undo_stack']

    def get_redo_stack(self) -> List[Dict[str, Any]]:
        """
        Get the redo stack (operations that can be redone).

        Returns:
            List of operations in the redo stack
        """
        history = self._read_history()
        return history['redo_stack']

    def clear_history(self):
        """
        Clear all operation history and reset stacks.
        """
        with open(self.history_file_path, 'w') as f:
            json.dump({
                'operations': [],
                'transfers': [],
                'undo_stack': [],
                'redo_stack': []
            }, f, indent=4)

    def get_all_merge_split_operations(self) -> List[MergeSplitOperation]:
        """
        Get all merge/split operations (maintaining backward compatibility).
        """
        history = self._read_history()
        merge_split_ops = []
        for op in history['operations']:
            if op.get('type', '').startswith('merge_split_'):
                # Create a basic MergeSplitOperation from the stored data
                # Note: This is a best-effort approach since the original format may differ
                try:
                    # Extract the ID and pass it as id_ parameter
                    op_id = op.get('id')
                    merge_split_ops.append(MergeSplitOperation(
                        operation_type=op.get('operation_type', 'merge_split'),
                        source_id=op.get('source_id', ''),
                        target_id=op.get('target_id'),
                        id_=op_id,  # Pass ID with underscore as expected by BaseModel
                        **{k: v for k, v in op.items() if k not in ['operation_type', 'source_id', 'target_id', 'id', 'type']}
                    ))
                except:
                    # If there's a problem reconstructing the object, skip it
                    continue
        return merge_split_ops

    # Backwards-compatible alias
    def get_all_operations(self) -> List[MergeSplitOperation]:
        """Alias for getting all merge/split operations (backwards compatibility)."""
        return self.get_all_merge_split_operations()

    def get_all_transfers(self) -> List[SenseTransfer]:
        """
        Get all sense transfers (maintaining backward compatibility).
        """
        history = self._read_history()
        return [SenseTransfer.from_dict(t) for t in history['transfers']]
