from __future__ import annotations
from typing import Dict

def get_project_languages() -> Dict[str, str]:
    """
    Return a dictionary of admissible language codes for the current project.
    This should be loaded from project config, database, or a static list.
    Example: {"pl": "Polish", "en": "English", "de": "German"}
    """
    # TODO: Replace with dynamic/project-specific logic
    return {
        "pl": "Polish",
        "en": "English",
        "de": "German",
        "fr": "French"
    }
