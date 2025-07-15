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
    'description': 'Creates a filtered collection of entries based on query criteria',
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
        data = request.get_json()
        if not data:
            return {'error': 'No JSON data provided'}, 400
        
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
    'description': 'Update the query criteria for an existing workset',
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
        data = request.get_json()
        if not data:
            return {'error': 'No JSON data provided'}, 400

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
    'description': 'Apply bulk operations to all entries in a workset',
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
        data = request.get_json()
        if not data:
            return {'error': 'No JSON data provided'}, 400

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
        validation_result = workset_service.validate_query(WorksetQuery.from_dict(data))
        
        return validation_result, 200
        
    except Exception as e:
        logger.error(f"Error validating query: {e}")
        return {'error': 'Failed to validate query'}, 500
