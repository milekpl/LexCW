import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.models.project_settings import ProjectSettings, db

class ConfigManager:
    """
    Manager for application configuration settings.
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        # Ensure we have settings in the database
        self._ensure_default_settings()

    def _ensure_default_settings(self):
        """Ensure default settings exist."""
        if not ProjectSettings.query.first():
            default_settings = ProjectSettings(
                project_name="Lexicographic Curation Workbench",
                source_language={"code": "en", "name": "English"},
                target_languages=[{"code": "fr", "name": "French"}],
            )
            db.session.add(default_settings)
            db.session.commit()

    def get_all_settings(self):
        """Get all settings objects."""
        return ProjectSettings.query.all()

    def get_current_settings(self):
        """Get the current active settings."""
        return ProjectSettings.query.first()

    def get_project_name(self):
        """Get the project name."""
        settings = self.get_current_settings()
        return settings.project_name if settings else "Lexicographic Curation Workbench"

    def get_source_language(self):
        """Get the source language information."""
        settings = self.get_current_settings()
        return settings.source_language if settings else {"code": "en", "name": "English"}

    def get_target_languages(self):
        """Get the list of target languages."""
        settings = self.get_current_settings()
        return settings.target_languages if settings else []

    def get_target_language(self):
        """
        Get the first target language (for backward compatibility).
        """
        target_languages = self.get_target_languages()
        return target_languages[0] if target_languages else {"code": "fr", "name": "French"}

    def update_project_settings(
        self, project_name: str, source_language: Dict[str, str], target_languages: List[Dict[str, str]]
    ):
        """Update project settings."""
        settings = self.get_current_settings()
        if not settings:
            settings = ProjectSettings(
                project_name=project_name,
                source_language=source_language,
                target_languages=target_languages,
            )
            db.session.add(settings)
        else:
            settings.project_name = project_name
            settings.source_language = source_language
            settings.target_languages = target_languages
        db.session.commit()

        # Update app config
        if self.app:
            self.app.config["PROJECT_SETTINGS"] = settings.settings_json
