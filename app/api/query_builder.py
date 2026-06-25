#!/usr/bin/env python3

"""
Query Builder API endpoints for dynamic query construction.
Implements TDD-validated interface per specification section 3.1.1.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify
from flasgger import swag_from
import logging
import time
from typing import Dict, Any, List

from app.services.query_builder_service import QueryBuilderService
from app.services.field_registry_service import get_field_registry_service

logger = logging.getLogger(__name__)

query_builder_bp = Blueprint('query_builder', __name__, url_prefix='/api/query-builder')


@query_builder_bp.route('/fields', methods=['GET'])
@swag_from({
    'tags': ['Query Builder'],
    'summary': 'Get searchable fields',
    'description': 'Returns a merged list of searchable fields from LIFT registry, database ranges, and discovered custom fields',
    'parameters': [
        {
            'name': 'search',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': 'Filter fields by search term (matches label, path, or category)'
        },
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 100,
            'description': 'Maximum number of fields to return'
        }
    ],
    'responses': {
        200: {
            'description': 'List of searchable fields',
            'schema': {
                'type': 'object',
                'properties': {
                    'fields': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'label': {'type': 'string', 'description': 'Human-readable field label'},
                                'path': {'type': 'string', 'description': 'Field path for queries'},
                                'category': {'type': 'string', 'description': 'Field category (Entry, Sense, Example, Range, etc.)'}
                            }
                        }
                    },
                    'count': {'type': 'integer', 'description': 'Total number of fields returned'}
                }
            }
        },
        500: {
            'description': 'Internal server error',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def get_fields() -> tuple[Dict[str, Any], int]:
    """Get all available searchable fields for query building."""
    try:
        # Get query parameters
        search_term = request.args.get('search', '').strip()
        limit = request.args.get('limit', 100, type=int)
        
        # Get the field registry service
        field_service = get_field_registry_service()
        
        # Get all fields
        if search_term:
            fields = field_service.search_fields(search_term, limit=limit)
        else:
            all_fields = field_service.get_fields()
            fields = all_fields[:limit]
        
        return {
            'fields': fields,
            'count': len(fields)
        }, 200
        
    except Exception as e:
        logger.error(f"Error getting searchable fields: {e}")
        return {'error': 'Failed to retrieve fields'}, 500


@query_builder_bp.route('/validate', methods=['POST'])
@swag_from({
    'tags': ['Query Builder'],
    'summary': 'Validate query',
    'description': 'Real-time validation of query syntax and performance estimation',
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
                    'estimated_count': {'type': 'integer'},
                    'performance_score': {'type': 'string'},
                    'validation_errors': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        }
    }
})
def validate_query() -> tuple[Dict[str, Any], int]:
    """Validate query syntax and estimate performance."""
    try:
        data = request.get_json()
        if not data:
            return {'error': 'No JSON data provided'}, 400
        
        service = QueryBuilderService()
        result = service.validate_query(data)
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Error validating query: {e}")
        return {'error': 'Failed to validate query'}, 500


@query_builder_bp.route('/preview', methods=['POST'])
@swag_from({
    'tags': ['Query Builder'],
    'summary': 'Preview query results',
    'description': 'Get a preview of entries that match the query',
    'parameters': [{
        'name': 'query_data',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'filters': {'type': 'array', 'items': {'type': 'object'}},
                'limit': {'type': 'integer', 'maximum': 20, 'default': 5}
            }
        }
    }],
    'responses': {
        200: {
            'description': 'Query preview results',
            'schema': {
                'type': 'object',
                'properties': {
                    'preview_entries': {'type': 'array', 'items': {'type': 'object'}},
                    'total_count': {'type': 'integer'}
                }
            }
        }
    }
})
def preview_query() -> tuple[Dict[str, Any], int]:
    """Get preview results for query."""
    try:
        data = request.get_json()
        if not data:
            return {'error': 'No JSON data provided'}, 400
        
        service = QueryBuilderService()
        result = service.preview_query(data)
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Error previewing query: {e}")
        return {'error': 'Failed to preview query'}, 500


@query_builder_bp.route('/save', methods=['POST'])
@swag_from({
    'tags': ['Query Builder'],
    'summary': 'Save named query',
    'description': 'Save a query with a name and description for reuse',
    'parameters': [{
        'name': 'save_data',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'description': {'type': 'string'},
                'query': {'type': 'object'}
            },
            'required': ['name', 'query']
        }
    }],
    'responses': {
        201: {
            'description': 'Query saved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'query_id': {'type': 'string'},
                    'name': {'type': 'string'}
                }
            }
        }
    }
})
def save_query() -> tuple[Dict[str, Any], int]:
    """Save a named query for reuse."""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'query' not in data:
            return {'error': 'Missing required fields: name, query'}, 400
        
        service = QueryBuilderService()
        result = service.save_query(data)
        
        return result, 201
        
    except Exception as e:
        logger.error(f"Error saving query: {e}")
        return {'error': 'Failed to save query'}, 500


@query_builder_bp.route('/saved', methods=['GET'])
@swag_from({
    'tags': ['Query Builder'],
    'summary': 'List saved queries',
    'description': 'Get list of all saved queries',
    'responses': {
        200: {
            'description': 'List of saved queries',
            'schema': {
                'type': 'object',
                'properties': {
                    'queries': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'name': {'type': 'string'},
                                'description': {'type': 'string'},
                                'created_at': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def get_saved_queries() -> tuple[Dict[str, Any], int]:
    """Get list of saved queries."""
    try:
        service = QueryBuilderService()
        result = service.get_saved_queries()
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Error getting saved queries: {e}")
        return {'error': 'Failed to get saved queries'}, 500


@query_builder_bp.route('/execute', methods=['POST'])
@swag_from({
    'tags': ['Query Builder'],
    'summary': 'Execute query and create workset',
    'description': 'Execute query and create a workset with the results',
    'parameters': [{
        'name': 'execute_data',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'workset_name': {'type': 'string'},
                'query': {'type': 'object'}
            },
            'required': ['workset_name', 'query']
        }
    }],
    'responses': {
        201: {
            'description': 'Workset created from query',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'workset_id': {'type': 'string'},
                    'entry_count': {'type': 'integer'},
                    'workset_name': {'type': 'string'}
                }
            }
        }
    }
})
def execute_query() -> tuple[Dict[str, Any], int]:
    """Execute query and create workset."""
    try:
        data = request.get_json()
        if not data or 'workset_name' not in data or 'query' not in data:
            return {'error': 'Missing required fields: workset_name, query'}, 400
        
        service = QueryBuilderService()
        result = service.execute_query(data)
        
        return result, 201
        
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {'error': 'Failed to execute query'}, 500
