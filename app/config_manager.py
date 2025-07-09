import os
import json
import logging
from typing import Dict, Any
from flask import current_app

class ConfigManager:
    def __init__(self, app_instance_path: str):
        self.instance_path = app_instance_path
        self.settings_file = os.path.join(self.instance_path, 'project_settings.json')
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Loads settings from the JSON file."""
        default_settings = {
            'project_name': 'Default Project',
            'source_language': {'code': 'en', 'name': 'English'},
            'target_language': {'code': 'es', 'name': 'Spanish'}
        }
        if not os.path.exists(self.instance_path):
            os.makedirs(self.instance_path)

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    # Ensure all default keys are present
                    for key, value in default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
            except json.JSONDecodeError:
                # If file is corrupted, load defaults and save them
                self._save_settings(default_settings)
                return default_settings
        else:
            self._save_settings(default_settings)
            return default_settings

    def _save_settings(self, settings: Dict[str, Any]) -> None:
        """Saves settings to the JSON file."""
        if not os.path.exists(self.instance_path):
            os.makedirs(self.instance_path)
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=4)
        self.settings = settings

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Gets a specific setting by key."""
        return self.settings.get(key, default)

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """Updates and saves settings."""
        self.settings.update(new_settings)
        self._save_settings(self.settings)

    def get_all_settings(self) -> Dict[str, Any]:
        """Returns all current settings."""
        return self.settings.copy()

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
        
