"""
API endpoints for managing dictionary entries.
"""

import logging
from flask import Blueprint, request, jsonify, current_app

from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
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
    # Create a BaseX connector using app config
    connector = BaseXConnector(
        host=current_app.config['BASEX_HOST'],
        port=current_app.config['BASEX_PORT'],
        username=current_app.config['BASEX_USERNAME'],
        password=current_app.config['BASEX_PASSWORD'],
        database=current_app.config['BASEX_DATABASE'],
    )
    
    # Create and return a dictionary service
    return DictionaryService(connector)


@entries_bp.route('/', methods=['GET'])
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
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'lexical_unit')
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # List entries
        entries, total_count = dict_service.list_entries(limit=limit, offset=offset, sort_by=sort_by)
        
        # Prepare response
        response = {
            'entries': [entry.to_dict() for entry in entries],
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
        }        
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


@entries_bp.route('/', methods=['POST'])
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
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Create entry object
        entry = Entry.from_dict(data)
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Create entry
        entry_id = dict_service.create_entry(entry)
        
        # Return response
        return jsonify({'id': entry_id}), 201
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating entry: {e}")
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
        logger.error(f"Error updating entry {entry_id}: {e}")
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
        logger.error(f"Error deleting entry {entry_id}: {e}")
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
        logger.error(f"Error getting related entries for {entry_id}: {e}")
        return jsonify({'error': str(e)}), 500
