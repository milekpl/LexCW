"""API endpoints for ranges editor."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app, Response
from typing import Union, Tuple, Any

from app.services.ranges_service import RangesService
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError
from flasgger import swag_from


ranges_editor_bp = Blueprint('ranges_editor', __name__, url_prefix='/api/ranges-editor')


@ranges_editor_bp.route('/', methods=['GET'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'List all LIFT ranges',
    'description': 'Retrieve all ranges from the database for editing',
    'responses': {
        200: {
            'description': 'List of ranges',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'description': 'Dictionary of ranges keyed by range ID'
                    }
                }
            }
        },
        500: {
            'description': 'Server error',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def list_ranges() -> Union[Response, Tuple[Response, int]]:
    """Get all ranges."""
    try:
        service = current_app.injector.get(RangesService)
        ranges = service.get_all_ranges()
        return jsonify({'success': True, 'data': ranges})
    except Exception as e:
        current_app.logger.error(f"Error listing ranges: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>', methods=['GET'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Get specific range',
    'description': 'Retrieve a specific range by ID',
    'parameters': [{
        'in': 'path',
        'name': 'range_id',
        'required': True,
        'type': 'string',
        'description': 'ID of the range to retrieve'
    }],
    'responses': {
        200: {
            'description': 'Range data',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'object'}
                }
            }
        },
        404: {
            'description': 'Range not found',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def get_range(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """Get specific range by ID."""
    try:
        service = current_app.injector.get(RangesService)
        range_data = service.get_range(range_id)
        return jsonify({'success': True, 'data': range_data})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/', methods=['POST'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Create new range',
    'description': 'Create a new range with the provided data. JSON input is disabled; use XML payloads.',
    'consumes': ['application/xml'],
    'parameters': [{
        'in': 'body',
        'name': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id', 'labels'],
            'properties': {
                'id': {
                    'type': 'string',
                    'description': 'Unique identifier for the range'
                },
                'labels': {
                    'type': 'object',
                    'description': 'Multilingual labels (lang -> text)',
                    'example': {'en': 'My Range'}
                },
                'descriptions': {
                    'type': 'object',
                    'description': 'Multilingual descriptions (lang -> text)',
                    'example': {'en': 'Description of my range'}
                }
            }
        }
    }],
    'responses': {
        201: {
            'description': 'Range created',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'guid': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Validation error',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        },
        500: {
            'description': 'Server error',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def create_range() -> Union[Response, Tuple[Response, int]]:
    """Create new range."""
    try:
        # Reject JSON body for data-rich endpoints; prefer XML request payloads
        if request.content_type and 'application/json' in request.content_type:
            return jsonify({'success': False, 'error': 'JSON input disabled; use XML payloads'}), 415
        data = request.get_json(silent=True)
        
        # Validate required fields
        if not data or 'id' not in data or 'labels' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: id, labels'
            }), 400
        
        service = current_app.injector.get(RangesService)
        guid = service.create_range(data)
        
        return jsonify({
            'success': True,
            'data': {'guid': guid}
        }), 201
    
    except ValidationError as e:
        current_app.logger.error(f"Validation error creating range: {e}. Data: {data}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating range: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>', methods=['PUT'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Update range',
    'description': 'Update an existing range. JSON input is disabled; use XML payloads.',
    'consumes': ['application/xml'],
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string',
            'description': 'ID of the range to update'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'labels': {'type': 'object'},
                    'descriptions': {'type': 'object'},
                    'guid': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Range updated',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        404: {'description': 'Range not found'},
        400: {'description': 'Validation error'},
        500: {'description': 'Server error'}
    }
})
def update_range(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """Update existing range."""
    try:
        if request.content_type and 'application/json' in request.content_type:
            return jsonify({'success': False, 'error': 'JSON input disabled; use XML payloads'}), 415
        data = request.get_json(silent=True)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        service = current_app.injector.get(RangesService)
        service.update_range(range_id, data)
        
        return jsonify({
            'success': True,
            'message': f"Range '{range_id}' updated successfully"
        })
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>', methods=['DELETE'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Delete range',
    'description': 'Delete a range with optional data migration',
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string',
            'description': 'ID of the range to delete'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': False,
            'schema': {
                'type': 'object',
                'properties': {
                    'migration': {
                        'type': 'object',
                        'properties': {
                            'operation': {
                                'type': 'string',
                                'enum': ['remove', 'replace'],
                                'description': 'Migration operation'
                            },
                            'new_value': {
                                'type': 'string',
                                'description': 'New value (required for replace)'
                            }
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        200: {'description': 'Range deleted'},
        400: {'description': 'Validation error'},
        404: {'description': 'Range not found'},
        500: {'description': 'Server error'}
    }
})
def delete_range(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """Delete range with optional migration."""
    try:
        data = request.get_json(silent=True) or {}
        migration = data.get('migration')
        
        service = current_app.injector.get(RangesService)
        service.delete_range(range_id, migration=migration)
        
        return jsonify({
            'success': True,
            'message': f"Range '{range_id}' deleted successfully"
        })
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error deleting range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Range Elements Endpoints ---

@ranges_editor_bp.route('/<range_id>/elements', methods=['GET'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'List range elements',
    'description': 'Get all elements within a range',
    'parameters': [{
        'in': 'path',
        'name': 'range_id',
        'required': True,
        'type': 'string',
        'description': 'ID of the parent range'
    }],
    'responses': {
        200: {'description': 'List of range elements'},
        404: {'description': 'Range not found'},
        500: {'description': 'Server error'}
    }
})
def list_range_elements(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """Get all elements in a range."""
    try:
        service = current_app.injector.get(RangesService)
        range_data = service.get_range(range_id)
        
        return jsonify({
            'success': True,
            'data': range_data.get('values', [])
        })
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error listing elements for range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>/elements', methods=['POST'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Create range element',
    'description': 'Create a new element within a range. JSON input is disabled; use XML payloads.',
    'consumes': ['application/xml'],
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['id', 'labels'],
                'properties': {
                    'id': {'type': 'string'},
                    'parent': {'type': 'string'},
                    'labels': {'type': 'object'},
                    'descriptions': {'type': 'object'},
                    'abbrevs': {'type': 'object'},
                    'traits': {'type': 'object'}
                }
            }
        }
    ],
    'responses': {
        201: {'description': 'Element created'},
        400: {'description': 'Validation error'},
        404: {'description': 'Range not found'},
        500: {'description': 'Server error'}
    }
})
def create_range_element(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """Create new element in range."""
    try:
        if request.content_type and 'application/json' in request.content_type:
            return jsonify({'success': False, 'error': 'JSON input disabled; use XML payloads'}), 415
        data = request.get_json(silent=True)

        
        if not data or 'id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: id'
            }), 400
        
        # Transform frontend format to backend format
        element_data = {
            'id': data['id'],
            'labels': data.get('labels', {}),
            'descriptions': data.get('descriptions', {}),
            'abbrevs': data.get('abbrevs', {}),
            'parent': data.get('parent', ''),
            'traits': data.get('traits', {})
        }
        
        # Set value field
        if 'value' in data:
            element_data['value'] = data['value']
        
        service = current_app.injector.get(RangesService)
        guid = service.create_range_element(range_id, element_data)
        
        return jsonify({
            'success': True,
            'data': {'guid': guid}
        }), 201
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        current_app.logger.error(f"Validation error creating element: {e}. Data: {element_data}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating element in range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>/elements/<element_id>', methods=['GET'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Get range element',
    'description': 'Get a specific element within a range',
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string',
            'description': 'ID of the parent range'
        },
        {
            'in': 'path',
            'name': 'element_id',
            'required': True,
            'type': 'string',
            'description': 'ID of the element'
        }
    ],
    'responses': {
        200: {'description': 'Element details'},
        404: {'description': 'Range or element not found'},
        500: {'description': 'Server error'}
    }
})
def get_range_element(range_id: str, element_id: str) -> Union[Response, Tuple[Response, int]]:
    """Get specific element from a range."""
    try:
        service = current_app.injector.get(RangesService)
        range_data = service.get_range(range_id)
        
        # Find the element
        element = None
        for elem in range_data.get('values', []):
            if elem.get('id') == element_id:
                element = elem
                break
        
        if not element:
            return jsonify({
                'success': False,
                'error': f'Element {element_id} not found in range {range_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': element
        })
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting element {element_id} from range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>/elements/<element_id>', methods=['PUT'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Update range element',
    'description': 'Update an existing element within a range. JSON input is disabled; use XML payloads.',
    'consumes': ['application/xml'],
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string'
        },
        {
            'in': 'path',
            'name': 'element_id',
            'required': True,
            'type': 'string'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'labels': {'type': 'object'},
                    'descriptions': {'type': 'object'},
                    'abbrevs': {'type': 'object'},
                    'parent': {'type': 'string'},
                    'traits': {'type': 'object'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': 'Element updated'},
        400: {'description': 'Validation error'},
        404: {'description': 'Range or element not found'},
        500: {'description': 'Server error'}
    }
})
def update_range_element(range_id: str, element_id: str) -> Union[Response, Tuple[Response, int]]:
    """Update existing range element."""
    try:
        if request.content_type and 'application/json' in request.content_type:
            return jsonify({'success': False, 'error': 'JSON input disabled; use XML payloads'}), 415
        data = request.get_json(silent=True)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        service = current_app.injector.get(RangesService)
        service.update_range_element(range_id, element_id, data)
        
        return jsonify({
            'success': True,
            'message': f"Element '{element_id}' updated successfully"
        })
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating element {element_id} in range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>/elements/<element_id>', methods=['DELETE'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Delete range element',
    'description': 'Delete an element from a range with optional migration',
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string'
        },
        {
            'in': 'path',
            'name': 'element_id',
            'required': True,
            'type': 'string'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': False,
            'schema': {
                'type': 'object',
                'properties': {
                    'migration': {
                        'type': 'object',
                        'properties': {
                            'operation': {
                                'type': 'string',
                                'enum': ['remove', 'replace']
                            },
                            'new_value': {'type': 'string'}
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        200: {'description': 'Element deleted'},
        400: {'description': 'Validation error'},
        404: {'description': 'Range or element not found'},
        500: {'description': 'Server error'}
    }
})
def delete_range_element(range_id: str, element_id: str) -> Union[Response, Tuple[Response, int]]:
    """Delete range element with optional migration."""
    try:
        data = request.get_json(silent=True) or {}
        migration = data.get('migration')
        
        service = current_app.injector.get(RangesService)
        service.delete_range_element(range_id, element_id, migration=migration)
        
        return jsonify({
            'success': True,
            'message': f"Element '{element_id}' deleted successfully"
        })
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error deleting element {element_id} from range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Usage Analysis & Migration Endpoints ---

@ranges_editor_bp.route('/<range_id>/usage', methods=['GET'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Get range usage',
    'description': 'Find entries using this range or specific element',
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string'
        },
        {
            'in': 'query',
            'name': 'element_id',
            'required': False,
            'type': 'string',
            'description': 'Specific element to check usage for'
        }
    ],
    'responses': {
        200: {
            'description': 'Usage information',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'entry_id': {'type': 'string'},
                                'headword': {'type': 'string'},
                                'count': {'type': 'integer'}
                            }
                        }
                    }
                }
            }
        },
        404: {'description': 'Range not found'},
        500: {'description': 'Server error'}
    }
})
def get_range_usage(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """Get usage information for range or element."""
    try:
        element_id = request.args.get('element_id')
        
        service = current_app.injector.get(RangesService)
        
        # If element_id is specified, return detailed usage for that element
        if element_id:
            usage = service.find_range_usage(range_id, element_id)
            return jsonify({
                'success': True,
                'data': usage
            })
        
        # Otherwise, return usage grouped by element
        usage_stats = service.get_usage_by_element(range_id)
        return jsonify({
            'success': True,
            'data': usage_stats
        })
    
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting usage for range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/<range_id>/migrate', methods=['POST'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Migrate range values',
    'description': 'Bulk migrate range values in entries. JSON input is disabled; use XML payloads.',
    'consumes': ['application/xml'],
    'parameters': [
        {
            'in': 'path',
            'name': 'range_id',
            'required': True,
            'type': 'string'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['operation'],
                'properties': {
                    'old_value': {
                        'type': 'string',
                        'description': 'Value to migrate (null for all)'
                    },
                    'operation': {
                        'type': 'string',
                        'enum': ['remove', 'replace'],
                        'description': 'Migration operation'
                    },
                    'new_value': {
                        'type': 'string',
                        'description': 'New value (required for replace)'
                    },
                    'dry_run': {
                        'type': 'boolean',
                        'description': 'If true, only count affected entries',
                        'default': False
                    }
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Migration result',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'entries_affected': {'type': 'integer'},
                            'fields_updated': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Validation error'},
        500: {'description': 'Server error'}
    }
})
def migrate_range_values(range_id: str) -> Union[Response, Tuple[Response, int]]:
    """Migrate range values in entries."""
    try:
        if request.content_type and 'application/json' in request.content_type:
            return jsonify({'success': False, 'error': 'JSON input disabled; use XML payloads'}), 415
        data = request.get_json(silent=True)
        
        if not data or 'operation' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: operation'
            }), 400
        
        old_value = data.get('old_value')
        operation = data['operation']
        new_value = data.get('new_value')
        dry_run = data.get('dry_run', False)
        
        service = current_app.injector.get(RangesService)
        result = service.migrate_range_values(
            range_id, old_value, operation, new_value, dry_run
        )
        
        return jsonify({
            'success': True,
            'data': result
        })

    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error migrating values for range {range_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Custom Ranges Endpoints ---

@ranges_editor_bp.route('/custom', methods=['GET'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'List custom ranges',
    'description': 'Get all custom ranges for the current project',
    'responses': {
        200: {
            'description': 'List of custom ranges',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    }
                }
            }
        },
        500: {'description': 'Server error'}
    }
})
def get_custom_ranges() -> Union[Response, Tuple[Response, int]]:
    """Get all custom ranges for the current project."""
    try:
        from app.models.custom_ranges import CustomRange

        # Get current project ID (assuming it's available via session or config)
        project_id = 1  # Default project ID, should be retrieved from session/context

        custom_ranges = CustomRange.query.filter_by(project_id=project_id).all()
        return jsonify({
            'success': True,
            'data': [cr.to_dict() for cr in custom_ranges]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting custom ranges: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/custom', methods=['POST'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Create custom range',
    'description': 'Create a new custom range with elements',
    'parameters': [{
        'in': 'body',
        'name': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['range_type', 'range_name', 'element_id'],
            'properties': {
                'range_type': {
                    'type': 'string',
                    'enum': ['relation', 'trait'],
                    'description': 'Type of range'
                },
                'range_name': {
                    'type': 'string',
                    'description': 'Name of the range'
                },
                'element_id': {
                    'type': 'string',
                    'description': 'ID of the range element'
                },
                'element_label': {
                    'type': 'string',
                    'description': 'Label for the element'
                },
                'element_description': {
                    'type': 'string',
                    'description': 'Description for the element'
                },
                'values': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'value': {'type': 'string'},
                            'label': {'type': 'string'},
                            'description': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }],
    'responses': {
        201: {'description': 'Custom range created'},
        400: {'description': 'Validation error'},
        500: {'description': 'Server error'}
    }
})
def create_custom_range() -> Union[Response, Tuple[Response, int]]:
    """Create new custom range."""
    try:
        from app.models.custom_ranges import CustomRange, CustomRangeValue
        from app.models.workset_models import db

        data = request.get_json()

        if not data or 'range_type' not in data or 'range_name' not in data or 'element_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: range_type, range_name, element_id'
            }), 400

        project_id = 1  # Default project ID, should be retrieved from session/context

        custom_range = CustomRange(
            project_id=project_id,
            range_type=data['range_type'],
            range_name=data['range_name'],
            element_id=data['element_id'],
            element_label=data.get('element_label'),
            element_description=data.get('element_description')
        )

        db.session.add(custom_range)
        db.session.flush()  # Get the ID

        # Add values if provided
        for val_data in data.get('values', []):
            value = CustomRangeValue(
                custom_range_id=custom_range.id,
                value=val_data['value'],
                label=val_data.get('label'),
                description=val_data.get('description')
            )
            db.session.add(value)

        db.session.commit()
        return jsonify({
            'success': True,
            'data': custom_range.to_dict()
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating custom range: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
