"""
API endpoints for centralized validation service.

This module provides REST API endpoints for validating entry data
using the centralized validation engine.
"""

from __future__ import annotations

import json
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


@validation_service_bp.route('/api/validation/batch', methods=['POST'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Batch validate multiple entries',
    'description': 'Validates multiple entries against validation rules and returns summary',
    'parameters': [
        {
            'name': 'entries',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'entries': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    },
                    'priority_filter': {
                        'type': 'string',
                        'description': 'Filter by priority: critical, warning, informational, or all'
                    }
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Batch validation results',
            'schema': {
                'type': 'object',
                'properties': {
                    'total_entries': {'type': 'integer'},
                    'valid_entries': {'type': 'integer'},
                    'invalid_entries': {'type': 'integer'},
                    'results': {'type': 'array'}
                }
            }
        }
    }
})
def batch_validate_entries() -> tuple[Dict[str, Any], int]:
    """
    Batch validate multiple entries against validation rules.

    Returns a summary of valid and invalid entries along with detailed results.
    """
    try:
        if not request.is_json:
            return {'error': 'Request must be JSON'}, 400

        data = request.get_json()
        if not data or 'entries' not in data:
            return {'error': 'No entries data provided'}, 400

        entries = data.get('entries', [])
        priority_filter = data.get('priority_filter', 'all')

        # Initialize validation engine
        engine = ValidationEngine()

        results = []
        valid_count = 0
        invalid_count = 0

        for entry in entries:
            # Skip entries that are not dictionaries or strings
            if not isinstance(entry, dict) and not isinstance(entry, str):
                current_app.logger.warning(f"Skipping entry of type {type(entry).__name__}: not a dict or string")
                continue

            # Try to parse string entries as JSON
            entry_data = entry
            entry_id = 'unknown'

            if isinstance(entry, str):
                try:
                    entry_data = json.loads(entry)
                except json.JSONDecodeError as e:
                    current_app.logger.warning(f"Failed to parse entry as JSON: {str(e)}")
                    results.append({
                        'entry_id': 'unknown',
                        'valid': False,
                        'error_count': 1,
                        'has_critical_errors': True,
                        'errors': [{'message': f'Invalid JSON format: {str(e)}', 'priority': 'critical', 'category': 'general'}],
                        'warnings': [],
                        'info': []
                    })
                    invalid_count += 1
                    continue

            # Get entry_id safely
            if isinstance(entry_data, dict):
                entry_id = entry_data.get('id', 'unknown')

            # Perform validation
            result = engine.validate_json(entry_data)

            # Filter by priority if needed
            if priority_filter != 'all':
                result.errors = [e for e in result.errors if e.priority.value == priority_filter]
                result.warnings = [w for w in result.warnings if w.priority.value == priority_filter]
                result.info = [i for i in result.info if i.priority.value == priority_filter]

            entry_result = {
                'entry_id': entry_id,
                'valid': result.is_valid,
                'error_count': result.error_count,
                'has_critical_errors': result.has_critical_errors,
                'errors': [_error_to_dict(error) for error in result.errors],
                'warnings': [_error_to_dict(warning) for warning in result.warnings],
                'info': [_error_to_dict(info) for info in result.info]
            }

            results.append(entry_result)

            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        return {
            'total_entries': len(entries),
            'valid_entries': valid_count,
            'invalid_entries': invalid_count,
            'results': results
        }, 200

    except Exception as e:
        current_app.logger.error(f"Error in batch validation endpoint: {str(e)}")
        return {'error': f'Batch validation error: {str(e)}'}, 500


# === Spell Check and LanguageTool Endpoints ===

