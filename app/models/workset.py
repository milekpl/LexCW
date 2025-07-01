#!/usr/bin/env python3

"""
Workset models for query-based bulk operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


@dataclass
class QueryFilter:
    """Individual filter criteria for workset queries."""
    field: str
    operator: str  # equals, starts_with, contains, in, gt, lt, etc.
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'field': self.field,
            'operator': self.operator,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QueryFilter:
        return cls(
            field=data['field'],
            operator=data['operator'],
            value=data['value']
        )


@dataclass
class WorksetQuery:
    """Query criteria for creating and updating worksets."""
    filters: List[QueryFilter] = field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: str = 'asc'  # asc or desc
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filters': [f.to_dict() for f in self.filters],
            'sort_by': self.sort_by,
            'sort_order': self.sort_order
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorksetQuery:
        filters = [QueryFilter.from_dict(f) for f in data.get('filters', [])]
        return cls(
            filters=filters,
            sort_by=data.get('sort_by'),
            sort_order=data.get('sort_order', 'asc')
        )


@dataclass
class Workset:
    """Workset containing filtered collection of entries."""
    id: str
    name: str
    query: WorksetQuery
    total_entries: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    entries: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'query': self.query.to_dict(),
            'total_entries': self.total_entries,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'entries': self.entries
        }
    
    @classmethod
    def create(cls, name: str, query: WorksetQuery) -> Workset:
        """Create a new workset with generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            query=query
        )


@dataclass
class BulkOperation:
    """Bulk operation configuration for workset processing."""
    operation: str  # update_field, delete_field, add_field
    field: str
    value: Optional[Any] = None
    apply_to: str = 'all'  # all or filtered
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation': self.operation,
            'field': self.field,
            'value': self.value,
            'apply_to': self.apply_to
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BulkOperation:
        return cls(
            operation=data['operation'],
            field=data['field'],
            value=data.get('value'),
            apply_to=data.get('apply_to', 'all')
        )


@dataclass
class WorksetProgress:
    """Progress tracking for long-running workset operations."""
    status: str  # pending, running, completed, failed
    progress: float = 0.0  # percentage 0-100
    total_items: int = 0
    completed_items: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'progress': self.progress,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'error_message': self.error_message
        }
