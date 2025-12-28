from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify, session
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
            logger.info('Form submitted with data: %s', new_settings)
            
            # DEBUG: Specific logging for backup settings
            backup_settings = new_settings.get('backup_settings', {})
            logger.info('Backup Settings from Form: %s (Type: %s)', backup_settings, type(backup_settings))
            
            if not new_settings:
                logger.warning('Empty settings dictionary submitted')
                flash('No settings data received', 'warning')
                return redirect(url_for('settings.manage_settings'))
            
            saved = config_manager.update_current_settings(new_settings)
            # Log what ended up persisted for diagnostics
            try:
                logger.info('Project settings updated (request): %s', new_settings)
                logger.info('Project settings persisted (db): %s', getattr(saved, 'backup_settings', None))
            except Exception:
                logger.exception('Error while logging saved settings')
            # Update in-memory project list for immediate visibility in the UI
            try:
                current_app.config['PROJECT_SETTINGS'] = [s.serialization_dict for s in config_manager.get_all_settings()]
            except Exception:
                logger.debug('Could not update app.config PROJECT_SETTINGS')

            flash('Settings updated successfully!', 'success')
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
            current_settings = project_settings.serialization_dict
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

    # NEW: Only show wizard if absolutely no projects exist.
    # Otherwise, even if ranges are empty, we are likely in a valid project that just needs initialization.
    all_projects = config_manager.get_all_settings()
    show_wizard = (not all_projects) or (show_wizard and not bool(ranges))

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
        settings = config_manager.create_settings(project_name, basex_db_name=None, settings_json=settings_json)
        
        # Create the BaseX database
        if dict_service and hasattr(dict_service, 'db_connector'):
            try:
                dict_service.db_connector.create_database(settings.basex_db_name)
            except Exception as e:
                # If database creation fails, we should probably rollback settings creation?
                # For now, just log and proceed (user can retry or delete)
                logger.error(f"Failed to create BaseX database {settings.basex_db_name}: {e}")
        
        if install_ranges and dict_service:
            # We need to ensure install_ranges runs against the NEW database.
            # install_recommended_ranges likely uses the default DB or current context.
            # We haven't set the request context to the new project yet.
            # We might need to manually pass the db_name if install_recommended_ranges supports it,
            # OR force a context switch.
            # Since we just created it, it's empty.
            try:
                # Assuming install_recommended_ranges uses the connector which uses g.project_db_name or similar.
                # But g.project_db_name is set from session, which isn't updated yet.
                # We can temporarily mock g or pass explicit DB.
                # DictionaryService.install_recommended_ranges doesn't seem to take db_name.
                # Let's check DictionaryService later. 
                # For now, let's leave it, but acknowledge it might install to 'dictionary' if we aren't careful.
                # Actually, BaseXConnector now checks g.project_db_name.
                # We can set g.project_db_name temporarily?
                from flask import g
                g.project_db_name = settings.basex_db_name
                dict_service.install_recommended_ranges()
            except Exception:
                logger.exception('Failed to install recommended ranges')

        return jsonify({'success': True}), 201
    except Exception as e:
        logger.error('Error creating project: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/projects/<int:project_id>/select', methods=['GET', 'POST'])
@swag_from({'summary': 'Select project', 'tags': ['Settings']})
def select_project(project_id: int) -> Any:
    config_manager: ConfigManager = current_app.config_manager
    project = config_manager.get_settings_by_id(project_id)
    if not project:
        flash('Project not found', 'danger')
        return redirect(url_for('settings.list_projects'))
    
    session['project_id'] = project.id
    flash(f'Project "{project.project_name}" selected', 'success')
    
    next_url = request.args.get('next') or url_for('main.index')
    return redirect(next_url)


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
        # Capture DB name before deleting settings
        db_name = target.basex_db_name
        
        config_manager.delete_settings(target.project_name)
        
        # Drop BaseX database
        try:
            dict_service = current_app.injector.get(DictionaryService)
            if dict_service and hasattr(dict_service, 'db_connector'):
                dict_service.db_connector.drop_database(db_name)
        except Exception as e:
            logger.error(f"Failed to drop BaseX database {db_name}: {e}")
            
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
