#!/usr/bin/env python3

"""
Workset service for managing query-based entry collections.
Implements workbench-oriented bulk operations with performance optimization.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging
import time
from datetime import datetime

from app.models.workset import Workset, WorksetQuery, BulkOperation, WorksetProgress
from app.api.entries import get_dictionary_service

logger = logging.getLogger(__name__)


class WorksetService:
    """Service for managing worksets and bulk operations."""
    
    def __init__(self):
        self._worksets: Dict[str, Workset] = {}
        self._progress_tracker: Dict[str, WorksetProgress] = {}
    
    def create_workset(self, name: str, query: WorksetQuery) -> Workset:
        """Create a new workset from query criteria."""
        try:
            workset = Workset.create(name, query)
            
            # Execute query to get matching entries
            dictionary_service = get_dictionary_service()
            entries, total_count = self._execute_query(query, dictionary_service)
            
            workset.entries = entries
            workset.total_entries = total_count
            
            # Store workset
            self._worksets[workset.id] = workset
            
            logger.info(f"Created workset '{name}' with {total_count} entries")
            return workset
            
        except Exception as e:
            logger.error(f"Failed to create workset '{name}': {e}")
            raise
    
    def get_workset(self, workset_id: str, limit: int = 50, offset: int = 0) -> Optional[Workset]:
        """Get workset with pagination."""
        try:
            workset = self._worksets.get(workset_id)
            if not workset:
                return None
            
            # Apply pagination to entries
            paginated_entries = workset.entries[offset:offset + limit]
            
            # Create a copy with paginated entries
            result = Workset(
                id=workset.id,
                name=workset.name,
                query=workset.query,
                total_entries=workset.total_entries,
                created_at=workset.created_at,
                updated_at=workset.updated_at,
                entries=paginated_entries
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get workset {workset_id}: {e}")
            return None
    
    def update_workset_query(self, workset_id: str, query: WorksetQuery) -> Optional[int]:
        """Update workset query criteria and refresh entries."""
        try:
            workset = self._worksets.get(workset_id)
            if not workset:
                return None
            
            # Update query
            workset.query = query
            workset.updated_at = datetime.now()
            
            # Re-execute query
            dictionary_service = get_dictionary_service()
            entries, total_count = self._execute_query(query, dictionary_service)
            
            workset.entries = entries
            workset.total_entries = total_count
            
            logger.info(f"Updated workset {workset_id} query, now has {total_count} entries")
            return total_count
            
        except Exception as e:
            logger.error(f"Failed to update workset {workset_id}: {e}")
            return None
    
    def delete_workset(self, workset_id: str) -> bool:
        """Delete a workset."""
        try:
            if workset_id in self._worksets:
                del self._worksets[workset_id]
                # Clean up progress tracking
                if workset_id in self._progress_tracker:
                    del self._progress_tracker[workset_id]
                logger.info(f"Deleted workset {workset_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete workset {workset_id}: {e}")
            return False
    
    def bulk_update_workset(self, workset_id: str, operation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply bulk operations to workset entries."""
        try:
            workset = self._worksets.get(workset_id)
            if not workset:
                return None
            
            operation = BulkOperation.from_dict(operation_data)
            
            # Initialize progress tracking
            progress = WorksetProgress(
                status='running',
                total_items=workset.total_entries
            )
            self._progress_tracker[workset_id] = progress
            
            # Simulate bulk operation (in real implementation, this would be async)
            updated_count = self._perform_bulk_operation(workset, operation)
            
            # Update progress
            progress.status = 'completed'
            progress.progress = 100.0
            progress.completed_items = updated_count
            
            task_id = f"bulk_{workset_id}_{int(time.time())}"
            
            logger.info(f"Bulk operation on workset {workset_id} updated {updated_count} entries")
            
            return {
                'task_id': task_id,
                'updated_count': updated_count
            }
            
        except Exception as e:
            logger.error(f"Failed bulk update on workset {workset_id}: {e}")
            # Mark as failed
            if workset_id in self._progress_tracker:
                self._progress_tracker[workset_id].status = 'failed'
                self._progress_tracker[workset_id].error_message = str(e)
            return None
    
    def get_workset_progress(self, workset_id: str) -> Optional[Dict[str, Any]]:
        """Get progress of bulk operations on workset."""
        try:
            progress = self._progress_tracker.get(workset_id)
            if progress:
                return progress.to_dict()
            
            # If no active operation, return default status
            workset = self._worksets.get(workset_id)
            if workset:
                return {
                    'status': 'completed',
                    'progress': 100.0,
                    'total_items': workset.total_entries,
                    'completed_items': workset.total_entries
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get progress for workset {workset_id}: {e}")
            return None
    
    def validate_query(self, query: WorksetQuery) -> Dict[str, Any]:
        """Validate query syntax and estimate performance."""
        try:
            errors = []
            
            # Validate filters
            for filter_obj in query.filters:
                if not filter_obj.field:
                    errors.append("Filter field cannot be empty")
                
                if filter_obj.operator not in ['equals', 'starts_with', 'contains', 'in', 'gt', 'lt']:
                    errors.append(f"Invalid operator: {filter_obj.operator}")
            
            # Validate sort fields
            if query.sort_by and query.sort_by not in ['lexical_unit', 'pos', 'created_at', 'updated_at']:
                errors.append(f"Invalid sort field: {query.sort_by}")
            
            # Estimate results (simplified)
            estimated_results = 100  # Mock estimation
            performance_estimate = "fast" if len(query.filters) <= 3 else "medium"
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'estimated_results': estimated_results,
                'performance_estimate': performance_estimate
            }
            
        except Exception as e:
            logger.error(f"Failed to validate query: {e}")
            return {
                'valid': False,
                'errors': [str(e)],
                'estimated_results': 0,
                'performance_estimate': 'unknown'
            }
    
    def _execute_query(self, query: WorksetQuery, dictionary_service) -> tuple[List[Dict[str, Any]], int]:
        """Execute workset query against dictionary service."""
        try:
            # Convert workset query to dictionary service format
            filter_text = None
            pos_filter = None
            sort_by = query.sort_by or 'lexical_unit'
            sort_order = query.sort_order
            
            # Extract common filters
            for filter_obj in query.filters:
                if filter_obj.field == 'lexical_unit' and filter_obj.operator == 'starts_with':
                    filter_text = filter_obj.value
                elif filter_obj.field == 'pos' and filter_obj.operator == 'equals':
                    pos_filter = filter_obj.value
            
            # Execute query with large limit to get all matching entries
            entries, total_count = dictionary_service.list_entries(
                limit=10000,  # Large limit for workset
                offset=0,
                filter_text=filter_text,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Convert entries to dict format
            entry_dicts = [entry.to_dict() if hasattr(entry, 'to_dict') else entry for entry in entries]
            
            # Apply additional filtering if needed
            if pos_filter:
                entry_dicts = [e for e in entry_dicts if e.get('pos') == pos_filter]
                total_count = len(entry_dicts)
            
            return entry_dicts, total_count
            
        except Exception as e:
            logger.error(f"Failed to execute workset query: {e}")
            return [], 0
    
    def _perform_bulk_operation(self, workset: Workset, operation: BulkOperation) -> int:
        """Perform bulk operation on workset entries."""
        try:
            updated_count = 0
            
            # Simulate bulk operation
            if operation.operation == 'update_field':
                for entry in workset.entries:
                    if operation.field in entry or operation.field == 'semantic_domain':
                        entry[operation.field] = operation.value
                        updated_count += 1
            
            elif operation.operation == 'delete_field':
                for entry in workset.entries:
                    if operation.field in entry:
                        del entry[operation.field]
                        updated_count += 1
            
            elif operation.operation == 'add_field':
                for entry in workset.entries:
                    entry[operation.field] = operation.value
                    updated_count += 1
            
            # Update workset timestamp
            workset.updated_at = datetime.now()
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to perform bulk operation: {e}")
            return 0
