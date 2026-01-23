"""
Layered Hunspell Validator.

Validates text using layered dictionaries (project + user) with
automatic field-to-dictionary detection.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

from app.models.dictionary_models import ProjectDictionary
from app.models.project_settings import ProjectSettings
from app.services.cache_service import cache_service, CacheService
from app.services.dictionary_loader import get_dictionary_loader, DictionaryLoader
from app.services.field_language_detector import get_language_detector, FieldLanguageDetector
from app.validators.base import ValidationResult


logger = logging.getLogger(__name__)


class LayeredHunspellValidator:
    """
    Hunspell validator with layered dictionary support.

    Features:
    - Automatic field-to-dictionary detection
    - Layered dictionaries (project + user)
    - Caching of validation results
    - IPA field detection (seh-fonipa)
    """

    def __init__(
        self,
        project_id: int,
        user_id: Optional[int] = None,
        cache_service: Optional[CacheService] = None,
        dictionary_loader: Optional[DictionaryLoader] = None,
        language_detector: Optional[FieldLanguageDetector] = None
    ):
        """
        Initialize validator.

        Args:
            project_id: Project ID for project dictionary lookup
            user_id: Optional user ID for user dictionaries
            cache_service: CacheService instance
            dictionary_loader: DictionaryLoader instance
            language_detector: FieldLanguageDetector instance
        """
        self.project_id = project_id
        self.user_id = user_id

        self.cache_service = cache_service or cache_service
        self.dictionary_loader = dictionary_loader or get_dictionary_loader()
        self.language_detector = language_detector or get_language_detector()

        # Cache for hunspell instances per language
        self._hunspell_cache: Dict[str, Any] = {}

        # Default language for this project
        self._default_lang_code: Optional[str] = None

    def validate_text(
        self,
        text: str,
        field_path: str = '',
        project_settings: Optional[ProjectSettings] = None,
        entry_data: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate text with automatic dictionary selection.

        Args:
            text: Text to validate
            field_path: Path to the field (for dictionary selection)
            project_settings: Project settings (optional)
            entry_data: Full entry data (alternative to field_path)

        Returns:
            ValidationResult with validation outcome
        """
        if not text or not text.strip():
            return ValidationResult(
                is_valid=True,
                validator_type='hunspell',
                metadata={'empty': True}
            )

        # Detect language code for this field
        if entry_data and project_settings:
            lang_code = self.language_detector.detect(
                field_path, text, project_settings
            )
        elif project_settings:
            lang_code = self._get_lang_code_for_field(field_path, project_settings)
        else:
            lang_code = 'en'  # Default

        # Check cache first
        cache_key = self._make_cache_key(text, lang_code)
        cached = self._get_from_cache(cache_key)
        if cached:
            cached.metadata['cached'] = True
            return cached

        # Get hunspell instance for this language
        hunspell = self._get_hunspell(lang_code)

        if not hunspell:
            # Try fallback
            fallback = self._get_fallback_hunspell()
            if fallback:
                hunspell = fallback
            else:
                # Can't validate, return success with warning
                return ValidationResult(
                    is_valid=True,
                    validator_type='hunspell',
                    metadata={
                        'warning': 'No dictionary available',
                        'lang_code': lang_code
                    }
                )

        # Extract words and validate
        words = self._extract_words(text)
        misspellings = []
        all_suggestions: Dict[str, List[str]] = {}

        for word in words:
            if not hunspell.spell(word):
                misspellings.append(word)
                suggestions = []
                if hasattr(hunspell, 'suggest'):
                    suggestions = hunspell.suggest(word)[:5]
                all_suggestions[word] = suggestions

        result = ValidationResult(
            is_valid=len(misspellings) == 0,
            validator_type='hunspell',
            suggestions=[s for suggs in all_suggestions.values() for s in suggs],
            metadata={
                'lang_code': lang_code,
                'misspellings': misspellings,
                'suggestions': all_suggestions,
                'word_count': len(words)
            }
        )

        # Cache the result
        self._save_to_cache(cache_key, result)

        return result

    def validate_entry(
        self,
        entry_data: Dict[str, Any],
        project_settings: ProjectSettings
    ) -> Dict[str, ValidationResult]:
        """
        Validate all text fields in an entry.

        Args:
            entry_data: Full entry data dictionary
            project_settings: Project settings

        Returns:
            Dict mapping field path to ValidationResult
        """
        results = {}

        # Validate lexical unit
        if 'lexical_unit' in entry_data:
            results['lexical_unit'] = self.validate_text(
                text=str(entry_data['lexical_unit']),
                field_path='lexical_unit',
                project_settings=project_settings,
                entry_data=entry_data
            )

        # Validate pronunciations
        if 'pronunciations' in entry_data:
            results['pronunciations'] = self.validate_text(
                text=str(entry_data['pronunciations']),
                field_path='pronunciations',
                project_settings=project_settings,
                entry_data=entry_data
            )

        # Validate senses
        for i, sense in enumerate(entry_data.get('senses', [])):
            if not isinstance(sense, dict):
                continue

            # Definition
            if 'definition' in sense:
                results[f'senses.{i}.definition'] = self.validate_text(
                    text=str(sense['definition']),
                    field_path=f'senses.{i}.definition',
                    project_settings=project_settings,
                    entry_data=entry_data
                )

            # Gloss
            if 'gloss' in sense:
                results[f'senses.{i}.gloss'] = self.validate_text(
                    text=str(sense['gloss']),
                    field_path=f'senses.{i}.gloss',
                    project_settings=project_settings,
                    entry_data=entry_data
                )

            # Examples
            for j, example in enumerate(sense.get('examples', [])):
                if isinstance(example, dict):
                    example_text = str(example.get('form', {}))
                    if example_text:
                        results[f'senses.{i}.examples.{j}'] = self.validate_text(
                            text=example_text,
                            field_path=f'senses.{i}.examples.{j}',
                            project_settings=project_settings,
                            entry_data=entry_data
                        )

        # Validate notes
        if 'notes' in entry_data:
            results['notes'] = self.validate_text(
                text=str(entry_data['notes']),
                field_path='notes',
                project_settings=project_settings,
                entry_data=entry_data
            )

        return results

    def validate_field(
        self,
        field_path: str,
        field_value: Any,
        project_settings: ProjectSettings
    ) -> ValidationResult:
        """
        Validate a single field with appropriate dictionary.

        Args:
            field_path: Path to the field
            field_value: Field value
            project_settings: Project settings

        Returns:
            ValidationResult
        """
        # Convert value to string
        text = str(field_value) if field_value else ''

        return self.validate_text(
            text=text,
            field_path=field_path,
            project_settings=project_settings
        )

    def check_word(
        self,
        word: str,
        lang_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check a single word against appropriate dictionary.

        Args:
            word: Word to check
            lang_code: Optional language code override

        Returns:
            Dict with 'valid', 'suggestions', 'lang_code'
        """
        if not lang_code:
            lang_code = 'en'

        hunspell = self._get_hunspell(lang_code)

        if not hunspell:
            return {
                'valid': True,
                'word': word,
                'suggestions': [],
                'lang_code': lang_code,
                'warning': 'No dictionary available'
            }

        valid = hunspell.spell(word)
        suggestions = hunspell.suggest(word)[:5] if not valid else []

        return {
            'valid': valid,
            'word': word,
            'suggestions': suggestions,
            'lang_code': lang_code
        }

    def suggest_words(
        self,
        word: str,
        lang_code: Optional[str] = None
    ) -> List[str]:
        """
        Get spelling suggestions for a word.

        Args:
            word: Word to get suggestions for
            lang_code: Optional language code override

        Returns:
            List of suggested words
        """
        if not lang_code:
            lang_code = 'en'

        hunspell = self._get_hunspell(lang_code)

        if not hunspell:
            return []

        return hunspell.suggest(word)[:10]

    def _get_lang_code_for_field(
        self,
        field_path: str,
        project_settings: ProjectSettings
    ) -> str:
        """Get language code for a field."""
        return self.language_detector.detect(
            field_path, '', project_settings
        )

    def _get_hunspell(self, lang_code: str) -> Optional[Any]:
        """Get hunspell instance for a language code."""
        cache_key = f"{self.project_id}:{self.user_id}:{lang_code}"

        if cache_key in self._hunspell_cache:
            return self._hunspell_cache[cache_key]

        hunspell = self.dictionary_loader.load_combined(
            project_id=self.project_id,
            lang_code=lang_code,
            user_id=self.user_id
        )

        if hunspell:
            self._hunspell_cache[cache_key] = hunspell

        return hunspell

    def _get_fallback_hunspell(self) -> Optional[Any]:
        """Get fallback hunspell instance."""
        # Try system dictionaries
        return self.dictionary_loader.load_system_dictionary('en')

    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text for validation."""
        # Handle IPA characters specially
        if self._contains_ipa(text):
            return self._extract_ipa_words(text)

        # Standard word extraction
        words = re.findall(r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b", text)
        return [w.lower() for w in words if len(w) > 1]

    def _extract_ipa_words(self, text: str) -> List[str]:
        """Extract IPA-like words from text."""
        # IPA characters pattern (simplified)
        ipa_pattern = r'[ˈˌa-zɑæɔəɛɪʊʏ∅ŋɲɳʎɾɣɦðβfvθszxçɡɣʁhɸɕʃʒɰɨʉiuyʏɯɤoɔɛʊəæɐʌɜɑɒɚɝᵻˌˈ‿]+\.?'
        matches = re.findall(ipa_pattern, text)
        return [m.strip('.').lower() for m in matches if len(m) > 1]

    def _contains_ipa(self, text: str) -> bool:
        """Check if text contains IPA characters."""
        ipa_chars = 'ɑæɔəɛɪʊʏɲŋɳʎɾðβθszxçɡɣʁɕʃʒɰɨʉɯɤoɛʊæɐʌɜɑɒɚɝ'
        return any(c in ipa_chars for c in text.lower())

    def _make_cache_key(self, text: str, lang_code: str) -> str:
        """Generate cache key for validation result."""
        content_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        return f"hunspell:{self.project_id}:{lang_code}:{content_hash}"

    def _get_from_cache(self, cache_key: str) -> Optional[ValidationResult]:
        """Get validation result from cache."""
        if not self.cache_service:
            return None

        cached = self.cache_service.get(cache_key)
        if cached:
            return ValidationResult(
                is_valid=cached.get('is_valid', True),
                validator_type='hunspell',
                cached=True,
                suggestions=cached.get('suggestions', []),
                metadata=cached.get('metadata', {})
            )
        return None

    def _save_to_cache(self, cache_key: str, result: ValidationResult) -> None:
        """Save validation result to cache."""
        if not self.cache_service:
            return

        cache_data = {
            'is_valid': result.is_valid,
            'suggestions': result.suggestions,
            'metadata': {
                **result.metadata,
                'cached_at': __import__('datetime').datetime.utcnow().isoformat()
            }
        }
        self.cache_service.set(cache_key, cache_data, ttl=86400)

    def clear_cache(self) -> int:
        """Clear cached validation results."""
        if not self.cache_service:
            return 0

        count = self.cache_service.clear_pattern(f"hunspell:{self.project_id}:*")
        self._hunspell_cache.clear()
        return count


# Factory function for creating validators
def create_hunspell_validator(
    project_id: int,
    user_id: Optional[int] = None
) -> LayeredHunspellValidator:
    """
    Create a configured hunspell validator.

    Args:
        project_id: Project ID
        user_id: Optional user ID

    Returns:
        LayeredHunspellValidator instance
    """
    return LayeredHunspellValidator(
        project_id=project_id,
        user_id=user_id
    )
