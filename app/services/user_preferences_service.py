"""
User preferences service for managing user-specific settings like field visibility.
"""

from typing import Optional, Dict, Any
from app.models.workset_models import db
from app.models.project_settings import User, ProjectSettings


# Default field visibility settings (hardcoded fallback)
DEFAULT_FIELD_VISIBILITY = {
    "sections": {
        "basic-info": True,
        "custom-fields": True,
        "notes": True,
        "pronunciation": True,
        "variants": True,
        "direct-variants": True,
        "relations": True,
        "annotations": True,
        "senses": True
    },
    "fields": {
        "basic-info": {
            "lexical-unit": True,
            "pronunciation": True,
            "variants": True
        },
        "custom-fields": {
            "custom-fields-all": True
        },
        "notes": {
            "notes-all": True
        },
        "pronunciation": {
            "pronunciation-all": True
        },
        "variants": {
            "variants-all": True
        },
        "direct-variants": {
            "direct-variants-all": True
        },
        "relations": {
            "relations-all": True
        },
        "annotations": {
            "annotations-all": True
        },
        "senses": {
            "sense-definition": True,
            "sense-gloss": True,
            "sense-grammatical": True,
            "sense-domain": True,
            "sense-examples": True,
            "sense-illustrations": True,
            "sense-relations": True,
            "sense-variants": True,
            "sense-reversals": False,
            "sense-annotations": False
        }
    }
}


class UserPreferencesService:
    """Service for managing user preferences, particularly field visibility settings."""

    @staticmethod
    def get_field_visibility(user_id: int, project_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get effective field visibility settings for a user.

        If user has saved preferences, return those.
        Otherwise, return project defaults (if project_id provided) or hardcoded defaults.

        Args:
            user_id: User ID
            project_id: Optional project ID to get project-level defaults

        Returns:
            Dictionary with 'sections' and 'fields' visibility settings
        """
        user = User.query.get(user_id)
        if not user:
            return {
                "sections": DEFAULT_FIELD_VISIBILITY["sections"],
                "fields": DEFAULT_FIELD_VISIBILITY["fields"],
                "source": "default"
            }

        # Initialize preferences if not exists
        if user.preferences is None:
            user.preferences = {}
        if "fieldVisibility" not in user.preferences:
            user.preferences["fieldVisibility"] = {}

        # Check for user-specific settings
        user_field_visibility = user.preferences.get("fieldVisibility", {})

        # If user has settings, return them
        if user_field_visibility:
            return {
                "sections": user_field_visibility.get("sections", DEFAULT_FIELD_VISIBILITY["sections"]),
                "fields": user_field_visibility.get("fields", DEFAULT_FIELD_VISIBILITY["fields"]),
                "source": "user"
            }

        # Otherwise, try project defaults
        if project_id:
            project = ProjectSettings.query.get(project_id)
            if project and project.field_visibility_defaults:
                return {
                    "sections": project.field_visibility_defaults.get("sections", DEFAULT_FIELD_VISIBILITY["sections"]),
                    "fields": project.field_visibility_defaults.get("fields", DEFAULT_FIELD_VISIBILITY["fields"]),
                    "source": "project"
                }

        # Fall back to hardcoded defaults
        return {
            "sections": DEFAULT_FIELD_VISIBILITY["sections"],
            "fields": DEFAULT_FIELD_VISIBILITY["fields"],
            "source": "default"
        }

    @staticmethod
    def save_field_visibility(
        user_id: int,
        project_id: Optional[int],
        settings: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Save field visibility settings for a user.

        Args:
            user_id: User ID
            project_id: Optional project ID (stored with settings for context)
            settings: Dictionary with 'sections' and/or 'fields' settings

        Returns:
            Tuple of (success, error_message)
        """
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        # Initialize preferences if not exists
        if user.preferences is None:
            user.preferences = {}

        # Initialize fieldVisibility if not exists
        if "fieldVisibility" not in user.preferences:
            user.preferences["fieldVisibility"] = {}

        # Merge new settings with existing
        current = user.preferences["fieldVisibility"]

        if "sections" in settings:
            current["sections"] = settings["sections"]
        if "fields" in settings:
            current["fields"] = settings["fields"]

        # Store project context for reference
        if project_id:
            current["project_id"] = project_id

        # Add timestamp
        current["updated_at"] = db.func.now()

        user.preferences["fieldVisibility"] = current
        db.session.commit()

        return True, None

    @staticmethod
    def reset_to_project_defaults(
        user_id: int,
        project_id: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Reset user's field visibility settings to project defaults (or hardcoded defaults).

        Args:
            user_id: User ID
            project_id: Optional project ID for project defaults

        Returns:
            Tuple of (success, error_message)
        """
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        # Initialize preferences if not exists
        if user.preferences is None:
            user.preferences = {}

        # Remove fieldVisibility to fall back to defaults
        if "fieldVisibility" in user.preferences:
            del user.preferences["fieldVisibility"]
            db.session.commit()

        return True, None

    @staticmethod
    def get_project_defaults(project_id: int) -> Dict[str, Any]:
        """
        Get field visibility defaults for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with 'sections' and 'fields' defaults, or empty dict if not set
        """
        project = ProjectSettings.query.get(project_id)
        if not project:
            return {}

        return project.field_visibility_defaults or {}

    @staticmethod
    def save_project_defaults(
        project_id: int,
        settings: Dict[str, Any],
        admin_user_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Save field visibility defaults for a project (admin only).

        Args:
            project_id: Project ID
            settings: Dictionary with 'sections' and/or 'fields' defaults
            admin_user_id: ID of admin making the change

        Returns:
            Tuple of (success, error_message)
        """
        project = ProjectSettings.query.get(project_id)
        if not project:
            return False, "Project not found"

        # Initialize if not exists
        if project.field_visibility_defaults is None:
            project.field_visibility_defaults = {}

        # Merge new settings
        current = project.field_visibility_defaults

        if "sections" in settings:
            current["sections"] = settings["sections"]
        if "fields" in settings:
            current["fields"] = settings["fields"]

        project.field_visibility_defaults = current
        db.session.commit()

        return True, None

    @staticmethod
    def clear_user_preference(user_id: int, key: str) -> tuple[bool, Optional[str]]:
        """
        Clear a specific user preference key.

        Args:
            user_id: User ID
            key: Preference key to clear

        Returns:
            Tuple of (success, error_message)
        """
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        if user.preferences and key in user.preferences:
            del user.preferences[key]
            db.session.commit()

        return True, None
