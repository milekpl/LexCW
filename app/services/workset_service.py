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

            conn = current_app.pg_pool.getconn()
            try:
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
            finally:
                current_app.pg_pool.putconn(conn)

            logger.info(f"Created workset '{name}' with {total_count} entries")
            return workset

        except Exception as e:
            logger.error(f"Failed to create workset '{name}': {e}")
            raise

    def create_ai_review_workset(
        self, 
        name: str, 
        query: WorksetQuery,
        ai_review_config: Optional[Dict[str, Any]] = None
    ) -> Workset:
        """
        Create a workset specifically for AI quality control review.
        
        This creates a workset with metadata marking it for AI review.
        
        Args:
            name: Workset name
            query: Query criteria for entries to review
            ai_review_config: Optional configuration for AI review
                
        Returns:
            Created Workset with ai_review metadata
        """
        try:
            # Create the workset normally first
            workset = self.create_workset(name, query)
            
            # Store AI review configuration in workset UI settings
            ai_config = ai_review_config or {}
            workset.ui_settings = {
                **(workset.ui_settings or {}),
                'ai_review_enabled': True,
                'ai_review_config': {
                    'prompt_template_id': ai_config.get('prompt_template_id', 'proofreading-default'),
                    'severity_threshold': ai_config.get('severity_threshold', 'warning'),
                    'auto_mark_review': ai_config.get('auto_mark_review', True),
                    'created_at': datetime.now().isoformat(),
                    'status': 'pending'
                }
            }

            conn = current_app.pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE worksets SET ui_settings = %s WHERE id = %s",
                        (json.dumps(workset.ui_settings), workset.id)
                    )
                conn.commit()
            finally:
                current_app.pg_pool.putconn(conn)

            logger.info(f"Created AI review workset '{name}' (id={workset.id})")
            return workset

        except Exception as e:
            logger.error(f"Failed to create AI review workset '{name}': {e}")
            raise

    def get_workset(self, workset_id: int, limit: int = 50, offset: int = 0) -> Optional[Workset]:
        """Retrieve workset with pagination."""
        try:
            conn = current_app.pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, name, query, total_entries, created_at, updated_at, ui_settings FROM worksets WHERE id = %s", (workset_id,))
                    workset_data = cur.fetchone()
                    if not workset_data:
                        return None

                    workset = Workset(
                        id=workset_data[0],
                        name=workset_data[1],
                        query=WorksetQuery.from_dict(workset_data[2]),
                        total_entries=workset_data[3],
                        created_at=workset_data[4],
                        updated_at=workset_data[5],
                        ui_settings=workset_data[6] if len(workset_data) > 6 and workset_data[6] else {}
                    )

                    cur.execute(
                        "SELECT entry_id FROM workset_entries WHERE workset_id = %s LIMIT %s OFFSET %s",
                        (workset_id, limit, offset)
                    )
                    entry_ids = [row[0] for row in cur.fetchall()]

                    dictionary_service = get_dictionary_service()
                    entries = []
                    missing_entry_ids = []
                    for entry_id in entry_ids:
                        entry = dictionary_service.get_entry(entry_id)
                        if entry is None:
                            missing_entry_ids.append(entry_id)
                            continue
                        entries.append(entry.to_dict())

                    if missing_entry_ids:
                        logger.warning(
                            "Workset %s references missing entry IDs: %s",
                            workset_id,
                            ", ".join(str(entry_id) for entry_id in missing_entry_ids),
                        )

                    workset.entries = entries

                    return workset
            finally:
                current_app.pg_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to get workset {workset_id}: {e}")
            return None

    def list_worksets(self) -> List[Workset]:
        """List all available worksets."""
        try:
            conn = current_app.pg_pool.getconn()
            try:
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
            finally:
                current_app.pg_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to list worksets: {e}")
            return []

    def update_workset_query(self, workset_id: int, query: WorksetQuery) -> Optional[int]:
        """Update workset query criteria and refresh entries."""
        try:
            dictionary_service = get_dictionary_service()
            entries, total_count = self._execute_query(query, dictionary_service)

            conn = current_app.pg_pool.getconn()
            try:
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

            finally:
                current_app.pg_pool.putconn(conn)
            logger.info(f"Updated workset {workset_id} query, now has {total_count} entries")
            return total_count

        except Exception as e:
            logger.error(f"Failed to update workset {workset_id}: {e}")
            return None

    def delete_workset(self, workset_id: int) -> bool:
        """Delete a workset."""
        try:
            conn = current_app.pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM worksets WHERE id = %s", (workset_id,))
                    conn.commit()
                    if cur.rowcount > 0:
                         if workset_id in self._progress_tracker:
                            del self._progress_tracker[workset_id]
                         logger.info(f"Deleted workset {workset_id}")
                         return True
                return False
            finally:
                current_app.pg_pool.putconn(conn)

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

            # Use list_entries instead of search_entries since it supports sorting
            # list_entries has filter_text, sort_by, and sort_order parameters
            entries, total_count = dictionary_service.list_entries(
                filter_text=search_term if search_term else "",
                limit=10000,  # Large limit for workset
                offset=0,
                sort_by=query.sort_by if query.sort_by else "lexical_unit",
                sort_order=query.sort_order if query.sort_order else "asc"
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

    def create_proposal_workset(
        self,
        name: str,
        source_script: str,
        proposals: List[Dict[str, Any]],
    ) -> Workset:
        """Create a Workset containing proposal entries from an external script."""
        query_dict = {"source_script": source_script, "type": "proposal_workset"}
        workset = Workset.create(name, WorksetQuery.from_dict(query_dict))
        workset.total_entries = len(proposals)
        workset.ui_settings = {
            "proposal_workset": True,
            "source_script": source_script,
            "created_at": datetime.now().isoformat(),
        }

        if hasattr(current_app, "pg_pool") and current_app.pg_pool is not None:
            conn = current_app.pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO worksets (name, query, total_entries, ui_settings) VALUES (%s, %s, %s, %s) RETURNING id, created_at, updated_at",
                        (workset.name, json.dumps(workset.query.to_dict()), workset.total_entries, json.dumps(workset.ui_settings))
                    )
                    workset.id, workset.created_at, workset.updated_at = cur.fetchone()

                    for prop in proposals:
                        eid = prop.get("entry_id")
                        notes_data = json.dumps(prop)
                        cur.execute(
                            "INSERT INTO workset_entries (workset_id, entry_id, status, notes) VALUES (%s, %s, %s, %s)",
                            (workset.id, eid, "pending_review", notes_data)
                        )
                conn.commit()
            finally:
                current_app.pg_pool.putconn(conn)
        else:
            from app.models.project_settings import db
            from app.models.workset_models import Workset as DBWorkset, WorksetEntry as DBWorksetEntry
            try:
                db_ws = DBWorkset(
                    name=name,
                    query=workset.query.to_dict(),
                    total_entries=len(proposals),
                    ui_settings=workset.ui_settings,
                )
                db.session.add(db_ws)
                db.session.commit()
                workset.id = db_ws.id
            except Exception as ex:
                logger.warning(f"DB fallback in create_proposal_workset: {ex}")
                try:
                    db.session.rollback()
                except Exception:
                    pass
                workset.id = 1


        return workset

    def approve_workset_entry_proposal(
        self,
        workset_id: int,
        entry_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve a proposal in a workset, applying changes directly to entry and updating status to 'approved'."""
        dictionary_service = get_dictionary_service()
        entry = dictionary_service.get_entry(entry_id)
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        proposal_data = None
        if hasattr(current_app, "pg_pool") and current_app.pg_pool is not None:
            conn = current_app.pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT notes FROM workset_entries WHERE workset_id = %s AND entry_id = %s",
                        (workset_id, entry_id)
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        proposal_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            finally:
                current_app.pg_pool.putconn(conn)
        else:
            from app.models.workset_models import WorksetEntry as DBWorksetEntry
            we = DBWorksetEntry.query.filter_by(workset_id=workset_id, entry_id=entry_id).first()
            if we and we.notes:
                proposal_data = json.loads(we.notes) if isinstance(we.notes, str) else we.notes

        if not proposal_data:
            raise ValueError(f"No proposal metadata found for entry {entry_id} in workset {workset_id}")

        field_name = proposal_data.get("field_name")
        proposed_val = proposal_data.get("proposed_value")
        proposal_type = proposal_data.get("proposal_type", "")

        entry_dict = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)

        if proposal_type == "ipa" or field_name == "pronunciation":
            if isinstance(proposed_val, dict):
                entry_dict["pronunciation"] = proposed_val
            elif isinstance(proposed_val, str):
                entry_dict["pronunciation"] = {"ipa": proposed_val, "lang": "seh-fonipa"}
        elif proposal_type == "pos" or field_name == "grammatical_info":
            entry_dict["grammatical_info"] = str(proposed_val)
        elif field_name:
            entry_dict[field_name] = proposed_val

        updated_entry = dictionary_service.update_entry(entry_id, entry_dict)

        from app.services.entry_revision_service import EntryRevisionService
        try:
            revision = EntryRevisionService.save_revision(
                entry_id=entry_id,
                snapshot=entry_dict,
                user_id=user_id or "system",
                created_by=f"ProposalApprove ({proposal_data.get('source_script', 'external_script')})",
            )
            rev_dict = revision.to_dict() if hasattr(revision, "to_dict") else {}
        except Exception as e:
            logger.warning(f"Revision save warning: {e}")
            rev_dict = {}

        if hasattr(current_app, "pg_pool") and current_app.pg_pool is not None:
            conn = current_app.pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE workset_entries SET status = %s, modified_at = %s WHERE workset_id = %s AND entry_id = %s",
                        ("approved", datetime.utcnow(), workset_id, entry_id)
                    )
                conn.commit()
            finally:
                current_app.pg_pool.putconn(conn)
        else:
            from app.models.project_settings import db
            from app.models.workset_models import WorksetEntry as DBWorksetEntry
            we = DBWorksetEntry.query.filter_by(workset_id=workset_id, entry_id=entry_id).first()
            if we:
                we.status = "approved"
                we.modified_at = datetime.utcnow()
                db.session.commit()

        return {
            "success": True,
            "entry_id": entry_id,
            "status": "approved",
            "applied_field": field_name,
            "applied_value": proposed_val,
            "revision": rev_dict,
        }

    def reject_workset_entry_proposal(
        self,
        workset_id: int,
        entry_id: str,
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reject a proposal in a workset, setting status to 'rejected' without modifying entry data."""
        if hasattr(current_app, "pg_pool") and current_app.pg_pool is not None:
            conn = current_app.pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE workset_entries SET status = %s, modified_at = %s WHERE workset_id = %s AND entry_id = %s",
                        ("rejected", datetime.utcnow(), workset_id, entry_id)
                    )
                conn.commit()
            finally:
                current_app.pg_pool.putconn(conn)
        else:
            from app.models.project_settings import db
            from app.models.workset_models import WorksetEntry as DBWorksetEntry
            we = DBWorksetEntry.query.filter_by(workset_id=workset_id, entry_id=entry_id).first()
            if we:
                we.status = "rejected"
                we.modified_at = datetime.utcnow()
                if notes:
                    we.notes = notes
                db.session.commit()

        return {
            "success": True,
            "entry_id": entry_id,
            "status": "rejected",
        }

