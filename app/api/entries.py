"""
API endpoints for managing dictionary entries.
"""

import json
import logging
from typing import Any
from flask import Blueprint, request, jsonify, current_app
from flasgger import swag_from

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app.models.entry import Entry
import datetime
from app.utils.exceptions import NotFoundError, ValidationError

# Create blueprint
entries_bp = Blueprint('entries', __name__)
logger = logging.getLogger(__name__)


def get_dictionary_service() -> DictionaryService:
    """
    Get an instance of the dictionary service from the current app context.
    
    Returns:
        DictionaryService instance.
    """
    return current_app.injector.get(DictionaryService)


@entries_bp.route('/', methods=['GET'], strict_slashes=False)
def list_entries() -> Any:
    """
    List dictionary entries with pagination, filtering, and sorting
    ---
    tags:
      - Entries
    parameters:
      - name: limit
        in: query
        type: integer
        required: false
        description: Maximum number of entries to return (default 100)
        example: 20
      - name: offset
        in: query
        type: integer
        required: false
        description: Number of entries to skip (default 0)
        example: 0
      - name: page
        in: query
        type: integer
        required: false
        description: Page number (alternative to offset/limit)
        example: 1
      - name: per_page
        in: query
        type: integer
        required: false
        description: Entries per page (alternative to offset/limit)
        example: 20
      - name: sort_by
        in: query
        type: string
        required: false
        description: Field to sort by
        enum: [lexical_unit, id, date_created, date_modified, citation_form, part_of_speech, gloss, definition]
        default: lexical_unit
      - name: sort_order
        in: query
        type: string
        required: false
        description: Sort order
        enum: [asc, desc]
        default: asc
      - name: filter_text
        in: query
        type: string
        required: false
        description: Text to filter entries by (searches in lexical_unit)
        example: test
    responses:
      200:
        description: List of entries
        schema:
          type: object
          properties:
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
                  senses:
                    type: array
                    description: Array of sense objects
                  notes:
                    type: object
                    description: |
                      Entry notes, supporting both legacy string format and multilingual object format.
                      Legacy format: {"general": "simple string note"}
                      Multilingual format: {"general": {"en": "English note", "pt": "Portuguese note"}}
                    additionalProperties:
                      oneOf:
                        - type: string
                          description: Legacy format - simple string note
                        - type: object
                          description: Multilingual format - notes by language code
                          additionalProperties:
                            type: string
                  custom_fields:
                    type: object
                    description: Custom fields for the entry
                    additionalProperties: true
                  date_modified:
                    type: string
                    description: Last modification date
                  date_created:
                    type: string
                    description: Creation date
            total_count:
              type: integer
              description: Total number of entries
            total:
              type: integer
              description: Total number of entries (backward compatibility)
            limit:
              type: integer
              description: Applied limit
            offset:
              type: integer
              description: Applied offset
            page:
              type: integer
              description: Current page (if pagination used)
            per_page:
              type: integer
              description: Entries per page (if pagination used)
      400:
        description: Bad request (invalid parameters)
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
        # Get query parameters - support both offset/limit and page/per_page formats
        limit = request.args.get('limit', None, type=int)
        offset = request.args.get('offset', None, type=int)
        page = request.args.get('page', None, type=int)
        per_page = request.args.get('per_page', None, type=int)
        sort_by = request.args.get('sort_by', 'lexical_unit')
        sort_order = request.args.get('sort_order', 'asc')
        filter_text = request.args.get('filter_text', '')
        
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
        # Redis cache key - include all relevant parameters for cache correctness
        cache_key = f"entries:{limit}:{offset}:{sort_by}:{sort_order}:{filter_text}"
        cache = CacheService()
        if cache.is_available():
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"Returning cached entries for key: {cache_key}")
                return jsonify(json.loads(cached))
        # Get dictionary service
        dict_service = get_dictionary_service()
        # List entries with all parameters
        entries, total_count = dict_service.list_entries(
            limit=limit, 
            offset=offset, 
            sort_by=sort_by,
            sort_order=sort_order,
            filter_text=filter_text
        )

        # Removed debug print for entry dates
        # Prepare response
        try:
            response_entries = []
            for i, entry in enumerate(entries):
                try:
                    response_entries.append(entry.to_display_dict())
                except AttributeError as e:
                    logger.error(f"Entry at index {i} has wrong type: {type(entry)}. Error: {e}")
                    raise e
            response = {
                'entries': response_entries,
                'total_count': total_count,  # Use total_count for consistency with other APIs
                'total': total_count,        # Keep total for backward compatibility
                'limit': limit,
                'offset': offset,
            }
        except Exception as e:
            logger.error(f"Error preparing response: {e}")
            raise e
            
        # Add page/per_page if they were provided in the request
        if page is not None and per_page is not None:
            response['page'] = page
            response['per_page'] = per_page
        # Cache the response for 3 minutes (180 seconds) for better user experience
        if cache.is_available():
            cache.set(cache_key, json.dumps(response), ttl=180)
            logger.info(f"Cached entries response for key: {cache_key}")
        return jsonify(response)
    except (ValidationError, ValueError) as e:
        logger.error("Error listing entries: %s", str(e))
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error listing entries: %s", str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<string:entry_id>', methods=['GET'])
def get_entry(entry_id: str) -> Any:
    """
    Get a dictionary entry by ID
    ---
    tags:
      - Entries
    parameters:
      - name: entry_id
        in: path
        type: string
        required: true
        description: ID of the entry to retrieve
        example: "test_entry_123"
    responses:
      200:
        description: Entry data
        schema:
          type: object
          properties:
            id:
              type: string
              description: Entry ID
            lexical_unit:
              type: object
              description: Lexical unit with language codes
            senses:
              type: array
              description: Array of sense objects
            notes:
              type: object
              description: |
                Entry notes, supporting both legacy string format and multilingual object format.
                Legacy format: {"general": "simple string note"}
                Multilingual format: {"general": {"en": "English note", "pt": "Portuguese note"}}
              additionalProperties:
                oneOf:
                  - type: string
                    description: Legacy format - simple string note
                  - type: object
                    description: Multilingual format - notes by language code
                    additionalProperties:
                      type: string
              example: {
                "general": {"en": "A general note in English", "pt": "Uma nota geral em português"},
                "usage": "Simple usage note"
              }
            custom_fields:
              type: object
              description: Custom fields for the entry
              additionalProperties: true
            date_modified:
              type: string
              description: Last modification date
            date_created:
              type: string
              description: Creation date
      404:
        description: Entry not found
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
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Get entry
        entry = dict_service.get_entry(entry_id)
        
        # Check if entry was found
        if entry is None:
            return jsonify({'error': f'Entry with ID {entry_id} not found'}), 404
            
        # Return response
        return jsonify(entry.to_dict())
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/', methods=['POST'], strict_slashes=False)
def create_entry() -> Any:
    """
    Create a new dictionary entry
    ---
    tags:
      - Entries
    parameters:
      - name: body
        in: body
        required: true
        description: Entry data to create
        schema:
          type: object
          required:
            - id
            - lexical_unit
          properties:
            id:
              type: string
              description: Unique entry identifier
              example: "test_entry_123"
            lexical_unit:
              type: object
              description: Lexical unit forms by language code
              example: {"en": "test", "pl": "test"}
            pronunciations:
              type: object
              description: Pronunciation forms by writing system (supports non-standard codes like 'seh-fonipa')
              example: {"seh-fonipa": "/tɛstɛ/"}
            grammatical_info:
              type: string
              description: Grammatical information
              example: "noun"
            senses:
              type: array
              description: Array of sense objects
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Sense identifier (auto-generated if not provided)
                  gloss:
                    type: object
                    description: Gloss by language code
                  definition:
                    type: object
                    description: Definition by language code
            etymologies:
              type: array
              description: Etymology information
              items:
                type: object
                properties:
                  type:
                    type: string
                  source:
                    type: string
                  form:
                    type: object
                  gloss:
                    type: object
            relations:
              type: array
              description: Semantic relations to other entries
              items:
                type: object
                properties:
                  type:
                    type: string
                    example: "synonym"
                  ref:
                    type: string
                    example: "target_entry_id"
            variants:
              type: array
              description: Variant forms
              items:
                type: object
                properties:
                  form:
                    type: object
                    description: Variant form by language
            notes:
              type: object
              description: |
                Entry notes, supporting both legacy string format and multilingual object format.
                Legacy format: {"general": "simple string note"}
                Multilingual format: {"general": {"en": "English note", "pt": "Portuguese note"}}
              additionalProperties:
                oneOf:
                  - type: string
                    description: Legacy format - simple string note
                    example: "This is a general note"
                  - type: object
                    description: Multilingual format - notes by language code
                    additionalProperties:
                      type: string
                    example: {"en": "English note", "pt": "Portuguese note"}
              example: {
                "general": {"en": "A general note in English", "pt": "Uma nota geral em português"},
                "usage": "Simple usage note",
                "etymology": {"en": "From Latin etymologia"}
              }
            custom_fields:
              type: object
              description: Custom fields for the entry
              additionalProperties: true
              example: {"field1": "value1", "field2": {"subfield": "value"}}
    responses:
      201:
        description: Entry created successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            entry_id:
              type: string
              description: ID of the created entry
              example: "test_entry_123"
      400:
        description: Invalid input data
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
        # Get request data
        try:
            data = request.get_json()
        except Exception as json_error:
            return jsonify({'error': f'Invalid JSON: {str(json_error)}'}), 400
            
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Create entry object
        now = datetime.datetime.utcnow().isoformat()
        data['date_created'] = now
        data['date_modified'] = now
        entry = Entry.from_dict(data)
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Create entry
        entry_id = dict_service.create_entry(entry)
        
        # Clear entries cache after successful creation
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            logger.info(f"Cleared entries cache after creating entry {entry_id}")
        
        # Return response
        return jsonify({'success': True, 'entry_id': entry_id}), 201
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error creating entry: %s", str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<string:entry_id>', methods=['PUT'])
def update_entry(entry_id: str) -> Any:
    """
    Update a dictionary entry
    ---
    tags:
      - Entries
    parameters:
      - name: entry_id
        in: path
        type: string
        required: true
        description: ID of the entry to update
        example: "test_entry_123"
      - name: body
        in: body
        required: true
        description: Updated entry data
        schema:
          type: object
          properties:
            id:
              type: string
              description: Entry identifier (must match path parameter)
              example: "test_entry_123"
            lexical_unit:
              type: object
              description: Lexical unit forms by language code
              example: {"en": "test", "pl": "test"}
            pronunciations:
              type: object
              description: Pronunciation forms by writing system (supports non-standard codes like 'seh-fonipa')
              example: {"seh-fonipa": "/tɛstɛ/"}
            grammatical_info:
              type: string
              description: Grammatical information
              example: "noun"
            senses:
              type: array
              description: Array of sense objects
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Sense identifier
                  gloss:
                    type: object
                    description: Gloss by language code
                  definition:
                    type: object
                    description: Definition by language code
            etymologies:
              type: array
              description: Etymology information
            relations:
              type: array
              description: Semantic relations to other entries
            variants:
              type: array
              description: Variant forms
              items:
                type: object
                properties:
                  form:
                    type: object
                    description: Variant form by language
            notes:
              type: object
              description: |
                Entry notes, supporting both legacy string format and multilingual object format.
                Legacy format: {"general": "simple string note"}
                Multilingual format: {"general": {"en": "English note", "pt": "Portuguese note"}}
              additionalProperties:
                oneOf:
                  - type: string
                    description: Legacy format - simple string note
                    example: "This is a general note"
                  - type: object
                    description: Multilingual format - notes by language code
                    additionalProperties:
                      type: string
                    example: {"en": "English note", "pt": "Portuguese note"}
              example: {
                "general": {"en": "A general note in English", "pt": "Uma nota geral em português"},
                "usage": "Simple usage note",
                "etymology": {"en": "From Latin etymologia"}
              }
            custom_fields:
              type: object
              description: Custom fields for the entry
              additionalProperties: true
              example: {"field1": "value1", "field2": {"subfield": "value"}}
    responses:
      200:
        description: Entry updated successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
      400:
        description: Invalid input data
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      404:
        description: Entry not found
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
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Log the senses being received
        logger.info(f"[SENSE UPDATE] Received update for entry {entry_id}")
        logger.info(f"[SENSE UPDATE] Number of senses in request: {len(data.get('senses', []))}")
        for i, sense in enumerate(data.get('senses', [])):
            logger.info(f"[SENSE UPDATE]   Sense {i}: id={sense.get('id')}")
        
        # Add the entry ID from the path if not present in data
        if 'id' not in data:
            data['id'] = entry_id
        
        # Ensure ID in path matches ID in data
        if data.get('id') != entry_id:
            return jsonify({'error': 'Entry ID in path does not match ID in data'}), 400
        
        # Create entry object
        # Preserve date_created, update date_modified
        existing_entry = get_dictionary_service().get_entry(entry_id)
        logger.info(f"[SENSE UPDATE] Existing entry has {len(existing_entry.senses) if existing_entry and existing_entry.senses else 0} senses")
        
        if existing_entry and existing_entry.date_created:
            data['date_created'] = existing_entry.date_created
        data['date_modified'] = datetime.datetime.utcnow().isoformat()
        entry = Entry.from_dict(data)
        
        logger.info(f"[SENSE UPDATE] New entry object has {len(entry.senses) if entry.senses else 0} senses")
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Check if skip_validation parameter is set
        skip_validation = data.pop('skip_validation', False) or request.args.get('skip_validation', 'false').lower() == 'true'
        
        # Update entry
        dict_service.update_entry(entry, skip_validation=skip_validation)
        
        # Clear entries cache after successful update
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            logger.info(f"Cleared entries cache after updating entry {entry_id}")
        
        # Return response
        return jsonify({'success': True})
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error updating entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<string:entry_id>', methods=['DELETE'])
def delete_entry(entry_id: str) -> Any:
    """
    Delete a dictionary entry.
    
    Args:
        entry_id: ID of the entry to delete.
    
    Returns:
        JSON response with success status.
    ---
    tags:
      - Entries
    """
    try:
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Delete entry
        dict_service.delete_entry(entry_id)
        
        # Clear entries cache after successful deletion
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            logger.info(f"Cleared entries cache after deleting entry {entry_id}")
        
        # Return response
        return jsonify({'success': True})
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error("Error deleting entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<string:entry_id>/related', methods=['GET'])
def get_related_entries(entry_id: str) -> Any:
    """
    Get entries related to the specified entry.
    
    Args:
        entry_id: ID of the entry.
    
    Query parameters:
        relation_type: Type of relation to filter by.
    
    Returns:
        JSON response with list of related entries.
    ---
    tags:
      - Entries
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



# Move clear-cache endpoint above dynamic routes
@entries_bp.route('/clear-cache', methods=['POST'])
@swag_from({
    'tags': ['Entries'],
    'summary': 'Clear the cache for the /entries endpoint',
    'description': 'Clears the cache used by the /entries endpoint. Useful for debugging or after data updates.',
    'responses': {
        200: {
            'description': 'Cache cleared successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'success'},
                    'message': {'type': 'string', 'example': 'Entries cache cleared.'}
                }
            }
        }
    }
})
def clear_entries_cache() -> Any:
    """
    Clear the cache for the /entries endpoint.
    """
    try:
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            logger.info("Entries cache cleared")
            return jsonify({'status': 'success', 'message': 'Entries cache cleared.'}), 200
        else:
            logger.info("Cache service not available, skipping cache clear")
            return jsonify({'status': 'success', 'message': 'Cache service not available, no cache to clear'}), 200
    except Exception as e:
        logger.error(f"Error clearing entries cache: {e}")
        return jsonify({'status': 'error', 'message': f'Error clearing cache: {e}'}), 500


@entries_bp.route('/search', methods=['GET'])
def search_entries() -> Any:
    """
    Search for entries based on a query.
    ---
    tags:
      - Entries
    parameters:
      - name: q
        in: query
        type: string
        required: true
        description: Search query
        example: "test"
      - name: search_field
        in: query
        type: string
        required: false
        description: Field to search in
        enum: [lexical_unit, gloss, definition]
        default: lexical_unit
    responses:
      200:
        description: Search results
        schema:
          type: object
          properties:
            entries:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  lexical_unit:
                    type: object
                  senses:
                    type: array
            count:
              type: integer
      400:
        description: Bad request (missing query)
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        # Get query parameters
        query = request.args.get('q')
        search_field = request.args.get('search_field', 'lexical_unit')
        
        if not query:
            return jsonify({'error': 'Search query (q) is required'}), 400
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Search entries
        entries, total_count = dict_service.search_entries(query, [search_field])
        
        # Prepare response
        response = {
            'entries': [entry.to_dict() for entry in entries],
            'count': total_count,
        }        
        return jsonify(response)
        
    except Exception as e:
        logger.error("Error searching entries for query '%s': %s", query, str(e))
        return jsonify({'error': str(e)}), 500