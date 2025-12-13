from __future__ import annotations

import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flasgger import swag_from

from app.forms.settings_form import SettingsForm
from app.config_manager import ConfigManager
from app.services.dictionary_service import DictionaryService

# Create blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')
logger = logging.getLogger(__name__)

@settings_bp.route('/', methods=['GET', 'POST'])
@swag_from({
    'summary': 'Manage Project Settings',
    'description': 'View and update project-specific settings such as project name, source language, and target language.',
    'tags': ['Settings'],
    'parameters': [
        {
            'name': 'project_name',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': 'The name of the lexicography project.'
        },
        {
            'name': 'source_language_code',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': 'The language code for the source/vernacular language (e.g., "en", "seh").'
        },
        {
            'name': 'source_language_name',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': 'The display name for the source language (e.g., "English", "Sena").'
        },
        {
            'name': 'target_language_code',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': 'The language code for the target language (e.g., "es", "pt").'
        },
        {
            'name': 'target_language_name',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': 'The display name for the target language (e.g., "Spanish", "Portuguese").'
        }
    ],
    'responses': {
        '200': {
            'description': 'Settings page rendered or settings successfully updated.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Settings updated successfully!'}
                }
            }
        },
        '400': {
            'description': 'Form validation error.'
        }
    }
})
def manage_settings():
    """Displays and handles updates for project settings."""
    config_manager = current_app.config_manager
    form = SettingsForm()

    if form.validate_on_submit():
        try:
            new_settings = form.to_dict()
            config_manager.update_current_settings(new_settings)
            flash('Settings updated successfully!', 'success')
            logger.info(f"Project settings updated: {new_settings}")
            return redirect(url_for('settings.manage_settings'))
        except Exception as e:
            logger.error(f"Error updating settings: {e}", exc_info=True)
            flash(f'Error updating settings: {str(e)}', 'danger')
    elif request.method == 'GET':
        form.populate_from_config(config_manager)

    # For displaying current settings, especially if form validation fails
    project_query = request.args.get('project')
    show_wizard = request.args.get('wizard', 'false').lower() == 'true'
    if project_query:
        # Load specific project settings
        project_settings = config_manager.get_settings(project_query)
        if project_settings:
            current_settings = project_settings.settings_json
        else:
            current_settings = {
                'project_name': config_manager.get_project_name(),
                'source_language': config_manager.get_source_language(),
                'target_languages': config_manager.get_target_languages()
            }
    else:
        current_settings = {
            'project_name': config_manager.get_project_name(),
            'source_language': config_manager.get_source_language(),
            'target_languages': config_manager.get_target_languages()
        }

    # Determine if we should show setup wizard (explicit param or missing ranges)
    dict_service = current_app.injector.get(DictionaryService)
    ranges = dict_service.get_lift_ranges()
    show_wizard = show_wizard or (not ranges)

    return render_template('settings.html',
                           form=form,
                           title="Project Settings",
                           current_settings=current_settings,
                           show_wizard=show_wizard,
                           project_query=project_query)


@settings_bp.route('/projects', methods=['GET'])
@swag_from({
    'summary': 'List Projects',
    'description': 'Return a list of configured projects with basic metadata.',
    'tags': ['Settings', 'Projects'],
    'responses': {
        '200': {'description': 'A list of projects (HTML page).'}
    }
})
def list_projects():
    """List all saved projects."""
    config_manager: ConfigManager = current_app.config_manager
    projects = config_manager.get_all_settings()
    return render_template('projects.html', projects=projects)


@settings_bp.route('/projects/create', methods=['POST'])
@swag_from({
    'summary': 'Create Project',
    'description': 'Create a new lexicography project and optionally install recommended ranges.',
    'tags': ['Settings', 'Projects'],
    'parameters': [
        {'name': 'project_name', 'in': 'body', 'type': 'string', 'required': True, 'description': 'Project name'},
        {'name': 'source_language_code', 'in': 'body', 'type': 'string', 'required': True, 'description': 'Source language code'},
        {'name': 'source_language_name', 'in': 'body', 'type': 'string', 'required': False, 'description': 'Source language display name'},
        {'name': 'target_language_code', 'in': 'body', 'type': 'string', 'required': False, 'description': 'First target language code'},
        {'name': 'target_language_name', 'in': 'body', 'type': 'string', 'required': False, 'description': 'Target language display name'},
        {'name': 'install_recommended_ranges', 'in': 'body', 'type': 'boolean', 'required': False, 'description': 'Whether to install recommended ranges'}
    ],
    'responses': {
        '201': {'description': 'Project created (JSON)'},
        '400': {'description': 'Bad request - validation failed'}
    }
})
def create_project():
    """Create a new project and optionally install recommended ranges."""
    config_manager: ConfigManager = current_app.config_manager
    dict_service: DictionaryService = current_app.injector.get(DictionaryService)
    try:
        project_name = request.form.get('project_name') or request.json.get('project_name')
        source_lang_code = request.form.get('source_language_code') or request.json.get('source_language_code')
        source_lang_name = request.form.get('source_language_name') or request.json.get('source_language_name')
        target_lang_code = request.form.get('target_language_code') or request.json.get('target_language_code')
        target_lang_name = request.form.get('target_language_name') or request.json.get('target_language_name')
        install_ranges = request.form.get('install_recommended_ranges') or request.json.get('install_recommended_ranges', False)

        if not project_name or not source_lang_code:
            return jsonify({'success': False, 'error': 'Missing project_name or source_language_code'}), 400

        settings_json = {
            'source_language': {'code': source_lang_code, 'name': source_lang_name or source_lang_code},
            'target_languages': [{'code': target_lang_code or '', 'name': target_lang_name or ''}] if target_lang_code else []
        }
        config_manager.create_settings(project_name, basex_db_name='dictionary', settings_json=settings_json)
        if install_ranges:
            dict_service.install_recommended_ranges()

        return jsonify({'success': True}), 201
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@swag_from({
    'summary': 'Delete Project',
    'description': 'Delete a named project by id.',
    'tags': ['Settings', 'Projects'],
    'parameters': [
        {'name': 'project_id', 'in': 'path', 'type': 'integer', 'required': True, 'description': 'ID of the project to delete'}
    ],
    'responses': {
        '200': {'description': 'Project deleted'},
        '404': {'description': 'Project not found'}
    }
})
def delete_project(project_id: int):
    config_manager: ConfigManager = current_app.config_manager
    project = config_manager.get_all_settings()
    target = None
    for p in project:
        if p.id == project_id:
            target = p
            break
    if not target:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    try:
        config_manager.delete_settings(target.project_name)
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def register_blueprints(app):
    """Registers the settings blueprint with the Flask app."""
    app.register_blueprint(settings_bp)

# Example of how to integrate with Flasgger for API documentation
# This would typically be in your main app __init__ or a dedicated Swagger setup file.
# For now, this is just a conceptual placement.
def add_settings_api_spec(swagger):
    """Adds the settings API spec to Swagger.
    This function is illustrative; actual integration might differ.
    """
    # Manually add the path if not using @swag_from directly on endpoint
    # This is usually handled by Flasgger's discovery.
    # If using @swag_from, this might not be strictly necessary unless
    # you have specs in separate YAML files you want to load.
    pass
