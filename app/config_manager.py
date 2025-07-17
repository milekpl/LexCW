
from typing import Any, Dict, Optional
from app.models.project_settings import ProjectSettings, db
from flask import current_app

class ConfigManager:
    def __init__(self, app_instance_path: str):
        self.app_instance_path = app_instance_path

    def get_settings(self, project_name: str) -> Optional[ProjectSettings]:
        return ProjectSettings.query.filter_by(project_name=project_name).first()

    def create_settings(self, project_name: str, basex_db_name: str, settings_json: Dict[str, Any]) -> ProjectSettings:
        settings = ProjectSettings(
            project_name=project_name,
            basex_db_name=basex_db_name,
            settings_json=settings_json
        )
        db.session.add(settings)
        db.session.commit()
        return settings

    def update_settings(self, project_name: str, new_values: Dict[str, Any]) -> Optional[ProjectSettings]:
        settings = self.get_settings(project_name)
        if not settings:
            return None
        # Update the settings_json field
        if settings.settings_json is None:
            settings.settings_json = {}
        settings.settings_json.update(new_values)
        db.session.commit()
        return settings

    def update_current_settings(self, new_values: Dict[str, Any]) -> Optional[ProjectSettings]:
        """Update settings for the current/default project."""
        # Get the first project settings or create default if none exist
        settings = ProjectSettings.query.first()
        if not settings:
            settings = self.create_settings(
                project_name='Default Project',
                basex_db_name='dictionary',
                settings_json={}
            )
        
        # Update the settings_json field
        if settings.settings_json is None:
            settings.settings_json = {}
        settings.settings_json.update(new_values)
        # Mark the field as modified for SQLAlchemy to detect changes
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(settings, 'settings_json')
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
        if settings and settings.settings_json:
            return settings.settings_json.get(key, default)
        return default

    def get_project_name(self) -> str:
        return self.get_setting('project_name', 'Default Project')

    def get_source_language(self) -> Dict[str, str]:
        return self.get_setting('source_language', {'code': 'en', 'name': 'English'})

    def get_target_language(self) -> Dict[str, str]:
        return self.get_setting('target_language', {'code': 'es', 'name': 'Spanish'})

    def set_project_name(self, name: str) -> None:
        self.update_current_settings({'project_name': name})

    def set_source_language(self, code: str, name: str) -> None:
        self.update_current_settings({'source_language': {'code': code, 'name': name}})

    def set_target_language(self, code: str, name: str) -> None:
        self.update_current_settings({'target_language': {'code': code, 'name': name}})

    def get_project_languages(self) -> list:
        return [self.get_setting('source_language'), self.get_setting('target_language')]
        
