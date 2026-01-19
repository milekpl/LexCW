"""
Hunspell Validator for Spell Checking.

Validates spelling using hunspell library with caching support.
Falls back to a simple word list if hunspell is not available.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from app.validators.base import (
    Validator,
    ValidationResult,
    CacheableValidator,
    BatchValidator
)


class HunspellValidator(CacheableValidator, BatchValidator):
    """
    Hunspell spell-check validator.

    Uses the hunspell library for spell checking with support for
    multiple languages. Falls back to a simple word list if hunspell
    is not available.

    Results are cached to avoid repeated lookups.
    """

    def __init__(
        self,
        cache_service: Optional[Any] = None,
        db_session: Optional[Any] = None,
        dictionaries_path: Optional[str] = None,
        default_lang: str = 'en_US',
        ttl: int = 86400
    ):
        """
        Initialize Hunspell validator.

        Args:
            cache_service: CacheService instance
            db_session: Database session for persistent cache
            dictionaries_path: Path to hunspell dictionaries
            default_lang: Default language code
            ttl: Cache TTL in seconds
        """
        super().__init__(cache_service, db_session, ttl)
        self.logger = logging.getLogger(__name__)

        self.default_lang = default_lang
        self.dictionaries_path = dictionaries_path

        # Lazy-loaded hunspell instances per language
        self._hunspell_instances: Dict[str, Any] = {}
        self._hunspell_available = None  # None = not checked yet

    @property
    def validator_type(self) -> str:
        return 'hunspell'

    @property
    def display_name(self) -> str:
        return 'Hunspell'

    @property
    def hunspell_available(self) -> bool:
        """Check if hunspell library is available."""
        if self._hunspell_available is None:
            try:
                import hunspell
                self._hunspell_available = True
            except ImportError:
                self._hunspell_available = False
                self.logger.warning(
                    "Hunspell library not available, using fallback"
                )
        return self._hunspell_available

    def _get_hunspell(self, lang: str) -> Optional[Any]:
        """
        Get or create hunspell instance for a language.

        Args:
            lang: Language code

        Returns:
            Hunspell instance or None
        """
        if lang in self._hunspell_instances:
            return self._hunspell_instances[lang]

        if not self.hunspell_available:
            return None

        try:
            import hunspell

            # Try to initialize with language code
            hunspell_obj = None

            # Try common dictionary paths
            dict_paths = []
            if self.dictionaries_path:
                dict_paths.append(self.dictionaries_path)

            # Add common system paths
            dict_paths.extend([
                '/usr/share/hunspell',
                '/usr/share/myspell/dicts',
                '/Library/Spelling',
            ])

            # Try to find dictionary
            for dict_path in dict_paths:
                dict_file = os.path.join(dict_path, f'{lang}.dic')
                aff_file = os.path.join(dict_path, f'{lang}.aff')

                if os.path.exists(dict_file) and os.path.exists(aff_file):
                    hunspell_obj = hunspell.Hunspell(lang, dict_path=dict_path)
                    break

            # If not found, try just the language code
            if hunspell_obj is None:
                try:
                    hunspell_obj = hunspell.Hunspell(lang)
                except Exception:
                    pass

            if hunspell_obj:
                self._hunspell_instances[lang] = hunspell_obj
                self.logger.debug(f"Loaded hunspell dictionary: {lang}")

            return hunspell_obj

        except Exception as e:
            self.logger.warning(f"Failed to load hunspell for {lang}: {e}")
            return None

    def validate(
        self,
        text: str,
        lang: Optional[str] = None,
        entry_id: Optional[str] = None,
        date_modified: Optional[str] = None,
        **kwargs
    ) -> ValidationResult:
        """
        Validate spelling in text.

        Args:
            text: Text to validate
            lang: Language code (uses default if not specified)
            entry_id: Entry ID for caching
            date_modified: Entry's date_modified for cache invalidation
            **kwargs: Additional options

        Returns:
            ValidationResult with misspellings and suggestions
        """
        if not text or not text.strip():
            return ValidationResult(
                is_valid=True,
                validator_type=self.validator_type,
                cached=False,
                metadata={'empty': True}
            )

        language = lang or self.default_lang

        # Build cache key
        cache_key = self.get_cache_key(
            entry_id or 'unknown',
            text,
            lang=language
        )

        # Try cache first
        cached = self._get_from_cache(cache_key)
        if cached:
            cached.metadata['cache_key'] = cache_key
            return cached

        # Check DB cache if we have entry info
        if entry_id and date_modified:
            content_hash = self._get_content_hash(text)
            db_cached = self._check_db_cache(entry_id, date_modified, content_hash)
            if db_cached:
                db_cached.metadata['cache_key'] = cache_key
                return db_cached

        # Extract words for validation
        words = self.extract_words(text)

        # Perform validation
        if self.hunspell_available:
            result = self._hunspell_validate(words, language)
        else:
            result = self._fallback_validate(words, language)

        validation_result = ValidationResult(
            is_valid=result['is_valid'],
            validator_type=self.validator_type,
            cached=False,
            suggestions=result['all_suggestions'],
            metadata={
                'cache_key': cache_key,
                'lang': language,
                'word_count': len(words),
                'misspelling_count': len(result['misspellings'])
            }
        )

        # Cache the result
        self._save_to_cache(cache_key, validation_result)
        if entry_id and date_modified:
            self._save_to_db(entry_id, date_modified, content_hash, validation_result)

        return validation_result

    def _hunspell_validate(
        self,
        words: List[str],
        lang: str
    ) -> Dict[str, Any]:
        """
        Validate words using hunspell.

        Args:
            words: List of words to validate
            lang: Language code

        Returns:
            Dict with 'is_valid', 'misspellings', 'suggestions'
        """
        hunspell = self._get_hunspell(lang)

        if not hunspell:
            return self._fallback_validate(words, lang)

        misspellings = []
        all_suggestions: Dict[str, List[str]] = {}

        for word in words:
            if not hunspell.spell(word):
                misspellings.append(word)
                suggestions = hunspell.suggest(word)[:5]  # Top 5 suggestions
                all_suggestions[word] = suggestions

        return {
            'is_valid': len(misspellings) == 0,
            'misspellings': misspellings,
            'suggestions': all_suggestions,
            'all_suggestions': [
                s for suggestions in all_suggestions.values()
                for s in suggestions
            ]
        }

    def _fallback_validate(
        self,
        words: List[str],
        lang: str
    ) -> Dict[str, Any]:
        """
        Fallback validation when hunspell is not available.

        Uses a simple check against a common words list.

        Args:
            words: List of words to validate
            lang: Language code

        Returns:
            Dict with 'is_valid', 'misspellings', 'suggestions'
        """
        # Simple fallback: accept short words, common patterns
        # This is intentionally basic - hunspell should be used when available

        misspellings = []
        all_suggestions: Dict[str, List[str]] = {}

        # Common English words that are often correct
        common_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
            'neither', 'not', 'only', 'own', 'same', 'than', 'too',
            'very', 'just', 'also', 'now', 'here', 'there', 'when',
            'where', 'why', 'how', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 'just', 'this', 'that', 'these', 'those', 'it',
            'its', 'he', 'she', 'they', 'them', 'his', 'her', 'their',
            'what', 'which', 'who', 'whom', 'whose', 'if', 'because',
            'until', 'while', 'although', 'though', 'after', 'before',
            'when', 'whenever', 'where', 'wherever', 'whether', 'which'
        }

        # Common suffixes to suggest (basic correction)
        suggestions_map = {
            'ing': ['in', 'sing', 'ring', 'thing'],
            'ed': ['e', 'bed', 'red', 'led'],
            's': ['is', 'as', 'us'],
            'ly': ['my', 'by', 'try'],
            'tion': ['tion', 'motion', 'action'],
            'able': ['able', 'table', 'cable'],
            'ible': ['ible', 'possible', 'terrible']
        }

        for word in words:
            if len(word) < 3:
                continue  # Skip very short words

            if word.lower() not in common_words:
                # Check for common patterns that might be typos
                if word.lower() not in misspellings:
                    misspellings.append(word)

                    # Generate basic suggestions
                    suggestions = []
                    word_lower = word.lower()

                    # Try removing common suffixes
                    for suffix, base_words in suggestions_map.items():
                        if word_lower.endswith(suffix):
                            stem = word_lower[:-len(suffix)]
                            for base in base_words:
                                if base != stem:
                                    suggestions.append(base + suffix)

                    # Add some generic suggestions
                    if len(suggestions) < 3:
                        suggestions.extend([
                            word,
                            word.lower().capitalize()
                        ])

                    all_suggestions[word] = suggestions[:5]

        return {
            'is_valid': len(misspellings) == 0,
            'misspellings': misspellings,
            'suggestions': all_suggestions,
            'all_suggestions': [
                s for suggestions in all_suggestions.values()
                for s in suggestions[:3]
            ]
        }

    def validate_word(
        self,
        word: str,
        lang: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate a single word.

        Args:
            word: Word to validate
            lang: Language code

        Returns:
            ValidationResult
        """
        language = lang or self.default_lang

        if self.hunspell_available:
            hunspell = self._get_hunspell(language)
            if hunspell:
                is_valid = hunspell.spell(word)
                suggestions = hunspell.suggest(word)[:5] if not is_valid else []
            else:
                is_valid = True
                suggestions = []
        else:
            # Fallback validation
            is_valid = len(word) >= 2
            suggestions = []

        return ValidationResult(
            is_valid=is_valid,
            validator_type=self.validator_type,
            cached=False,
            suggestions=suggestions,
            metadata={'word': word, 'lang': language}
        )

    def get_cache_key(
        self,
        entry_id: str,
        text: str,
        **kwargs
    ) -> str:
        """
        Generate cache key for spell checking.

        Args:
            entry_id: Entry identifier
            text: Text being validated
            **kwargs: Parameters that affect validation

        Returns:
            Cache key string
        """
        content_hash = self._get_content_hash(text)
        lang = kwargs.get('lang', self.default_lang)
        return f"hunspell:{lang}:{entry_id}:{content_hash}"

    def _get_content_hash(self, text: str) -> str:
        """Get truncated SHA256 hash of text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def extract_words(self, text: str) -> List[str]:
        """
        Extract words from text for spell checking.

        Override this for language-specific word extraction.

        Args:
            text: Input text

        Returns:
            List of words to validate
        """
        import re

        # Basic word extraction - includes contractions
        words = re.findall(
            r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b",
            text
        )
        return [w.lower() for w in words]

    def invalidate_for_entry(self, entry_id: str) -> int:
        """
        Invalidate all cached results for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Number of cache entries invalidated
        """
        count = 0

        # Clear Redis cache
        if self.cache_service:
            count += self.cache_service.clear_pattern(f"hunspell:*:{entry_id}:*")

        # Clear DB cache
        try:
            from app.models.validation_cache_models import ValidationResultCache
            count += ValidationResultCache.query.filter(
                ValidationResultCache.entry_id == entry_id,
                ValidationResultCache.validator_type == 'hunspell'
            ).delete()
            if self.db_session:
                self.db_session.commit()
        except Exception as e:
            self.logger.warning(f"DB invalidation error: {e}")

        return count

    def validate_batch(
        self,
        entries: List[Dict[str, Any]],
        lang: Optional[str] = None,
        **kwargs
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple entries.

        Args:
            entries: List of {'id': str, 'text': str}
            lang: Language code
            **kwargs: Additional options

        Returns:
            Dict mapping entry_id -> ValidationResult
        """
        results = {}

        for entry in entries:
            entry_id = entry['id']
            text = entry.get('text', '')

            result = self.validate(
                text=text,
                lang=lang,
                entry_id=entry_id,
                **kwargs
            )
            results[entry_id] = result

        return results

    def check_words(
        self,
        words: List[str],
        lang: Optional[str] = None
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple words at once.

        Args:
            words: List of words to validate
            lang: Language code

        Returns:
            Dict mapping word -> ValidationResult
        """
        language = lang or self.default_lang
        results = {}

        for word in words:
            results[word] = self.validate_word(word, language)

        return results

    def suggest(
        self,
        word: str,
        lang: Optional[str] = None,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Get spelling suggestions for a word.

        Args:
            word: Word to get suggestions for
            lang: Language code
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggested words
        """
        language = lang or self.default_lang

        if self.hunspell_available:
            hunspell = self._get_hunspell(language)
            if hunspell:
                return hunspell.suggest(word)[:max_suggestions]

        return []
