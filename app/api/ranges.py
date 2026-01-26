"""
API endpoints for LIFT ranges functionality.

This module provides REST API endpoints for accessing LIFT ranges data
to support dynamic dropdown population in the UI.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, Response, current_app, request
from typing import Union, Tuple

from app.services.dictionary_service import DictionaryService


ranges_bp = Blueprint('ranges', __name__, url_prefix='/api/ranges')


@ranges_bp.route('', methods=['GET'])
def get_all_ranges() -> Union[Response, Tuple[Response, int]]:
    """
    Get all LIFT ranges data.
    
    Returns:
        JSON response with all ranges data.
    ---
    tags:
      - Ranges
    summary: Get all LIFT ranges
    description: Retrieve all LIFT ranges for dynamic UI dropdown population
    responses:
      200:
        description: Successfully retrieved ranges
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              description: Dictionary of all ranges keyed by range ID
              additionalProperties:
                type: object
                properties:
                  id:
                    type: string
                    description: Range identifier
                  values:
                    type: array
                    description: Array of range values
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                        value:
                          type: string
                        abbrev:
                          type: string
                        description:
                          type: object
                        children:
                          type: array
      500:
        description: Error retrieving ranges
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              description: Error message
    """
    # Remove hardcoded test ranges - use dynamic ranges from service layer
    try:
        # Get dictionary service using dependency injection
        dict_service = current_app.injector.get(DictionaryService)
        # Check query param to request resolved view
        resolved_param = (request.args.get('resolved') or '').lower()
        resolved = resolved_param in ('1', 'true', 'yes')
        # Use force_reload=True to ensure fresh data from the database,
        # since self.ranges may have been pre-populated with defaults during app startup
        ranges = dict_service.get_ranges(resolved=resolved, force_reload=True)
        return jsonify({
            'success': True,
            'data': ranges
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ranges_bp.route('/<range_id>', methods=['GET'])
def get_specific_range(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """
    Get specific LIFT range by ID.
    
    Args:
        range_id: ID of the range to retrieve.
        
    Returns:
        JSON response with specific range data.
    ---
    tags:
      - Ranges
    summary: Get specific LIFT range
    description: Retrieve a specific LIFT range by its ID
    parameters:
      - name: range_id
        in: path
        required: true
        type: string
        example: grammatical-info
    responses:
      200:
        description: Successfully retrieved range
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                id:
                  type: string
                  description: Range identifier
                values:
                  type: array
                  description: Array of range values
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                      value:
                        type: string
                      abbrev:
                        type: string
                      description:
                        type: object
                      children:
                        type: array
      404:
        description: Range not found
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: Range not found
      500:
        description: Error retrieving range
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              description: Error message
    """
    try:
        # Get dictionary service using dependency injection
        dict_service = current_app.injector.get(DictionaryService)
        current_app.logger.debug("get_range hit for %s", range_id)
        # Accept `resolved` query param for resolved view
        resolved_param = (request.args.get('resolved') or '').lower()
        resolved = resolved_param in ('1', 'true', 'yes')
        # Use force_reload=True to ensure fresh data from the database,
        # since self.ranges may have been pre-populated with defaults during app startup
        ranges = dict_service.get_ranges(resolved=resolved, force_reload=True)

        # Use exact ID matching first. Do not attempt plural/singular
        # or heuristic fallbacks here; callers should use canonical IDs.
        lookup_id = range_id
        if lookup_id in ranges:
            return jsonify({
                'success': True,
                'data': ranges[lookup_id]
            })

        # If not found in loaded ranges, check if it's a special range that should be
        # derived from trait usage in the LIFT data (e.g., 'variant-type', 'complex-form-type')
        if lookup_id in ['variant-type', 'lexical-relation', 'complex-form-type']:
            # Try to get values from trait extraction
            try:
                if lookup_id == 'variant-type':
                    variant_types = dict_service.get_variant_types_from_traits()
                    return jsonify({
                        'success': True,
                        'data': {
                            'id': 'variant-type',
                            'values': variant_types
                        }
                    })
                elif lookup_id == 'complex-form-type':
                    # Get complex form types from trait values in LIFT data
                    complex_form_types = dict_service.get_complex_form_types_from_traits()
                    return jsonify({
                        'success': True,
                        'data': {
                            'id': 'complex-form-type',
                            'values': complex_form_types
                        }
                    })
                elif lookup_id == 'lexical-relation':
                    # Get relation types from trait values in LIFT data
                    lexical_relations = dict_service.get_lexical_relation_types_from_traits()
                    return jsonify({
                        'success': True,
                        'data': {
                            'id': 'lexical-relation',
                            'values': lexical_relations
                        }
                    })
            except AttributeError:
                # These methods might not exist yet, fall back to error
                pass

        return jsonify({
            'success': False,
            'error': f'Range "{range_id}" not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ranges_bp.route('/grammatical-info', methods=['GET'])
def get_grammatical_info_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get grammatical information range.
    
    Convenience endpoint for accessing grammatical categories.
    
    Returns:
        JSON response with grammatical info range.
    ---
    tags:
      - Ranges
    summary: Get grammatical information range
    description: Convenience endpoint for grammatical categories
    responses:
      200:
        description: Successfully retrieved grammatical info range
      404:
        description: Grammatical info range not found
      500:
        description: Error retrieving range
    """
    return get_specific_range('grammatical-info')


