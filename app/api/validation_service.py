"""
API endpoints for centralized validation service.

This module provides REST API endpoints for validating entry data
using the centralized validation engine.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from flasgger import swag_from
from typing import Dict, Any, List

from app.services.validation_engine import ValidationEngine, ValidationResult


validation_service_bp = Blueprint('validation_service', __name__)


@validation_service_bp.route('/api/validation/entry', methods=['POST'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Validate entry data using centralized validation engine',
    'description': 'Validates JSON entry data against all applicable validation rules',
    'parameters': [
        {
            'name': 'entry_data',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'description': 'Entry ID'},
                    'lexical_unit': {
                        'type': 'object',
                        'description': 'Lexical unit with language codes as keys'
                    },
                    'senses': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'definition': {'type': 'string'},
                                'gloss': {'type': 'string'}
                            }
                        }
                    },
                    'pronunciations': {
                        'type': 'object',
                        'description': 'Pronunciations with language codes as keys'
                    },
                    'notes': {
                        'type': 'object',
                        'description': 'Notes with note types as keys'
                    },
                    'relations': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'type': {'type': 'string'},
                                'target': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Validation completed',
            'schema': {
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'errors': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rule_id': {'type': 'string'},
                                'rule_name': {'type': 'string'},
                                'message': {'type': 'string'},
                                'path': {'type': 'string'},
                                'priority': {'type': 'string'},
                                'category': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    },
                    'warnings': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rule_id': {'type': 'string'},
                                'rule_name': {'type': 'string'},
                                'message': {'type': 'string'},
                                'path': {'type': 'string'},
                                'priority': {'type': 'string'},
                                'category': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    },
                    'info': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rule_id': {'type': 'string'},
                                'rule_name': {'type': 'string'},
                                'message': {'type': 'string'},
                                'path': {'type': 'string'},
                                'priority': {'type': 'string'},
                                'category': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    },
                    'error_count': {'type': 'integer'},
                    'has_critical_errors': {'type': 'boolean'}
                }
            }
        },
        400: {
            'description': 'Invalid request data',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def validate_entry() -> tuple[Dict[str, Any], int]:
    """
    Validate entry data using centralized validation engine.
    
    This endpoint receives JSON entry data from the client-side form
    and validates it against all applicable validation rules.
    
    Returns:
        Validation result with errors, warnings, and info
    """
    try:
        if not request.is_json:
            return {'error': 'Request must be JSON'}, 400
        
        entry_data = request.get_json()
        if not entry_data:
            return {'error': 'No entry data provided'}, 400
        
        # Initialize validation engine
        engine = ValidationEngine()
        
        # Perform validation
        result = engine.validate_json(entry_data)
        
        # Convert result to JSON-serializable format
        response = {
            'valid': result.is_valid,
            'errors': [_error_to_dict(error) for error in result.errors],
            'warnings': [_error_to_dict(error) for error in result.warnings],
            'info': [_error_to_dict(error) for error in result.info],
            'error_count': result.error_count,
            'has_critical_errors': result.has_critical_errors
        }
        
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error in validation endpoint: {str(e)}")
        return {'error': f'Validation error: {str(e)}'}, 500


@validation_service_bp.route('/api/validation/xml', methods=['POST'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Validate LIFT XML entry using centralized validation engine',
    'description': 'Validates LIFT XML entry data against all applicable validation rules. Parses XML to Entry object and applies same validation as JSON endpoint.',
    'consumes': ['application/xml', 'text/xml'],
    'parameters': [
        {
            'name': 'xml_entry',
            'in': 'body',
            'required': True,
            'description': 'LIFT XML string for a single entry',
            'schema': {
                'type': 'string',
                'example': '<entry id="test-1"><lexical-unit><form lang="en"><text>test</text></form></lexical-unit></entry>'
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Validation completed',
            'schema': {
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'errors': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rule_id': {'type': 'string'},
                                'rule_name': {'type': 'string'},
                                'message': {'type': 'string'},
                                'path': {'type': 'string'},
                                'priority': {'type': 'string'},
                                'category': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    },
                    'warnings': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rule_id': {'type': 'string'},
                                'rule_name': {'type': 'string'},
                                'message': {'type': 'string'},
                                'path': {'type': 'string'},
                                'priority': {'type': 'string'},
                                'category': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    },
                    'info': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rule_id': {'type': 'string'},
                                'rule_name': {'type': 'string'},
                                'message': {'type': 'string'},
                                'path': {'type': 'string'},
                                'priority': {'type': 'string'},
                                'category': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    },
                    'error_count': {'type': 'integer'},
                    'has_critical_errors': {'type': 'boolean'}
                }
            }
        },
        400: {
            'description': 'Invalid XML data',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def validate_xml_entry() -> tuple[Dict[str, Any], int]:
    """
    Validate LIFT XML entry using centralized validation engine.
    
    This endpoint receives LIFT XML entry data and validates it
    against all applicable validation rules by:
    1. Parsing XML to Entry object
    2. Converting to dictionary
    3. Applying same validation as JSON endpoint
    
    Returns:
        Validation result with errors, warnings, and info
    """
    try:
        # Get XML data from request body
        xml_data = request.data.decode('utf-8')
        if not xml_data or not xml_data.strip():
            return {'error': 'No XML data provided'}, 400
        
        # Initialize validation engine
        engine = ValidationEngine()
        
        # Perform XML validation
        result = engine.validate_xml(xml_data)
        
        # Convert result to JSON-serializable format
        response = {
            'valid': result.is_valid,
            'errors': [_error_to_dict(error) for error in result.errors],
            'warnings': [_error_to_dict(error) for error in result.warnings],
            'info': [_error_to_dict(error) for error in result.info],
            'error_count': result.error_count,
            'has_critical_errors': result.has_critical_errors
        }
        
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error in XML validation endpoint: {str(e)}")
        return {'error': f'XML validation error: {str(e)}'}, 500


@validation_service_bp.route('/api/validation/rules', methods=['GET'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Get available validation rules',
    'description': 'Returns list of all available validation rules with their metadata',
    'responses': {
        200: {
            'description': 'List of validation rules',
            'schema': {
                'type': 'object',
                'properties': {
                    'rules': {
                        'type': 'object',
                        'description': 'Validation rules by rule ID'
                    },
                    'categories': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Available validation categories'
                    },
                    'priorities': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Available validation priorities'
                    }
                }
            }
        }
    }
})
def get_validation_rules() -> tuple[Dict[str, Any], int]:
    """
    Get available validation rules and metadata.
    
    Returns:
        Dictionary containing all validation rules and their metadata
    """
    try:
        engine = ValidationEngine()
        
        # Get categories and priorities from the engine
        categories = list(set(rule.get('category') for rule in engine.rules.values()))
        priorities = ['critical', 'warning', 'informational']
        
        response = {
            'rules': engine.rules,
            'categories': categories,
            'priorities': priorities
        }
        
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting validation rules: {str(e)}")
        return {'error': f'Error loading validation rules: {str(e)}'}, 500


@validation_service_bp.route('/api/validation/rules/<rule_id>', methods=['GET'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Get specific validation rule',
    'description': 'Returns details for a specific validation rule',
    'parameters': [
        {
            'name': 'rule_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'The ID of the validation rule'
        }
    ],
    'responses': {
        200: {
            'description': 'Validation rule details',
            'schema': {
                'type': 'object',
                'properties': {
                    'rule_id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'category': {'type': 'string'},
                    'priority': {'type': 'string'},
                    'path': {'type': 'string'},
                    'condition': {'type': 'string'},
                    'validation': {'type': 'object'},
                    'error_message': {'type': 'string'},
                    'client_side': {'type': 'boolean'}
                }
            }
        },
        404: {
            'description': 'Rule not found',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def get_validation_rule(rule_id: str) -> tuple[Dict[str, Any], int]:
    """
    Get details for a specific validation rule.
    
    Args:
        rule_id: The ID of the validation rule
        
    Returns:
        Validation rule details or error if not found
    """
    try:
        engine = ValidationEngine()
        
        if rule_id not in engine.rules:
            return {'error': f'Validation rule {rule_id} not found'}, 404
        
        rule = engine.rules[rule_id].copy()
        rule['rule_id'] = rule_id
        
        return rule, 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting validation rule {rule_id}: {str(e)}")
        return {'error': f'Error loading validation rule: {str(e)}'}, 500


def _error_to_dict(error) -> Dict[str, Any]:
    """Convert ValidationError to dictionary for JSON serialization."""
    return {
        'rule_id': error.rule_id,
        'rule_name': error.rule_name,
        'message': error.message,
        'path': error.path,
        'priority': error.priority.value,
        'category': error.category.value,
        'value': str(error.value) if error.value is not None else None
    }


def validate_language(language_code: str, project_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Validate if a language is configured for the project."""
    configured_languages: List[str] = [project_settings['source_language']['code']] + \
                                   [lang['code'] for lang in project_settings['target_languages']]
    
    if language_code not in configured_languages:
        return {
            'is_valid': False,
            'errors': [],
            'warnings': [f"Language '{language_code}' is not configured for this project"],
            'info': []
        }
    return {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'info': []
    }
