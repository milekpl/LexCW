"""
API endpoints for entry and dictionary validation.
"""

from flask import Blueprint, jsonify
from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import NotFoundError
from app import injector

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
        errors = entry.validate(raise_exception=False)
        if errors:
            return jsonify({'valid': False, 'errors': errors}), 400
        return jsonify({'valid': True, 'errors': []})
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
