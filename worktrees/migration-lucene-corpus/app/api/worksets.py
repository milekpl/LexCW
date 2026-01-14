#!/usr/bin/env python3

"""
Workset management API endpoints.
Implements query-based worksets for bulk lexicographic operations.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from flasgger import swag_from
import logging
from typing import Dict, Any, List
from datetime import datetime

from app.services.workset_service import WorksetService
from app.models.workset import Workset, WorksetQuery

logger = logging.getLogger(__name__)

worksets_bp = Blueprint('worksets_api', __name__)


@worksets_bp.route('/api/worksets', methods=['GET'])
@swag_from({
    'tags': ['Worksets'],
    'summary': 'List all worksets',
    'description': 'Retrieve a list of all available worksets',
    'responses': {
        200: {
            'description': 'Worksets retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'worksets': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'name': {'type': 'string'},
                                'total_entries': {'type': 'integer'},
                                'created_at': {'type': 'string'},
                                'query': {'type': 'object'}
                            }
                        }
                    }
                }
            }
        },
        500: {'description': 'Internal server error'}
    }
})
def list_worksets() -> tuple[Dict[str, Any], int]:
    """List all available worksets."""
    try:
        workset_service = WorksetService()
        worksets = workset_service.list_worksets()
        
        return {
            'success': True,
            'worksets': [workset.to_dict() for workset in worksets]
        }, 200
        
    except Exception as e:
        logger.error(f"Error listing worksets: {e}")
        return {'error': 'Failed to list worksets'}, 500


@worksets_bp.route('/api/worksets', methods=['POST'])
@swag_from({
    'tags': ['Worksets'],
    'summary': 'Create a new workset from query',
    'description': 'Creates a filtered collection of entries based on query criteria. JSON input disabled; use XML payloads',
    'consumes': ['application/xml'],
    'parameters': [{
        'name': 'workset_data',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string', 'description': 'Workset name'},
                'query': {
                    'type': 'object',
                    'properties': {
                        'filters': {'type': 'array', 'items': {'type': 'object'}},
                        'sort_by': {'type': 'string'},
                        'sort_order': {'type': 'string', 'enum': ['asc', 'desc']}
                    }
                }
            },
            'required': ['name', 'query']
        }
    }],
    'responses': {
        201: {
            'description': 'Workset created successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'workset_id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'total_entries': {'type': 'integer'}
                }
            }
        },
        400: {'description': 'Invalid request data'},
        500: {'description': 'Internal server error'}
    }
})
def create_workset() -> tuple[Dict[str, Any], int]:
    """Create a new workset from query criteria."""
    try:
        # Reject JSON body for data-rich workset creation; use service or XML payloads
        if request.content_type and 'application/json' in request.content_type:
            return {'error': 'JSON input disabled; use XML or service-driven creation'}, 415
        data = request.get_json(silent=True)
        
        # Validate required fields
        if 'name' not in data or 'query' not in data:
            return {'error': 'Missing required fields: name, query'}, 400
        
        workset_service = WorksetService()
        workset = workset_service.create_workset(
            name=data['name'],
            query=WorksetQuery.from_dict(data['query'])
        )
        
        return {
            'success': True,
            'workset_id': workset.id,
            'name': workset.name,
            'total_entries': workset.total_entries
        }, 201
        
    except Exception as e:
        logger.error(f"Error creating workset: {e}")
        return {'error': 'Failed to create workset'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>', methods=['GET'])
@swag_from({
    'tags': ['Worksets'],
    'summary': 'Get workset with pagination',
    'description': 'Retrieve workset entries with pagination support',
    'parameters': [
        {'name': 'workset_id', 'in': 'path', 'type': 'integer', 'required': True},
        {'name': 'limit', 'in': 'query', 'type': 'integer', 'default': 50},
        {'name': 'offset', 'in': 'query', 'type': 'integer', 'default': 0}
    ],
    'responses': {
        200: {
            'description': 'Workset retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'total_entries': {'type': 'integer'},
                    'entries': {'type': 'array', 'items': {'type': 'object'}}
                }
            }
        },
        404: {'description': 'Workset not found'},
        500: {'description': 'Internal server error'}
    }
})
def get_workset(workset_id: int) -> tuple[Dict[str, Any], int]:
    """Get workset with pagination."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        workset_service = WorksetService()
        workset = workset_service.get_workset(workset_id, limit=limit, offset=offset)

        if not workset:
            return {'error': 'Workset not found'}, 404

        return workset.to_dict(), 200

    except Exception as e:
        logger.error(f"Error retrieving workset {workset_id}: {e}")
        return {'error': 'Failed to retrieve workset'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/query', methods=['PUT'])
@swag_from({
    'tags': ['Worksets'],
    'summary': 'Update workset query',
    'description': 'Update the query criteria for an existing workset. JSON input disabled; use XML payloads',
    'consumes': ['application/xml'],
    'parameters': [
        {'name': 'workset_id', 'in': 'path', 'type': 'integer', 'required': True},
        {
            'name': 'query_data',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'filters': {'type': 'array', 'items': {'type': 'object'}},
                    'sort_by': {'type': 'string'},
                    'sort_order': {'type': 'string', 'enum': ['asc', 'desc']}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Query updated successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'updated_entries': {'type': 'integer'}
                }
            }
        },
        404: {'description': 'Workset not found'},
        500: {'description': 'Internal server error'}
    }
})
def update_workset_query(workset_id: int) -> tuple[Dict[str, Any], int]:
    """Update workset query criteria."""
    try:
        if request.content_type and 'application/json' in request.content_type:
            return {'error': 'JSON input disabled; use XML or service-driven update'}, 415
        data = request.get_json(silent=True)

        workset_service = WorksetService()
        updated_count = workset_service.update_workset_query(
            workset_id, WorksetQuery.from_dict(data)
        )

        if updated_count is None:
            return {'error': 'Workset not found'}, 404

        return {
            'success': True,
            'updated_entries': updated_count
        }, 200

    except Exception as e:
        logger.error(f"Error updating workset {workset_id}: {e}")
        return {'error': 'Failed to update workset query'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>', methods=['DELETE'])
@swag_from({
    'tags': ['Worksets'],
    'summary': 'Delete workset',
    'description': 'Remove a workset (does not delete the entries)',
    'parameters': [
        {'name': 'workset_id', 'in': 'path', 'type': 'integer', 'required': True}
    ],
    'responses': {
        200: {
            'description': 'Workset deleted successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'}
                }
            }
        },
        404: {'description': 'Workset not found'},
        500: {'description': 'Internal server error'}
    }
})
def delete_workset(workset_id: int) -> tuple[Dict[str, Any], int]:
    """Delete a workset."""
    try:
        workset_service = WorksetService()
        success = workset_service.delete_workset(workset_id)

        if not success:
            return {'error': 'Workset not found'}, 404

        return {'success': True}, 200

    except Exception as e:
        logger.error(f"Error deleting workset {workset_id}: {e}")
        return {'error': 'Failed to delete workset'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/bulk-update', methods=['POST'])
@swag_from({
    'tags': ['Worksets'],
    'summary': 'Bulk update workset entries',
    'description': 'Apply bulk operations to all entries in a workset. JSON input disabled; use XML payloads',
    'consumes': ['application/xml'],
    'parameters': [
        {'name': 'workset_id', 'in': 'path', 'type': 'integer', 'required': True},
        {
            'name': 'bulk_operation',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'operation': {'type': 'string', 'enum': ['update_field', 'delete_field', 'add_field']},
                    'field': {'type': 'string'},
                    'value': {'type': 'string'},
                    'apply_to': {'type': 'string', 'enum': ['all', 'filtered']}
                },
                'required': ['operation', 'field']
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Bulk operation initiated',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'task_id': {'type': 'string'},
                    'updated_count': {'type': 'integer'}
                }
            }
        },
        404: {'description': 'Workset not found'},
        500: {'description': 'Internal server error'}
    }
})
def bulk_update_workset(workset_id: int) -> tuple[Dict[str, Any], int]:
    """Apply bulk updates to workset entries."""
    try:
        if request.content_type and 'application/json' in request.content_type:
            return {'error': 'JSON input disabled; use XML or service-driven bulk updates'}, 415
        data = request.get_json(silent=True)

        if 'operation' not in data or 'field' not in data:
            return {'error': 'Missing required fields: operation, field'}, 400

        workset_service = WorksetService()
        result = workset_service.bulk_update_workset(workset_id, data)

        if not result:
            return {'error': 'Workset not found'}, 404

        return {
            'success': True,
            'task_id': result.get('task_id'),
            'updated_count': result.get('updated_count', 0)
        }, 200

    except Exception as e:
        logger.error(f"Error bulk updating workset {workset_id}: {e}")
        return {'error': 'Failed to perform bulk update'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/progress', methods=['GET'])
@swag_from({
    'tags': ['Worksets'],
    'summary': 'Get bulk operation progress',
    'description': 'Track progress of long-running bulk operations',
    'parameters': [
        {'name': 'workset_id', 'in': 'path', 'type': 'integer', 'required': True}
    ],
    'responses': {
        200: {
            'description': 'Progress information',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'enum': ['pending', 'running', 'completed', 'failed']},
                    'progress': {'type': 'number', 'minimum': 0, 'maximum': 100},
                    'total_items': {'type': 'integer'},
                    'completed_items': {'type': 'integer'}
                }
            }
        },
        404: {'description': 'Workset not found'},
        500: {'description': 'Internal server error'}
    }
})
def get_workset_progress(workset_id: int) -> tuple[Dict[str, Any], int]:
    """Get progress of bulk operations on workset."""
    try:
        workset_service = WorksetService()
        progress = workset_service.get_workset_progress(workset_id)

        if not progress:
            return {'error': 'Workset not found'}, 404

        return progress, 200

    except Exception as e:
        logger.error(f"Error getting workset progress {workset_id}: {e}")
        return {'error': 'Failed to get progress'}, 500


