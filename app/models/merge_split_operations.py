"""
Data models for merge and split operations in LIFT editors.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from datetime import datetime
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.entry import Entry
    from app.models.sense import Sense

class MergeSplitOperation(BaseModel):
    """
    Represents a merge or split operation on dictionary entries.

    Attributes:
        operation_type: Type of operation ('split_entry', 'merge_entries', 'merge_senses')
        source_id: ID of the source entry
        target_id: ID of the target entry (optional for split operations)
        sense_ids: List of sense IDs involved in the operation
        timestamp: When the operation was created
        user_id: ID of the user who initiated the operation
        status: Current status of the operation ('pending', 'completed', 'failed')
        metadata: Additional operation metadata
    """

    def __init__(
        self,
        operation_type: str,
        source_id: str,
        target_id: Optional[str] = None,
        sense_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Initialize a merge/split operation.

        Args:
            operation_type: Type of operation ('split_entry', 'merge_entries', 'merge_senses')
            source_id: ID of the source entry
            target_id: ID of the target entry (optional for split operations)
            sense_ids: List of sense IDs involved in the operation
            user_id: ID of the user who initiated the operation
            **kwargs: Additional attributes to set on the operation
        """
        super().__init__(**kwargs)

        if operation_type not in ['split_entry', 'merge_entries', 'merge_senses']:
            raise ValueError(f"Invalid operation_type: {operation_type}")

        self.operation_type: str = operation_type
        self.source_id: str = source_id
        self.target_id: Optional[str] = target_id
        self.sense_ids: List[str] = sense_ids or []
        self.timestamp: datetime = kwargs.get('timestamp', datetime.now())
        self.user_id: Optional[str] = user_id
        self.status: str = kwargs.get('status', 'pending')
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the operation to a dictionary for serialization.

        Returns:
            Dictionary representation of the operation
        """
        result = super().to_dict()
        result['operation_type'] = self.operation_type
        result['source_id'] = self.source_id
        result['target_id'] = self.target_id
        result['sense_ids'] = self.sense_ids
        result['timestamp'] = self.timestamp.isoformat()
        result['user_id'] = self.user_id
        result['status'] = self.status
        result['metadata'] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MergeSplitOperation":
        """
        Create a MergeSplitOperation instance from a dictionary.
        """
        # Extract positional arguments for __init__
        operation_type = data.pop("operation_type")
        source_id = data.pop("source_id")

        # Convert timestamp from ISO format string to datetime object
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Create instance
        return cls(
            operation_type=operation_type,
            source_id=source_id,
            **data
        )

    def mark_completed(self) -> None:
        """Mark the operation as completed."""
        self.status = 'completed'
        self.metadata['completed_at'] = datetime.now().isoformat()

    def mark_failed(self, error_message: str) -> None:
        """Mark the operation as failed with an error message."""
        self.status = 'failed'
        self.metadata['error_message'] = error_message
        self.metadata['failed_at'] = datetime.now().isoformat()

class SenseTransfer(BaseModel):
    """
    Represents the transfer of a sense from one entry to another.

    Attributes:
        sense_id: ID of the sense being transferred
        original_entry_id: ID of the original entry
        new_entry_id: ID of the new entry
        transfer_date: When the transfer occurred
        metadata: Additional transfer metadata
    """

    def __init__(
        self,
        sense_id: str,
        original_entry_id: str,
        new_entry_id: str,
        **kwargs: Any
    ):
        """
        Initialize a sense transfer record.

        Args:
            sense_id: ID of the sense being transferred
            original_entry_id: ID of the original entry
            new_entry_id: ID of the new entry
            **kwargs: Additional attributes to set on the transfer
        """
        super().__init__(**kwargs)

        self.sense_id: str = sense_id
        self.original_entry_id: str = original_entry_id
        self.new_entry_id: str = new_entry_id
        self.transfer_date: datetime = kwargs.get('transfer_date', datetime.now())
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transfer to a dictionary for serialization.

        Returns:
            Dictionary representation of the transfer
        """
        result = super().to_dict()
        result['sense_id'] = self.sense_id
        result['original_entry_id'] = self.original_entry_id
        result['new_entry_id'] = self.new_entry_id
        result['transfer_date'] = self.transfer_date.isoformat()
        result['metadata'] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SenseTransfer":
        """
        Create a SenseTransfer instance from a dictionary.
        """
        # Extract positional arguments for __init__
        sense_id = data.pop("sense_id")
        original_entry_id = data.pop("original_entry_id")
        new_entry_id = data.pop("new_entry_id")

        # Convert transfer_date from ISO format string to datetime object
        if 'transfer_date' in data and isinstance(data['transfer_date'], str):
            data['transfer_date'] = datetime.fromisoformat(data['transfer_date'])

        # Create instance
        return cls(
            sense_id=sense_id,
            original_entry_id=original_entry_id,
            new_entry_id=new_entry_id,
            **data
        )

class MergeSplitResult(BaseModel):
    """
    Represents the result of a merge or split operation.

    Attributes:
        operation_id: ID of the operation
        success: Whether the operation was successful
        source_entry: Source entry after operation
        target_entry: Target entry after operation (if applicable)
        transferred_senses: List of transferred sense IDs
        conflicts_resolved: Number of conflicts resolved
        warnings: List of warning messages
        errors: List of error messages
    """

    def __init__(
        self,
        operation_id: str,
        success: bool,
        source_entry: Optional[Entry] = None,
        target_entry: Optional[Entry] = None,
        **kwargs: Any
    ):
        """
        Initialize a merge/split operation result.

        Args:
            operation_id: ID of the operation
            success: Whether the operation was successful
            source_entry: Source entry after operation
            target_entry: Target entry after operation (if applicable)
            **kwargs: Additional attributes to set on the result
        """
        super().__init__(**kwargs)

        self.operation_id: str = operation_id
        self.success: bool = success
        self.source_entry: Optional[Entry] = source_entry
        self.target_entry: Optional[Entry] = target_entry
        self.transferred_senses: List[str] = kwargs.get('transferred_senses', [])
        self.conflicts_resolved: int = kwargs.get('conflicts_resolved', 0)
        self.warnings: List[str] = kwargs.get('warnings', [])
        self.errors: List[str] = kwargs.get('errors', [])
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result to a dictionary for serialization.

        Returns:
            Dictionary representation of the result
        """
        result = super().to_dict()
        result['operation_id'] = self.operation_id
        result['success'] = self.success
        result['transferred_senses'] = self.transferred_senses
        result['conflicts_resolved'] = self.conflicts_resolved
        result['warnings'] = self.warnings
        result['errors'] = self.errors
        result['metadata'] = self.metadata

        if self.source_entry:
            result['source_entry'] = self.source_entry.to_dict()
        if self.target_entry:
            result['target_entry'] = self.target_entry.to_dict()

        return result

    def add_warning(self, warning_message: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning_message)

    def add_error(self, error_message: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error_message)