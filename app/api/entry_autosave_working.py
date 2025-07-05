"""
Working auto-save API endpoint for testing Phase 2 implementation
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime, timezone

from app.services.validation_engine import ValidationEngine, ValidationPriority

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
autosave_bp = Blueprint('autosave', __name__)


@autosave_bp.route('/api/entry/autosave', methods=['POST'])
def autosave_entry():
    """Auto-save entry data with validation"""
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
        client_version = data.get('version', 'unknown')
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
                        'path': e.path,
                        'priority': e.priority.value
                    } for e in critical_errors
                ],
                'message': f'Cannot save due to {len(critical_errors)} critical validation errors'
            }), 400
        
        # For now, simulate successful save (actual database operations would go here)
        new_version = str(datetime.now(timezone.utc).timestamp())
        
        logger.info(f"Auto-save successful (simulated) for entry {entry_data.get('id', 'new')}")
        
        response_data = {
            'success': True,
            'newVersion': new_version,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': 'Entry auto-saved successfully (simulation)'
        }
        
        # Add warnings if any
        if validation_result.warnings:
            response_data['warnings'] = [
                {
                    'rule_id': w.rule_id,
                    'message': w.message,
                    'path': w.path,
                    'priority': w.priority.value
                } for w in validation_result.warnings
            ]
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Unexpected error during auto-save: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': f'An unexpected error occurred during auto-save: {str(e)}'
        }), 500


@autosave_bp.route('/api/entry/autosave/test', methods=['GET'])
def test_autosave():
    """Test endpoint to verify auto-save API is working"""
    return jsonify({
        'success': True,
        'message': 'Auto-save API is working',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200