@worksets_bp.route('/api/queries/validate', methods=['POST'])
@swag_from({
    'tags': ['Queries'],
    'summary': 'Validate query',
    'description': 'Validate query syntax and estimate performance',
    'parameters': [{
        'name': 'query_data',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'filters': {'type': 'array', 'items': {'type': 'object'}},
                'sort_by': {'type': 'string'},
                'sort_order': {'type': 'string', 'enum': ['asc', 'desc']}
            }
        }
    }],
    'responses': {
        200: {
            'description': 'Query validation result',
            'schema': {
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'errors': {'type': 'array', 'items': {'type': 'string'}},
                    'estimated_results': {'type': 'integer'},
                    'performance_estimate': {'type': 'string'}
                }
            }
        },
        400: {'description': 'Invalid request data'},
        500: {'description': 'Internal server error'}
    }
})
def validate_query() -> tuple[Dict[str, Any], int]:
    """Validate query syntax and performance."""
    try:
        data = request.get_json()
        if not data:
            return {'error': 'No JSON data provided'}, 400
        
        workset_service = WorksetService()
        
        try:
            query = WorksetQuery.from_dict(data)
            validation_result = workset_service.validate_query(query)
            return validation_result, 200
        except (ValueError, KeyError, TypeError) as validation_error:
            # Return validation errors as part of the response, not as HTTP errors
            return {
                'valid': False,
                'errors': [str(validation_error)],
                'estimated_results': 0,
                'performance_estimate': 'unknown'
            }, 200
        
    except Exception as e:
        logger.error(f"Error validating query: {e}")
        return {'error': 'Failed to validate query'}, 500


