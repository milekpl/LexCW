"""
API endpoints for searching dictionary entries.
"""

import logging
from flask import Blueprint, request, jsonify, current_app

from app.services.dictionary_service import DictionaryService
from app.database.connector_factory import create_database_connector
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
    # Check if there's a pre-configured service (for testing) - prioritize this
    if hasattr(current_app, 'dict_service') and current_app.dict_service:
        return current_app.dict_service
    
    # Try to use injector (for production and dependency injection)
    try:
        from app import injector
        return injector.get(DictionaryService)
    except (ImportError, AttributeError):
        pass
    
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


@search_bp.route('/', methods=['GET'], strict_slashes=False)
def search_entries():
    """
    Search for dictionary entries using XQuery-based search
    ---
    tags:
      - search
    parameters:
      - name: q
        in: query
        type: string
        required: true
        description: Search query string
        example: "test"
      - name: fields
        in: query
        type: string
        required: false
        description: Comma-separated list of fields to search in
        default: "lexical_unit,glosses,definitions,note"
        example: "lexical_unit,pronunciations,senses,note"
      - name: limit
        in: query
        type: integer
        required: false
        description: Maximum number of entries to return
        default: 100
        example: 20
      - name: offset
        in: query
        type: integer
        required: false
        description: Number of entries to skip for pagination
        default: 0
        example: 0
    responses:
      200:
        description: Search results
        schema:
          type: object
          properties:
            query:
              type: string
              description: The search query used
              example: "test"
            fields:
              type: array
              items:
                type: string
              description: Fields that were searched
              example: ["lexical_unit", "senses"]
            entries:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Entry ID
                  lexical_unit:
                    type: object
                    description: Lexical unit with language codes
                  pronunciations:
                    type: object
                    description: Pronunciation forms by writing system
                  senses:
                    type: array
                    description: Array of sense objects
                  grammatical_info:
                    type: string
                    description: Grammatical information
                  etymologies:
                    type: array
                    description: Etymology information
                  relations:
                    type: array
                    description: Semantic relations
                  variants:
                    type: array
                    description: Variant forms
            total:
              type: integer
              description: Total number of matching entries
              example: 150
            limit:
              type: integer
              description: Limit used for pagination
              example: 20
            offset:
              type: integer
              description: Offset used for pagination
              example: 0
      400:
        description: Invalid request parameters
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
    """
    try:
        # Get query parameters
        query = request.args.get('q', '')
        fields_str = request.args.get('fields', 'lexical_unit,glosses,definitions,note,citation_form,example')
        limit_raw = request.args.get('limit', 100)
        offset_raw = request.args.get('offset', 0)
        try:
            limit = int(limit_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'Limit must be an integer'}), 400
        try:
            offset = int(offset_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'Offset must be an integer'}), 400

        # Validate input parameters
        if not query.strip():
            return jsonify({'error': 'Query parameter is required and cannot be empty'}), 400
        if limit < 0:
            return jsonify({'error': 'Limit must be non-negative'}), 400
        if offset < 0:
            return jsonify({'error': 'Offset must be non-negative'}), 400

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
            'total': total_count,
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
    try:        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get ranges from service
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        
        # Return response
        return jsonify({
            'success': True,
            'data': ranges
        })
        
    except Exception as e:
        logger.error("Error getting ranges: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        
        # Get all ranges
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        
        # Special case handling for renamed ranges
        if range_id == 'relation-types' and 'relation-type' in ranges:
            range_id = 'relation-type'
        elif range_id == 'variant-types' and 'variant-type' in ranges:
            range_id = 'variant-type'
        
        # Check if range exists
        if range_id not in ranges:
            raise NotFoundError(f"Range '{range_id}' not found")
        
        # Return response
        return jsonify({
            'success': True,
            'data': ranges[range_id]
        })
        
    except NotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error("Error getting range values for %s: %s", range_id, str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@search_bp.route('/ranges/relation-types', methods=['GET'])
def get_relation_types():
    """
    Get the relation types from ranges.
    
    Returns:
        JSON response with relation types.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get all ranges
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        
        # Look for relation types in different formats
        relation_types = None
        if 'relation-types' in ranges:
            relation_types = ranges['relation-types']
        elif 'relation-type' in ranges:
            relation_types = ranges['relation-type']
        
        if not relation_types:
            raise NotFoundError("Relation types not found in ranges")
        
        # Return response
        return jsonify({
            'success': True,
            'data': relation_types
        })
        
    except NotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error("Error getting relation types: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@search_bp.route('/ranges/variant-types', methods=['GET'])
def get_variant_types():
    """
    Get the variant types from ranges.
    
    Returns:
        JSON response with variant types.
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get all ranges
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        
        # Look for variant types in different formats
        variant_types = None
        if 'variant-types' in ranges:
            variant_types = ranges['variant-types']
        elif 'variant-type' in ranges:
            variant_types = ranges['variant-type']
        
        if not variant_types:
            raise NotFoundError("Variant types not found in ranges")
        
        # Return response
        return jsonify({
            'success': True,
            'data': variant_types
        })
        
    except NotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error("Error getting variant types: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
