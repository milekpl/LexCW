#!/usr/bin/env python3

"""
Workset service for managing query-based entry collections.
Implements workbench-oriented bulk operations with performance optimization.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging
import time
import json
from datetime import datetime
from flask import current_app

from app.models.workset import Workset, WorksetQuery, BulkOperation, WorksetProgress
from app.api.entries import get_dictionary_service

logger = logging.getLogger(__name__)


class WorksetService:
    """Service for managing worksets and bulk operations."""

    def __init__(self):
        self._progress_tracker: Dict[str, WorksetProgress] = {}

    def create_workset(self, name: str, query: WorksetQuery) -> Workset:
        """Create a new workset from query criteria."""
        try:
            dictionary_service = get_dictionary_service()
            entries, total_count = self._execute_query(query, dictionary_service)

            workset = Workset.create(name, query)
            workset.total_entries = total_count
            
            with current_app.pg_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO worksets (name, query, total_entries) VALUES (%s, %s, %s) RETURNING id, created_at, updated_at",
                        (workset.name, json.dumps(workset.query.to_dict()), workset.total_entries)
                    )
                    workset.id, workset.created_at, workset.updated_at = cur.fetchone()

                    entry_ids = [entry['id'] for entry in entries]
                    for entry_id in entry_ids:
                        cur.execute(
                            "INSERT INTO workset_entries (workset_id, entry_id) VALUES (%s, %s)",
                            (workset.id, entry_id)
                        )
                    conn.commit()

            logger.info(f"Created workset '{name}' with {total_count} entries")
            return workset

        except Exception as e:
            logger.error(f"Failed to create workset '{name}': {e}")
            raise

    def get_workset(self, workset_id: int, limit: int = 50, offset: int = 0) -> Optional[Workset]:
        """Retrieve workset with pagination."""
        try:
            with current_app.pg_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, name, query, total_entries, created_at, updated_at FROM worksets WHERE id = %s", (workset_id,))
                    workset_data = cur.fetchone()
                    if not workset_data:
                        return None

                    workset = Workset(
                        id=workset_data[0],
                        name=workset_data[1],
                        query=WorksetQuery.from_dict(workset_data[2]),
                        total_entries=workset_data[3],
                        created_at=workset_data[4],
                        updated_at=workset_data[5]
                    )

                    cur.execute(
                        "SELECT entry_id FROM workset_entries WHERE workset_id = %s LIMIT %s OFFSET %s",
                        (workset_id, limit, offset)
                    )
                    entry_ids = [row[0] for row in cur.fetchall()]

                    dictionary_service = get_dictionary_service()
                    entries = [dictionary_service.get_entry(entry_id).to_dict() for entry_id in entry_ids]
                    workset.entries = entries

                    return workset
        except Exception as e:
            logger.error(f"Failed to get workset {workset_id}: {e}")
            return None

    def list_worksets(self) -> List[Workset]:
        """List all available worksets."""
        try:
            with current_app.pg_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, name, query, total_entries, created_at, updated_at FROM worksets")
                    worksets_data = cur.fetchall()
                    worksets = []
                    for row in worksets_data:
                        worksets.append(Workset(
                            id=row[0],
                            name=row[1],
                            query=WorksetQuery.from_dict(row[2]),
                            total_entries=row[3],
                            created_at=row[4],
                            updated_at=row[5]
                        ))
                    return worksets
        except Exception as e:
            logger.error(f"Failed to list worksets: {e}")
            return []

    def update_workset_query(self, workset_id: int, query: WorksetQuery) -> Optional[int]:
        """Update workset query criteria and refresh entries."""
        try:
            dictionary_service = get_dictionary_service()
            entries, total_count = self._execute_query(query, dictionary_service)

            with current_app.pg_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE worksets SET query = %s, total_entries = %s, updated_at = %s WHERE id = %s",
                        (json.dumps(query.to_dict()), total_count, datetime.now(), workset_id)
                    )
                    cur.execute("DELETE FROM workset_entries WHERE workset_id = %s", (workset_id,))

                    entry_ids = [entry['id'] for entry in entries]
                    for entry_id in entry_ids:
                        cur.execute(
                            "INSERT INTO workset_entries (workset_id, entry_id) VALUES (%s, %s)",
                            (workset_id, entry_id)
                        )
                    conn.commit()

            logger.info(f"Updated workset {workset_id} query, now has {total_count} entries")
            return total_count

        except Exception as e:
            logger.error(f"Failed to update workset {workset_id}: {e}")
            return None

    def delete_workset(self, workset_id: int) -> bool:
        """Delete a workset."""
        try:
            with current_app.pg_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM worksets WHERE id = %s", (workset_id,))
                    conn.commit()
                    if cur.rowcount > 0:
                         if workset_id in self._progress_tracker:
                            del self._progress_tracker[workset_id]
                         logger.info(f"Deleted workset {workset_id}")
                         return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete workset {workset_id}: {e}")
            return False
    
    def bulk_update_workset(self, workset_id: int, operation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply bulk operations to workset entries."""
        try:
            workset = self.get_workset(workset_id, limit=10000) # Get all entries
            if not workset:
                return None

            operation = BulkOperation.from_dict(operation_data)

            progress = WorksetProgress(
                status='running',
                total_items=workset.total_entries
            )
            self._progress_tracker[workset_id] = progress

            updated_count = self._perform_bulk_operation(workset, operation, progress)

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
            if workset_id in self._progress_tracker:
                self._progress_tracker[workset_id].status = 'failed'
                self._progress_tracker[workset_id].error_message = str(e)
            return None

    def get_workset_progress(self, workset_id: int) -> Optional[Dict[str, Any]]:
        """Get progress of bulk operations on workset."""
        try:
            progress = self._progress_tracker.get(workset_id)
            if progress:
                return progress.to_dict()

            workset = self.get_workset(workset_id)
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
            # This is a simplified conversion. A more robust implementation would
            # map all query filters to the search_entries parameters.
            search_term = ""
            fields = []
            for f in query.filters:
                if f.field == 'lexical_unit':
                    search_term = f.value
                    fields.append('lexical_unit')

            entries, total_count = dictionary_service.search_entries(
                query=search_term,
                fields=fields,
                limit=10000,  # Large limit for workset
                offset=0,
                sort_by=query.sort_by,
                sort_order=query.sort_order
            )

            entry_dicts = [entry.to_dict() for entry in entries]
            return entry_dicts, total_count

        except Exception as e:
            logger.error(f"Failed to execute workset query: {e}")
            return [], 0

    def _perform_bulk_operation(self, workset: Workset, operation: BulkOperation, progress: WorksetProgress) -> int:
        """Perform bulk operation on workset entries."""
        try:
            updated_count = 0
            dictionary_service = get_dictionary_service()

            for i, entry_dict in enumerate(workset.entries):
                entry = dictionary_service.get_entry(entry_dict['id'])
                if operation.operation == 'update_field':
                    # This is a simplified update. A more robust implementation
                    # would handle different field types and nested structures.
                    setattr(entry, operation.field, operation.value)
                    dictionary_service.update_entry(entry)
                    updated_count += 1
                elif operation.operation == 'delete_field':
                    # This is a simplified delete. A more robust implementation
                    # would handle different field types and nested structures.
                    if hasattr(entry, operation.field):
                        setattr(entry, operation.field, None)
                        dictionary_service.update_entry(entry)
                        updated_count += 1
                elif operation.operation == 'add_field':
                    # This is a simplified add. A more robust implementation
                    # would handle different field types and nested structures.
                    setattr(entry, operation.field, operation.value)
                    dictionary_service.update_entry(entry)
                    updated_count += 1

                progress.completed_items = i + 1
                progress.progress = (progress.completed_items / progress.total_items) * 100

            workset.updated_at = datetime.now()
            with current_app.pg_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE worksets SET updated_at = %s WHERE id = %s", (workset.updated_at, workset.id))
                    conn.commit()

            return updated_count

        except Exception as e:
            logger.error(f"Failed to perform bulk operation: {e}")
            return 0
