"""
API endpoints for entry and dictionary validation.
"""

from flask import Blueprint, jsonify, request, current_app
from flasgger import swag_from
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import NotFoundError, ValidationError

validation_bp = Blueprint('validation_bp', __name__)

@validation_bp.route('/api/validation/entry/<string:entry_id>', methods=['GET'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Validate a single dictionary entry',
    'parameters': [
        {'name': 'entry_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'The ID of the entry to validate.'}
    ],
    'responses': {'200': {'description': 'Validation result.'}, '404': {'description': 'Entry not found.'}}
})
def validate_entry(entry_id: str):
    """Validate a single dictionary entry."""
    dictionary_service = current_app.injector.get(DictionaryService)
    try:
        entry = dictionary_service.get_entry(entry_id)
        try:
            entry.validate()
            return jsonify({'valid': True, 'errors': []})
        except ValidationError as ve:
            return jsonify({'valid': False, 'errors': ve.errors if ve.errors else [str(ve)]}), 200
    except NotFoundError:
        return jsonify({'error': 'Entry not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@validation_bp.route('/api/validation/dictionary', methods=['GET'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Validate the entire dictionary',
    'responses': {'200': {'description': 'Validation result.'}}
})
def validate_dictionary():
    """Validate the entire dictionary."""
    dictionary_service = current_app.injector.get(DictionaryService)
    try:
        entries, _ = dictionary_service.list_entries(limit=None)
        all_errors = []
        for entry in entries:
            errors = entry.validate(raise_exception=False)
            if errors:
                all_errors.append({'entry_id': entry.id, 'errors': errors})
        
        if all_errors:
            return jsonify({'valid': False, 'errors': all_errors}), 400
        return jsonify({'valid': True, 'errors': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@validation_bp.route('/api/validation/check', methods=['POST'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Validate entry data provided in the request',
    'parameters': [{'name': 'entry_data', 'in': 'body', 'required': True, 'description': 'Entry data to validate'}],
    'responses': {'200': {'description': 'Validation result.'}, '400': {'description': 'Invalid request data.'}}
})
def check_entry_data():
    """Validate entry data provided in the request."""
    try:
        entry_data = request.get_json()
    except Exception:
        # Invalid JSON data
        return jsonify({'valid': False, 'errors': ['Invalid JSON data']}), 400
    
    try:
        if entry_data is None:
            return jsonify({'valid': False, 'errors': ['Invalid JSON data']}), 400
        
        if not entry_data:
            return jsonify({'valid': False, 'errors': ['No data provided']}), 400
        
        # Create an Entry object from the data
        entry = Entry.from_dict(entry_data)
        
        # Validate the entry
        try:
            entry.validate()
            return jsonify({
                'valid': True,
                'errors': []
            }), 200
        except ValidationError as ve:
            return jsonify({
                'valid': False,
                'errors': ve.errors if ve.errors else [str(ve)]
            }), 200
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [f'Validation error: {str(e)}']
        }), 200  # Return 200 for validation results even if invalid

@validation_bp.route('/api/validation/batch', methods=['POST'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Validate multiple entries in batch',
    'parameters': [{'name': 'entries_data', 'in': 'body', 'required': True, 'description': 'Dictionary containing entries to validate'}],
    'responses': {'200': {'description': 'Batch validation results.'}, '400': {'description': 'Invalid request data.'}}
})
def validate_batch():
    """Validate multiple entries in batch."""
    try:
        entries_data = request.get_json()
        if not entries_data:
            return jsonify({'valid': False, 'errors': ['No data provided']}), 400
        
        if 'entries' not in entries_data:
            return jsonify({'valid': False, 'errors': ['Missing entries key']}), 400
        
        entries = entries_data['entries']
        all_errors = []
        
        for i, entry_data in enumerate(entries):
            try:
                entry = Entry.from_dict(entry_data)
                entry.validate()
            except ValidationError as ve:
                all_errors.append({
                    'index': i,
                    'id': entry_data.get('id', f'entry_{i}'),
                    'errors': ve.errors if ve.errors else [str(ve)]
                })
            except Exception as e:
                all_errors.append({
                    'index': i,
                    'id': entry_data.get('id', f'entry_{i}'),
                    'errors': [f'Validation error: {str(e)}']
                })
        
        if all_errors:
            return jsonify({'valid': False, 'errors': all_errors}), 200
        return jsonify({'valid': True, 'errors': []}), 200
        
    except Exception as e:
        return jsonify({'valid': False, 'errors': [f'Batch validation error: {str(e)}']}), 200


@validation_bp.route('/api/validation/schema', methods=['GET'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Get the JSON schema for entry validation',
    'responses': {'200': {'description': 'Entry validation schema.'}}
})
def get_validation_schema():
    """Get the JSON schema for entry validation."""
    try:
        # Return a basic entry schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "lexical_unit": {"type": "object"},
                "senses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "definition": {"type": "string"},
                            "glosses": {"type": "array"}
                        }
                    }
                }
            },
            "required": ["id", "lexical_unit"]
        }
        return jsonify(schema), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@validation_bp.route('/api/validation/rules', methods=['GET'])
@swag_from({
    'tags': ['Validation'],
    'summary': 'Get the validation rules for entries',
    'responses': {'200': {'description': 'Entry validation rules.'}}
})
def get_validation_rules():
    """Get the validation rules for entries."""
    try:
        rules = {
            "required_fields": ["id", "lexical_unit"],
            "field_types": {
                "id": "string",
                "lexical_unit": "object",
                "senses": "array"
            },
            "constraints": {
                "id": "Must be unique and non-empty",
                "lexical_unit": "Must contain at least one language entry",
                "senses": "Each sense must have a definition or glosses"
            }
        }
        return jsonify(rules), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@validation_bp.route('/validation/check', methods=['POST'])
@swag_from({'tags': ['Validation'], 'summary': 'Check a single dictionary entry for validation issues'})
def validation_check():
    """Checks a single dictionary entry for validation issues."""
    data = request.get_json()
    if not data or 'entry' not in data:
        return jsonify({'error': 'Invalid JSON. "entry" field is required.'}), 400

    try:
        dictionary_service = current_app.injector.get(DictionaryService)
        validation_result = dictionary_service.validate_entry(data['entry'])
        return jsonify(validation_result)
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@validation_bp.route('/validation/batch', methods=['POST'])
@swag_from({'tags': ['Validation'], 'summary': 'Validate a batch of dictionary entries'})
def validation_batch():
    """Validates a batch of dictionary entries."""
    data = request.get_json()
    if not data or 'entries' not in data:
        return jsonify({'error': 'Invalid JSON. "entries" field is required.'}), 400

    try:
        dictionary_service = current_app.injector.get(DictionaryService)
        results = dictionary_service.validate_batch(data['entries'])
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@validation_bp.route('/validation/schema', methods=['GET'])
@swag_from({'tags': ['Validation'], 'summary': 'Return the validation schema for dictionary entries'})
def validation_schema():
    """Returns the validation schema for dictionary entries."""
    try:
        dictionary_service = current_app.injector.get(DictionaryService)
        schema = dictionary_service.get_validation_schema()
        return jsonify(schema)
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@validation_bp.route('/validation/rules', methods=['GET'])
@swag_from({'tags': ['Validation'], 'summary': 'Return the validation rules for dictionary entries'})
def validation_rules():
    """Returns the validation rules for dictionary entries."""
    try:
        dictionary_service = current_app.injector.get(DictionaryService)
        rules = dictionary_service.get_validation_rules()
        return jsonify(rules)
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500
