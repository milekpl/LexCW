"""
Data models for the backup system.

This module defines the models for:
- Backup metadata storage
- Scheduled backup configurations
- Operation history tracking for undo/redo
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from datetime import datetime
import uuid
from app.models.base import BaseModel

if TYPE_CHECKING:
    pass


class Backup(BaseModel):
    """
    Model representing database backup metadata.
    
    Tracks information about BaseX database backups including file location,
    timestamp, type, and validation status.
    """
    
    def __init__(
        self,
        db_name: str,
        type_: str,
        file_path: str,
        file_size: int,
        description: Optional[str] = None,
        status: str = 'created',
        restore_timestamp: Optional[datetime] = None,
        restore_status: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Initialize a backup record.

        Args:
            db_name: Name of the database backed up
            type_: Type of backup ('full', 'incremental', 'manual')
            file_path: Path to the backup file
            file_size: Size of the backup file in bytes
            description: Optional description of the backup
            status: Status of the backup ('created', 'completed', 'failed')
            restore_timestamp: When backup was restored (if applicable)
            restore_status: Status of the last restore ('successful', 'failed')
            **kwargs: Additional attributes to set on the backup
        """
        super().__init__(**kwargs)
        
        self.db_name = db_name
        self.type = type_
        self.file_path = file_path
        self.file_size = file_size
        self.description = description
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.status = status
        self.restore_timestamp = restore_timestamp
        self.restore_status = restore_status

    def to_dict(self) -> Dict[str, Any]:
        """Convert backup record to dictionary for serialization."""
        result = super().to_dict()
        result['db_name'] = self.db_name
        result['type'] = self.type
        result['file_path'] = self.file_path
        result['file_size'] = self.file_size
        result['description'] = self.description
        result['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        result['status'] = self.status
        result['restore_timestamp'] = self.restore_timestamp.isoformat() if self.restore_timestamp else None
        result['restore_status'] = self.restore_status
        # Friendly display name: prefer description, else filename, else timestamp
        try:
            if self.description and str(self.description).strip():
                result['display_name'] = str(self.description).strip()
            else:
                from pathlib import Path
                if self.file_path:
                    result['display_name'] = Path(self.file_path).name
                else:
                    result['display_name'] = result.get('timestamp') or ''
        except Exception:
            result['display_name'] = result.get('timestamp') or ''
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Backup":
        """Create a Backup instance from a dictionary."""
        # Extract the required arguments for initialization
        db_name = data.pop('db_name')
        type_ = data.pop('type')
        file_path = data.pop('file_path')
        file_size = data.pop('file_size')
        
        # Convert timestamp from ISO format string to datetime object
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if 'restore_timestamp' in data and isinstance(data['restore_timestamp'], str):
            data['restore_timestamp'] = datetime.fromisoformat(data['restore_timestamp'])

        return cls(
            db_name=db_name,
            type_=type_,
            file_path=file_path,
            file_size=file_size,
            **data
        )


class ScheduledBackup(BaseModel):
    """
    Model representing scheduled backup configurations.
    
    Contains information about recurring backup schedules including 
    frequency, timing, and status.
    """
    
    def __init__(
        self,
        db_name: str,
        interval: str,
        time_: str,
        type_: str,
        next_run: datetime,
        active: bool = True,
        last_run: Optional[datetime] = None,
        last_status: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Initialize a scheduled backup record.

        Args:
            db_name: Name of database to backup
            interval: Frequency of backup ('hourly', 'daily', 'weekly')
            time_: Time specification in cron format or HH:MM
            type_: Type of backup ('full', 'incremental')
            next_run: When next backup is scheduled
            active: Whether the schedule is active
            last_run: When backup was last executed
            last_status: Result of last backup ('success', 'failed', 'skipped')
            **kwargs: Additional attributes to set on the scheduled backup
        """
        super().__init__(**kwargs)
        
        self.db_name = db_name
        self.interval = interval
        self.time = time_
        self.type = type_
        self.next_run = next_run
        self.active = active
        self.last_run = last_run
        self.last_status = last_status

    def to_dict(self) -> Dict[str, Any]:
        """Convert scheduled backup record to dictionary for serialization."""
        result = super().to_dict()
        result['db_name'] = self.db_name
        result['interval'] = self.interval
        result['time'] = self.time
        result['type'] = self.type
        result['next_run'] = self.next_run.isoformat() if self.next_run else None
        result['active'] = self.active
        result['last_run'] = self.last_run.isoformat() if self.last_run else None
        result['last_status'] = self.last_status
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledBackup":
        """Create a ScheduledBackup instance from a dictionary."""
        # Extract the required arguments for initialization
        db_name = data.pop('db_name')
        interval = data.pop('interval')
        time_ = data.pop('time')
        type_ = data.pop('type')
        next_run = data.pop('next_run')
        
        # Convert datetime strings to datetime objects
        if isinstance(next_run, str):
            next_run = datetime.fromisoformat(next_run)
        if 'last_run' in data and isinstance(data['last_run'], str):
            data['last_run'] = datetime.fromisoformat(data['last_run'])

        return cls(
            db_name=db_name,
            interval=interval,
            time_=time_,
            type_=type_,
            next_run=next_run,
            **data
        )


class OperationHistory(BaseModel):
    """
    Model representing editor operation history for undo/redo functionality.
    
    Tracks user actions that can be undone/redone such as create, update, delete,
    merge, and split operations on dictionary entries.
    """
    
    def __init__(
        self,
        type_: str,
        data: str,
        entry_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: str = 'completed',
        **kwargs: Any
    ):
        """
        Initialize an operation history record.

        Args:
            type_: Type of operation ('create', 'update', 'delete', 'merge', 'split')
            data: JSON string containing operation details for undo/redo
            entry_id: ID of the affected entry (if applicable)
            user_id: ID of the user who performed the operation
            status: Status of the operation ('completed', 'undone', 'aborted')
            **kwargs: Additional attributes to set on the operation history
        """
        super().__init__(**kwargs)
        
        self.type = type_
        self.data = data
        self.entry_id = entry_id
        self.user_id = user_id
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """Convert operation history record to dictionary for serialization."""
        result = super().to_dict()
        result['type'] = self.type
        result['data'] = self.data
        result['entry_id'] = self.entry_id
        result['user_id'] = self.user_id
        result['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        result['status'] = self.status
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationHistory":
        """Create an OperationHistory instance from a dictionary."""
        # Extract the required arguments for initialization
        type_ = data.pop('type')
        data_json = data.pop('data')
        
        # Convert timestamp from ISO format string to datetime object
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])

        return cls(
            type_=type_,
            data=data_json,
            **data
        )
