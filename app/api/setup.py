"""Setup API for first-run project configuration."""
from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from typing import Union, Tuple
from flasgger import swag_from

from app.services.dictionary_service import DictionaryService
from app.config_manager import ConfigManager
from app.utils.exceptions import DatabaseError

setup_bp = Blueprint('setup', __name__, url_prefix='/api/setup')


@setup_bp.route('', methods=['POST'])
@swag_from({
    'tags': ['Setup'],
    'summary': 'Configure project settings',
    'description': 'Create or update the default project settings and optionally install recommended ranges.',
    'parameters': [
        {'name': 'project_name', 'in': 'body', 'required': False, 'type': 'string'},
        {'name': 'source_language', 'in': 'body', 'required': False, 'type': 'object'},
        {'name': 'target_languages', 'in': 'body', 'required': False, 'type': 'array'},
        {'name': 'install_recommended_ranges', 'in': 'body', 'required': False, 'type': 'boolean'}
    ],
    'responses': {
        '201': {'description': 'Project configured'},
        '400': {'description': 'Bad request'},
        '500': {'description': 'Server error'}
    }
})
def configure_project() -> Union[tuple, dict]:
    try:
        data = request.get_json() or {}
        project_name = data.get('project_name', 'Default Project')
        source_language = data.get('source_language', {'code': 'en', 'name': 'English'})
        target_languages = data.get('target_languages', [])
        install_ranges = bool(data.get('install_recommended_ranges', False))

        # Update project settings via ConfigManager
        config_manager: ConfigManager = current_app.injector.get(ConfigManager)
        config_manager.update_current_settings({
            'project_name': project_name,
            'source_language': source_language,
            'target_languages': target_languages,
        })

        # Optionally install recommended ranges
        if install_ranges:
            dict_service: DictionaryService = current_app.injector.get(DictionaryService)
            dict_service.install_recommended_ranges()

        # Refresh in-process project settings cache
        try:
            current_app.config['PROJECT_SETTINGS'] = [s.settings_json for s in config_manager.get_all_settings()]
        except Exception:
            current_app.config['PROJECT_SETTINGS'] = []

        return jsonify({'success': True}), 201
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
