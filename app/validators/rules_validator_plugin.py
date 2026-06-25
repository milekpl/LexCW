"""
Rules Validator Plugin for Unified Validation Pipeline.

Adapts ValidationEngine to the unified validation pipeline plugin interface.
Converts ValidationEngine results to ValidationIssue format.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.services.unified_validation_pipeline import (
    ValidatorPlugin, ValidationType, ValidationSeverity,
    ValidationIssue, ValidationOptions
)
from app.services.validation_engine import (
    ValidationEngine, ValidationPriority,
    ValidationCategory as EngineCategory
)


# Map ValidationEngine categories to severity levels
CATEGORY_TO_SEVERITY: Dict[EngineCategory, ValidationSeverity] = {
    EngineCategory.ENTRY_LEVEL: ValidationSeverity.ERROR,
    EngineCategory.SENSE_LEVEL: ValidationSeverity.ERROR,
    EngineCategory.HIERARCHICAL_VALIDATION: ValidationSeverity.ERROR,
    EngineCategory.RELATION_VALIDATION: ValidationSeverity.WARNING,
    EngineCategory.NOTE_VALIDATION: ValidationSeverity.WARNING,
    EngineCategory.PRONUNCIATION: ValidationSeverity.WARNING,
    EngineCategory.RESOURCE_VALIDATION: ValidationSeverity.WARNING,
    EngineCategory.LANGUAGE_VALIDATION: ValidationSeverity.ERROR,
    EngineCategory.DATE_VALIDATION: ValidationSeverity.WARNING,
    EngineCategory.GENERAL: ValidationSeverity.WARNING,
    EngineCategory.SPELLING: ValidationSeverity.WARNING,
}

# Map ValidationEngine priorities to severity levels
PRIORITY_TO_SEVERITY: Dict[ValidationPriority, ValidationSeverity] = {
    ValidationPriority.CRITICAL: ValidationSeverity.CRITICAL,
    ValidationPriority.WARNING: ValidationSeverity.WARNING,
    ValidationPriority.INFORMATIONAL: ValidationSeverity.INFO,
}


class RulesValidatorPlugin(ValidatorPlugin):
    """
    Plugin adapter for rule-based validation using ValidationEngine.

    Converts ValidationEngine's rule-based validation results to the
    unified ValidationIssue format.
    """

    def __init__(
        self,
        rules_file: Optional[str] = None,
        project_config: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        engine: Optional[ValidationEngine] = None
    ):
        """
        Initialize rules validator plugin.

        Args:
            rules_file: Path to validation rules JSON file
            project_config: Optional project configuration
            project_id: Optional project ID for project-specific rules
            engine: Optional pre-configured ValidationEngine instance
        """
        self._rules_file = rules_file
        self._project_config = project_config
        self._project_id = project_id
        self._engine = engine

    @property
    def validation_type(self) -> ValidationType:
        return ValidationType.RULES

    def validate(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> List[ValidationIssue]:
        """
        Validate entry using ValidationEngine rules.

        Args:
            entry_data: Entry dictionary
            options: Validation options

        Returns:
            List of rule validation issues
        """
        # Get or create engine instance
        engine = self._get_engine(options)
        if engine is None:
            return []

        # Run validation
        try:
            result = engine.validate_entry(entry_data, options.validation_mode)
        except Exception as e:
            return [ValidationIssue(
                type=ValidationType.RULES,
                severity=ValidationSeverity.ERROR,
                code="RULES_VALIDATION_ERROR",
                message=f"Rules validation failed: {str(e)}",
                path="",
                metadata={'error': str(e)}
            )]

        # Convert ValidationEngine result to ValidationIssue format
        issues = []

        # Convert errors
        for error in result.errors:
            issue = self._convert_engine_error(error)
            issues.append(issue)

        # Convert warnings
        for warning in result.warnings:
            issue = self._convert_engine_error(warning, is_warning=True)
            issues.append(issue)

        # Convert info
        for info in result.info:
            issue = self._convert_engine_error(info, is_info=True)
            issues.append(issue)

        return issues

    def get_cache_key(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> Optional[str]:
        """
        Generate cache key for rules validation.

        Args:
            entry_data: Entry dictionary
            options: Validation options

        Returns:
            Cache key string or None
        """
        entry_id = entry_data.get('id', 'unknown')
        # Include validation mode in key as different modes run different rules
        mode = options.validation_mode
        return f"rules:{self._project_id}:{mode}:{entry_id}"

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

    def _get_engine(self, options: ValidationOptions) -> Optional[ValidationEngine]:
        """
        Get or create ValidationEngine instance.

        Args:
            options: Validation options

        Returns:
            ValidationEngine instance or None
        """
        if self._engine is not None:
            return self._engine

        # Create new engine with appropriate configuration
        project_id = options.project_id or self._project_id
        project_config = options.validator_options.get('project_config', self._project_config)

        try:
            self._engine = ValidationEngine(
                rules_file=self._rules_file,
                project_config=project_config,
                project_id=project_id,
                existing_entry_ids=options.existing_entry_ids
            )
            return self._engine
        except Exception:
            # Engine initialization failed
            return None

    def _convert_engine_error(
        self,
        engine_error,
        is_warning: bool = False,
        is_info: bool = False
    ) -> ValidationIssue:
        """
        Convert ValidationEngine error to ValidationIssue.

        Args:
            engine_error: ValidationEngine ValidationError
            is_warning: Whether this is a warning-level issue
            is_info: Whether this is an info-level issue

        Returns:
            ValidationIssue
        """
        # Determine severity
        if is_info:
            severity = ValidationSeverity.INFO
        elif is_warning:
            severity = ValidationSeverity.WARNING
        else:
            # Map priority to severity
            priority = getattr(engine_error, 'priority', ValidationPriority.WARNING)
            severity = PRIORITY_TO_SEVERITY.get(priority, ValidationSeverity.ERROR)

            # Override based on category if not explicitly critical
            if severity != ValidationSeverity.CRITICAL:
                category = getattr(engine_error, 'category', EngineCategory.GENERAL)
                category_severity = CATEGORY_TO_SEVERITY.get(category, ValidationSeverity.WARNING)
                # Use more severe of priority vs category mapping
                if category_severity.value == "critical" or severity.value == "critical":
                    severity = ValidationSeverity.CRITICAL
                elif category_severity.value == "error" or severity.value == "error":
                    severity = ValidationSeverity.ERROR

        # Get path
        path = getattr(engine_error, 'path', '')

        # Get field from path (last component)
        field = None
        if path and '.' in path:
            field = path.split('.')[-1]
        elif path:
            field = path

        # Get suggestions from metadata if available
        suggestions = []
        value = getattr(engine_error, 'value', None)
        if value and isinstance(value, dict):
            suggestions = value.get('suggestions', [])

        return ValidationIssue(
            type=ValidationType.RULES,
            severity=severity,
            code=getattr(engine_error, 'rule_id', 'UNKNOWN'),
            message=getattr(engine_error, 'message', 'Validation error'),
            path=path,
            field=field,
            suggestions=suggestions,
            metadata={
                'rule_name': getattr(engine_error, 'rule_name', 'unknown'),
                'category': getattr(engine_error, 'category', EngineCategory.GENERAL).value,
                'priority': getattr(engine_error, 'priority', ValidationPriority.WARNING).value,
                'value': value
            }
        )


class StructuralValidatorPlugin(RulesValidatorPlugin):
    """
    Plugin for structural/schema validation.

    A specialized version of RulesValidatorPlugin focused on
    structural and schema validation only.
    """

    STRUCTURAL_CATEGORIES: Set[EngineCategory] = {
        EngineCategory.ENTRY_LEVEL,
        EngineCategory.SENSE_LEVEL,
        EngineCategory.HIERARCHICAL_VALIDATION,
    }

    def validate(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> List[ValidationIssue]:
        """
        Validate only structural rules.

        Args:
            entry_data: Entry dictionary
            options: Validation options

        Returns:
            List of structural validation issues
        """
        # Get all issues from parent
        all_issues = super().validate(entry_data, options)

        # Filter to structural categories only
        structural_issues = [
            issue for issue in all_issues
            if issue.metadata.get('category') in {
                cat.value for cat in self.STRUCTURAL_CATEGORIES
            }
        ]

        # Change type to STRUCTURAL
        for issue in structural_issues:
            issue.type = ValidationType.STRUCTURAL

        return structural_issues

    @property
    def validation_type(self) -> ValidationType:
        return ValidationType.STRUCTURAL


class ReferenceValidatorPlugin(RulesValidatorPlugin):
    """
    Plugin for reference/cross-link validation.

    Validates relations and cross-references between entries.
    """

    REFERENCE_CATEGORIES: Set[EngineCategory] = {
        EngineCategory.RELATION_VALIDATION,
    }

    def validate(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> List[ValidationIssue]:
        """
        Validate only reference/cross-link rules.

        Args:
            entry_data: Entry dictionary
            options: Validation options

        Returns:
            List of reference validation issues
        """
        # Get all issues from parent
        all_issues = super().validate(entry_data, options)

        # Filter to reference categories only
        reference_issues = [
            issue for issue in all_issues
            if issue.metadata.get('category') in {
                cat.value for cat in self.REFERENCE_CATEGORIES
            }
        ]

        # Change type to REFERENCE
        for issue in reference_issues:
            issue.type = ValidationType.REFERENCE

        return reference_issues

    @property
    def validation_type(self) -> ValidationType:
        return ValidationType.REFERENCE
