from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flasgger import swag_from

from app.forms.settings_form import SettingsForm
from app.config_manager import ConfigManager
from app.services.dictionary_service import DictionaryService

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')
logger = logging.getLogger(__name__)


@settings_bp.route('/', methods=['GET', 'POST'])
@swag_from({'summary': 'Manage Project Settings', 'tags': ['Settings']})
def manage_settings() -> Any:
    """Displays and handles updates for project settings.

    Defensive: missing auxiliary services (DictionaryService) must not
    cause the page to raise an exception. If ranges cannot be loaded,
    the page will show the project wizard by default.
    """
    config_manager: ConfigManager = current_app.config_manager
    form = SettingsForm()

    if form.validate_on_submit():
        try:
            new_settings = form.to_dict()
            config_manager.update_current_settings(new_settings)
            flash('Settings updated successfully!', 'success')
            logger.info('Project settings updated: %s', new_settings)
            return redirect(url_for('settings.manage_settings'))
        except Exception as e:
            logger.error('Error updating settings: %s', e, exc_info=True)
            flash(f'Error updating settings: {str(e)}', 'danger')
    elif request.method == 'GET':
        form.populate_from_config(config_manager)

    project_query = request.args.get('project')
    show_wizard = request.args.get('wizard', 'false').lower() == 'true'
    if project_query:
        project_settings = config_manager.get_settings(project_query)
        if project_settings:
            current_settings = project_settings.settings_json
        else:
            current_settings = {
                'project_name': config_manager.get_project_name(),
                'source_language': config_manager.get_source_language(),
                'target_languages': config_manager.get_target_languages(),
                'backup_settings': getattr(config_manager, 'get_backup_settings', lambda: {})(),
                'basex_db_name': config_manager.get_setting('basex_db_name', 'dictionary')
            }
    else:
        current_settings = {
            'project_name': config_manager.get_project_name(),
            'source_language': config_manager.get_source_language(),
            'target_languages': config_manager.get_target_languages(),
            'backup_settings': getattr(config_manager, 'get_backup_settings', lambda: {})(),
            'basex_db_name': config_manager.get_setting('basex_db_name', 'dictionary')
        }

    # Resolve ranges defensively so missing services do not crash the page
    ranges: Dict[str, Any] = {}
    try:
        dict_svc = getattr(current_app, 'dict_service', None)
        if dict_svc is None and hasattr(current_app, 'injector'):
            try:
                dict_svc = current_app.injector.get(DictionaryService)
            except Exception:
                dict_svc = None
        if dict_svc:
            ranges = dict_svc.get_lift_ranges() or {}
    except Exception as e:
        logger.debug('Could not load ranges via DictionaryService: %s', e)

    show_wizard = show_wizard or (not bool(ranges))

    return render_template('settings.html',
                           form=form,
                           title='Project Settings',
                           current_settings=current_settings,
                           show_wizard=show_wizard,
                           project_query=project_query)


@settings_bp.route('/projects', methods=['GET'])
@swag_from({'summary': 'List projects', 'tags': ['Settings']})
def list_projects() -> Any:
    config_manager: ConfigManager = current_app.config_manager
    projects = config_manager.get_all_settings()
    return render_template('projects.html', projects=projects)


