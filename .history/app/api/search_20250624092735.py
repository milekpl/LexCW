"""
API endpoints for searching dictionary entries.
"""

import logging
from flask import Blueprint, request, jsonify, current_app

from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
from app.utils.exceptions import NotFoundError

# Create blueprint
search_bp = Blueprint('search', __name__)
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


@search_bp.route('/', methods=['GET'])
def search_entries():
    """
    Search for dictionary entries.
    
    Query parameters:
        q: Search query.
        fields: Comma-separated list of fields to search in.
        limit: Maximum number of entries to return.
        offset: Number of entries to skip.
    
    Returns:
        JSON response with search results.
    """
    try:
        # Get query parameters
        query = request.args.get('q', '')
        fields_str = request.args.get('fields', 'lexical_unit,glosses,definitions')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Parse fields
        fields = [field.strip() for field in fields_str.split(',') if field.strip()]
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Search entries
        entries, total_count = dict_service.search_entries(
            query=query,
            fields=fields,
            limit=limit,
            offset=offset
        )
        
        # Prepare response
        response = {
            'query': query,
            'fields': fields,
            'entries': [entry.to_dict() for entry in entries],
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
        }        
        return jsonify(response)
        
    except Exception as e:
        logger.error("Error searching entries: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/grammatical', methods=['GET'])
def search_by_grammatical_info():
    """
    Search for entries by grammatical information.
    
    Query parameters:
        value: Grammatical information value.
    
    Returns:
        JSON response with search results.
    """
    try:
        # Get query parameters
        grammatical_info = request.args.get('value', '')
        if not grammatical_info:
            return jsonify({'error': 'Missing grammatical information value'}), 400
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get entries by grammatical info
        entries = dict_service.get_entries_by_grammatical_info(grammatical_info)
        
        # Prepare response
        response = {
            'grammatical_info': grammatical_info,
            'entries': [entry.to_dict() for entry in entries],
            'count': len(entries),
        }        
        return jsonify(response)
        
    except Exception as e:
        logger.error("Error searching entries by grammatical info: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/ranges', methods=['GET'])
def get_ranges():
    """
    Get the ranges data for the dictionary.
    
    Returns:
        JSON response with ranges data.
    """
    try:        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get ranges (placeholder - needs implementation)
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        
        # Return response
        return jsonify(ranges)
        
    except Exception as e:
        logger.error("Error getting ranges: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/ranges/<range_id>', methods=['GET'])
def get_range_values(range_id):
    """
    Get the values for a specific range.
    
    Args:
        range_id: ID of the range.
    
    Returns:
        JSON response with range values.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get range values
        values = dict_service.get_range_values(range_id)
        
        # Return response
        return jsonify(values)
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting range values for {range_id}: {e}")
        return jsonify({'error': str(e)}), 500
