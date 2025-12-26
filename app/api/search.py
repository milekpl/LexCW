"""
API endpoints for searching dictionary entries.
"""

import logging
from flask import Blueprint, request, jsonify, current_app, session
from flasgger import swag_from

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
@swag_from({
        'tags': ['Search'],
        'parameters': [
                {'name': 'q', 'in': 'query', 'type': 'string', 'required': True, 'description': 'Search query string', 'example': 'test'},
                {'name': 'fields', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Comma-separated list of fields to search in', 'default': 'lexical_unit,glosses,definitions,note', 'example': 'lexical_unit,pronunciations,senses,note'},
                {'name': 'pos', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Part of speech to filter by', 'example': 'noun'},
                {'name': 'exact_match', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Whether to perform exact match (default: false)', 'example': 'false'},
                {'name': 'case_sensitive', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Whether the search should be case-sensitive (default: false)', 'example': 'false'},
                {'name': 'limit', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Maximum number of entries to return', 'default': 100, 'example': 20},
                {'name': 'offset', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Number of entries to skip for pagination', 'default': 0, 'example': 0}
        ],
        'responses': {
                '200': {'description': 'Search results'},
                '400': {'description': 'Invalid request parameters'},
                '500': {'description': 'Internal server error'}
        }
})
def search_entries():
    """Search for dictionary entries using XQuery-based search"""
    try:
        # Get query parameters
        query = request.args.get('q', '')
        fields_str = request.args.get('fields', 'lexical_unit,glosses,definitions,note,citation_form,example')
        pos = request.args.get('pos')  # Part of speech filter
        exact_match_raw = request.args.get('exact_match', 'false')
        case_sensitive_raw = request.args.get('case_sensitive', 'false')
        limit_raw = request.args.get('limit', 100)
        offset_raw = request.args.get('offset', 0)

        # Parse boolean parameters
        exact_match = exact_match_raw.lower() in ['true', '1', 'yes', 'on']
        case_sensitive = case_sensitive_raw.lower() in ['true', '1', 'yes', 'on']

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
        project_id = session.get('project_id')
        entries, total_count = dict_service.search_entries(
            project_id=project_id,
            query=query,
            fields=fields,
            limit=limit,
            offset=offset,
            pos=pos,
            exact_match=exact_match,
            case_sensitive=case_sensitive
        )

        # Prepare response
        response = {
            'query': query,
            'fields': fields,
            'entries': [entry.to_dict() for entry in entries],
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'pos': pos,  # Include pos in response to show it was applied
        }
        return jsonify(response)

    except Exception as e:
        import traceback
        logger.error("Error searching entries: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
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
        
        # Canonical forms only - no backward compatibility mappings
        
        # Check if range exists; if not, attempt a forced refresh (handles transient load race)
        if range_id not in ranges:
            logger.debug("Range %s not found in cached ranges; forcing refresh", range_id)
            try:
                ranges = dict_service.get_ranges(force_reload=True) if hasattr(dict_service, 'get_ranges') else ranges
            except Exception as e:
                logger.warning("Forced ranges refresh failed: %s", str(e))
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


@search_bp.route('/ranges/lexical-relation', methods=['GET'])
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
        
        # Look for relation types in canonical format only
        if 'lexical-relation' not in ranges:
            raise NotFoundError("Relation types not found in ranges")

        relation_types = ranges['lexical-relation']
        
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


@search_bp.route('/ranges/variant-type', methods=['GET'])
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
        
        # Look for variant types in canonical format only
        if 'variant-type' not in ranges:
            raise NotFoundError("Variant types not found in ranges")

        variant_types = ranges['variant-type']
        
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