@settings_bp.route('/projects/create', methods=['POST'])
@swag_from({'summary': 'Create project', 'tags': ['Settings']})
def create_project() -> Any:
    config_manager: ConfigManager = current_app.config_manager
    try:
        dict_service: DictionaryService = current_app.injector.get(DictionaryService)
    except Exception:
        dict_service = None

    try:
        data = request.get_json() or request.form
        project_name = data.get('project_name')
        source_lang_code = data.get('source_language_code')
        source_lang_name = data.get('source_language_name')
        target_lang_code = data.get('target_language_code')
        target_lang_name = data.get('target_language_name')
        install_ranges = data.get('install_recommended_ranges', False)

        if not project_name or not source_lang_code:
            return jsonify({'success': False, 'error': 'Missing project_name or source_language_code'}), 400

        settings_json = {
            'source_language': {'code': source_lang_code, 'name': source_lang_name or source_lang_code},
            'target_languages': [{'code': target_lang_code or '', 'name': target_lang_name or ''}] if target_lang_code else []
        }
        config_manager.create_settings(project_name, basex_db_name='dictionary', settings_json=settings_json)
        if install_ranges and dict_service:
            try:
                dict_service.install_recommended_ranges()
            except Exception:
                logger.exception('Failed to install recommended ranges')

        return jsonify({'success': True}), 201
    except Exception as e:
        logger.error('Error creating project: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@swag_from({'summary': 'Delete project', 'tags': ['Settings']})
def delete_project(project_id: int) -> Any:
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
        logger.error('Error deleting project: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/drop-database', methods=['POST'])
@swag_from({
    'summary': 'Drop Database Content',
    'description': 'Drop all content from the dictionary database. This action cannot be undone.',
    'tags': ['Settings', 'Database'],
    'responses': {
        '200': {'description': 'Database content dropped successfully.'},
        '500': {'description': 'Error dropping database content.'}
    }
})
def drop_database():
    """Drop all content from the dictionary database."""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'drop')
        
        dict_svc = getattr(current_app, 'dict_service', None)
        if dict_svc is None and hasattr(current_app, 'injector'):
            try:
                dict_svc = current_app.injector.get(DictionaryService)
            except Exception:
                dict_svc = None
        
        if not dict_svc:
            return jsonify({'success': False, 'error': 'Dictionary service not available'}), 500
        
        if action == 'drop_ranges':
            # Drop database and install recommended ranges
            dict_svc.drop_database_content()
            # Install ranges - this would need to be implemented
            # For now, just drop
            logger.info('Database dropped and ranges installation requested')
        else:
            # Just drop the database content
            dict_svc.drop_database_content()
        
        logger.info('Database operation completed successfully: %s', action)
        return jsonify({'success': True, 'message': f'Database {action} completed successfully'})
    
    except Exception as e:
        logger.error('Error in database operation: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/import-lift-replace', methods=['POST'])
@swag_from({
    'summary': 'Import LIFT file (replace mode)',
    'description': 'Replace the entire database with content from a LIFT file.',
    'tags': ['Settings', 'Import'],
    'responses': {
        '200': {'description': 'LIFT file imported successfully.'},
        '400': {'description': 'Invalid file or request.'},
        '500': {'description': 'Error importing LIFT file.'}
    }
})
def import_lift_replace():
    """Import LIFT file in replace mode."""
    # Validate upload
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.lift'):
        return jsonify({'success': False, 'error': 'Invalid LIFT file'}), 400

    # Save the uploaded file temporarily
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False, suffix='.lift') as temp_file:
        file.save(temp_file.name)
        temp_path = temp_file.name

    # Attempt import and ensure cleanup of temporary files
    ranges_temp_path = None
    try:
        dict_svc = getattr(current_app, 'dict_service', None)
        if dict_svc is None and hasattr(current_app, 'injector'):
            try:
                dict_svc = current_app.injector.get(DictionaryService)
            except Exception:
                dict_svc = None

        if not dict_svc:
            return jsonify({'success': False, 'error': 'Dictionary service not available'}), 500

        # If a ranges file was uploaded, save it and pass it to the import
        if 'ranges' in request.files and request.files['ranges'].filename:
            ranges_file = request.files['ranges']
            with tempfile.NamedTemporaryFile(delete=False, suffix='.lift-ranges') as ranges_temp:
                ranges_file.save(ranges_temp.name)
                ranges_temp_path = ranges_temp.name

        # Import in replace mode; pass ranges file path if provided
        count = dict_svc.import_lift(temp_path, mode='replace', ranges_path=ranges_temp_path)

        logger.info('LIFT file imported successfully: %d entries', count)
        return jsonify({'success': True, 'count': count, 'message': f'Imported {count} entries successfully'})

    except Exception as e:
        logger.error('Error importing LIFT file: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        # Clean up temp files
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        if ranges_temp_path and os.path.exists(ranges_temp_path):
            try:
                os.unlink(ranges_temp_path)
            except Exception:
                pass


def register_blueprints(app) -> None:
    app.register_blueprint(settings_bp)