# ============ CURATION ENDPOINTS ============

ENTRY_STATUS = {
    'PENDING': 'pending',
    'DONE': 'done',
    'NEEDS_REVIEW': 'review'
}


@worksets_bp.route('/api/worksets/<int:workset_id>/entries/<entry_id>/status', methods=['PATCH'])
def update_entry_status(workset_id: int, entry_id: str) -> tuple[Dict[str, Any], int]:
    """Update status of an entry within a workset."""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return {'error': 'Missing status field'}, 400

        status = data['status']
        if status not in ENTRY_STATUS.values():
            return {'error': f'Invalid status. Must be one of: {list(ENTRY_STATUS.values())}'}, 400

        notes = data.get('notes', '')

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE workset_entries
                    SET status = %s, notes = %s, modified_at = %s
                    WHERE workset_id = %s AND entry_id = %s
                """, (status, notes, datetime.now(), workset_id, entry_id))

                if cur.rowcount == 0:
                    return {'error': 'Entry not found in workset'}, 404

                conn.commit()

        return {
            'success': True,
            'entry_id': entry_id,
            'status': status,
            'notes': notes
        }, 200

    except Exception as e:
        logger.error(f"Error updating entry status: {e}")
        return {'error': 'Failed to update status'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/entries/<entry_id>/favorite', methods=['POST'])
def toggle_favorite(workset_id: int, entry_id: str) -> tuple[Dict[str, Any], int]:
    """Toggle favorite status for an entry in a workset."""
    try:
        data = request.get_json()
        if not data or 'is_favorite' not in data:
            return {'error': 'Missing is_favorite field'}, 400

        is_favorite = data['is_favorite']

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE workset_entries
                    SET is_favorite = %s, modified_at = %s
                    WHERE workset_id = %s AND entry_id = %s
                """, (is_favorite, datetime.now(), workset_id, entry_id))

                if cur.rowcount == 0:
                    return {'error': 'Entry not found in workset'}, 404

                conn.commit()

        return {
            'success': True,
            'entry_id': entry_id,
            'is_favorite': is_favorite
        }, 200

    except Exception as e:
        logger.error(f"Error toggling favorite: {e}")
        return {'error': 'Failed to toggle favorite'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/progress', methods=['GET'])
def get_curation_progress(workset_id: int) -> tuple[Dict[str, Any], int]:
    """Get curation progress for a workset with status counts."""
    try:
        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                # Get status counts
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE status = 'done') as done,
                        COUNT(*) FILTER (WHERE status = 'review') as review,
                        COUNT(*) FILTER (WHERE is_favorite = TRUE) as favorites
                    FROM workset_entries
                    WHERE workset_id = %s
                """, (workset_id,))

                row = cur.fetchone()
                if not row:
                    return {'error': 'Workset not found'}, 404

                total, pending, done, review, favorites = row

                # Calculate progress percentage
                progress_pct = (done / total * 100) if total > 0 else 0

                return {
                    'workset_id': workset_id,
                    'total': total,
                    'pending': pending,
                    'done': done,
                    'review': review,
                    'favorites': favorites,
                    'progress_percent': round(progress_pct, 1)
                }, 200

    except Exception as e:
        logger.error(f"Error getting curation progress: {e}")
        return {'error': 'Failed to get progress'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/navigation/current', methods=['GET'])
def get_current_entry(workset_id: int) -> tuple[Dict[str, Any], int]:
    """Get current entry for curation navigation."""
    try:
        position = request.args.get('position', 0, type=int)

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                # Get total count first
                cur.execute("SELECT COUNT(*) FROM workset_entries WHERE workset_id = %s", (workset_id,))
                total = cur.fetchone()[0]

                if total == 0:
                    return {'error': 'Workset is empty'}, 404

                # Clamp position
                if position < 0:
                    position = 0
                elif position >= total:
                    position = total - 1

                # Get entry at position
                cur.execute("""
                    SELECT we.entry_id, we.status, we.is_favorite, we.position, we.notes
                    FROM workset_entries we
                    WHERE we.workset_id = %s
                    ORDER BY we.position NULLS LAST, we.id
                    LIMIT 1 OFFSET %s
                """, (workset_id, position))

                row = cur.fetchone()
                if not row:
                    # Fallback - get first if position not set
                    cur.execute("""
                        SELECT we.entry_id, we.status, we.is_favorite, we.position, we.notes
                        FROM workset_entries we
                        WHERE we.workset_id = %s
                        ORDER BY we.id
                        LIMIT 1
                    """, (workset_id,))
                    row = cur.fetchone()
                    if not row:
                        return {'error': 'No entries in workset'}, 404
                    position = 0

                entry_id, status, is_favorite, entry_position, notes = row

                # Get full entry data
                dictionary_service = get_dictionary_service()
                entry = dictionary_service.get_entry(entry_id)

                # Get prev/next entry IDs
                prev_id = None
                next_id = None

                if position > 0:
                    cur.execute("""
                        SELECT entry_id FROM workset_entries
                        WHERE workset_id = %s
                        ORDER BY position NULLS LAST, id
                        LIMIT 1 OFFSET %s
                    """, (workset_id, position - 1))
                    prev_row = cur.fetchone()
                    if prev_row:
                        prev_id = prev_row[0]

                if position < total - 1:
                    cur.execute("""
                        SELECT entry_id FROM workset_entries
                        WHERE workset_id = %s
                        ORDER BY position NULLS LAST, id
                        LIMIT 1 OFFSET %s
                    """, (workset_id, position + 1))
                    next_row = cur.fetchone()
                    if next_row:
                        next_id = next_row[0]

                return {
                    'entry': entry.to_dict() if entry else {'id': entry_id},
                    'curation': {
                        'status': status or 'pending',
                        'is_favorite': is_favorite or False,
                        'position': entry_position if entry_position is not None else position,
                        'notes': notes or ''
                    },
                    'navigation': {
                        'current_position': position if entry_position is None else entry_position,
                        'total': total,
                        'prev_entry_id': prev_id,
                        'next_entry_id': next_id,
                        'has_prev': position > 0,
                        'has_next': position < total - 1
                    }
                }, 200

    except Exception as e:
        logger.error(f"Error getting current entry: {e}")
        return {'error': 'Failed to get current entry'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/navigation/<direction>', methods=['POST'])
def navigate_entries(workset_id: int, direction: str) -> tuple[Dict[str, Any], int]:
    """Navigate to next/prev/first/last entry in workset."""
    try:
        valid_directions = ['next', 'prev', 'first', 'last']
        if direction not in valid_directions:
            return {'error': f'Invalid direction. Must be one of: {valid_directions}'}, 400

        data = request.get_json(silent=True) or {}
        current_position = data.get('position', 0)

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute("SELECT COUNT(*) FROM workset_entries WHERE workset_id = %s", (workset_id,))
                total = cur.fetchone()[0]

                if total == 0:
                    return {'error': 'Workset is empty'}, 404

                # Calculate new position
                if direction == 'first':
                    new_position = 0
                elif direction == 'last':
                    new_position = total - 1
                elif direction == 'next':
                    new_position = min(current_position + 1, total - 1)
                else:  # prev
                    new_position = max(current_position - 1, 0)

                # Get entry at new position
                cur.execute("""
                    SELECT we.entry_id, we.status, we.is_favorite, we.position, we.notes
                    FROM workset_entries we
                    WHERE we.workset_id = %s
                    ORDER BY we.position NULLS LAST, we.id
                    LIMIT 1 OFFSET %s
                """, (workset_id, new_position))

                row = cur.fetchone()
                if not row:
                    return {'error': 'Position out of bounds'}, 400

                entry_id, status, is_favorite, entry_position, notes = row

                # Get full entry data
                dictionary_service = get_dictionary_service()
                entry = dictionary_service.get_entry(entry_id)

                # Get prev/next for response
                prev_id = None
                next_id = None

                if new_position > 0:
                    cur.execute("""
                        SELECT entry_id FROM workset_entries
                        WHERE workset_id = %s
                        ORDER BY position NULLS LAST, id
                        LIMIT 1 OFFSET %s
                    """, (workset_id, new_position - 1))
                    prev_row = cur.fetchone()
                    if prev_row:
                        prev_id = prev_row[0]

                if new_position < total - 1:
                    cur.execute("""
                        SELECT entry_id FROM workset_entries
                        WHERE workset_id = %s
                        ORDER BY position NULLS LAST, id
                        LIMIT 1 OFFSET %s
                    """, (workset_id, new_position + 1))
                    next_row = cur.fetchone()
                    if next_row:
                        next_id = next_row[0]

                return {
                    'entry': entry.to_dict() if entry else {'id': entry_id},
                    'curation': {
                        'status': status or 'pending',
                        'is_favorite': is_favorite or False,
                        'position': entry_position if entry_position is not None else new_position,
                        'notes': notes or ''
                    },
                    'navigation': {
                        'current_position': new_position,
                        'total': total,
                        'prev_entry_id': prev_id,
                        'next_entry_id': next_id,
                        'direction': direction
                    }
                }, 200

    except Exception as e:
        logger.error(f"Error navigating entries: {e}")
        return {'error': 'Failed to navigate'}, 500


@worksets_bp.route('/api/worksets/<int:workset_id>/entries', methods=['GET'])
def list_workset_entries(workset_id: int) -> tuple[Dict[str, Any], int]:
    """List entries in a workset with curation status."""
    try:
        status_filter = request.args.get('status')  # 'pending', 'done', 'review', or None for all
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                # Get workset info
                cur.execute("SELECT name FROM worksets WHERE id = %s", (workset_id,))
                ws_row = cur.fetchone()
                if not ws_row:
                    return {'error': 'Workset not found'}, 404

                workset_name = ws_row[0]

                # Build query with optional status filter
                if status_filter and status_filter in ENTRY_STATUS.values():
                    count_query = """
                        SELECT COUNT(*) FROM workset_entries
                        WHERE workset_id = %s AND status = %s
                    """
                    data_query = """
                        SELECT we.entry_id, we.status, we.is_favorite, we.position, we.notes
                        FROM workset_entries we
                        WHERE we.workset_id = %s AND we.status = %s
                        ORDER BY we.position NULLS LAST, we.id
                        LIMIT %s OFFSET %s
                    """
                    count_params = (workset_id, status_filter)
                    data_params = (workset_id, status_filter, limit, offset)
                else:
                    count_query = "SELECT COUNT(*) FROM workset_entries WHERE workset_id = %s"
                    data_query = """
                        SELECT we.entry_id, we.status, we.is_favorite, we.position, we.notes
                        FROM workset_entries we
                        WHERE we.workset_id = %s
                        ORDER BY we.position NULLS LAST, we.id
                        LIMIT %s OFFSET %s
                    """
                    count_params = (workset_id,)
                    data_params = (workset_id, limit, offset)

                # Get total count
                cur.execute(count_query, count_params)
                total = cur.fetchone()[0]

                # Get entries
                cur.execute(data_query, data_params)
                rows = cur.fetchall()

                # Get full entry data for each
                dictionary_service = get_dictionary_service()
                entries = []
                for row in rows:
                    entry_id, status, is_favorite, position, notes = row
                    entry = dictionary_service.get_entry(entry_id)
                    entries.append({
                        'entry': entry.to_dict() if entry else {'id': entry_id},
                        'curation': {
                            'status': status or 'pending',
                            'is_favorite': is_favorite or False,
                            'position': position,
                            'notes': notes or ''
                        }
                    })

                return {
                    'workset': {
                        'id': workset_id,
                        'name': workset_name,
                        'total_entries': total
                    },
                    'entries': entries,
                    'pagination': {
                        'limit': limit,
                        'offset': offset,
                        'total': total,
                        'has_more': offset + limit < total
                    }
                }, 200

    except Exception as e:
        logger.error(f"Error listing workset entries: {e}")
        return {'error': 'Failed to list entries'}, 500


# ============ BULK DELETE ENDPOINT ============

@worksets_bp.route('/api/worksets/bulk/delete', methods=['POST'])
def bulk_delete_worksets() -> tuple[Dict[str, Any], int]:
    """Bulk delete worksets by IDs."""
    try:
        data = request.get_json()
        if not data or 'ids' not in data:
            return {'error': 'Missing ids field'}, 400

        ids = data['ids']
        if not isinstance(ids, list) or len(ids) == 0:
            return {'error': 'ids must be a non-empty array'}, 400

        # Validate all IDs are integers
        try:
            ids = [int(i) for i in ids]
        except (ValueError, TypeError):
            return {'error': 'All IDs must be integers'}, 400

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                # Delete worksets (cascade deletes workset_entries)
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"DELETE FROM worksets WHERE id IN ({placeholders})", ids)
                deleted_count = cur.rowcount

                conn.commit()

        return {
            'success': True,
            'deleted': deleted_count,
            'requested': len(ids)
        }, 200

    except Exception as e:
        logger.error(f"Error bulk deleting worksets: {e}")
        return {'error': 'Failed to delete worksets'}, 500


# ============ PIPELINE TEMPLATE ENDPOINTS ============

@worksets_bp.route('/api/pipelines', methods=['GET'])
def list_pipelines() -> tuple[Dict[str, Any], int]:
    """List all pipeline templates."""
    try:
        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, description, pipeline_config, type, created_at, updated_at
                    FROM worksets
                    WHERE type = 'pipeline'
                    ORDER BY updated_at DESC
                """)
                rows = cur.fetchall()

                pipelines = []
                for row in rows:
                    config = row[3] or {}
                    pipelines.append({
                        'id': row[0],
                        'name': row[1],
                        'description': config.get('description', ''),
                        'steps': len(config.get('steps', [])),
                        'conditions': config.get('conditions'),
                        'created_at': row[5].isoformat() if row[5] else None,
                        'updated_at': row[6].isoformat() if row[6] else None
                    })

        return {
            'success': True,
            'pipelines': pipelines,
            'total': len(pipelines)
        }, 200

    except Exception as e:
        logger.error(f"Error listing pipelines: {e}")
        return {'error': 'Failed to list pipelines'}, 500


