
from typing import Any, Dict, Optional, List
from app.models.project_settings import ProjectSettings, db
from flask import current_app
import json

class ConfigManager:
    def __init__(self, app_instance_path: str):
        self.app_instance_path = app_instance_path

    def get_settings(self, project_name: str) -> Optional[ProjectSettings]:
        return ProjectSettings.query.filter_by(project_name=project_name).first()

    def create_settings(self, project_name: str, basex_db_name: str, settings_json: Dict[str, Any] = None) -> ProjectSettings:
        # Extract language settings if present, otherwise use defaults
        if settings_json is None:
            settings_json = {}
            
        source_language = settings_json.get('source_language', {'code': 'en', 'name': 'English'})
        target_languages = settings_json.get('target_languages', [{'code': 'fr', 'name': 'French'}])
        
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
        """Update settings for the current/default project."""
        # Get the first project settings or create default if none exist
        settings = ProjectSettings.query.first()
        if not settings:
            settings = self.create_settings(
                project_name='Default Project',
                basex_db_name='dictionary'
            )
        
        # Update specific fields directly
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
        
