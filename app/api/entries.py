"""
API endpoints for managing dictionary entries.
"""

import json
import logging
from typing import Any
from flask import Blueprint, request, jsonify, current_app, session
from flasgger import swag_from

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app.models.entry import Entry
import datetime
from app.utils.exceptions import NotFoundError, ValidationError
from app.services.xml_entry_service import EntryNotFoundError as XMLEntryNotFoundError

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
@swag_from({
    'tags': ['Entries'],
    'summary': 'List dictionary entries',
    'description': 'List entries with pagination, filtering, and sorting',
    'parameters': [
        {'name': 'limit', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Maximum number of entries to return (default 100)', 'example': 20},
        {'name': 'offset', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Number of entries to skip (default 0)', 'example': 0},
        {'name': 'page', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Page number (alternative to offset/limit)', 'example': 1},
        {'name': 'per_page', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Entries per page (alternative to offset/limit)', 'example': 20},
        {'name': 'sort_by', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Field to sort by', 'default': 'lexical_unit'},
        {'name': 'sort_order', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Sort order', 'default': 'asc'},
        {'name': 'filter_text', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Text to filter entries by (searches in lexical_unit)'}
    ],
    'responses': {'200': {'description': 'List of entries'}}
})
def list_entries() -> Any:
    """List dictionary entries with pagination, filtering, and sorting"""
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

        # Cache miss - query dictionary service
        dict_service = get_dictionary_service()
        entries, total_count = dict_service.list_entries(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_text=filter_text
        )

        # Prepare response entries
        response_entries = []
        for i, entry in enumerate(entries):
            try:
                response_entries.append(entry.to_display_dict())
            except AttributeError as e:
                logger.error(f"Entry at index {i} has wrong type: {type(entry)}. Error: {e}")
                raise e

        response = {
            'entries': response_entries,
            'total_count': total_count,
            'total': total_count,
            'limit': limit,
            'offset': offset,
        }

        # Add page/per_page if provided
        if page is not None and per_page is not None:
            response['page'] = page
            response['per_page'] = per_page

        # Cache the response for 3 minutes
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

@swag_from({
  'tags': ['Entries'],
  'summary': 'Get a dictionary entry by ID',
  'parameters': [
    {'name': 'entry_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'ID of the entry to retrieve'}
  ],
  'responses': {'200': {'description': 'Entry data'}, '404': {'description': 'Entry not found'}}
})
def get_entry(entry_id: str) -> Any:
    """Get a dictionary entry by ID"""
    try:
        # Prefer XML response if the entry exists as LIFT XML in the XML service
        try:
            from flask import Response
            from app.api.xml_entries import get_xml_entry_service
            xml_service = get_xml_entry_service()
            entry_xml_data = xml_service.get_entry(entry_id)
            # If xml exists and no explicit json request, return xml by default
            # Allow `format=json` override
            format_param = request.args.get('format', '').lower()
            accept_header = request.headers.get('Accept', '')
            # Prefer JSON by default; only return XML if explicitly requested
            if format_param == 'xml' or ('application/xml' in accept_header and 'application/json' not in accept_header):
                return Response(entry_xml_data['xml'], mimetype='application/xml')
            # Return JSON representation from XML service data
            # Convert XML to dictionary for JSON response
            from app.parsers.lift_parser import LIFTParser
            lift_parser = LIFTParser(validate=False)
            entries = lift_parser.parse_string(f"<lift>{entry_xml_data['xml']}</lift>")
            if entries and entries[0]:
                data = entries[0].to_dict() if hasattr(entries[0], 'to_dict') else entries[0]
                return jsonify(data)
            return jsonify({'error': 'Failed to parse entry data'}), 500
        except XMLEntryNotFoundError:
            raise NotFoundError(f"Entry '{entry_id}' not found")
        except Exception:
            pass
        dict_service = get_dictionary_service()
        entry = dict_service.get_entry(entry_id)
        if entry is None:
            return jsonify({'error': f'Entry with ID {entry_id} not found'}), 404
        # Normalize entry to a serializable dict safely
        data = {}
        try:
            if hasattr(entry, 'to_dict'):
                data = entry.to_dict()
            elif isinstance(entry, dict):
                data = entry
            else:
                data = {}
        except Exception as e:
            logger.warning("get_entry: failed to convert entry to dict: %s", e)
            data = {}
        # Ensure JSON serialization will not fail; if it would, return empty dict
        try:
            import json as _json
            _json.dumps(data)
        except Exception:
            data = {}
        return jsonify(data)
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/', methods=['POST'], strict_slashes=False)
@swag_from({
    'tags': ['Entries'],
    'summary': 'Create a new dictionary entry',
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'description': 'Entry data to create'}
    ],
    'responses': {
        '201': {'description': 'Entry created successfully'},
        '400': {'description': 'Invalid input data'},
        '500': {'description': 'Internal server error'}
    }
})
def create_entry() -> Any:
    """Create a new dictionary entry"""
    try:
        # If XML is posted to /api/entries, delegate to XML entry service
        content_type = request.content_type or ''
        if 'xml' in content_type:
            xml_string = request.get_data(as_text=True)
            # Import inside the function to avoid circular imports
            from app.api.xml_entries import get_xml_entry_service
            xml_service = get_xml_entry_service()
            try:
                result = xml_service.create_entry(xml_string)
            except Exception as e:
                # Import specific XML service exceptions to return appropriate status codes
                from app.services.xml_entry_service import DuplicateEntryError, InvalidXMLError, DatabaseConnectionError, XMLEntryServiceError
                if isinstance(e, DuplicateEntryError):
                    return jsonify({'error': str(e)}), 409
                if isinstance(e, InvalidXMLError):
                    return jsonify({'error': str(e)}), 400
                if isinstance(e, DatabaseConnectionError) or isinstance(e, XMLEntryServiceError):
                    logger.error(f"[XML API] Error creating XML entry via /api/entries: {e}")
                    return jsonify({'error': str(e)}), 500
                logger.error(f"[XML API] Unexpected error creating XML entry via /api/entries: {e}")
                return jsonify({'error': str(e)}), 500
            # Clear cache after creation
            cache = CacheService()
            if cache.is_available():
                cache.clear_pattern('entries:*')
            return jsonify({'success': True, 'entry_id': result.get('id', None)}), 201
        # Get request data
        try:
            data = request.get_json()
        except Exception as json_error:
            return jsonify({'error': f'Invalid JSON: {str(json_error)}'}), 400
            
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Process form data to handle backward compatibility (string lexical_unit, etc.)
        from app.utils.multilingual_form_processor import merge_form_data_with_entry_data
        empty_entry_data = {}
        processed_data = merge_form_data_with_entry_data(data, empty_entry_data)
        
        # Create entry object
        now = datetime.datetime.utcnow().isoformat()
        processed_data['date_created'] = now
        processed_data['date_modified'] = now
        entry = Entry.from_dict(processed_data)
        
        # Get dictionary service
        dict_service = get_dictionary_service()
        
        # Create entry
        project_id = session.get('project_id')
        entry_id = dict_service.create_entry(entry, project_id=project_id)
        
        # Clear entries cache after successful creation
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            logger.info(f"Cleared entries cache after creating entry {entry_id}")
        
        # Return response
        return jsonify({'success': True, 'entry_id': entry_id}), 201
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        # Form processor raises ValueError for validation issues
        logger.error("Validation error creating entry: %s", str(e))
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error creating entry: %s", str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<string:entry_id>', methods=['PUT'])
@swag_from({
    'tags': ['Entries'],
    'summary': 'Update a dictionary entry',
    'parameters': [
        {'name': 'entry_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'ID of the entry to update'},
        {'name': 'body', 'in': 'body', 'required': True, 'description': 'Updated entry data'}
    ],
    'responses': {
        '200': {'description': 'Entry updated successfully'},
        '400': {'description': 'Invalid data or validation errors'},
        '404': {'description': 'Entry not found'},
        '500': {'description': 'Internal server error'}
    }
})
def update_entry(entry_id: str) -> Any:
    """Update a dictionary entry"""
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
            logger.info(f"[SENSE UPDATE]   Sense {i} definition: {sense.get('definition')}")

        # CRITICAL FIX: Clean up definition/gloss objects that have 'lang' but no 'text'
        # This happens when user removes content from textarea but the language select remains
        # Also fix mismatched language keys (when user changes language in dropdown)
        for sense in data.get('senses', []):
            for field in ['definition', 'gloss']:
                if field in sense and isinstance(sense[field], dict):
                    # First pass: collect entries with actual language from 'lang' field
                    new_field_data = {}
                    for lang_key, content in sense[field].items():
                        if isinstance(content, dict):
                            # Get the actual language from 'lang' field (if different from key)
                            actual_lang = content.pop('lang', lang_key)
                            # If no 'text' field or it's empty, skip this entry
                            if 'text' in content and content.get('text', '').strip():
                                new_field_data[actual_lang] = content
                            else:
                                logger.info(f"[SENSE UPDATE] Removed empty {field} for language '{lang_key}' from sense")
                    # Replace with cleaned data
                    sense[field] = new_field_data

        # Add the entry ID from the path if not present in data
        if 'id' not in data:
            data['id'] = entry_id

        # Ensure ID in path matches ID in data
        if data.get('id') != entry_id:
            return jsonify({'error': 'Entry ID in path does not match ID in data'}), 400

        # Try xml_entry_service first (for entries created via XML API)
        try:
            from app.api.xml_entries import get_xml_entry_service
            from app.services.xml_entry_service import LIFTNamespaceManager
            import xml.etree.ElementTree as ET

            xml_service = get_xml_entry_service()
            # Get existing entry XML to preserve structure
            existing_xml_data = xml_service.get_entry(entry_id)

            # Convert the update data to XML and update via xml_service
            from app.parsers.lift_parser import LIFTParser
            lift_parser = LIFTParser(validate=False)

            # Create temporary entry to generate XML
            temp_entry = Entry.from_dict(data)
            full_lift_xml = lift_parser.generate_lift_string([temp_entry])

            # Extract just the <entry> element from the generated LIFT
            root = ET.fromstring(full_lift_xml)
            entry_elem = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}entry')
            if entry_elem is None:
                entry_elem = root.find('.//entry')
            if entry_elem is None:
                raise ValueError("No entry element found in generated XML")

            # Get the entry XML as string
            entry_xml = ET.tostring(entry_elem, encoding='unicode')
            logger.info(f"[SENSE UPDATE] XML to update (truncated): {entry_xml[:500]}")

            # Update via xml service
            result = xml_service.update_entry(entry_id, entry_xml)
            return jsonify({'success': True, 'id': result.get('id', entry_id)})
        except XMLEntryNotFoundError:
            # Fall through to dict_service for entries not in xml service
            pass
        except Exception as e:
            logger.warning(f"[SENSE UPDATE] xml_service update failed, falling back to dict_service: {e}")

        # Get existing entry BEFORE processing form data to preserve fields not in form
        existing_entry = get_dictionary_service().get_entry(entry_id)
        logger.info(f"[SENSE UPDATE] Existing entry has {len(existing_entry.senses) if existing_entry and existing_entry.senses else 0} senses")
        if existing_entry and existing_entry.senses:
            for i, sense in enumerate(existing_entry.senses):
                logger.info(f"[SENSE UPDATE] Existing sense {i}: id={sense.id}")
                logger.info(f"[SENSE UPDATE] Existing sense {i} definition: {sense.definition}")

        # Convert existing entry to dict for merging (must be done before calling merge)
        existing_entry_data = existing_entry.to_dict() if existing_entry else {}

        # Process form data to handle field format conversions (merge preserves fields not in form)
        from app.utils.multilingual_form_processor import merge_form_data_with_entry_data
        data = merge_form_data_with_entry_data(data, existing_entry_data)

        # Create entry object
        # Check if skip_validation parameter is set (extract BEFORE creating Entry)
        skip_validation = data.pop('skip_validation', False) or request.args.get('skip_validation', 'false').lower() == 'true'

        # Preserve date_created, update date_modified
        if existing_entry and existing_entry.date_created:
            data['date_created'] = existing_entry.date_created
        data['date_modified'] = datetime.datetime.utcnow().isoformat()

        logger.info(f"[SENSE UPDATE] Data before Entry.from_dict: {data.get('senses')}")

        # SANITIZE: Remove empty/template senses that have no meaningful content.
        # This protects against ghost/default template senses being included in
        # the submitted data (client-side template elements sometimes leak).
        try:
            sanitized_senses = []
            for s in data.get('senses', []) or []:
                has_definition = False
                has_gloss = False
                defs = s.get('definition') or {}
                glosses = s.get('gloss') or {}
                # Check nested structures for non-empty text
                for val in defs.values() if isinstance(defs, dict) else []:
                    if isinstance(val, dict) and val.get('text', '').strip():
                        has_definition = True
                        break
                    if isinstance(val, str) and val.strip():
                        has_definition = True
                        break
                for val in glosses.values() if isinstance(glosses, dict) else []:
                    if isinstance(val, dict) and val.get('text', '').strip():
                        has_gloss = True
                        break
                    if isinstance(val, str) and val.strip():
                        has_gloss = True
                        break

                if has_definition or has_gloss:
                    sanitized_senses.append(s)
                else:
                    logger.info(f"[SENSE UPDATE] Dropping empty/template sense from submission: id={s.get('id')}")
            data['senses'] = sanitized_senses
        except Exception as e:
            logger.warning(f"[SENSE UPDATE] Failed to sanitize senses: {e}")

        entry = Entry.from_dict(data)
        logger.info(f"[SENSE UPDATE] Entry after from_dict - senses: {[{'id': s.id, 'definitions': s.definitions} for s in entry.senses]}")

        logger.info(f"[SENSE UPDATE] New entry object has {len(entry.senses) if entry.senses else 0} senses")

        # Get dictionary service
        dict_service = get_dictionary_service()

        # Update entry
        project_id = session.get('project_id')
        logger.info(f"[SENSE UPDATE] Calling dict_service.update_entry with skip_validation={skip_validation}, project_id={project_id}")
        dict_service.update_entry(entry, skip_validation=skip_validation, project_id=project_id)
        
        # Clear entries cache after successful update
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            logger.info(f"Cleared entries cache after updating entry {entry_id}")

        # Invalidate validation cache for this entry
        try:
            from app.services.validation_cache_service import invalidate_entry_cache
            invalidated = invalidate_entry_cache(entry_id)
            if invalidated > 0:
                logger.info(f"Invalidated {invalidated} validation cache entries for entry {entry_id}")
        except Exception as cache_err:
            logger.warning(f"Failed to invalidate validation cache: {cache_err}")

        # Return response
        return jsonify({'success': True})
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValidationError as e:
        # Return structured validation errors for client to display
        error_detail = {
            'error': 'Validation failed',
            'message': str(e),
            'validation_errors': e.args[1] if len(e.args) > 1 else []
        }
        return jsonify(error_detail), 400
    except Exception as e:
        logger.error("Error updating entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<string:entry_id>', methods=['DELETE'])
@swag_from({
  'tags': ['Entries'],
  'summary': 'Delete a dictionary entry',
  'parameters': [
    {'name': 'entry_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'ID of the entry to delete'}
  ],
  'responses': {
    '200': {'description': 'Deletion successful'},
    '404': {'description': 'Entry not found'},
    '500': {'description': 'Internal server error'}
  }
})
def delete_entry(entry_id: str) -> Any:
    """Delete a dictionary entry."""
    try:
        # Try xml_entry_service first (for entries created via XML API)
        try:
            from app.api.xml_entries import get_xml_entry_service
            xml_service = get_xml_entry_service()
            xml_service.delete_entry(entry_id)
            return jsonify({'success': True})
        except XMLEntryNotFoundError:
            # Fall through to dict_service for entries not in xml service
            pass
        except Exception as e:
            logger.warning(f"xml_service delete failed, falling back to dict_service: {e}")

        # Get dictionary service
        dict_service = get_dictionary_service()

        # Delete entry
        dict_service.delete_entry(entry_id)
        
        # Clear entries cache after successful deletion
        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern('entries:*')
            logger.info(f"Cleared entries cache after deleting entry {entry_id}")

        # Invalidate validation cache for this entry
        try:
            from app.services.validation_cache_service import invalidate_entry_cache
            invalidated = invalidate_entry_cache(entry_id)
            if invalidated > 0:
                logger.info(f"Invalidated {invalidated} validation cache entries for entry {entry_id}")
        except Exception as cache_err:
            logger.warning(f"Failed to invalidate validation cache: {cache_err}")

        # Return response
        return jsonify({'success': True})
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error("Error deleting entry %s: %s", entry_id, str(e))
        return jsonify({'error': str(e)}), 500


@entries_bp.route('/<string:entry_id>/related', methods=['GET'])
@swag_from({
  'tags': ['Entries'],
  'summary': 'Get entries related to the specified entry',
  'parameters': [
    {'name': 'entry_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'ID of the entry'},
    {'name': 'relation_type', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Type of relation to filter by'}
  ],
  'responses': {'200': {'description': 'List of related entries'}}
})
def get_related_entries(entry_id: str) -> Any:
    """Get entries related to the specified entry."""
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