@worksets_bp.route('/api/pipelines', methods=['POST'])
def create_pipeline() -> tuple[Dict[str, Any], int]:
    """Create a new pipeline template."""
    try:
        data = request.get_json()
        if not data:
            return {'error': 'No data provided'}, 400

        name = data.get('name', '').strip()
        if not name:
            return {'error': 'Pipeline name is required'}, 400

        description = data.get('description', '')
        steps = data.get('steps', [])
        conditions = data.get('conditions')

        pipeline_config = {
            'description': description,
            'steps': steps,
            'conditions': conditions
        }

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO worksets (name, type, pipeline_config, total_entries, query)
                    VALUES (%s, 'pipeline', %s, 0, %s)
                    RETURNING id, created_at
                """, (name, json.dumps(pipeline_config), json.dumps({'pipeline': True})))

                row = cur.fetchone()
                pipeline_id = row[0]
                created_at = row[1]

                conn.commit()

        return {
            'success': True,
            'id': pipeline_id,
            'name': name,
            'steps': len(steps),
            'created_at': created_at.isoformat()
        }, 201

    except Exception as e:
        logger.error(f"Error creating pipeline: {e}")
        return {'error': 'Failed to create pipeline'}, 500


@worksets_bp.route('/api/pipelines/<int:pipeline_id>', methods=['GET'])
def get_pipeline(pipeline_id: int) -> tuple[Dict[str, Any], int]:
    """Get pipeline template details."""
    try:
        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, pipeline_config, type, created_at, updated_at
                    FROM worksets
                    WHERE id = %s AND type = 'pipeline'
                """, (pipeline_id,))

                row = cur.fetchone()
                if not row:
                    return {'error': 'Pipeline not found'}, 404

                config = row[2] or {}

        return {
            'success': True,
            'id': row[0],
            'name': row[1],
            'type': row[3],
            'config': config,
            'created_at': row[4].isoformat() if row[4] else None,
            'updated_at': row[5].isoformat() if row[5] else None
        }, 200

    except Exception as e:
        logger.error(f"Error getting pipeline: {e}")
        return {'error': 'Failed to get pipeline'}, 500


