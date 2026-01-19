"""
Validation Cache Service.

Orchestrates validation caching across all validator types.
Provides unified interface for:
- Multiple validator types
- Cache-aside pattern with Redis primary, DB fallback
- Batch validation for dictionaries
- Automatic invalidation based on date_modified
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from app.services.cache_service import cache_service, CacheService
from app.validators.base import Validator, ValidationResult
from app.validators.hunspell_validator import HunspellValidator
from app.validators.languagetool_validator import LanguageToolValidator
from app.models.workset_models import db


class ValidationCacheService:
    """
    Orchestrates validation caching across all validator types.

    Features:
    - Single point of access for all validation results
    - Cache-aside pattern with automatic invalidation
    - Batch processing support
    - Statistics tracking
    """

    _instance: Optional['ValidationCacheService'] = None

    def __new__(cls) -> 'ValidationCacheService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self.logger = logging.getLogger(__name__)
        self._initialized = True

        # Cache service for Redis operations
        self.cache_service = cache_service

        # Registry of validator instances
        self._validators: Dict[str, Validator] = {}

        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'validations': 0
        }

        # Initialize default validators
        self._init_default_validators()

    def _init_default_validators(self) -> None:
        """Initialize default validators."""
        try:
            # Hunspell validator
            hunspell = HunspellValidator(
                cache_service=self.cache_service
            )
            self.register_validator(hunspell)
            self.logger.info("Hunspell validator initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Hunspell: {e}")

        try:
            # LanguageTool validator
            languagetool = LanguageToolValidator(
                cache_service=self.cache_service
            )
            self.register_validator(languagetool)
            self.logger.info("LanguageTool validator initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize LanguageTool: {e}")

    def register_validator(self, validator: Validator) -> None:
        """
        Register a validator instance.

        Args:
            validator: Validator implementation
        """
        self._validators[validator.validator_type] = validator
        self.logger.info(f"Registered validator: {validator.validator_type}")

    def get_validator(self, validator_type: str) -> Optional[Validator]:
        """Get registered validator by type."""
        return self._validators.get(validator_type)

    def get_available_validators(self) -> List[str]:
        """Get list of available validator types."""
        return list(self._validators.keys())

    def validate(
        self,
        entry_id: str,
        text: str,
        validator_types: List[str],
        lang: str = 'en',
        target_lang: Optional[str] = None,
        date_modified: Optional[str] = None,
        **kwargs
    ) -> Dict[str, ValidationResult]:
        """
        Validate text using specified validators.

        Args:
            entry_id: Entry identifier
            text: Text to validate
            validator_types: List of validator types to use
            lang: Language code
            target_lang: Target language for bitext checking
            date_modified: Entry's date_modified for cache validation
            **kwargs: Additional options for validators

        Returns:
            Dict mapping validator_type -> ValidationResult
        """
        results: Dict[str, ValidationResult] = {}

        for vtype in validator_types:
            validator = self._validators.get(vtype)
            if not validator:
                self.logger.warning(f"Validator {vtype} not registered")
                continue

            # Build kwargs for this validator
            val_kwargs = kwargs.copy()
            if vtype == 'languagetool' and target_lang:
                val_kwargs['target_lang'] = target_lang
            val_kwargs['entry_id'] = entry_id
            val_kwargs['date_modified'] = date_modified

            # Perform validation
            try:
                result = validator.validate(text, lang, **val_kwargs)
                results[vtype] = result
                self._stats['validations'] += 1

                if result.metadata.get('cached'):
                    self._stats['hits'] += 1
                else:
                    self._stats['misses'] += 1

            except Exception as e:
                self.logger.error(f"Validation error for {vtype}: {e}")
                results[vtype] = ValidationResult(
                    is_valid=True,
                    validator_type=vtype,
                    metadata={'error': str(e), 'error_type': 'validation'}
                )

        return results

    def validate_entry(
        self,
        entry_id: str,
        entry_data: Dict[str, Any],
        validator_types: Optional[List[str]] = None,
        lang: str = 'en'
    ) -> Dict[str, ValidationResult]:
        """
        Validate an entire entry.

        Extracts relevant text fields and validates them.

        Args:
            entry_id: Entry identifier
            entry_data: Full entry data dictionary
            validator_types: Specific validators to use (all if None)
            lang: Default language code

        Returns:
            Dict mapping validator_type -> ValidationResult
        """
        if validator_types is None:
            validator_types = list(self._validators.keys())

        # Extract text from entry for validation
        text = self._extract_text_from_entry(entry_data)
        date_modified = entry_data.get('date_modified')

        return self.validate(
            entry_id=entry_id,
            text=text,
            validator_types=validator_types,
            lang=lang,
            date_modified=date_modified
        )

    def validate_batch(
        self,
        entries: List[Dict[str, Any]],
        validator_types: Optional[List[str]] = None,
        lang: str = 'en',
        target_lang: Optional[str] = None
    ) -> Dict[str, Dict[str, ValidationResult]]:
        """
        Validate multiple entries.

        Args:
            entries: List of entry dicts with 'id' key
            validator_types: Specific validators to use
            lang: Language code
            target_lang: Target language for bitext

        Returns:
            Dict mapping entry_id -> validator_type -> ValidationResult
        """
        if validator_types is None:
            validator_types = list(self._validators.keys())

        results: Dict[str, Dict[str, ValidationResult]] = {}

        for entry in entries:
            entry_id = entry.get('id')
            if not entry_id:
                continue

            entry_results = self.validate_entry(
                entry_id=entry_id,
                entry_data=entry,
                validator_types=validator_types,
                lang=lang
            )
            results[entry_id] = entry_results

        return results

    def get_cached_result(
        self,
        entry_id: str,
        validator_type: str,
        date_modified: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached result from Redis only.

        Args:
            entry_id: Entry identifier
            validator_type: Type of validator
            date_modified: Entry's date_modified

        Returns:
            Cached result dict or None
        """
        cache_key = self._make_cache_key(validator_type, entry_id, date_modified)
        return self.cache_service.get(cache_key)

    def get_entries_needing_validation(
        self,
        entries: List[Dict[str, str]],  # List of {id, date_modified}
        validator_type: str
    ) -> List[str]:
        """
        Filter entries that need validation (not in cache).

        Args:
            entries: List of dicts with 'id' and 'date_modified' keys
            validator_type: Type of validator

        Returns:
            List of entry_ids that need fresh validation
        """
        missing_ids = []

        for entry in entries:
            entry_id = entry['id']
            date_modified = entry['date_modified']

            cached = self.get_cached_result(
                entry_id, validator_type, date_modified
            )
            if not cached:
                missing_ids.append(entry_id)

        return missing_ids

    def invalidate_entry(self, entry_id: str) -> int:
        """
        Invalidate all cached validation results for an entry.

        Called when entry is modified.

        Args:
            entry_id: Entry identifier

        Returns:
            Total number of cache entries invalidated
        """
        total = 0

        for validator in self._validators.values():
            invalidated = validator.invalidate_for_entry(entry_id)
            total += invalidated

        self._stats['invalidations'] += total
        self.logger.info(f"Invalidated {total} cache entries for entry {entry_id}")

        return total

    def invalidate_entries(self, entry_ids: List[str]) -> int:
        """
        Invalidate cache for multiple entries.

        Args:
            entry_ids: List of entry identifiers

        Returns:
            Total invalidations performed
        """
        total = 0
        for entry_id in entry_ids:
            total += self.invalidate_entry(entry_id)
        return total

    def invalidate_all(self) -> int:
        """
        Invalidate all validation cache.

        Returns:
            Total invalidations performed
        """
        total = 0

        # Clear all validation-related Redis keys
        total += self.cache_service.clear_pattern('hunspell:*')
        total += self.cache_service.clear_pattern('lt:*')
        total += self.cache_service.clear_pattern('validation:*')

        # Clear DB cache using current app context
        try:
            from app.models.validation_cache_models import ValidationResultCache
            from flask import current_app
            with current_app.app_context():
                count = ValidationResultCache.query.delete()
                db.session.commit()
                total += count
        except Exception as e:
            self.logger.warning(f"DB clear error: {e}")

        self._stats['invalidations'] += total
        return total

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries from database.

        Returns:
            Number of entries removed
        """
        try:
            from app.models.validation_cache_models import ValidationResultCache
            return ValidationResultCache.cleanup_expired()
        except Exception as e:
            self.logger.warning(f"Cleanup error: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats['hits'] + self._stats['misses']
        return {
            **self._stats,
            'hit_rate': round(
                self._stats['hits'] / max(total, 1) * 100, 2
            ),
            'validators_registered': list(self._validators.keys()),
            'redis_available': self.cache_service.is_available()
        }

    def get_validation_summary(
        self,
        entry_id: str,
        entry_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get a summary of all validation results for an entry.

        Args:
            entry_id: Entry identifier
            entry_data: Entry data dictionary

        Returns:
            Summary dict with overall status and per-validator results
        """
        results = self.validate_entry(entry_id, entry_data)

        all_valid = all(r.is_valid for r in results.values())
        all_suggestions = []
        all_matches = []

        for vtype, result in results.items():
            all_suggestions.extend(result.suggestions)
            all_matches.extend(result.matches)

        return {
            'entry_id': entry_id,
            'is_valid': all_valid,
            'validator_count': len(results),
            'validators': {
                vtype: {
                    'is_valid': r.is_valid,
                    'cached': r.metadata.get('cached', False),
                    'issue_count': len(r.suggestions) or len(r.matches)
                }
                for vtype, r in results.items()
            },
            'total_issues': len(all_suggestions) + len(all_matches),
            'suggestions': list(set(all_suggestions))[:20],
            'validation_time': datetime.utcnow().isoformat()
        }

    def _make_cache_key(
        self,
        validator_type: str,
        entry_id: str,
        date_modified: str
    ) -> str:
        """Generate cache key for validation."""
        date_hash = hashlib.md5(date_modified.encode()).hexdigest()[:8]
        return f"validation:{validator_type}:{entry_id}:{date_hash}"

    def _extract_text_from_entry(self, entry_data: Dict[str, Any]) -> str:
        """
        Extract text from entry for spell/grammar checking.

        Args:
            entry_data: Entry dictionary

        Returns:
            Combined text for validation
        """
        text_parts = []

        # Lexical unit
        lu = entry_data.get('lexical_unit', {})
        if isinstance(lu, dict):
            text_parts.extend(str(v) for v in lu.values() if v)
        elif isinstance(lu, str):
            text_parts.append(lu)

        # Senses - definitions and glosses
        for sense in entry_data.get('senses', []):
            if isinstance(sense, dict):
                defn = sense.get('definition', {})
                if isinstance(defn, dict):
                    text_parts.extend(str(v) for v in defn.values() if v)
                elif isinstance(defn, str):
                    text_parts.append(defn)

                gloss = sense.get('gloss', {})
                if isinstance(gloss, dict):
                    text_parts.extend(str(v) for v in gloss.values() if v)
                elif isinstance(gloss, str):
                    text_parts.append(gloss)

                # Examples
                for ex in sense.get('examples', []):
                    if isinstance(ex, dict):
                        form = ex.get('form', {})
                        if isinstance(form, dict):
                            text_parts.extend(str(v) for v in form.values() if v)

        # Notes
        notes = entry_data.get('notes', {})
        if isinstance(notes, dict):
            text_parts.extend(str(v) for v in notes.values() if v)

        # Variants
        for variant in entry_data.get('variants', []):
            if isinstance(variant, dict):
                form = variant.get('form', {})
                if isinstance(form, dict):
                    text_parts.extend(str(v) for v in form.values() if v)

        return ' '.join(filter(None, text_parts))


# Global singleton instance
validation_cache_service = ValidationCacheService()


def get_validation_service() -> ValidationCacheService:
    """Get the global validation cache service instance."""
    return validation_cache_service


def invalidate_entry_cache(entry_id: str) -> int:
    """
    Convenience function to invalidate cache for an entry.

    Args:
        entry_id: Entry identifier

    Returns:
        Number of cache entries invalidated
    """
    return validation_cache_service.invalidate_entry(entry_id)
