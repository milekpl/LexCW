"""
Spelling Validator Plugin for Unified Validation Pipeline.

Adapts LayeredHunspellValidator and other spelling validators to the
unified validation pipeline plugin interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.unified_validation_pipeline import (
    ValidatorPlugin, ValidationType, ValidationSeverity,
    ValidationIssue, ValidationOptions
)
from app.validators.layered_hunspell_validator import LayeredHunspellValidator
from app.models.project_settings import ProjectSettings


class SpellingValidatorPlugin(ValidatorPlugin):
    """
    Plugin adapter for spelling validation using LayeredHunspellValidator.

    Converts the old-style field-by-field validation results to the
    unified ValidationIssue format.
    """

    def __init__(
        self,
        project_id: int,
        user_id: Optional[int] = None,
        validator: Optional[LayeredHunspellValidator] = None
    ):
        """
        Initialize spelling validator plugin.

        Args:
            project_id: Project ID for dictionary lookup
            user_id: Optional user ID for user dictionaries
            validator: Optional pre-configured validator instance
        """
        self._project_id = project_id
        self._user_id = user_id
        self._validator = validator

    @property
    def validation_type(self) -> ValidationType:
        return ValidationType.SPELLING

    def validate(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> List[ValidationIssue]:
        """
        Validate entry spelling using LayeredHunspellValidator.

        Args:
            entry_data: Entry dictionary
            options: Validation options

        Returns:
            List of spelling validation issues
        """
        # Get or create validator instance
        validator = self._get_validator(options)
        if validator is None:
            # Spelling validation not available
            return []

        # Get project settings
        project_settings = self._get_project_settings(options)

        # Run validation
        try:
            results = validator.validate_entry(entry_data, project_settings)
        except Exception as e:
            # Log error and return empty
            return [ValidationIssue(
                type=ValidationType.SPELLING,
                severity=ValidationSeverity.ERROR,
                code="SPELLING_VALIDATION_ERROR",
                message=f"Spelling validation failed: {str(e)}",
                path="",
                metadata={'error': str(e)}
            )]

        # Convert results to ValidationIssue format
        issues = []
        for field_path, result in results.items():
            if result.is_valid:
                continue

            # Determine severity based on result
            if result.metadata.get('error'):
                severity = ValidationSeverity.ERROR
            elif not result.suggestions:
                # No suggestions = probably critical
                severity = ValidationSeverity.ERROR
            else:
                # Has suggestions = warning
                severity = ValidationSeverity.WARNING

            issue = ValidationIssue(
                type=ValidationType.SPELLING,
                severity=severity,
                code="SPELLING_ERROR",
                message=f"Spelling issues in {field_path}",
                path=field_path,
                field=field_path.split('.')[-1] if '.' in field_path else field_path,
                suggestions=result.suggestions,
                metadata={
                    'word_count': result.metadata.get('word_count', 0),
                    'invalid_words': result.metadata.get('invalid_words', [])
                }
            )
            issues.append(issue)

        return issues

    def get_cache_key(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> Optional[str]:
        """
        Generate cache key for spelling validation.

        Args:
            entry_data: Entry dictionary
            options: Validation options

        Returns:
            Cache key string or None
        """
        entry_id = entry_data.get('id', 'unknown')
        # Include project_id in key as dictionaries are project-specific
        return f"spelling:{self._project_id}:{entry_id}"

    def invalidate_cache(self, entry_id: str) -> int:
        """
        Invalidate cached results for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Number of cache entries invalidated (always 0 for this plugin)
        """
        # Cache invalidation is handled by ValidationCacheService
        return 0

    def _get_validator(
        self,
        options: ValidationOptions
    ) -> Optional[LayeredHunspellValidator]:
        """
        Get or create validator instance.

        Args:
            options: Validation options

        Returns:
            LayeredHunspellValidator instance or None
        """
        if self._validator is not None:
            return self._validator

        # Get project_id from options if different
        project_id = options.validator_options.get('project_id', self._project_id)
        user_id = options.user_id or self._user_id

        try:
            self._validator = LayeredHunspellValidator(
                project_id=project_id,
                user_id=user_id
            )
            return self._validator
        except Exception:
            # Validator initialization failed (e.g., dictionaries not available)
            return None

    def _get_project_settings(
        self,
        options: ValidationOptions
    ) -> ProjectSettings:
        """
        Get project settings for validation.

        Args:
            options: Validation options

        Returns:
            ProjectSettings instance
        """
        # Use provided settings or create defaults
        if hasattr(options, 'project_settings') and options.project_settings:
            return options.project_settings

        # Create settings from options
        settings_data = {
            'source_language': options.source_lang or 'en',
            'target_language': options.target_lang or 'en',
            'project_id': options.project_id or str(self._project_id)
        }
        return ProjectSettings(**settings_data)


class HunspellValidatorPlugin(SpellingValidatorPlugin):
    """
    Alias for SpellingValidatorPlugin for backward compatibility.

    Some code may reference HunspellValidatorPlugin specifically.
    """
    pass
