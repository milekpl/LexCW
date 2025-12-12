"""
Service for persisting and retrieving merge/split operation history.
"""

import json
import os
from typing import List
from app.models.merge_split_operations import MergeSplitOperation, SenseTransfer

class OperationHistoryService:
    """
    Service for persisting and retrieving merge/split operation history.
    """

    def __init__(self, history_file_path: str = 'instance/merge_split_history.json'):
        self.history_file_path = history_file_path
        self._ensure_history_file_exists()

    def _ensure_history_file_exists(self):
        if not os.path.exists(os.path.dirname(self.history_file_path)):
            os.makedirs(os.path.dirname(self.history_file_path))
        if not os.path.exists(self.history_file_path):
            with open(self.history_file_path, 'w') as f:
                json.dump({'operations': [], 'transfers': []}, f)

    def _read_history(self):
        with open(self.history_file_path, 'r') as f:
            return json.load(f)

    def _write_history(self, data):
        with open(self.history_file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def save_operation(self, operation: MergeSplitOperation):
        history = self._read_history()
        history['operations'].append(operation.to_dict())
        self._write_history(history)

    def save_transfer(self, transfer: SenseTransfer):
        history = self._read_history()
        history['transfers'].append(transfer.to_dict())
        self._write_history(history)

    def get_all_operations(self) -> List[MergeSplitOperation]:
        history = self._read_history()
        return [MergeSplitOperation.from_dict(op) for op in history['operations']]

    def get_all_transfers(self) -> List[SenseTransfer]:
        history = self._read_history()
        return [SenseTransfer.from_dict(t) for t in history['transfers']]
