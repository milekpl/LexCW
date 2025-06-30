"""
API endpoints for entry and dictionary validation.
"""

from flask import Blueprint, jsonify, request
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import NotFoundError, ValidationError
from app import injector
from app.models.entry import Entry

validation_bp = Blueprint('validation_bp', __name__)

@validation_bp.route('/api/validation/entry/<string:entry_id>', methods=['GET'])
def validate_entry(entry_id: str):
    """
    Validate a single dictionary entry.
    ---
    parameters:
      - name: entry_id
        in: path
        type: string
        required: true
        description: The ID of the entry to validate.
    responses:
      200:
        description: Validation result.
        schema:
          type: object
          properties:
            valid:
              type: boolean
            errors:
              type: array
              items:
                type: string
      404:
        description: Entry not found.
    """
    dictionary_service = injector.get(DictionaryService)
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
def validate_dictionary():
    """
    Validate the entire dictionary.
    ---
    responses:
      200:
        description: Validation result.
        schema:
          type: object
          properties:
            valid:
              type: boolean
            errors:
              type: array
              items:
                type: object
                properties:
                  entry_id:
                    type: string
                  errors:
                    type: array
                    items:
                      type: string
    """
    dictionary_service = injector.get(DictionaryService)
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
def check_entry_data():
    """
    Validate entry data provided in the request.
    ---
    parameters:
      - name: entry_data
        in: body
        description: Entry data to validate
        required: true
        schema:
          type: object
    responses:
      200:
        description: Validation result.
        schema:
          type: object
          properties:
            valid:
              type: boolean
            errors:
              type: array
              items:
                type: string
      400:
        description: Invalid request data.
    """
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
def validate_batch():
    """
    Validate multiple entries in batch.
    ---
    parameters:
      - name: entries_data
        in: body
        description: Dictionary containing entries to validate
        required: true
        schema:
          type: object
          properties:
            entries:
              type: array
              items:
                type: object
    responses:
      200:
        description: Batch validation results.
        schema:
          type: object
          properties:
            valid:
              type: boolean
            errors:
              type: array
              items:
                type: object
      400:
        description: Invalid request data.
    """
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
def get_validation_schema():
    """
    Get the JSON schema for entry validation.
    ---
    responses:
      200:
        description: Entry validation schema.
        schema:
          type: object
    """
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
def get_validation_rules():
    """
    Get the validation rules for entries.
    ---
    responses:
      200:
        description: Entry validation rules.
        schema:
          type: object
    """
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
