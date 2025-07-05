"""
Simplified auto-save API endpoint for testing
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify
from typing import Any
import logging
from datetime import datetime

from app.services.validation_engine import ValidationEngine, ValidationPriority

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
autosave_bp = Blueprint('autosave', __name__)


@autosave_bp.route('/api/entry/autosave', methods=['POST'])
def autosave_entry() -> tuple[Any, int]:
    """
    Auto-save entry data with validation (simplified version for testing)
    """
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': 'No JSON data provided'
            }), 400
        
        entry_data = data.get('entryData')
        client_version = data.get('version')
        timestamp = data.get('timestamp')
        
        if not entry_data:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': 'Missing entryData'
            }), 400
        
        logger.info(f"Auto-save request for entry {entry_data.get('id', 'new')} at {timestamp}")
        
        # Validate the entry data using centralized validation
        validator = ValidationEngine()
        validation_result = validator.validate_json(entry_data)
        
        # Check for critical errors that should block saving
        critical_errors = [e for e in validation_result.errors if e.priority == ValidationPriority.CRITICAL]
        if critical_errors:
            logger.warning(f"Auto-save blocked by {len(critical_errors)} critical validation errors")
            return jsonify({
                'success': False,
                'error': 'validation_failed',
                'validation_errors': [
                    {
                        'rule_id': e.rule_id,
                        'message': e.message,
                        'field_path': e.field_path,
                        'priority': e.priority.value
                    } for e in critical_errors
                ],
                'message': f'Cannot save due to {len(critical_errors)} critical validation errors'
            }), 400
        
        # For now, simulate successful save (actual database operations would go here)
        new_version = str(datetime.utcnow().timestamp())
        
        logger.info(f"Auto-save successful (simulated) for entry {entry_data.get('id', 'new')}")
        
        return jsonify({
            'success': True,
            'newVersion': new_version,
            'timestamp': datetime.utcnow().isoformat(),
            'warnings': [
                {
                    'rule_id': w.rule_id,
                    'message': w.message,
                    'field_path': w.field_path,
                    'priority': w.priority.value
                } for w in validation_result.warnings
            ] if validation_result.warnings else [],
            'message': 'Entry auto-saved successfully (simulation)'
        })
    
    except Exception as e:
        logger.error(f"Unexpected error during auto-save: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': f'An unexpected error occurred during auto-save: {str(e)}'
        }), 500


@autosave_bp.route('/api/entry/autosave/test', methods=['GET'])
def test_autosave() -> tuple[Any, int]:
    """Test endpoint to verify auto-save API is working"""
    return jsonify({
        'success': True,
        'message': 'Auto-save API is working',
        'timestamp': datetime.utcnow().isoformat()
    })