@validation_service_bp.route('/api/validation/spell-check', methods=['POST'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Check spelling using Hunspell',
    'description': 'Validates text spelling using Hunspell with caching support',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'Text to check'},
                    'lang': {'type': 'string', 'description': 'Language code (e.g., en, pl)', 'default': 'en'},
                    'entry_id': {'type': 'string', 'description': 'Optional entry ID for caching'},
                    'date_modified': {'type': 'string', 'description': 'Entry date_modified for cache validation'}
                },
                'required': ['text']
            }
        }
    ],
    'responses': {
        '200': {'description': 'Spell check results'},
        '400': {'description': 'Invalid request'},
        '500': {'description': 'Server error'}
    }
})
def spell_check():
    """Check spelling using Hunspell with caching."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        text = data.get('text', '')
        lang = data.get('lang', 'en')
        entry_id = data.get('entry_id')
        date_modified = data.get('date_modified')

        if not text:
            return jsonify({
                'is_valid': True,
                'misspellings': [],
                'suggestions': [],
                'word_count': 0
            })

        from app.services.validation_cache_service import get_validation_service
        service = get_validation_service()

        result = service.validate(
            entry_id=entry_id or 'unknown',
            text=text,
            validator_types=['hunspell'],
            lang=lang,
            date_modified=date_modified
        )

        hunspell_result = result.get('hunspell')
        if hunspell_result:
            return jsonify({
                'is_valid': hunspell_result.is_valid,
                'misspellings': hunspell_result.metadata.get('misspellings', []),
                'suggestions': hunspell_result.suggestions,
                'cached': hunspell_result.metadata.get('cached', False),
                'word_count': hunspell_result.metadata.get('word_count', 0)
            })

        return jsonify({
            'is_valid': True,
            'misspellings': [],
            'suggestions': [],
            'cached': False,
            'message': 'Hunspell validator not available'
        })

    except Exception as e:
        current_app.logger.error(f"Spell check error: {str(e)}")
        return jsonify({'error': f'Spell check error: {str(e)}'}), 500


@validation_service_bp.route('/api/validation/languagetool-check', methods=['POST'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Check text using LanguageTool',
    'description': 'Validates text using LanguageTool with grammar, spelling, and bitext checking',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'Text to check'},
                    'lang': {'type': 'string', 'description': 'Source language code'},
                    'target_lang': {'type': 'string', 'description': 'Target language for bitext checking'},
                    'entry_id': {'type': 'string', 'description': 'Optional entry ID for caching'},
                    'date_modified': {'type': 'string', 'description': 'Entry date_modified for cache validation'}
                },
                'required': ['text', 'lang']
            }
        }
    ],
    'responses': {
        '200': {'description': 'LanguageTool check results'},
        '400': {'description': 'Invalid request'},
        '500': {'description': 'Server error'}
    }
})
def languagetool_check():
    """Check text using LanguageTool with caching."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        text = data.get('text', '')
        lang = data.get('lang')
        target_lang = data.get('target_lang')
        entry_id = data.get('entry_id')
        date_modified = data.get('date_modified')

        if not text:
            return jsonify({
                'is_valid': True,
                'matches': [],
                'suggestions': [],
                'cached': False
            })

        if not lang:
            return jsonify({'error': 'Language code is required'}), 400

        from app.services.validation_cache_service import get_validation_service
        service = get_validation_service()

        result = service.validate(
            entry_id=entry_id or 'unknown',
            text=text,
            validator_types=['languagetool'],
            lang=lang,
            target_lang=target_lang,
            date_modified=date_modified
        )

        lt_result = result.get('languagetool')
        if lt_result:
            return jsonify({
                'is_valid': lt_result.is_valid,
                'matches': lt_result.matches,
                'suggestions': lt_result.suggestions,
                'bitext_quality': lt_result.bitext_quality,
                'cached': lt_result.metadata.get('cached', False),
                'target_lang': lt_result.metadata.get('target_lang')
            })

        return jsonify({
            'is_valid': True,
            'matches': [],
            'suggestions': [],
            'cached': False,
            'message': 'LanguageTool validator not available'
        })

    except Exception as e:
        current_app.logger.error(f"LanguageTool check error: {str(e)}")
        return jsonify({'error': f'LanguageTool check error: {str(e)}'}), 500


