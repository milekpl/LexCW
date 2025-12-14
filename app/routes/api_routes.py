"""
API routes for the dictionary application.
These routes provide JSON-based endpoints for frontend integration.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from ..services.dictionary_service import DictionaryService
from ..utils.exceptions import NotFoundError, ValidationError

# Create blueprint
api_bp = Blueprint('additional_api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)




@api_bp.route('/entries')
def list_entries():
    """List entries with pagination and sorting."""
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'lexical_unit', type=str)
        sort_order = request.args.get('sort_order', 'asc', type=str)
        filter_text = request.args.get('filter_text', None, type=str)
        
        # Validate parameters
        if limit <= 0 or limit > 1000:
            limit = 10
        if offset < 0:
            offset = 0
        if sort_order.lower() not in ['asc', 'desc']:
            sort_order = 'asc'
        
        dict_service = current_app.injector.get(DictionaryService)
        entries, total = dict_service.list_entries(
            limit=limit, 
            offset=offset, 
            sort_by=sort_by, 
            sort_order=sort_order, 
            filter_text=filter_text
        )

        # Convert entries to dictionaries for JSON response
        entry_dicts = []
        for entry in entries:
            if hasattr(entry, 'to_dict'):
                entry_dicts.append(entry.to_dict())
            # Skip non-Entry objects silently

        return jsonify({
            'entries': entry_dicts,
            'total': total,
            'total_count': total,  # Add for compatibility
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error listing entries: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/entries/<entry_id>')
def get_entry(entry_id: str):
    """Get a specific entry by ID."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        entry = dict_service.get_entry(entry_id)
        
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
        
        return jsonify(entry.to_dict())
        
    except NotFoundError:
        return jsonify({'error': 'Entry not found'}), 404
    except Exception as e:
        logger.error(f"Error getting entry {entry_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# LIFT Ranges API endpoints
@api_bp.route('/ranges')
def get_all_ranges():
    """Get all available LIFT ranges."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        ranges = dict_service.get_lift_ranges()
        
        return jsonify({
            'success': True,
            'data': ranges,
            'available_types': list(ranges.keys())
        })
        
    except Exception as e:
        logger.error(f"Error getting ranges: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/ranges/<range_type>')
def get_range_by_type(range_type: str):
    """Get a specific range type (e.g., grammatical-info, lexical-relation)."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        ranges = dict_service.get_lift_ranges()
        
        logger.info(f"[Ranges API] Requested: {range_type}, Available: {list(ranges.keys())[:5]}...")
        
        # Handle both singular and plural forms
        range_data = None
        if range_type in ranges:
            range_data = ranges[range_type]
            logger.info(f"[Ranges API] Found {range_type} directly in ranges")
        else:
            # No alternative mappings - only canonical forms are supported
            logger.info(f"[Ranges API] Range '{range_type}' not found in ranges")
        
        if not range_data:
            logger.warning(f"[Ranges API] Range '{range_type}' not found. Available: {list(ranges.keys())}")
            return jsonify({
                'success': False,
                'error': f'Range type "{range_type}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'type': range_type,
            'data': range_data
        })
        
    except Exception as e:
        logger.error(f"Error getting range {range_type}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/ranges/language-codes')
def get_language_codes():
    """Get available language codes for variant forms."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        
        # Extract language codes from the LIFT data
        # This could be enhanced to get actual codes from the data
        # For now, provide a basic set of common language codes
        language_codes = [
            {'code': 'en', 'name': 'English'},
            {'code': 'seh-fonipa', 'name': 'Sena (IPA)'},
            {'code': 'pl', 'name': 'Polish'},
            {'code': 'fr', 'name': 'French'},
            {'code': 'es', 'name': 'Spanish'},
        ]
        
        return jsonify({
            'language_codes': language_codes,
            'count': len(language_codes)
        })
        
    except Exception as e:
        logger.error(f"Error getting language codes: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