@ranges_bp.route('/variant-type', methods=['GET'])
def get_variant_types_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get variant type range.

    Convenience endpoint for accessing variant type categories.

    Returns:
        JSON response with variant types range.
    ---
    tags:
      - Ranges
    summary: Get variant types range
    description: Convenience endpoint for variant type categories
    responses:
      200:
        description: Successfully retrieved variant types range
      404:
        description: Variant type range not found
      500:
        description: Error retrieving range
    """
    # Delegate to the generic function for consistency
    return get_specific_range('variant-type')


@ranges_bp.route('/lexical-relation', methods=['GET'])
def get_relation_types_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get relation types range.
    
    Convenience endpoint for accessing relation type categories.
    
    Returns:
        JSON response with relation types range.
    ---
    tags:
      - Ranges
    summary: Get relation types range
    description: Convenience endpoint for relation type categories
    responses:
      200:
        description: Successfully retrieved relation types range
      404:
        description: Relation types range not found
      500:
        description: Error retrieving range
    """
    return get_specific_range('lexical-relation')


@ranges_bp.route('/semantic-domain-ddp4', methods=['GET'])
def get_semantic_domains_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get semantic domains range.
    
    Convenience endpoint for accessing semantic domain categories.
    
    Returns:
        JSON response with semantic domains range.
    ---
    tags:
      - Ranges
    summary: Get semantic domains range
    description: Convenience endpoint for semantic domain categories
    responses:
      200:
        description: Successfully retrieved semantic domains range
      404:
        description: Semantic domains range not found
      500:
        description: Error retrieving range
    """
    return get_specific_range('semantic-domain-ddp4')


@ranges_bp.route('/install_recommended', methods=['POST'])
def install_recommended_ranges() -> Union[Response, Tuple[Response, int]]:
    """
    Install a minimal recommended set of ranges into the database.
    Intended for initial project setup or when ranges are missing.
    ---
    tags:
      - Ranges
    summary: Install recommended LIFT ranges
    description: Add a minimal set of recommended ranges (for initial setup). Does not overwrite existing ranges.
    responses:
      201:
        description: Ranges installed successfully
      500:
        description: Error installing ranges
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        ranges = dict_service.install_recommended_ranges()
        return jsonify({'success': True, 'data': ranges}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_bp.route('/etymology', methods=['GET'])
def get_etymology_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get etymology range.
    
    Convenience endpoint for accessing etymology categories for word origins.
    
    Returns:
        JSON response with etymology range.
    ---
    tags:
      - Ranges
    summary: Get etymology range
    description: Convenience endpoint for etymology categories (inheritance, borrowing, etc.)
    responses:
      200:
        description: Successfully retrieved etymology range
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                id:
                  type: string
                  example: "etymology"
                values:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                        example: "borrowed"
                      value:
                        type: string
                        example: "borrowed"
                      abbrev:
                        type: string
                        example: "bor"
                      description:
                        type: object
                        properties:
                          en:
                            type: string
                            example: "The word is borrowed from another language"
      404:
        description: Etymology range not found
      500:
        description: Error retrieving range
    """
    return get_specific_range('etymology')


@ranges_bp.route('/language-codes', methods=['GET'])
def get_language_codes() -> Union[Response, Tuple[Response, int]]:
    """
    Get language codes used in the LIFT file.
    
    This endpoint provides the actual language codes used in the LIFT file,
    rather than a predefined list.
    
    Returns:
        JSON response with language codes from the LIFT file.
    ---
    tags:
      - Ranges
    summary: Get language codes
    description: Retrieve language codes used in the LIFT file
    responses:
      200:
        description: Successfully retrieved language codes
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: array
              description: Array of language codes
              items:
                type: string
      500:
        description: Error retrieving language codes
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              description: Error message
    """
    try:
        # Get dictionary service using dependency injection
        dict_service = current_app.injector.get(DictionaryService)
        language_codes = dict_service.get_language_codes()
        
        return jsonify({
            'success': True,
            'data': language_codes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ranges_bp.route('/project-languages', methods=['GET'])
def get_project_languages_api() -> Union[Response, Tuple[Response, int]]:
    """
    Get project-specific language codes and names.

    This endpoint provides the language codes configured in the project settings
    (source language + target languages), which are the only languages that
    should be used in the project.

    Returns:
        JSON response with project language codes and names.
    ---
    tags:
      - Ranges
    summary: Get project languages
    description: Retrieve language codes configured in project settings (source + target languages)
    responses:
      200:
        description: Successfully retrieved project languages
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: array
              description: Array of language objects with code and name
              items:
                type: object
                properties:
                  code:
                    type: string
                    description: Language code (e.g., 'en', 'pl')
                  name:
                    type: string
                    description: Language name (e.g., 'English', 'Polish')
      500:
        description: Error retrieving project languages
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              description: Error message
    """
    try:
        from app.utils.language_utils import get_project_languages

        # Get project languages as (code, name) tuples
        project_lang_tuples = get_project_languages()

        # Convert to the expected format: array of objects with code and name
        project_languages = []
        for code, name in project_lang_tuples:
            # Handle the case where name might be a Markup object (with tooltip)
            if hasattr(name, '__html__'):
                # Extract just the text part without the tooltip markup
                import re
                clean_name = re.sub(r'<.*?>', '', str(name)).strip()
                # If the name was marked as vernacular, try to extract the clean name
                if clean_name.startswith((' ', '\n')):
                    clean_name = clean_name.lstrip()
            else:
                clean_name = str(name)

            project_languages.append({
                'code': code,
                'name': clean_name
            })

        return jsonify({
            'success': True,
            'data': project_languages
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
