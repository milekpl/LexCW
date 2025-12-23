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
@swag_from({
    'summary': 'Manage Project Settings',
    'description': 'View and update project-specific settings such as project name and languages.',
    'tags': ['Settings']
})
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
@swag_from({
    'summary': 'List Projects',
    'description': 'Return a list of configured projects with basic metadata.',
    'tags': ['Settings', 'Projects'],
    'responses': {
        '200': {'description': 'A list of projects (HTML page).'}
    }
})
def list_projects() -> Any:
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
def create_project() -> Any:
    """Create a new project and optionally install recommended ranges."""
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


def register_blueprints(app) -> None:
    app.register_blueprint(settings_bp)

@swag_from({
    'summary': 'Manage Project Settings',
    'description': 'View and update project-specific settings such as project name and languages.',
    'tags': ['Settings']
})
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
@swag_from({
    'summary': 'List Projects',
    'description': 'Return a list of configured projects with basic metadata.',
    'tags': ['Settings', 'Projects'],
    'responses': {
        '200': {'description': 'A list of projects (HTML page).'}
    }
})
def list_projects() -> Any:
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
def create_project() -> Any:
    """Create a new project and optionally install recommended ranges."""
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


def register_blueprints(app) -> None:
    app.register_blueprint(settings_bp)

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
@swag_from({
    'summary': 'List Projects',
    'description': 'Return a list of configured projects with basic metadata.',
    'tags': ['Settings', 'Projects'],
    'responses': {
        '200': {'description': 'A list of projects (HTML page).'}
    }
})
def list_projects() -> Any:
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
def create_project() -> Any:
    """Create a new project and optionally install recommended ranges."""
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
        logger.error(f"Error deleting project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def register_blueprints(app) -> None:
    app.register_blueprint(settings_bp)

    form = SettingsForm()

    if form.validate_on_submit():
        try:
            new_settings = form.to_dict()
            config_manager.update_current_settings(new_settings)
            flash('Settings updated successfully!', 'success')
            logger.info('Project settings updated: %s', new_settings)
            return redirect(url_for('settings.manage_settings'))
        except Exception as e:
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
                ranges = {}
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

@settings_bp.route('/projects/create', methods=['POST'])
def create_project():
    config_manager: ConfigManager = current_app.config_manager
    dict_service: DictionaryService = current_app.injector.get(DictionaryService)
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
        if install_ranges:
            dict_service.install_recommended_ranges()

        return jsonify({'success': True}), 201
    except Exception as e:
        logger.error('Error creating project: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
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
        logger.error('Error deleting project: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


def register_blueprints(app):
    app.register_blueprint(settings_bp)

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

    # Attempt to collect ranges via DictionaryService; be defensive so the
    # settings page does not crash when services are unavailable during debug
    # or startup. If ranges cannot be loaded, assume none and allow the
    # UI to present a sane default/empty state.
    # Resolve a dictionary service instance in a defensive way. Prefer an
    # already-attached `app.dict_service` if present, fall back to the
    # injector, and always avoid referencing an undefined name.
    ranges = {}
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
        # Any failure to load ranges should not prevent the settings page
        # from rendering; log for diagnostics and continue with empty ranges.
        logger.debug('Could not load ranges via DictionaryService: %s', e)

    show_wizard = show_wizard or (not bool(ranges))

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
        dict_svc = getattr(current_app, 'dict_service', None)
        if dict_svc is None and hasattr(current_app, 'injector'):
            try:
                dict_svc = current_app.injector.get(DictionaryService)
            except Exception:
                dict_svc = None
        
        if not dict_svc:
            return jsonify({'success': False, 'error': 'Dictionary service not available'}), 500
        
        # Drop the database content
        dict_svc.drop_database_content()
        
        logger.info('Database content dropped successfully')
        return jsonify({'success': True, 'message': 'Database content dropped successfully'})
    
    except Exception as e:
        logger.error('Error dropping database content: %s', e, exc_info=True)
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