@validation_service_bp.route('/api/validation/spell-check-batch', methods=['POST'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Batch spell check multiple entries',
    'description': 'Validates spelling for multiple entries with caching',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'entries': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'text': {'type': 'string'}
                            }
                        }
                    },
                    'lang': {'type': 'string', 'description': 'Language code', 'default': 'en'}
                },
                'required': ['entries']
            }
        }
    ],
    'responses': {
        '200': {'description': 'Batch spell check results'},
        '400': {'description': 'Invalid request'},
        '500': {'description': 'Server error'}
    }
})
def spell_check_batch():
    """Batch spell check multiple entries."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        entries = data.get('entries', [])
        lang = data.get('lang', 'en')

        if not entries:
            return jsonify({'error': 'No entries provided'}), 400

        from app.services.validation_cache_service import get_validation_service
        service = get_validation_service()

        # Convert entries to expected format
        entry_data_list = [
            {'id': e.get('id', f'unknown-{i}'), 'text': e.get('text', '')}
            for i, e in enumerate(entries)
        ]

        results = service.validate_batch(
            entries=entry_data_list,
            validator_types=['hunspell'],
            lang=lang
        )

        return jsonify({
            'total_entries': len(entries),
            'results': {
                entry_id: {
                    'is_valid': r.is_valid,
                    'misspellings': r.metadata.get('misspellings', []),
                    'suggestions': r.suggestions,
                    'cached': r.metadata.get('cached', False)
                }
                for entry_id, r in results.items()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Batch spell check error: {str(e)}")
        return jsonify({'error': f'Batch spell check error: {str(e)}'}), 500


@validation_service_bp.route('/api/validation/validate-entry', methods=['POST'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Validate a complete entry with all validators',
    'description': 'Validates an entry using Hunspell and LanguageTool with full caching',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'entry': {'type': 'object', 'description': 'Full entry data dictionary'},
                    'validators': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Validator types to use (hunspell, languagetool)',
                        'default': ['hunspell', 'languagetool']
                    },
                    'lang': {'type': 'string', 'description': 'Primary language code', 'default': 'en'},
                    'target_lang': {'type': 'string', 'description': 'Target language for bitext'}
                },
                'required': ['entry']
            }
        }
    ],
    'responses': {
        '200': {'description': 'Full validation results'},
        '400': {'description': 'Invalid request'},
        '500': {'description': 'Server error'}
    }
})
def validate_entry_full():
    """Validate a complete entry with all validators."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        entry = data.get('entry')
        if not entry:
            return jsonify({'error': 'Entry data is required'}), 400

        validators = data.get('validators', ['hunspell', 'languagetool'])
        lang = data.get('lang', 'en')
        target_lang = data.get('target_lang')

        from app.services.validation_cache_service import get_validation_service
        service = get_validation_service()

        entry_id = entry.get('id', 'unknown')
        summary = service.get_validation_summary(entry_id, entry)

        return jsonify(summary)

    except Exception as e:
        current_app.logger.error(f"Entry validation error: {str(e)}")
        return jsonify({'error': f'Entry validation error: {str(e)}'}), 500


@validation_service_bp.route('/api/validation/cache-stats', methods=['GET'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Get validation cache statistics',
    'description': 'Returns statistics about the validation cache',
    'responses': {
        '200': {'description': 'Cache statistics'}
    }
})
def cache_stats():
    """Get validation cache statistics."""
    try:
        from app.services.validation_cache_service import get_validation_service
        service = get_validation_service()
        return jsonify(service.get_cache_stats())
    except Exception as e:
        current_app.logger.error(f"Cache stats error: {str(e)}")
        return jsonify({'error': f'Cache stats error: {str(e)}'}), 500


@validation_service_bp.route('/api/validation/cache-invalidate', methods=['POST'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Invalidate validation cache',
    'description': 'Clears validation cache for specific entries or all entries',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'entry_ids': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Entry IDs to invalidate (all if not provided)'
                    },
                    'invalidate_all': {'type': 'boolean', 'description': 'Invalidate all cache if true'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Invalidation results'},
        '400': {'description': 'Invalid request'}
    }
})
def invalidate_cache():
    """Invalidate validation cache."""
    try:
        data = request.get_json() or {}
        entry_ids = data.get('entry_ids', [])
        invalidate_all = data.get('invalidate_all', False)

        from app.services.validation_cache_service import get_validation_service
        service = get_validation_service()

        if invalidate_all:
            count = service.invalidate_all()
        elif entry_ids:
            count = service.invalidate_entries(entry_ids)
        else:
            return jsonify({'error': 'No entry_ids or invalidate_all specified'}), 400

        return jsonify({
            'success': True,
            'invalidated_count': count
        })

    except Exception as e:
        current_app.logger.error(f"Cache invalidation error: {str(e)}")
        return jsonify({'error': f'Cache invalidation error: {str(e)}'}), 500
