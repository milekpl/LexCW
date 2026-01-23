"""
Abstract Base Classes for Validators.

Defines the interface that all validators must implement,
with support for caching and batch processing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    """
    Result from a validator.

    Attributes:
        is_valid: Whether the content passed validation
        validator_type: Identifier for the validator type
        cached: Whether this result came from cache
        suggestions: Spelling/grammar suggestions if not valid
        matches: Rule matches (for grammar checkers)
        bitext_quality: Translation quality assessment (for bitext mode)
        metadata: Additional validator-specific information
    """
    is_valid: bool
    validator_type: str
    cached: bool = False
    suggestions: List[str] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)
    bitext_quality: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'is_valid': self.is_valid,
            'validator_type': self.validator_type,
            'cached': self.cached,
            'suggestions': self.suggestions,
            'matches': self.matches,
            'bitext_quality': self.bitext_quality,
            'metadata': self.metadata
        }


@dataclass
class CacheEntry:
    """Cached validation result with metadata."""
    entry_id: str
    validator_type: str
    content_hash: str
    result: ValidationResult
    date_modified: str  # Entry's date_modified at cache time
    cached_at: datetime = field(default_factory=datetime.utcnow)


class Validator(ABC):
    """
    Abstract base class for all validators.

    Validators can be spell checkers (hunspell), grammar checkers
    (LanguageTool), or any other content validation service.

    All validators support:
    - Single text validation
    - Cache key generation for caching support
    - Entry-level cache invalidation
    """

    @property
    @abstractmethod
    def validator_type(self) -> str:
        """
        Unique identifier for this validator type.

        Returns:
            String identifier (e.g., 'hunspell', 'languagetool')
        """
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name for display in UI."""
        return self.validator_type.title().replace('_', ' ')

    @abstractmethod
    def validate(
        self,
        text: str,
        lang: str,
        **kwargs
    ) -> ValidationResult:
        """
        Validate text and return results.

        Args:
            text: Text to validate
            lang: Language code (e.g., 'en', 'pl')
            **kwargs: Validator-specific options:
                - target_lang: Target language for bitext checking
                - mother_tongue: User's mother tongue (LanguageTool)
                - enabled_rules: List of rule IDs to enable

        Returns:
            ValidationResult with validation outcome
        """
        ...

    @abstractmethod
    def get_cache_key(
        self,
        entry_id: str,
        text: str,
        **kwargs
    ) -> str:
        """
        Generate cache key for this validation.

        Args:
            entry_id: Entry identifier
            text: Text being validated
            **kwargs: Additional parameters that affect validation

        Returns:
            Cache key string
        """
        ...

    @abstractmethod
    def invalidate_for_entry(self, entry_id: str) -> int:
        """
        Invalidate all cached results for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Number of cache entries invalidated
        """
        ...

    def check(
        self,
        text: str,
        lang: str,
        **kwargs
    ) -> ValidationResult:
        """
        Shorthand for validate() method.

        Args:
            text: Text to validate
            lang: Language code
            **kwargs: Additional options

        Returns:
            ValidationResult
        """
        return self.validate(text, lang, **kwargs)

    def extract_words(self, text: str) -> List[str]:
        """
        Extract words from text for validation.

        Override this method for language-specific word extraction.

        Args:
            text: Input text

        Returns:
            List of words to validate
        """
        import re
        # Basic word extraction - override for language-specific logic
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        return [w.lower() for w in words if len(w) > 1]