@worksets_bp.route('/api/pipelines/<int:pipeline_id>', methods=['PUT'])
def update_pipeline(pipeline_id: int) -> tuple[Dict[str, Any], int]:
    """Update pipeline template."""
    try:
        data = request.get_json()
        if not data:
            return {'error': 'No data provided'}, 400

        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                # Check pipeline exists
                cur.execute("SELECT id FROM worksets WHERE id = %s AND type = 'pipeline'", (pipeline_id,))
                if not cur.fetchone():
                    return {'error': 'Pipeline not found'}, 404

                # Build update
                name = data.get('name', '').strip()
                description = data.get('description', '')
                steps = data.get('steps', [])
                conditions = data.get('conditions')

                pipeline_config = {
                    'description': description,
                    'steps': steps,
                    'conditions': conditions
                }

                cur.execute("""
                    UPDATE worksets
                    SET name = %s, pipeline_config = %s, updated_at = %s
                    WHERE id = %s
                """, (name, json.dumps(pipeline_config), datetime.now(), pipeline_id))

                conn.commit()

        return {
            'success': True,
            'id': pipeline_id,
            'name': name,
            'steps': len(steps)
        }, 200

    except Exception as e:
        logger.error(f"Error updating pipeline: {e}")
        return {'error': 'Failed to update pipeline'}, 500


