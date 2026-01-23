"""
Dictionary Loader Service.

Loads and manages hunspell dictionary instances with support for
project dictionaries and user custom words.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Set

from app.models.dictionary_models import ProjectDictionary, UserDictionary


logger = logging.getLogger(__name__)


class DictionaryLoader:
    """
    Service for loading hunspell dictionary instances.

    Handles:
    - Loading project dictionaries
    - Loading user dictionaries
    - Merging dictionaries (project + user layers)
    - Caching loaded instances
    - System dictionary discovery
    """

    # Common system dictionary paths
    SYSTEM_DICT_PATHS = [
        '/usr/share/hunspell',
        '/usr/share/myspell/dicts',
        '/Library/Spelling',
        '/usr/local/share/hunspell',
        '/snap/current/lib/hunspell',
    ]

    def __init__(self):
        """Initialize dictionary loader."""
        self._hunspell_available = None
        self._hunspell = None
        self._cache: Dict[str, Any] = {}  # lang_code -> hunspell instance
        self._merged_cache: Dict[str, Any] = {}  # project_id:user_id:lang_code -> merged hunspell
        self._system_dicts: Dict[str, Dict[str, str]] = {}  # lang_code -> {dic_path, aff_path}

        # Check hunspell availability once
        self._check_hunspell()

    def _check_hunspell(self) -> None:
        """Check if hunspell library is available."""
        try:
            import hunspell
            self._hunspell_available = True
            self._hunspell = hunspell
            logger.info("Hunspell library available")
        except ImportError:
            self._hunspell_available = False
            logger.warning("Hunspell library not available")

    @property
    def is_available(self) -> bool:
        """Check if hunspell is available."""
        return self._hunspell_available or self._check_hunspell() or False

    def discover_system_dictionaries(self) -> Dict[str, Dict[str, str]]:
        """Discover hunspell dictionaries installed on the system."""
        if self._system_dicts:
            return self._system_dicts

        for dict_path in self.SYSTEM_DICT_PATHS:
            if not os.path.exists(dict_path):
                continue

            for filename in os.listdir(dict_path):
                if not filename.endswith('.dic'):
                    continue

                lang_code = filename.replace('.dic', '')
                aff_path = filename.replace('.dic', '.aff')
                full_aff_path = os.path.join(dict_path, aff_path)

                if os.path.exists(full_aff_path):
                    self._system_dicts[lang_code] = {
                        'dic_path': os.path.join(dict_path, filename),
                        'aff_path': full_aff_path,
                        'source': 'system'
                    }

        logger.info(f"Discovered {len(self._system_dicts)} system dictionaries")
        return self._system_dicts

    def load_project_dictionary(
        self,
        project_id: int,
        lang_code: str
    ) -> Optional[Any]:
        """
        Load a project dictionary for a language code.

        Args:
            project_id: Project ID
            lang_code: Language code (e.g., 'en_US', 'seh-fonipa')

        Returns:
            Hunspell instance or None
        """
        cache_key = f"project:{project_id}:{lang_code}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.is_available:
            return None

        # Get project dictionary for this language
        dictionary = ProjectDictionary.get_for_language(project_id, lang_code)

        if not dictionary or not dictionary.files_exist():
            return None

        try:
            hunspell_obj = self._hunspell.HunSpell(
                dictionary.dic_path,
                dictionary.aff_path
            )
            self._cache[cache_key] = hunspell_obj
            return hunspell_obj

        except Exception as e:
            logger.error(f"Failed to load project dictionary: {e}")
            return None

    def load_user_dictionary(
        self,
        user_id: int,
        lang_code: str
    ) -> List[Any]:
        """
        Load all user dictionaries for a language code.

        Args:
            user_id: User ID
            lang_code: Language code

        Returns:
            List of hunspell instances (may include custom word list wrapper)
        """
        dictionaries = UserDictionary.get_by_lang_code(user_id, lang_code)
        instances = []

        for user_dict in dictionaries:
            # File-based dictionaries
            if user_dict.dic_file:
                storage_path = user_dict.storage_path
                dic_path = os.path.join(storage_path, user_dict.dic_file)
                aff_path = os.path.join(storage_path, user_dict.aff_file) if user_dict.aff_file else None
                if os.path.exists(dic_path):
                    try:
                        if aff_path and os.path.exists(aff_path):
                            instance = self._hunspell.HunSpell(dic_path, aff_path)
                        else:
                            instance = self._hunspell.HunSpell(dic_path, dic_path.replace('.dic', '.aff'))
                        instances.append(instance)
                    except Exception as e:
                        logger.warning(f"Failed to load user dict {user_dict.id}: {e}")

            # Custom words (create simple wrapper)
            elif user_dict.custom_words:
                instance = CustomWordsWrapper(user_dict.get_all_words())
                instances.append(instance)

        return instances

    def load_combined(
        self,
        project_id: int,
        lang_code: str,
        user_id: Optional[int] = None
    ) -> Optional[Any]:
        """
        Load a combined hunspell instance with project + user dictionaries.

        The project dictionary is the primary, and user dictionaries add
        additional words.

        Args:
            project_id: Project ID
            lang_code: Language code
            user_id: Optional user ID for personalized dictionaries

        Returns:
            Combined hunspell instance or None
        """
        cache_key = f"combined:{project_id}:{user_id}:{lang_code}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load project dictionary (primary)
        project_hunspell = self.load_project_dictionary(project_id, lang_code)

        if not project_hunspell and not user_id:
            return None

        # Load user dictionaries
        user_instances = []
        if user_id:
            user_instances = self.load_user_dictionary(user_id, lang_code)

        # If only project dict, return it directly
        if project_hunspell and not user_instances:
            self._cache[cache_key] = project_hunspell
            return project_hunspell

        # If only user dicts, return first one
        if not project_hunspell and user_instances:
            combined = user_instances[0]
            self._cache[cache_key] = combined
            return combined

        # Merge project with user dictionaries
        # Strategy: create a wrapper that checks project first, then user
        combined = MergedHunspellWrapper(
            primary=project_hunspell,
            secondary=user_instances
        )

        self._cache[cache_key] = combined
        return combined

    def load_system_dictionary(self, lang_code: str) -> Optional[Any]:
        """
        Load a system-installed dictionary.

        Args:
            lang_code: Language code

        Returns:
            Hunspell instance or None
        """
        cache_key = f"system:{lang_code}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check system dictionaries
        system_dicts = self.discover_system_dictionaries()
        system_dict = system_dicts.get(lang_code)

        if not system_dict:
            # Try common variations
            for variant in [lang_code.replace('_', '-'), lang_code.split('_')[0]]:
                if variant in system_dicts:
                    system_dict = system_dicts[variant]
                    break

        if system_dict:
            try:
                hunspell_obj = self._hunspell.HunSpell(
                    system_dict['dic_path'],
                    system_dict['aff_path']
                )
                self._cache[cache_key] = hunspell_obj
                return hunspell_obj
            except Exception as e:
                logger.warning(f"Failed to load system dictionary {lang_code}: {e}")

        return None

    def load_fallback(
        self,
        project_id: int,
        lang_code: str,
        user_id: Optional[int] = None
    ) -> Optional[Any]:
        """
        Load dictionary with fallback chain:
        1. Project dictionary
        2. User dictionary
        3. System dictionary
        4. Project default dictionary

        Args:
            project_id: Project ID
            lang_code: Language code
            user_id: Optional user ID

        Returns:
            First available hunspell instance or None
        """
        # Try combined (project + user)
        combined = self.load_combined(project_id, lang_code, user_id)
        if combined:
            return combined

        # Try system dictionary
        system = self.load_system_dictionary(lang_code)
        if system:
            return system

        # Try base language (e.g., en_US -> en)
        base_lang = lang_code.split('_')[0].split('-')[0]
        if base_lang != lang_code:
            return self.load_fallback(project_id, base_lang, user_id)

        # Try project default
        default_dict = ProjectDictionary.get_default(project_id)
        if default_dict:
            return self.load_project_dictionary(project_id, default_dict.lang_code)

        return None

    def invalidate_project_cache(self, project_id: int) -> int:
        """
        Invalidate cached dictionaries for a project.

        Args:
            project_id: Project ID

        Returns:
            Number of cache entries cleared
        """
        keys_to_remove = [
            key for key in self._cache.keys()
            if f":{project_id}:" in key
        ]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    def invalidate_user_cache(self, user_id: int) -> int:
        """
        Invalidate cached dictionaries for a user.

        Args:
            user_id: User ID

        Returns:
            Number of cache entries cleared
        """
        keys_to_remove = [
            key for key in self._cache.keys()
            if f":{user_id}:" in key
        ]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    def clear_cache(self) -> int:
        """Clear all cached dictionaries."""
        count = len(self._cache)
        self._cache.clear()
        return count


class CustomWordsWrapper:
    """
    Simple wrapper for custom word lists.

    Provides hunspell-like interface for a list of custom words.
    Used when users add words without a full dictionary file.
    """

    def __init__(self, words: List[str]):
        """
        Initialize wrapper with words.

        Args:
            words: List of valid words
        """
        self._words = set(w.lower() for w in words)

    def spell(self, word: str) -> bool:
        """Check if word is in the custom list."""
        return word.lower() in self._words

    def suggest(self, word: str) -> List[str]:
        """Return suggestions (placeholder - could implement simple matching)."""
        # Simple suggestion: words that share prefix or are close
        suggestions = []
        word_lower = word.lower()

        for w in sorted(self._words):
            if w.startswith(word_lower[:3]) and w != word_lower:
                suggestions.append(w)
                if len(suggestions) >= 5:
                    break

        return suggestions


class MergedHunspellWrapper:
    """
    Wrapper that merges multiple hunspell instances.

    Primary dictionary is checked first, then secondary dictionaries.
    """

    def __init__(
        self,
        primary: Any,
        secondary: List[Any]
    ):
        """
        Initialize wrapper.

        Args:
            primary: Primary hunspell instance
            secondary: List of secondary instances to check if primary fails
        """
        self._primary = primary
        self._secondary = secondary

    def spell(self, word: str) -> bool:
        """Check primary first, then secondary."""
        if self._primary.spell(word):
            return True

        for hunspell in self._secondary:
            if hunspell.spell(word):
                return True

        return False

    def suggest(self, word: str) -> List[str]:
        """Get suggestions from all dictionaries."""
        suggestions = []

        # Get suggestions from primary
        if hasattr(self._primary, 'suggest'):
            suggestions.extend(self._primary.suggest(word))

        # Get suggestions from secondary
        for hunspell in self._secondary:
            if hasattr(hunspell, 'suggest'):
                suggestions.extend(hunspell.suggest(word))

        # Deduplicate and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)

        return unique_suggestions[:10]


# Singleton instance
dictionary_loader = DictionaryLoader()


def get_dictionary_loader() -> DictionaryLoader:
    """Get the global dictionary loader instance."""
    return dictionary_loader