class BatchValidator(ABC):
    """
    Interface for validators that support batch processing.

    Validators implementing this interface can process multiple
    entries more efficiently than individual validation calls.
    """

    @abstractmethod
    def validate_batch(
        self,
        entries: List[Dict[str, Any]],
        lang: str,
        **kwargs
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple entries efficiently.

        Args:
            entries: List of entry dicts, each with 'id' and 'text' keys
            lang: Language code
            **kwargs: Validator-specific options

        Returns:
            Dict mapping entry_id -> ValidationResult
        """
        ...

    def validate_batch_from_entries(
        self,
        entries: List[Dict[str, Any]],
        lang: str,
        text_extractor: Optional[callable] = None,
        **kwargs
    ) -> Dict[str, ValidationResult]:
        """
        Validate entries, extracting text if needed.

        Args:
            entries: List of entry dicts with 'id' key
            lang: Language code
            text_extractor: Optional function(entry) -> text
            **kwargs: Additional options

        Returns:
            Dict mapping entry_id -> ValidationResult
        """
        if text_extractor:
            processed = [
                {'id': e['id'], 'text': text_extractor(e)}
                for e in entries
            ]
        else:
            processed = [
                {'id': e['id'], 'text': self._default_extract(e)}
                for e in entries
            ]
        return self.validate_batch(processed, lang, **kwargs)

    def _default_extract(self, entry: Dict[str, Any]) -> str:
        """Default text extraction from entry."""
        text_parts = []

        # Lexical unit
        lu = entry.get('lexical_unit', {})
        if isinstance(lu, dict):
            text_parts.extend(str(v) for v in lu.values() if v)
        elif isinstance(lu, str):
            text_parts.append(lu)

        # Senses - definitions and glosses
        for sense in entry.get('senses', []):
            if isinstance(sense, dict):
                defn = sense.get('definition', {})
                if isinstance(defn, dict):
                    text_parts.extend(str(v) for v in defn.values() if v)
                gloss = sense.get('gloss', {})
                if isinstance(gloss, dict):
                    text_parts.extend(str(v) for v in gloss.values() if v)

        # Notes
        notes = entry.get('notes', {})
        if isinstance(notes, dict):
            text_parts.extend(str(v) for v in notes.values() if v)

        return ' '.join(text_parts)


class CacheableValidator(Validator, ABC):
    """
    Mixin for validators with built-in caching support.

    Provides methods for checking and using the cache layer.
    """

    def __init__(
        self,
        cache_service: Optional[Any] = None,
        db_session: Optional[Any] = None,
        ttl: int = 86400  # 24 hours
    ):
        """
        Initialize cacheable validator.

        Args:
            cache_service: CacheService instance
            db_session: Database session for persistent cache
            ttl: Cache TTL in seconds
        """
        self.cache_service = cache_service
        self.db_session = db_session
        self.ttl = ttl

    def _get_from_cache(self, cache_key: str) -> Optional[ValidationResult]:
        """Try to get result from Redis cache."""
        if not self.cache_service:
            return None

        cached = self.cache_service.get(cache_key)
        if cached:
            return ValidationResult(
                is_valid=cached.get('is_valid', True),
                validator_type=self.validator_type,
                cached=True,
                suggestions=cached.get('suggestions', []),
                matches=cached.get('matches', []),
                metadata={'source': 'redis'}
            )
        return None

    def _save_to_cache(
        self,
        cache_key: str,
        result: ValidationResult
    ) -> None:
        """Save result to Redis cache."""
        if not self.cache_service:
            return

        cache_data = {
            'is_valid': result.is_valid,
            'suggestions': result.suggestions,
            'matches': result.matches,
            'cached_at': datetime.utcnow().isoformat()
        }
        self.cache_service.set(cache_key, cache_data, self.ttl)

    def _check_db_cache(
        self,
        entry_id: str,
        date_modified: str,
        content_hash: str
    ) -> Optional[ValidationResult]:
        """Check persistent DB cache."""
        if not self.db_session:
            return None

        try:
            from app.models.validation_cache_models import ValidationResultCache

            if self.validator_type == 'hunspell':
                cached = ValidationResultCache.get_hunspell_result(
                    entry_id, date_modified, content_hash
                )
                if cached:
                    return ValidationResult(
                        is_valid=cached.get('valid', True),
                        validator_type=self.validator_type,
                        cached=True,
                        suggestions=cached.get('suggestions', {}).get('__all__', []),
                        metadata={'source': 'db'}
                    )
            elif self.validator_type == 'languagetool':
                cached = ValidationResultCache.get_languagetool_result(
                    entry_id, date_modified, content_hash
                )
                if cached:
                    return ValidationResult(
                        is_valid=len(cached.get('matches', [])) == 0,
                        validator_type=self.validator_type,
                        cached=True,
                        matches=cached.get('matches', []),
                        metadata={'source': 'db'}
                    )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"DB cache read failed for {self.validator_type}: {e}"
            )

        return None

    def _save_to_db(
        self,
        entry_id: str,
        date_modified: str,
        content_hash: str,
        result: ValidationResult
    ) -> None:
        """Save result to persistent DB cache."""
        if not self.db_session:
            return

        try:
            from app.models.validation_cache_models import ValidationResultCache

            if self.validator_type == 'hunspell':
                suggestions_dict = {'__all__': result.suggestions}
                ValidationResultCache.save_hunspell_result(
                    entry_id=entry_id,
                    date_modified=date_modified,
                    content_hash=content_hash,
                    valid=result.is_valid,
                    suggestions=suggestions_dict,
                    misspellings=result.suggestions  # Same list for simplicity
                )
            elif self.validator_type == 'languagetool':
                ValidationResultCache.save_languagetool_result(
                    entry_id=entry_id,
                    date_modified=date_modified,
                    content_hash=content_hash,
                    target_lang=result.metadata.get('target_lang'),
                    matches=result.matches,
                    bitext_quality=result.bitext_quality,
                    errors=result.metadata.get('errors', [])
                )
            self.db_session.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"DB cache write failed for {self.validator_type}: {e}"
            )