@worksets_bp.route('/api/pipelines/<int:pipeline_id>', methods=['DELETE'])
def delete_pipeline(pipeline_id: int) -> tuple[Dict[str, Any], int]:
    """Delete pipeline template."""
    try:
        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM worksets
                    WHERE id = %s AND type = 'pipeline'
                """, (pipeline_id,))

                if cur.rowcount == 0:
                    return {'error': 'Pipeline not found'}, 404

                conn.commit()

        return {'success': True, 'deleted': pipeline_id}, 200

    except Exception as e:
        logger.error(f"Error deleting pipeline: {e}")
        return {'error': 'Failed to delete pipeline'}, 500


@worksets_bp.route('/api/pipelines/<int:pipeline_id>/execute', methods=['POST'])
def execute_pipeline(pipeline_id: int) -> tuple[Dict[str, Any], int]:
    """Execute a pipeline on entries matching conditions."""
    try:
        data = request.get_json(silent=True) or {}
        scope = data.get('scope', 'all')  # 'all', 'filtered', 'workset'
        workset_id = data.get('workset_id')
        filters = data.get('filters')

        # Get pipeline config
        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT name, pipeline_config FROM worksets
                    WHERE id = %s AND type = 'pipeline'
                """, (pipeline_id,))

                row = cur.fetchone()
                if not row:
                    return {'error': 'Pipeline not found'}, 404

                pipeline_name = row[0]
                pipeline_config = row[1] or {}
                steps = pipeline_config.get('steps', [])
                conditions = pipeline_config.get('conditions') or filters

        if not steps:
            return {'error': 'Pipeline has no steps'}, 400

        # Get matching entries
        dictionary_service = get_dictionary_service()
        entry_ids = []

        if scope == 'workset' and workset_id:
            # Get entries from workset
            with current_app.pg_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT entry_id FROM workset_entries WHERE workset_id = %s
                    """, (workset_id,))
                    entry_ids = [row[0] for row in cur.fetchall()]
        elif conditions:
            # Query matching entries using bulk query service
            from app.services.bulk_query_service import BulkQueryService
            bqs = BulkQueryService(dictionary_service)

            try:
                if 'and' in conditions or 'or' in conditions:
                    condition = bqs.parse_condition(conditions)
                else:
                    condition = bqs.parse_condition({'and': conditions} if isinstance(conditions, list) else conditions)

                matching_ids, total = bqs.execute_query(condition, limit=10000)
                entry_ids = matching_ids
            except Exception as e:
                logger.warning(f"Condition parsing failed, using all entries: {e}")
                # Fallback to all entries
                all_entries, _ = dictionary_service.list_entries(limit=10000)
                entry_ids = [e.id for e in all_entries]
        else:
            # All entries
            all_entries, _ = dictionary_service.list_entries(limit=10000)
            entry_ids = [e.id for e in all_entries]

        if not entry_ids:
            return {
                'success': True,
                'message': 'No entries match the conditions',
                'matched': 0,
                'executed': 0
            }, 200

        # Execute pipeline steps on each entry
        from app.services.bulk_action_service import BulkActionService, BulkAction
        bas = BulkActionService(dictionary_service)

        results = {
            'pipeline_id': pipeline_id,
            'pipeline_name': pipeline_name,
            'matched': len(entry_ids),
            'executed': 0,
            'failed': 0,
            'skipped': 0,
            'step_results': []
        }

        for step_data in steps:
            action = BulkAction.from_dict(step_data)
            is_valid, errors = bas.validate_action(action)
            if not is_valid:
                return {'error': f'Invalid action: {errors}'}, 400

        # Process entries
        for entry_id in entry_ids:
            entry_results = []
            for i, step_data in enumerate(steps):
                action = BulkAction.from_dict(step_data)
                result = bas.execute_action(entry_id, action, dry_run=False)
                entry_results.append({
                    'step': i + 1,
                    'status': result.get('status')
                })

            # Count results
            for r in entry_results:
                if r['status'] == 'changed':
                    results['executed'] += 1
                    break  # Count once per entry if any step changed it
                elif r['status'] == 'skipped':
                    results['skipped'] += 1

            if not any(r['status'] == 'changed' for r in entry_results):
                results['skipped'] += 1

        results['step_count'] = len(steps)

        return results, 200

    except Exception as e:
        logger.error(f"Error executing pipeline: {e}")
        return {'error': f'Failed to execute pipeline: {str(e)}'}, 500
