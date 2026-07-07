"""
API endpoints for entry and dictionary validation.
"""

import json

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
    'summary': 'Validate multiple entries in batch using centralized validation engine',
    'parameters': [{'name': 'entries_data', 'in': 'body', 'required': True, 'description': 'Dictionary containing entries to validate'}],
    'responses': {'200': {'description': 'Batch validation results.'}, '400': {'description': 'Invalid request data.'}}
})
def validate_batch():
    """Validate multiple entries in batch using centralized validation engine."""
    from app.services.validation_engine import ValidationEngine

    try:
        entries_data = request.get_json()
        if not entries_data:
            return jsonify({'valid': False, 'errors': ['No data provided'], 'total_entries': 0, 'valid_entries': 0, 'invalid_entries': 0, 'results': []}), 400

        if 'entries' not in entries_data:
            return jsonify({'valid': False, 'errors': ['Missing entries key'], 'total_entries': 0, 'valid_entries': 0, 'invalid_entries': 0, 'results': []}), 400

        entries = entries_data.get('entries', [])
        priority_filter = entries_data.get('priority_filter', 'all')
        project_id = entries_data.get('project_id')
        validate_all = entries_data.get('validate_all', False)
        rule_id_filter = entries_data.get('rule_id') or entries_data.get('rule_id_filter')

        # First pass: collect all entry IDs for relation target validation
        existing_entry_ids: set = set()
        parsed_entries: list = []

        # For a full-dictionary audit (validate_all) we need the complete set of
        # valid targets for relation-target validation (R5.3.1). For a normal
        # batch of supplied entries this full collection scan is skipped and
        # targets are derived from the provided entries instead (see fallback below).
        if validate_all:
            from app.database.basex_connector import BaseXConnector
            try:
                db = BaseXConnector(
                    host=current_app.config.get('BASEX_HOST', 'localhost'),
                    port=current_app.config.get('BASEX_PORT', 1984),
                    username=current_app.config.get('BASEX_USER', 'admin'),
                    password=current_app.config.get('BASEX_PASSWORD', 'admin'),
                    database=current_app.config.get('BASEX_DB', 'dictionary')
                )
                db_name = db.database or current_app.config.get('BASEX_DB', 'dictionary')

                res_entry_ids = db.execute_query(f'XQUERY collection("{db_name}")//entry/@id/string()') or ""
                res_entry_guids = db.execute_query(f'XQUERY collection("{db_name}")//sense/@guid/string()') or ""
                res_sense_ids = db.execute_query(f'XQUERY collection("{db_name}")//sense/@id/string()') or ""
                res_sense_guids = db.execute_query(f'XQUERY collection("{db_name}")//sense/@guid/string()') or ""

                all_targets = set(
                    [line.strip() for line in res_entry_ids.splitlines() if line.strip()]
                    + [line.strip() for line in res_entry_guids.splitlines() if line.strip()]
                    + [line.strip() for line in res_sense_ids.splitlines() if line.strip()]
                    + [line.strip() for line in res_sense_guids.splitlines() if line.strip()]
                )
                for eid in list(all_targets):
                    if "_" in eid:
                        all_targets.add(eid.rsplit("_", 1)[-1])

                existing_entry_ids = all_targets
                current_app.logger.info(f"Loaded {len(existing_entry_ids)} valid entry/sense IDs & GUIDs from database for validation")
            except Exception as e:
                current_app.logger.warning(f"Failed to load all entry IDs from database: {e}")

        # If validate_all is requested with an empty entries list, perform a full server-side database audit
        if validate_all and not entries:
            try:
                db = BaseXConnector(
                    host=current_app.config.get('BASEX_HOST', 'localhost'),
                    port=current_app.config.get('BASEX_PORT', 1984),
                    username=current_app.config.get('BASEX_USER', 'admin'),
                    password=current_app.config.get('BASEX_PASSWORD', 'admin'),
                    database=current_app.config.get('BASEX_DB', 'dictionary')
                )
                db_name = db.database or current_app.config.get('BASEX_DB', 'dictionary')

                total_db_count_str = db.execute_query(f'XQUERY count(collection("{db_name}")//entry)') or "0"
                total_db_entries = int(total_db_count_str.strip()) if total_db_count_str.strip().isdigit() else 0

                from app.services.dictionary_service import DictionaryService
                dictionary_service = current_app.injector.get(DictionaryService)
                engine = ValidationEngine(existing_entry_ids=existing_entry_ids, project_id=project_id)

                invalid_results = []
                total_issues = 0
                total_invalid = 0
                all_errors = []
                all_warnings = []
                all_info = []

                # Run validation in chunks across the entire dictionary database
                chunk_size = 5000
                for offset in range(0, total_db_entries, chunk_size):
                    chunk_res = dictionary_service.list_entries(limit=chunk_size, offset=offset)

                    # Correctly unpack tuple (entries_list, total_count) returned by list_entries
                    if isinstance(chunk_res, tuple):
                        entries_list = chunk_res[0]
                    elif isinstance(chunk_res, dict):
                        entries_list = chunk_res.get('entries', [])
                    else:
                        entries_list = chunk_res

                    for e in entries_list:
                        e_dict = e.to_dict() if hasattr(e, 'to_dict') else (e if isinstance(e, dict) else {})
                        res = engine.validate_json(e_dict, rule_id_filter=rule_id_filter)
                        if res.errors or res.warnings or res.info:
                            total_invalid += 1
                            total_issues += len(res.errors) + len(res.warnings) + len(res.info)

                            # Capped limit to prevent massive JSON response sizes that could lock/hang the UI client
                            if len(invalid_results) < 2000:
                                headword = e.headword if hasattr(e, 'headword') else e_dict.get('id')
                                entry_errors = [{'rule_id': err.rule_id, 'rule_name': err.rule_name, 'message': err.message, 'path': err.path, 'priority': err.priority.value if hasattr(err.priority, 'value') else str(err.priority)} for err in res.errors]
                                entry_warnings = [{'rule_id': w.rule_id, 'rule_name': w.rule_name, 'message': w.message, 'path': w.path, 'priority': w.priority.value if hasattr(w.priority, 'value') else str(w.priority)} for w in res.warnings]
                                entry_info = [{'rule_id': i.rule_id, 'rule_name': i.rule_name, 'message': i.message, 'path': i.path, 'priority': i.priority.value if hasattr(i.priority, 'value') else str(i.priority)} for i in res.info]
                                invalid_results.append({
                                    'entry_id': e_dict.get('id'),
                                    'headword': headword,
                                    'valid': res.is_valid,
                                    'error_count': len(res.errors),
                                    'has_critical_errors': res.has_critical_errors,
                                    'errors': entry_errors,
                                    'warnings': entry_warnings,
                                    'info': entry_info
                                })
                                # Mirror the top-level flat lists (capped like results).
                                if len(all_errors) < 2000:
                                    all_errors.extend(entry_errors)
                                    all_warnings.extend(entry_warnings)
                                    all_info.extend(entry_info)

                total_valid = max(0, total_db_entries - total_invalid)
                return jsonify({
                    'valid': total_invalid == 0,
                    'errors': all_errors,
                    'warnings': all_warnings,
                    'info': all_info,
                    'total_entries': total_db_entries,
                    'valid_entries': total_valid,
                    'invalid_entries': total_invalid,
                    'total_issues': total_issues,
                    'results': invalid_results
                })
            except Exception as e:
                current_app.logger.error(f"Error during validate_all full audit: {e}", exc_info=True)
                return jsonify({'valid': False, 'errors': [f'Full audit error: {str(e)}'], 'total_entries': 0, 'valid_entries': 0, 'invalid_entries': 0, 'results': []}), 500






        # If we couldn't load from DB, collect from batch
        if not existing_entry_ids:
            for entry_data in entries:
                # Parse string entries as JSON
                entry = entry_data
                if isinstance(entry_data, str):
                    try:
                        entry = json.loads(entry_data)
                    except json.JSONDecodeError:
                        entry = None
                if entry and isinstance(entry, dict):
                    entry_id = entry.get('id')
                    if entry_id:
                        existing_entry_ids.add(entry_id)
                parsed_entries.append((entry_data, entry))
        else:
            # Already loaded from DB, just parse entries
            for entry_data in entries:
                entry = entry_data
                if isinstance(entry_data, str):
                    try:
                        entry = json.loads(entry_data)
                    except json.JSONDecodeError:
                        entry = None
                parsed_entries.append((entry_data, entry))

        # Initialize validation engine with existing entry IDs and project_id for project-specific rules
        engine = ValidationEngine(existing_entry_ids=existing_entry_ids, project_id=project_id)

        results = []
        valid_count = 0
        invalid_count = 0
        all_errors = []
        all_warnings = []
        all_info = []

        for i, (entry_data, entry) in enumerate(parsed_entries):
            # Skip entries that are not dictionaries or strings
            if not isinstance(entry_data, dict) and not isinstance(entry_data, str):
                results.append({
                    'entry_id': f'entry_{i}',
                    'valid': False,
                    'error_count': 1,
                    'has_critical_errors': True,
                    'errors': [{'message': f'Invalid entry type: {type(entry_data).__name__}', 'priority': 'critical', 'category': 'general'}],
                    'warnings': [],
                    'info': []
                })
                invalid_count += 1
                continue

            # Skip entries that failed to parse
            if entry is None:
                results.append({
                    'entry_id': f'entry_{i}',
                    'valid': False,
                    'error_count': 1,
                    'has_critical_errors': True,
                    'errors': [{'message': f'Invalid JSON format', 'priority': 'critical', 'category': 'general'}],
                    'warnings': [],
                    'info': []
                })
                invalid_count += 1
                continue

            # Get entry_id safely
            entry_id = f'entry_{i}'
            if isinstance(entry, dict):
                entry_id = entry.get('id', f'entry_{i}')

            try:
                result = engine.validate_json(entry, rule_id_filter=rule_id_filter)
            except Exception as e:
                result = type('ValidationResult', (), {'is_valid': False, 'errors': [type('ValidationError', (), {'message': str(e), 'priority': 'critical', 'category': 'general'})()], 'warnings': [], 'info': [], 'has_critical_errors': True, 'error_count': 1})()

            # Filter by priority if needed
            if priority_filter != 'all':
                result.errors = [e for e in result.errors if e.priority.value == priority_filter]
                result.warnings = [w for w in result.warnings if w.priority.value == priority_filter]
                result.info = [i for i in result.info if i.priority.value == priority_filter]

            def error_to_dict(error):
                return {
                    'rule_id': getattr(error, 'rule_id', 'unknown'),
                    'rule_name': getattr(error, 'rule_name', 'unknown'),
                    'message': error.message,
                    'path': getattr(error, 'path', ''),
                    'priority': error.priority.value if hasattr(error, 'priority') else 'critical',
                    'category': error.category.value if hasattr(error, 'category') else 'general',
                    'value': str(getattr(error, 'value', None)) if hasattr(error, 'value') else None
                }

            # Get headword
            headword = None
            if isinstance(entry, dict):
                lu = entry.get('lexical_unit') or {}
                if isinstance(lu, dict):
                    if 'en' in lu:
                        headword = lu['en']
                    elif lu:
                        headword = next(iter(lu.values()))
            if not headword:
                headword = entry_id

            entry_result = {
                'entry_id': entry_id,
                'headword': headword,
                'valid': result.is_valid,
                'error_count': result.error_count,
                'has_critical_errors': result.has_critical_errors,
                'errors': [error_to_dict(e) for e in result.errors],
                'warnings': [error_to_dict(w) for w in result.warnings],
                'info': [error_to_dict(i) for i in result.info]
            }
            results.append(entry_result)

            # Aggregate flat lists for the top-level response shape (consistent
            # with the single-entry /validate/check endpoint).
            all_errors.extend(entry_result['errors'])
            all_warnings.extend(entry_result['warnings'])
            all_info.extend(entry_result['info'])

            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        response = {
            'valid': invalid_count == 0,
            'errors': all_errors,
            'warnings': all_warnings,
            'info': all_info,
            'total_entries': len(entries),
            'valid_entries': valid_count,
            'invalid_entries': invalid_count,
            'results': results
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({'valid': False, 'errors': [f'Batch validation error: {str(e)}'], 'total_entries': 0, 'valid_entries': 0, 'invalid_entries': 0, 'results': []}), 200


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
        from app.services.validation_engine import ValidationEngine

        entry = data['entry']
        engine = ValidationEngine(project_id=data.get('project_id'))
        result = engine.validate_json(entry)

        def _to_dict(error):
            return {
                'rule_id': error.rule_id,
                'rule_name': error.rule_name,
                'message': error.message,
                'path': error.path,
                'priority': error.priority.value,
                'category': error.category.value,
            }

        return jsonify({
            'valid': result.is_valid,
            'has_critical_errors': result.has_critical_errors,
            'error_count': result.error_count,
            'errors': [_to_dict(e) for e in result.errors],
            'warnings': [_to_dict(w) for w in result.warnings],
            'info': [_to_dict(i) for i in result.info],
        })
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@validation_bp.route('/validation/batch', methods=['POST'])
@swag_from({'tags': ['Validation'], 'summary': 'Validate a batch of dictionary entries'})
def validation_batch():
    """Validates a batch of dictionary entries (delegates to the canonical batch handler)."""
    return validate_batch()

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
