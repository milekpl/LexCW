
from typing import Any, Dict, Optional, List
from app.models.project_settings import ProjectSettings, db
from flask import current_app
import json
import uuid
import logging
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, app_instance_path: str):
        self.app_instance_path = app_instance_path

    def get_settings(self, project_name: str) -> Optional[ProjectSettings]:
        return ProjectSettings.query.filter_by(project_name=project_name).first()

    def get_settings_by_id(self, project_id: int) -> Optional[ProjectSettings]:
        return ProjectSettings.query.get(project_id)

    def create_settings(self, project_name: str, basex_db_name: str = None, settings_json: Dict[str, Any] = None) -> ProjectSettings:
        # Extract language settings if present, otherwise use defaults
        if settings_json is None:
            settings_json = {}
            
        source_language = settings_json.get('source_language', {'code': 'en', 'name': 'English'})
        target_languages = settings_json.get('target_languages', [{'code': 'fr', 'name': 'French'}])
        
        # Generate a unique database name if not provided
        if not basex_db_name:
            # Check if we are in testing mode
            is_testing = False
            try:
                from flask import current_app
                is_testing = current_app.config.get('TESTING') or current_app.config.get('FLASK_CONFIG') == 'testing'
            except (ImportError, RuntimeError):
                import os
                is_testing = os.environ.get('FLASK_CONFIG') == 'testing' or os.environ.get('TESTING') == 'true'
            
            prefix = "test_project_" if is_testing else "project_"
            basex_db_name = f"{prefix}{uuid.uuid4().hex}"

        settings = ProjectSettings(
            project_name=project_name,
            basex_db_name=basex_db_name,
            source_language=source_language,
            target_languages=target_languages
        )
        db.session.add(settings)
        db.session.commit()
        return settings

    def update_settings(self, project_name: str, new_values: Dict[str, Any]) -> Optional[ProjectSettings]:
        settings = self.get_settings(project_name)
        if not settings:
            return None
            
        # Handle specific fields that are now direct columns
        if 'source_language' in new_values:
            settings.source_language = new_values.pop('source_language')
            
        if 'target_languages' in new_values:
            settings.target_languages = new_values.pop('target_languages')
            
        if 'project_name' in new_values:
            settings.project_name = new_values.pop('project_name')
            
        if 'basex_db_name' in new_values:
            settings.basex_db_name = new_values.pop('basex_db_name')
            
        db.session.commit()
        return settings

    def update_current_settings(self, new_values: Dict[str, Any]) -> Optional[ProjectSettings]:
        """Update settings for the current/default project.

        Adds detailed logging so callers can trace what data is applied and
        whether it persisted correctly to the database.
        """
        # Avoid mutating caller's dictionary
        new_values = dict(new_values or {})
        logger.debug('update_current_settings called with: %s', new_values)

        # Get the first project settings or create default if none exist
        settings = ProjectSettings.query.first()
        if not settings:
            settings = self.create_settings(
                project_name='Default Project',
                basex_db_name='dictionary'
            )

        # Log previous state for diagnostics
        prev_backup = getattr(settings, 'backup_settings', None)
        logger.debug('Previous backup_settings: %s', prev_backup)

        # Update specific fields directly
        if 'source_language' in new_values:
            settings.source_language = new_values.pop('source_language')
            logger.debug('Updated source_language to: %s', settings.source_language)

        if 'target_languages' in new_values:
            settings.target_languages = new_values.pop('target_languages')
            logger.debug('Updated target_languages to: %s', settings.target_languages)

        if 'project_name' in new_values:
            settings.project_name = new_values.pop('project_name')
            logger.debug('Updated project_name to: %s', settings.project_name)

        if 'basex_db_name' in new_values:
            settings.basex_db_name = new_values.pop('basex_db_name')
            logger.debug('Updated basex_db_name to: %s', settings.basex_db_name)

        if 'backup_settings' in new_values:
            new_backup = new_values.pop('backup_settings')
            settings.backup_settings = new_backup
            # Ensure SQLAlchemy detects in-place JSON changes
            try:
                flag_modified(settings, 'backup_settings')
            except Exception:
                # If flag_modified isn't applicable, it's fine - assignment usually suffices
                logger.debug('flag_modified not applicable for backup_settings')
            logger.debug('Updated backup_settings to: %s', settings.backup_settings)

        # Attempt commit with error handling and logging
        try:
            db.session.commit()
            # Refresh from DB to ensure persisted state is accurate
            try:
                db.session.refresh(settings)
            except Exception:
                # Some SQLAlchemy setups may not have refresh; ignore if not available
                pass
            logger.info('Settings saved successfully: id=%s backup_settings=%s', getattr(settings, 'id', None), getattr(settings, 'backup_settings', None))
        except Exception as e:
            logger.error('Failed to commit settings to database: %s', e, exc_info=True)
            db.session.rollback()
            # Re-raise so callers can react to the failure if needed
            raise

        return settings

    def delete_settings(self, project_name: str) -> bool:
        settings = self.get_settings(project_name)
        if not settings:
            return False
        db.session.delete(settings)
        db.session.commit()
        return True

    def get_all_settings(self) -> list[ProjectSettings]:
        """Returns all project settings from database."""
        return ProjectSettings.query.all()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value from the current project settings."""
        # For now, get the first (default) project settings
        # In a multi-project setup, this would need to be project-specific
        settings = ProjectSettings.query.first()
        if not settings:
            return default
            
        # Handle direct columns first
        if key == 'project_name':
            return settings.project_name
        elif key == 'basex_db_name':
            return settings.basex_db_name
        elif key == 'source_language':
            return settings.source_language
        elif key == 'target_languages':
            return settings.target_languages
            
        # Other settings are not supported in the new model
        return default

    def get_project_name(self) -> str:
        project_name = self.get_setting('project_name')
        return project_name if project_name else 'Default Project'

    def get_source_language(self) -> Dict[str, str]:
        source_lang = self.get_setting('source_language')
        return source_lang if source_lang else {'code': 'en', 'name': 'English'}

    def get_target_languages(self) -> List[Dict[str, str]]:
        target_langs = self.get_setting('target_languages')
        return target_langs if target_langs else [{'code': 'es', 'name': 'Spanish'}]

    def get_target_language(self) -> Dict[str, str]:
        # For backward compatibility - returns the first target language
        target_langs = self.get_target_languages()
        return target_langs[0] if target_langs else {'code': 'es', 'name': 'Spanish'}

    def set_project_name(self, name: str) -> None:
        self.update_current_settings({'project_name': name})

    def set_source_language(self, code: str, name: str) -> None:
        self.update_current_settings({'source_language': {'code': code, 'name': name}})

    def set_target_languages(self, target_languages: List[Dict[str, str]]) -> None:
        self.update_current_settings({'target_languages': target_languages})
        
    def set_target_language(self, code: str, name: str) -> None:
        # For backward compatibility - updates the first target language or creates a new list
        self.set_target_languages([{'code': code, 'name': name}])

    def get_project_languages(self) -> List[Dict[str, str]]:
        source_lang = self.get_source_language()
        target_langs = self.get_target_languages()
        return [source_lang] + target_langs

    def get_backup_settings(self) -> Dict[str, Any]:
        """Get backup settings from the current project settings."""
        settings = ProjectSettings.query.first()
        if not settings:
            return {
                'directory': 'app/static/backup',
                'schedule': 'daily',
                'retention': 10,
                'compression': True
            }
        
        backup_settings = settings.backup_settings or {}
        return {
            'directory': backup_settings.get('directory', 'app/static/backup'),
            'schedule': backup_settings.get('schedule', 'daily'),
            'retention': backup_settings.get('retention', 10),
            'compression': backup_settings.get('compression', True),
            'include_media': backup_settings.get('include_media', False)
        }
        
