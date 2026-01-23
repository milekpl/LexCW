"""
API endpoints for dictionary management.

Provides endpoints for:
- Project dictionary CRUD operations
- User dictionary management
- Dictionary upload and validation
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, request, jsonify, current_app, session, render_template
from flasgger import swag_from

from app.models.dictionary_models import ProjectDictionary, UserDictionary, SystemDictionary
from app.models.project_settings import ProjectSettings
from app.services.dictionary_storage_service import get_storage_service
from app.services.dictionary_loader import get_dictionary_loader
from app.models.workset_models import db

# Create blueprint
dictionary_bp = Blueprint('dictionaries', __name__)
logger = logging.getLogger(__name__)


# === Project Dictionary Endpoints ===

@dictionary_bp.route('/api/projects/<int:project_id>/dictionaries', methods=['GET'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'List project dictionaries',
    'parameters': [
        {'name': 'project_id', 'in': 'path', 'type': 'integer', 'required': True}
    ],
    'responses': {
        '200': {'description': 'List of dictionaries'},
        '404': {'description': 'Project not found'}
    }
})
def list_project_dictionaries(project_id: int):
    """List all dictionaries for a project."""
    # Verify project exists
    project = ProjectSettings.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    dictionaries = ProjectDictionary.query.filter(
        ProjectDictionary.project_id == project_id,
        ProjectDictionary.is_active == True
    ).all()

    # Get IPA dictionary if configured
    ipa_dict = ProjectDictionary.get_ipa_dictionary(project_id)

    return jsonify({
        'dictionaries': [d.to_summary() for d in dictionaries],
        'ipa_dictionary_id': ipa_dict.id if ipa_dict else None,
        'default_dictionary_id': project.settings_json.get('spell_check', {}).get('default_dictionary_id')
    })


@dictionary_bp.route('/api/projects/<int:project_id>/dictionaries/upload', methods=['POST'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'Upload a dictionary',
    'parameters': [
        {'name': 'project_id', 'in': 'path', 'type': 'integer', 'required': True},
        {'name': 'dic_file', 'in': 'formData', 'type': 'file', 'required': True},
        {'name': 'aff_file', 'in': 'formData', 'type': 'file', 'required': True},
        {'name': 'name', 'in': 'formData', 'type': 'string', 'required': False},
        {'name': 'lang_code', 'in': 'formData', 'type': 'string', 'required': False}
    ],
    'responses': {
        '200': {'description': 'Upload successful'},
        '400': {'description': 'Invalid upload'}
    }
})
def upload_project_dictionary(project_id: int):
    """Upload a new hunspell dictionary to a project."""
    # Verify project exists
    project = ProjectSettings.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Get uploaded files
    dic_file = request.files.get('dic_file')
    aff_file = request.files.get('aff_file')

    if not dic_file:
        return jsonify({'error': 'Dictionary file (.dic) is required'}), 400

    try:
        storage = get_storage_service()

        # Validate and save dictionary
        dictionary, warnings = storage.validate_and_save_project_dictionary(
            project_id=project_id,
            dic_file=dic_file,
            aff_file=aff_file,
            name=request.form.get('name'),
            lang_code=request.form.get('lang_code')
        )

        # Save to database
        db.session.add(dictionary)
        db.session.commit()

        # Invalidate dictionary cache
        loader = get_dictionary_loader()
        loader.invalidate_project_cache(project_id)

        return jsonify({
            'success': True,
            'dictionary': dictionary.to_summary(),
            'warnings': warnings
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Dictionary upload failed: {e}")
        return jsonify({'error': 'Upload failed'}), 500


@dictionary_bp.route('/api/projects/<int:project_id>/dictionaries/<dict_id>', methods=['DELETE'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'Delete a dictionary',
    'parameters': [
        {'name': 'project_id', 'in': 'path', 'type': 'integer', 'required': True},
        {'name': 'dict_id', 'in': 'path', 'type': 'string', 'required': True}
    ],
    'responses': {
        '200': {'description': 'Deletion successful'},
        '404': {'description': 'Dictionary not found'}
    }
})
def delete_project_dictionary(project_id: int, dict_id: str):
    """Delete a project dictionary (soft delete)."""
    dictionary = ProjectDictionary.query.filter(
        ProjectDictionary.id == dict_id,
        ProjectDictionary.project_id == project_id
    ).first()

    if not dictionary:
        return jsonify({'error': 'Dictionary not found'}), 404

    # Soft delete
    dictionary.is_active = False
    db.session.commit()

    # Delete files
    storage = get_storage_service()
    storage.delete_dictionary_files(dictionary)

    # Invalidate cache
    loader = get_dictionary_loader()
    loader.invalidate_project_cache(project_id)

    return jsonify({'success': True})


@dictionary_bp.route('/api/projects/<int:project_id>/dictionaries/<dict_id>/default', methods=['PUT'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'Set dictionary as default',
    'parameters': [
        {'name': 'project_id', 'in': 'path', 'type': 'integer', 'required': True},
        {'name': 'dict_id', 'in': 'path', 'type': 'string', 'required': True}
    ],
    'responses': {
        '200': {'description': 'Success'},
        '404': {'description': 'Dictionary not found'}
    }
})
def set_default_dictionary(project_id: int, dict_id: str):
    """Set a dictionary as the default for a project."""
    dictionary = ProjectDictionary.query.filter(
        ProjectDictionary.id == dict_id,
        ProjectDictionary.project_id == project_id,
        ProjectDictionary.is_active == True
    ).first()

    if not dictionary:
        return jsonify({'error': 'Dictionary not found'}), 404

    # Clear existing default
    ProjectDictionary.query.filter(
        ProjectDictionary.project_id == project_id,
        ProjectDictionary.is_default == True
    ).update({'is_default': False})

    # Set new default
    dictionary.is_default = True
    db.session.commit()

    # Update project settings
    project = ProjectSettings.query.get(project_id)
    if project:
        if 'spell_check' not in project.settings_json:
            project.settings_json['spell_check'] = {}
        project.settings_json['spell_check']['default_dictionary_id'] = dict_id
        db.session.commit()

    return jsonify({'success': True})


@dictionary_bp.route('/api/projects/<int:project_id>/dictionaries/<dict_id>/ipa', methods=['PUT'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'Set dictionary as IPA dictionary',
    'parameters': [
        {'name': 'project_id', 'in': 'path', 'type': 'integer', 'required': True},
        {'name': 'dict_id', 'in': 'path', 'type': 'string', 'required': True}
    ],
    'responses': {
        '200': {'description': 'Success'},
        '404': {'description': 'Dictionary not found'}
    }
})
def set_ipa_dictionary(project_id: int, dict_id: str):
    """Set a dictionary as the IPA dictionary for a project."""
    dictionary = ProjectDictionary.query.filter(
        ProjectDictionary.id == dict_id,
        ProjectDictionary.project_id == project_id,
        ProjectDictionary.is_active == True
    ).first()

    if not dictionary:
        return jsonify({'error': 'Dictionary not found'}), 404

    # Update project settings
    project = ProjectSettings.query.get(project_id)
    if project:
        if 'spell_check' not in project.settings_json:
            project.settings_json['spell_check'] = {}
        project.settings_json['spell_check']['ipa_dictionary_id'] = dict_id
        db.session.commit()

    return jsonify({'success': True})


# === User Dictionary Endpoints ===

@dictionary_bp.route('/api/user/dictionaries', methods=['GET'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'List user dictionaries',
    'responses': {
        '200': {'description': 'List of dictionaries'}
    }
})
def list_user_dictionaries():
    """List all dictionaries for the current user."""
    try:
        from flask_login import current_user
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
    except (RuntimeError, AttributeError):
        return jsonify({'error': 'Authentication required'}), 401

    dictionaries = UserDictionary.query.filter(
        UserDictionary.user_id == current_user.id,
        UserDictionary.is_active == True
    ).all()

    return jsonify({
        'dictionaries': [d.to_summary() for d in dictionaries]
    })


@dictionary_bp.route('/api/user/dictionaries/custom-words', methods=['POST'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'Add custom words',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'lang_code': {'type': 'string'},
                    'words': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Success'},
        '400': {'description': 'Invalid request'}
    }
})
def add_custom_words():
    """Add custom words to user dictionary."""
    try:
        from flask_login import current_user
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
    except (RuntimeError, AttributeError):
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', 'Custom Words')
    lang_code = data.get('lang_code')
    words = data.get('words', [])

    if not lang_code:
        return jsonify({'error': 'Language code is required'}), 400

    if not words:
        return jsonify({'error': 'At least one word is required'}), 400

    try:
        dictionary = UserDictionary.create_custom_words(
            user_id=current_user.id,
            name=name,
            lang_code=lang_code,
            words=words
        )

        db.session.add(dictionary)
        db.session.commit()

        # Invalidate cache
        loader = get_dictionary_loader()
        loader.invalidate_user_cache(current_user.id)

        return jsonify({
            'success': True,
            'dictionary': dictionary.to_summary()
        })

    except Exception as e:
        logger.error(f"Failed to add custom words: {e}")
        return jsonify({'error': 'Failed to save words'}), 500


@dictionary_bp.route('/api/user/dictionaries/<dict_id>', methods=['DELETE'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'Delete user dictionary',
    'responses': {
        '200': {'description': 'Success'},
        '404': {'description': 'Dictionary not found'}
    }
})
def delete_user_dictionary(dict_id: str):
    """Delete a user dictionary."""
    try:
        from flask_login import current_user
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
    except (RuntimeError, AttributeError):
        return jsonify({'error': 'Authentication required'}), 401

    dictionary = UserDictionary.query.filter(
        UserDictionary.id == dict_id,
        UserDictionary.user_id == current_user.id
    ).first()

    if not dictionary:
        return jsonify({'error': 'Dictionary not found'}), 404

    dictionary.is_active = False
    db.session.commit()

    # Invalidate cache
    loader = get_dictionary_loader()
    loader.invalidate_user_cache(current_user.id)

    return jsonify({'success': True})


# === System Dictionary Endpoints ===

@dictionary_bp.route('/api/dictionaries/system', methods=['GET'])
@swag_from({
    'tags': 'Dictionaries',
    'summary': 'List system dictionaries',
    'responses': {
        '200': {'description': 'List of system dictionaries'}
    }
})
def list_system_dictionaries():
    """List hunspell dictionaries installed on the server."""
    loader = get_dictionary_loader()
    system_dicts = loader.discover_system_dictionaries()

    return jsonify({
        'dictionaries': [
            {
                'lang_code': lang_code,
                'dic_path': info['dic_path'],
                'aff_path': info['aff_path']
            }
            for lang_code, info in system_dicts.items()
        ]
    })


# === UI Routes ===

@dictionary_bp.route('/projects/<int:project_id>/dictionaries', methods=['GET'])
def project_dictionaries_page(project_id: int):
    """Show dictionary management page for a project."""
    # Get project
    project = ProjectSettings.query.get_or_404(project_id)

    # Get project dictionaries
    dictionaries = ProjectDictionary.query.filter(
        ProjectDictionary.project_id == project_id,
        ProjectDictionary.is_active == True
    ).all()

    # Get IPA dictionary
    ipa_dict = ProjectDictionary.get_ipa_dictionary(project_id)
    ipa_dictionary_id = ipa_dict.id if ipa_dict else None

    # Get user dictionaries if logged in
    user_dictionaries = []
    user_id = None
    try:
        from flask_login import current_user
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            user_id = current_user.id
            user_dictionaries = UserDictionary.query.filter(
                UserDictionary.user_id == user_id,
                UserDictionary.is_active == True
            ).all()
    except (RuntimeError, AttributeError):
        # Flask-Login not initialized or no user context
        pass

    # Get system dictionaries
    loader = get_dictionary_loader()
    system_dicts = loader.discover_system_dictionaries()
    system_dictionaries = [
        {'lang_code': lang_code, 'dic_path': info['dic_path'], 'aff_path': info['aff_path']}
        for lang_code, info in system_dicts.items()
    ]

    # Get spell_check settings from project
    spell_check_settings = project.settings_json.get('spell_check', {})

    return render_template(
        'project_dictionaries.html',
        project=project,
        dictionaries=[d.to_summary() for d in dictionaries],
        ipa_dictionary_id=ipa_dictionary_id,
        user_dictionaries=[d.to_summary() for d in user_dictionaries],
        system_dictionaries=system_dictionaries,
        spell_check_settings=spell_check_settings
    )


# === Dictionary Validation Endpoints ===

@dictionary_bp.route('/api/validation/dictionary-check', methods=['POST'])
@swag_from({
    'tags': 'Validation',
    'summary': 'Validate text with automatic dictionary detection',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string'},
                    'field_path': {'type': 'string'},
                    'project_id': {'type': 'integer'},
                    'entry_data': {'type': 'object'}
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Validation results'}
    }
})
def validate_with_dictionary():
    """Validate text using automatic dictionary selection."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    text = data.get('text', '')
    field_path = data.get('field_path', '')
    project_id = data.get('project_id')
    entry_data = data.get('entry_data')

    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400

    # Get project settings
    project = ProjectSettings.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    try:
        from flask_login import current_user
        user_id = current_user.id if current_user.is_authenticated else None

        from app.validators.layered_hunspell_validator import create_hunspell_validator
        validator = create_hunspell_validator(project_id, user_id)

        result = validator.validate_text(
            text=text,
            field_path=field_path,
            project_settings=project,
            entry_data=entry_data
        )

        return jsonify({
            'is_valid': result.is_valid,
            'suggestions': result.suggestions,
            'metadata': result.metadata
        })

    except Exception as e:
        logger.error(f"Dictionary validation failed: {e}")
        return jsonify({'error': 'Validation failed'}), 500


# === Utility Endpoints ===

@dictionary_bp.route('/api/dictionaries/<project_id>/stats', methods=['GET'])
def get_dictionary_stats(project_id: int):
    """Get storage statistics for project dictionaries."""
    try:
        storage = get_storage_service()
        stats = storage.get_dictionary_stats(project_id)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500


@dictionary_bp.route('/api/projects/<int:project_id>/dictionaries/cleanup', methods=['POST'])
def cleanup_orphaned_files(project_id: int):
    """Clean up orphaned dictionary files."""
    try:
        storage = get_storage_service()
        removed = storage.cleanup_orphaned_files(project_id)
        return jsonify({
            'success': True,
            'removed_count': removed
        })
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500
