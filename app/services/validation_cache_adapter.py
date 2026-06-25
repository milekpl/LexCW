"""
Validation Cache Service Adapter for Unified Validation Pipeline.

Provides backward-compatible interface to ValidationCacheService while
internally delegating to the UnifiedValidationPipeline.

This allows gradual migration from the old ValidationCacheService API
to the new unified pipeline without breaking existing code.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from app.services.validation_cache_service import ValidationCacheService as OldValidationCacheService
from app.services.unified_validation_pipeline import (
    UnifiedValidationPipeline,
    ValidationOptions,
    ValidationType,
    get_validation_pipeline,
    reset_validation_pipeline
)
from app.validators.base import ValidationResult


logger = logging.getLogger(__name__)


class ValidationCacheServiceAdapter:
    """
    Adapter class that wraps UnifiedValidationPipeline with the
    legacy ValidationCacheService API.

    This allows existing code to continue using ValidationCacheService
    while internally benefiting from the unified validation pipeline.

    Migration path:
    1. This adapter provides full backward compatibility
    2. Gradually update code to use UnifiedValidationPipeline directly
    3. Eventually remove this adapter once all code is migrated
    """

    _instance: Optional['ValidationCacheServiceAdapter'] = None

    def __new__(cls) -> 'ValidationCacheServiceAdapter':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        pipeline: Optional[UnifiedValidationPipeline] = None,
        legacy_service: Optional[OldValidationCacheService] = None
    ):
        """
        Initialize the adapter.

        Args:
            pipeline: UnifiedValidationPipeline instance (creates new if None)
            legacy_service: Legacy ValidationCacheService for fallback (creates if None)
        """
        if hasattr(self, '_initialized'):
            return

        self.logger = logging.getLogger(__name__)
        self._initialized = True

        # Get or create pipeline
        if pipeline:
            self._pipeline = pipeline
        else:
            # Get pipeline with spelling enabled
            self._pipeline = get_validation_pipeline(
                enable_spelling=True,
                enable_rules=False,  # Rules handled separately
                enable_structural=False,
                enable_reference=False
            )

        # Keep legacy service for operations not yet in pipeline
        self._legacy = legacy_service or OldValidationCacheService()

        # Statistics (from legacy format)
        self._stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'validations': 0
        }

    # =====================================================================
    # Backward-compatible API methods (from ValidationCacheService)
    # =====================================================================

    def register_validator(self, validator) -> None:
        """
        Register a validator (legacy method - no-op in new system).

        Validators are now registered as plugins in the pipeline.
        This method exists for backward compatibility only.

        Args:
            validator: Validator instance (ignored in new system)
        """
        self.logger.warning(
            "register_validator() is deprecated. "
            "Validators are now registered as pipeline plugins."
        )
        # Pass to legacy service for any legacy validators
        try:
            self._legacy.register_validator(validator)
        except Exception:
            pass

    def get_validator(self, validator_type: str) -> Optional[Any]:
        """
        Get registered validator by type (legacy method).

        Args:
            validator_type: Type of validator

        Returns:
            Validator instance or None
        """
        return self._legacy.get_validator(validator_type)

    def get_available_validators(self) -> List[str]:
        """
        Get list of available validator types (legacy method).

        Returns:
            List of validator type strings
        """
        # Combine legacy and new pipeline types
        legacy_types = self._legacy.get_available_validators()
        pipeline_types = [t.name.lower() for t in ValidationType]
        return list(set(legacy_types + pipeline_types))

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
        Validate text using specified validators (legacy method).

        Args:
            entry_id: Entry identifier
            text: Text to validate
            validator_types: List of validator types
            lang: Language code
            target_lang: Target language for bitext
            date_modified: Entry modification date
            **kwargs: Additional options

        Returns:
            Dict mapping validator_type -> ValidationResult
        """
        # Map legacy validator types to pipeline types
        types_to_run: Set[ValidationType] = set()
        for vtype in validator_types:
            vtype_lower = vtype.lower()
            if vtype_lower in ('hunspell', 'spelling'):
                types_to_run.add(ValidationType.SPELLING)
            elif vtype_lower in ('languagetool', 'grammar'):
                types_to_run.add(ValidationType.SPELLING)
            elif vtype_lower in ('rules', 'rule'):
                types_to_run.add(ValidationType.RULES)
            elif vtype_lower in ('structural', 'structure'):
                types_to_run.add(ValidationType.STRUCTURAL)

        # Create options
        options = ValidationOptions(
            types=types_to_run if types_to_run else None,
            source_lang=lang,
            target_lang=target_lang,
            validator_options={'date_modified': date_modified, **kwargs}
        )

        # Run validation through pipeline
        entry_data = {'id': entry_id, 'text': text}
        result = self._pipeline.validate_entry(entry_data, options)

        # Update stats
        self._stats['validations'] += 1
        if result.cached:
            self._stats['hits'] += 1
        else:
            self._stats['misses'] += 1

        # Convert pipeline result back to legacy format
        return self._convert_to_legacy_results(result, validator_types)

    def validate_entry(
        self,
        entry_id: str,
        entry_data: Dict[str, Any],
        validator_types: Optional[List[str]] = None,
        lang: str = 'en'
    ) -> Dict[str, ValidationResult]:
        """
        Validate an entire entry (legacy method).

        Args:
            entry_id: Entry identifier
            entry_data: Full entry data dictionary
            validator_types: Specific validators to use (all if None)
            lang: Default language code

        Returns:
            Dict mapping validator_type -> ValidationResult
        """
        # Map legacy types to pipeline types
        types_to_run: Optional[Set[ValidationType]] = None
        if validator_types:
            types_to_run = set()
            for vtype in validator_types:
                vtype_lower = vtype.lower()
                if vtype_lower in ('hunspell', 'spelling'):
                    types_to_run.add(ValidationType.SPELLING)
                elif vtype_lower in ('languagetool', 'grammar'):
                    types_to_run.add(ValidationType.SPELLING)
                elif vtype_lower in ('rules', 'rule'):
                    types_to_run.add(ValidationType.RULES)
                elif vtype_lower in ('structural', 'structure'):
                    types_to_run.add(ValidationType.STRUCTURAL)

        # Ensure entry_id is in entry_data
        if 'id' not in entry_data:
            entry_data = {**entry_data, 'id': entry_id}

        # Create options
        options = ValidationOptions(
            types=types_to_run,
            source_lang=lang
        )

        # Run validation through pipeline
        result = self._pipeline.validate_entry(entry_data, options)

        # Update stats
        self._stats['validations'] += 1
        if result.cached:
            self._stats['hits'] += 1
        else:
            self._stats['misses'] += 1

        # Convert to legacy format
        if validator_types is None:
            validator_types = ['spelling', 'rules']
        return self._convert_to_legacy_results(result, validator_types)

    def validate_batch(
        self,
        entries: List[Dict[str, Any]],
        validator_types: Optional[List[str]] = None,
        lang: str = 'en',
        target_lang: Optional[str] = None
    ) -> Dict[str, Dict[str, ValidationResult]]:
        """
        Validate multiple entries (legacy method).

        Args:
            entries: List of entry dicts
            validator_types: Specific validators to use
            lang: Language code
            target_lang: Target language for bitext

        Returns:
            Dict mapping entry_id -> validator_type -> ValidationResult
        """
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
        Get cached result from Redis (legacy method).

        Args:
            entry_id: Entry identifier
            validator_type: Type of validator
            date_modified: Entry's date_modified

        Returns:
            Cached result dict or None
        """
        return self._legacy.get_cached_result(entry_id, validator_type, date_modified)

    def get_entries_needing_validation(
        self,
        entries: List[Dict[str, str]],
        validator_type: str
    ) -> List[str]:
        """
        Filter entries needing validation (legacy method).

        Args:
            entries: List of {id, date_modified} dicts
            validator_type: Type of validator

        Returns:
            List of entry_ids needing fresh validation
        """
        return self._legacy.get_entries_needing_validation(entries, validator_type)

    def invalidate_entry(self, entry_id: str) -> int:
        """
        Invalidate cached results for an entry (legacy method).

        Args:
            entry_id: Entry identifier

        Returns:
            Number of cache entries invalidated
        """
        # Invalidate in both pipeline and legacy
        pipeline_count = self._pipeline.invalidate_entry(entry_id)
        legacy_count = self._legacy.invalidate_entry(entry_id)
        total = max(pipeline_count, legacy_count)

        self._stats['invalidations'] += total
        return total

    def invalidate_entries(self, entry_ids: List[str]) -> int:
        """
        Invalidate cache for multiple entries (legacy method).

        Args:
            entry_ids: List of entry identifiers

        Returns:
            Total invalidations performed
        """
        total = 0
        for entry_id in entry_ids:
            total += self.invalidate_entry(entry_id)
        return total

    def get_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics (legacy method).

        Returns:
            Statistics dictionary
        """
        # Combine legacy and pipeline stats
        legacy_stats = self._legacy._stats
        pipeline_stats = self._pipeline.get_stats()

        return {
            'hits': self._stats['hits'] + legacy_stats['hits'],
            'misses': self._stats['misses'] + legacy_stats['misses'],
            'invalidations': self._stats['invalidations'] + legacy_stats['invalidations'],
            'validations': self._stats['validations'] + legacy_stats['validations'],
            'pipeline_stats': pipeline_stats
        }

    def reset_stats(self) -> None:
        """Reset statistics (legacy method)."""
        self._stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'validations': 0
        }
        self._legacy.reset_stats()
        self._pipeline.reset_stats()

    # =====================================================================
    # New Unified Pipeline API methods
    # =====================================================================

    def get_pipeline(self) -> UnifiedValidationPipeline:
        """
        Get the underlying UnifiedValidationPipeline instance.

        Returns:
            UnifiedValidationPipeline instance
        """
        return self._pipeline

    def validate_with_pipeline(
        self,
        entry_data: Dict[str, Any],
        options: Optional[ValidationOptions] = None
    ):
        """
        Validate using the new pipeline API directly.

        This method provides access to the full pipeline capabilities
        beyond what the legacy API supports.

        Args:
            entry_data: Entry data dictionary
            options: Validation options

        Returns:
            PipelineValidationResult
        """
        return self._pipeline.validate_entry(entry_data, options)

    # =====================================================================
    # Helper methods
    # =====================================================================

    def _convert_to_legacy_results(
        self,
        result,
        validator_types: List[str]
    ) -> Dict[str, ValidationResult]:
        """
        Convert pipeline result to legacy ValidationResult format.

        Args:
            result: PipelineValidationResult
            validator_types: List of requested validator types

        Returns:
            Dict mapping validator_type -> ValidationResult
        """
        legacy_results: Dict[str, ValidationResult] = {}

        # Group issues by type
        for vtype in validator_types:
            vtype_lower = vtype.lower()

            # Find matching issues in pipeline result
            matching_issues = []
            for issue in result.issues:
                issue_type = issue.type.name.lower()
                if vtype_lower in (issue_type, issue_type.rstrip('s')):  # handle plural
                    matching_issues.append(issue)

            # Create ValidationResult
            is_valid = len(matching_issues) == 0
            suggestions = []
            metadata = {
                'issue_count': len(matching_issues),
                'pipeline_result': True
            }

            for issue in matching_issues:
                suggestions.extend(issue.suggestions)

            validation_result = ValidationResult(
                is_valid=is_valid,
                validator_type=vtype,
                cached=result.cached,
                suggestions=suggestions,
                metadata=metadata
            )
            legacy_results[vtype] = validation_result

        # If no results were created (empty validator_types), create a default
        if not legacy_results and validator_types:
            for vtype in validator_types:
                legacy_results[vtype] = ValidationResult(
                    is_valid=True,
                    validator_type=vtype,
                    cached=result.cached,
                    metadata={'pipeline_result': True}
                )

        return legacy_results


# Convenience function to get the adapter instance
def get_validation_cache_adapter() -> ValidationCacheServiceAdapter:
    """
    Get the singleton ValidationCacheServiceAdapter instance.

    Returns:
        ValidationCacheServiceAdapter instance
    """
    return ValidationCacheServiceAdapter()
