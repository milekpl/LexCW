"""
Project Language Service.

Provides utility functions to aggregate and manage language codes supported
by a project (combining source language, target languages, admissible languages,
and uploaded active project dictionaries).
"""

from typing import List, Set, Optional, Dict, Any
from app.models.project_settings import ProjectSettings
from app.models.dictionary_models import ProjectDictionary


class ProjectLanguageService:
    """Service for querying project language code definitions."""

    @staticmethod
    def get_all_language_codes(project_id: int) -> Set[str]:
        """
        Get the union of all language codes associated with a project.

        Combines:
        1. Primary source language code
        2. Target language codes
        3. Admissible extra language codes
        4. Language codes from active uploaded ProjectDictionary entries

        Args:
            project_id: The project ID

        Returns:
            Set of string BCP-47 language tags (e.g. {'en', 'pl', 'seh-fonipa'})
        """
        lang_codes: Set[str] = set()

        # Fetch project settings
        project = ProjectSettings.query.get(project_id)
        if project:
            # 1. Source language
            src = project.source_language
            if isinstance(src, dict) and src.get('code'):
                lang_codes.add(src['code'])
            elif isinstance(src, str) and src:
                lang_codes.add(src)

            # 2. Target languages
            targets = project.target_languages or []
            if isinstance(targets, list):
                for tgt in targets:
                    if isinstance(tgt, dict) and tgt.get('code'):
                        lang_codes.add(tgt['code'])
                    elif isinstance(tgt, str) and tgt:
                        lang_codes.add(tgt)

            # 3. Admissible extra languages
            admissible = project.admissible_languages or []
            if isinstance(admissible, list):
                for adm in admissible:
                    if isinstance(adm, str) and adm:
                        lang_codes.add(adm)

        # 4. Active project dictionaries
        active_dicts = ProjectDictionary.query.filter_by(
            project_id=project_id,
            is_active=True
        ).all()
        for dict_obj in active_dicts:
            if dict_obj.lang_code:
                lang_codes.add(dict_obj.lang_code)

        return lang_codes
