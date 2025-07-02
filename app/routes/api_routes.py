"""
API routes for the dictionary application.
These routes provide JSON-based endpoints for frontend integration.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from ..services.dictionary_service import DictionaryService
from ..utils.exceptions import NotFoundError, ValidationError

# Create blueprint
api_bp = Blueprint('additional_api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


@api_bp.route('/search')
def search_entries():
    """Search for entries with query parameters."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Query parameter "q" is required'}), 400
        
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate limit and offset
        if limit <= 0 or limit > 1000:
            limit = 10
        if offset < 0:
            offset = 0
        
        dict_service = current_app.injector.get(DictionaryService)
        entries, total = dict_service.search_entries(
            query=query,
            limit=limit,
            offset=offset
        )
        
        # Convert entries to dictionaries for JSON response
        entry_dicts = [entry.to_dict() for entry in entries]
        
        return jsonify({
            'entries': entry_dicts,
            'total': total,
            'query': query,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/entries')
def list_entries():
    """List entries with pagination."""
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate parameters
        if limit <= 0 or limit > 1000:
            limit = 10
        if offset < 0:
            offset = 0
        
        dict_service = current_app.injector.get(DictionaryService)
        entries = dict_service.list_entries(limit=limit, offset=offset)
        total = dict_service.count_entries()
        
        # Convert entries to dictionaries for JSON response
        entry_dicts = [entry.to_dict() for entry in entries]
        
        return jsonify({
            'entries': entry_dicts,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error listing entries: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/entries/<entry_id>')
def get_entry(entry_id: str):
    """Get a specific entry by ID."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        entry = dict_service.get_entry(entry_id)
        
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
        
        return jsonify(entry.to_dict())
        
    except NotFoundError:
        return jsonify({'error': 'Entry not found'}), 404
    except Exception as e:
        logger.error(f"Error getting entry {entry_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# LIFT Ranges API endpoints
@api_bp.route('/ranges')
def get_all_ranges():
    """Get all available LIFT ranges."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        ranges = dict_service.get_lift_ranges()
        
        return jsonify({
            'ranges': ranges,
            'available_types': list(ranges.keys())
        })
        
    except Exception as e:
        logger.error(f"Error getting ranges: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/ranges/<range_type>')
def get_range_by_type(range_type: str):
    """Get a specific range type (e.g., grammatical-info, relation-types)."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        ranges = dict_service.get_lift_ranges()
        
        # Handle both singular and plural forms
        range_data = None
        if range_type in ranges:
            range_data = ranges[range_type]
        else:
            # Try alternative mappings
            type_mappings = {
                'grammatical-info': ['grammatical-info', 'grammatical-infos'],
                'relation-types': ['lexical-relation', 'lexical-relations', 'relation-types'],
                'variant-types': ['variant-types', 'variants'],
                'semantic-domains': ['semantic-domain', 'semantic-domains', 'semantic-domain-ddp4'],
                'usage-types': ['usage-type', 'usage-types'],
                'status': ['status'],
                'etymology': ['etymology'],
                'note-types': ['note-type', 'note-types'],
            }
            
            for alt_key in type_mappings.get(range_type, []):
                if alt_key in ranges:
                    range_data = ranges[alt_key]
                    break
        
        if not range_data:
            return jsonify({'error': f'Range type "{range_type}" not found'}), 404
        
        return jsonify({
            'type': range_type,
            'data': range_data
        })
        
    except Exception as e:
        logger.error(f"Error getting range {range_type}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# Query validation endpoint
@api_bp.route('/queries/validate', methods=['POST'])
def validate_query():
    """Validate a query for performance and syntax."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No query data provided'}), 400
        
        query = data.get('query', '')
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Basic validation - in a real implementation, this would be more sophisticated
        validation_result = {
            'valid': True,
            'estimated_time': 0.1,
            'warnings': [],
            'suggestions': []
        }
        
        # Check for potentially slow operations
        if len(query) > 100:
            validation_result['warnings'].append('Long queries may be slower')
        
        if '*' in query:
            validation_result['warnings'].append('Wildcard searches may be resource-intensive')
            validation_result['estimated_time'] = 2.0
        
        return jsonify(validation_result)
        
    except Exception as e:
        logger.error(f"Error validating query: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
