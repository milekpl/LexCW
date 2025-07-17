
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
        for key, value in new_values.items():
            setattr(settings, key, value)
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

    def get_project_name(self) -> str:
        return self.get_setting('project_name', 'Default Project')

    def get_source_language(self) -> Dict[str, str]:
        return self.get_setting('source_language', {'code': 'en', 'name': 'English'})

    def get_target_language(self) -> Dict[str, str]:
        return self.get_setting('target_language', {'code': 'es', 'name': 'Spanish'})

    def set_project_name(self, name: str) -> None:
        self.update_settings({'project_name': name})

    def set_source_language(self, code: str, name: str) -> None:
        self.update_settings({'source_language': {'code': code, 'name': name}})

    def set_target_language(self, code: str, name: str) -> None:
        self.update_settings({'target_language': {'code': code, 'name': name}})

    def get_project_languages(self) -> list:
        return [self.get_setting('source_language'), self.get_setting('target_language')]
        
