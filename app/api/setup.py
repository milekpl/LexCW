"""Setup API for first-run project configuration."""
from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from typing import Union, Tuple

from app.services.dictionary_service import DictionaryService
from app.config_manager import ConfigManager
from app.utils.exceptions import DatabaseError

setup_bp = Blueprint('setup', __name__, url_prefix='/api/setup')


@setup_bp.route('', methods=['POST'])
def configure_project() -> Union[tuple, dict]:
    """Configure basic project settings on first-run.

    Expects JSON body like:
    {
      "project_name": "My Project",
      "source_language": {"code":"en","name":"English"},
      "target_languages": [{"code":"es","name":"Spanish"}],
      "install_recommended_ranges": true
    }
    """
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
