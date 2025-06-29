"""
API endpoints for managing dictionary entries.
"""

import json
import logging
from flask import Blueprint, request, jsonify, current_app

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app.database.connector_factory import create_database_connector
from app.models.entry import Entry
from app.utils.exceptions import NotFoundError, ValidationError

# Create blueprint
entries_bp = Blueprint('entries', __name__)
logger = logging.getLogger(__name__)


def get_dictionary_service():
    """
    Get an instance of the dictionary service.
    
    Returns:
        DictionaryService instance.
    """
    # Check if there's a pre-configured service (for testing)
    if hasattr(current_app, 'dict_service') and current_app.dict_service:
        return current_app.dict_service
    
    # Create a database connector using app config
    connector = create_database_connector(
        host=current_app.config.get('BASEX_HOST', 'localhost'),
        port=current_app.config.get('BASEX_PORT', 1984),
        username=current_app.config.get('BASEX_USERNAME', 'admin'),
        password=current_app.config.get('BASEX_PASSWORD', 'admin'),
        database=current_app.config.get('BASEX_DATABASE', 'dictionary'),
    )
    
    # Create and return a dictionary service
    return DictionaryService(connector)


@entries_bp.route('/', methods=['GET'], strict_slashes=False)
def list_entries():
    """
    List dictionary entries with pagination.
    
    Query parameters:
        limit: Maximum number of entries to return.
        offset: Number of entries to skip.
        sort_by: Field to sort by.
    
    Returns:
        JSON response with list of entries.
    """
    try:
        # Get query parameters - support both offset/limit and page/per_page formats
        limit = request.args.get('limit', None, type=int)
        offset = request.args.get('offset', None, type=int)
        page = request.args.get('page', None, type=int)
        per_page = request.args.get('per_page', None, type=int)
        sort_by = request.args.get('sort_by', 'lexical_unit')
        
        # Validate individual parameters first
        if page is not None and page < 1:
            return jsonify({'error': 'Page parameter must be a positive integer'}), 400
        if per_page is not None and per_page < 1:
            return jsonify({'error': 'Per_page parameter must be a positive integer'}), 400
        if limit is not None and limit < 0:
            return jsonify({'error': 'Limit parameter must be non-negative'}), 400
        if offset is not None and offset < 0:
            return jsonify({'error': 'Offset parameter must be non-negative'}), 400
        
        # If page/per_page are provided, convert to offset/limit
        if page is not None and per_page is not None:
            limit = per_page
            offset = (page - 1) * per_page
        else:
            if limit is None:
                limit = 100
            if offset is None:
                offset = 0
        # Redis cache key
        cache_key = f"entries:{limit}:{offset}:{sort_by}"
        cache = CacheService()
        if cache.is_available():
            cached = cache.get(cache_key)
            if cached:
                return jsonify(json.loads(cached))
        # Get dictionary service
        dict_service = get_dictionary_service()
        # List entries
        entries, total_count = dict_service.list_entries(limit=limit, offset=offset, sort_by=sort_by)
        # Prepare response
        response = {
            'entries': [entry.to_dict() for entry in entries],
            'total': total_count,
            'limit': limit,
            'offset': offset,
        }
        
        # Add page/per_page if they were provided in the request
        if page is not None and per_page is not None:
            response['page'] = page
            response['per_page'] = per_page
        if cache.is_available():
            cache.set(cache_key, json.dumps(response), ttl=300)
        return jsonify(response)
    except (ValidationError, ValueError) as e:
        logger.error("Error listing entries: %s", str(e))
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error listing entries: %s", str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<entry_id>', methods=['GET'])
def get_entry(entry_id):
    """
    Get a dictionary entry by ID.
    
    Args:
        entry_id: ID of the entry.
    
    Returns:
        JSON response with the entry.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get entry
        entry = dict_service.get_entry(entry_id)        
        # Return response
        return jsonify(entry.to_dict())
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/', methods=['POST'], strict_slashes=False)
def create_entry():
    """
    Create a new dictionary entry.
    
    Request body:
        JSON object with entry data.
    
    Returns:
        JSON response with the created entry ID.
    """
    try:
        # Get request data
        try:
            data = request.get_json()
        except Exception as json_error:
            return jsonify({'error': f'Invalid JSON: {str(json_error)}'}), 400
            
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Create entry object
        entry = Entry.from_dict(data)
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Create entry
        entry_id = dict_service.create_entry(entry)        
        # Return response
        return jsonify({'success': True, 'entry_id': entry_id}), 201
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error creating entry: %s", str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<entry_id>', methods=['PUT'])
def update_entry(entry_id):
    """
    Update a dictionary entry.
    
    Args:
        entry_id: ID of the entry to update.
    
    Request body:
        JSON object with entry data.
    
    Returns:
        JSON response with success status.
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Ensure ID in path matches ID in data
        if data.get('id') != entry_id:
            return jsonify({'error': 'Entry ID in path does not match ID in data'}), 400
        
        # Create entry object
        entry = Entry.from_dict(data)
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Update entry
        dict_service.update_entry(entry)        
        # Return response
        return jsonify({'success': True})
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error updating entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    """
    Delete a dictionary entry.
    
    Args:
        entry_id: ID of the entry to delete.
    
    Returns:
        JSON response with success status.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Delete entry
        dict_service.delete_entry(entry_id)        
        # Return response
        return jsonify({'success': True})
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error("Error deleting entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<entry_id>/related', methods=['GET'])
def get_related_entries(entry_id):
    """
    Get entries related to the specified entry.
    
    Args:
        entry_id: ID of the entry.
    
    Query parameters:
        relation_type: Type of relation to filter by.
    
    Returns:
        JSON response with list of related entries.
    """
    try:
        # Get query parameters
        relation_type = request.args.get('relation_type')
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get related entries
        entries = dict_service.get_related_entries(entry_id, relation_type)
        
        # Prepare response
        response = {
            'entries': [entry.to_dict() for entry in entries],
            'count': len(entries),
        }        
        return jsonify(response)
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting related entries for %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500
