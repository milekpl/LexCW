from __future__ import annotations

import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flasgger import swag_from

from app.forms.settings_form import SettingsForm
from app.config_manager import ConfigManager

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
            config_manager.update_settings(new_settings)
            flash('Settings updated successfully!', 'success')
            logger.info(f"Project settings updated: {new_settings}")
            return redirect(url_for('settings.manage_settings'))
        except Exception as e:
            logger.error(f"Error updating settings: {e}", exc_info=True)
            flash(f'Error updating settings: {str(e)}', 'danger')
    elif request.method == 'GET':
        form.populate_from_config(config_manager)

    # For displaying current settings, especially if form validation fails
    current_settings = config_manager.get_all_settings()

    return render_template('settings.html',
                           form=form,
                           title="Project Settings",
                           current_settings=current_settings)

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
