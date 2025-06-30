"""
API endpoints for LIFT ranges functionality.

This module provides REST API endpoints for accessing LIFT ranges data
to support dynamic dropdown population in the UI.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, Response
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
      - ranges
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
    try:
        # Get dictionary service using dependency injection
        from app import injector
        dict_service = injector.get(DictionaryService)
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
      - ranges
    summary: Get specific LIFT range
    description: Retrieve a specific LIFT range by its ID
    parameters:
      - name: range_id
        in: path
        required: true
        type: string
        description: ID of the range to retrieve
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
        from app import injector
        dict_service = injector.get(DictionaryService)
        ranges = dict_service.get_ranges()
        
        if range_id not in ranges:
            return jsonify({
                'success': False,
                'error': f'Range "{range_id}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': ranges[range_id]
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
      - ranges
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
    
    Returns:
        JSON response with variant types range.
    ---
    tags:
      - ranges
    summary: Get variant types range
    description: Convenience endpoint for variant type categories
    responses:
      200:
        description: Successfully retrieved variant types range
      404:
        description: Variant types range not found
      500:
        description: Error retrieving range
    """
    return get_specific_range('variant-types')


@ranges_bp.route('/relation-types', methods=['GET'])
def get_relation_types_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get relation types range.
    
    Convenience endpoint for accessing relation type categories.
    
    Returns:
        JSON response with relation types range.
    ---
    tags:
      - ranges
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
      - ranges
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


@ranges_bp.route('/etymology-types', methods=['GET'])
def get_etymology_types_range() -> Union[Response, Tuple[Response, int]]:
    """
    Get etymology types range.
    
    Convenience endpoint for accessing etymology type categories for word origins.
    
    Returns:
        JSON response with etymology types range.
    ---
    tags:
      - ranges
    summary: Get etymology types range
    description: Convenience endpoint for etymology type categories (inheritance, borrowing, etc.)
    responses:
      200:
        description: Successfully retrieved etymology types range
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
                  example: "etymology-types"
                values:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                        example: "borrowing"
                      value:
                        type: string
                        example: "borrowing"
                      abbrev:
                        type: string
                        example: "bor"
                      description:
                        type: object
                        properties:
                          en:
                            type: string
                            example: "Word borrowed from another language"
      404:
        description: Etymology types range not found
      500:
        description: Error retrieving range
    """
    return get_specific_range('etymology-types')
