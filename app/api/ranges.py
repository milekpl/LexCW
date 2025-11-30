"""
API endpoints for LIFT ranges functionality.

This module provides REST API endpoints for accessing LIFT ranges data
to support dynamic dropdown population in the UI.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, Response, current_app
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
        ranges = dict_service.get_ranges()
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
        ranges = dict_service.get_ranges()

        # Define specific mappings for known problematic range names
        range_mappings = {
            'relation-type': 'lexical-relation',
            'relation-types': 'lexical-relation', 
            'etymology': 'etymology',
            'variant-types-from-traits': 'variant-types',
            'semantic-domains': 'semantic-domain-ddp4',
            'semantic-domain': 'semantic-domain-ddp4',
            'academic-domain': 'domain-type',
            'academic-domains': 'domain-type',
            'usage-types': 'usage-type',
            'note-types': 'note-type',
            'publications': 'Publications',
        }

        # First check direct mapping
        lookup_id = range_mappings.get(range_id, range_id)
        
        # If direct mapping doesn't exist, try the original fallback logic
        if lookup_id not in ranges:
            # For relation-types, try different variations
            if range_id == 'relation-types':
                if 'relation-types' in ranges:
                    lookup_id = 'relation-types'
                elif 'relation-type' in ranges:
                    lookup_id = 'relation-type'
                elif 'lexical-relation' in ranges:
                    lookup_id = 'lexical-relation'
            else:
                # Try singular/plural fallback for other ranges
                if lookup_id.endswith('s') and lookup_id[:-1] in ranges:
                    lookup_id = lookup_id[:-1]
                elif lookup_id + 's' in ranges:
                    lookup_id = lookup_id + 's'

        if lookup_id not in ranges:
            return jsonify({
                'success': False,
                'error': f'Range "{range_id}" not found'
            }), 404

        return jsonify({
            'success': True,
            'data': ranges[lookup_id]
        })
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


@ranges_bp.route('/variant-types', methods=['GET'])
def get_variant_types_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get variant types range.
    
    Convenience endpoint for accessing variant type categories.
    Provides fallback data when LIFT ranges don't include variant-types.
    
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
      500:
        description: Error retrieving range
    """
    try:
        # Get dictionary service using dependency injection
        dict_service = current_app.injector.get(DictionaryService)
        ranges = dict_service.get_ranges()
        
        # Check if variant-types exists in LIFT ranges
        if 'variant-types' in ranges:
            return jsonify({
                'success': True,
                'data': ranges['variant-types']
            })
        
        # If not found in LIFT ranges, provide fallback data
        fallback_data = {
            'id': 'variant-types',
            'description': {},
            'guid': '',
            'values': [
                {
                    'id': 'dialectal',
                    'value': 'dialectal',
                    'abbrev': 'dial',
                    'description': {'en': 'Dialectal variant'},
                    'guid': '',
                    'children': []
                },
                {
                    'id': 'spelling',
                    'value': 'spelling',
                    'abbrev': 'sp',
                    'description': {'en': 'Spelling variant'},
                    'guid': '',
                    'children': []
                },
                {
                    'id': 'phonetic',
                    'value': 'phonetic',
                    'abbrev': 'phon',
                    'description': {'en': 'Phonetic variant'},
                    'guid': '',
                    'children': []
                },
                {
                    'id': 'formal',
                    'value': 'formal',
                    'abbrev': 'form',
                    'description': {'en': 'Formal variant'},
                    'guid': '',
                    'children': []
                },
                {
                    'id': 'informal',
                    'value': 'informal',
                    'abbrev': 'inf',
                    'description': {'en': 'Informal variant'},
                    'guid': '',
                    'children': []
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'data': fallback_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ranges_bp.route('/relation-types', methods=['GET'])
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
    return get_specific_range('relation-types')


@ranges_bp.route('/semantic-domains', methods=['GET'])
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
    return get_specific_range('semantic-domains')


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


@ranges_bp.route('/variant-types-from-traits', methods=['GET'])
def get_variant_types_from_traits() -> Union[Response, Tuple[Response, int]]:
    """
    Get variant types extracted from traits in the LIFT data.
    
    This endpoint provides variant types actually used in the LIFT file,
    rather than predefined ranges, extracted from <trait> elements.
    
    Returns:
        JSON response with variant types from traits.
    ---
    tags:
      - Ranges
    summary: Get variant types from traits
    description: Retrieve variant types from traits in LIFT data
    responses:
      200:
        description: Successfully retrieved variant types
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
                  description: Array of variant type values
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
      500:
        description: Error retrieving variant types
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
        variant_types = dict_service.get_variant_types_from_traits()
        
        return jsonify({
            'success': True,
            'data': {
                'id': 'variant-types-from-traits',
                'values': variant_types
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
