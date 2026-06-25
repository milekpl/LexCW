"""
Unified Validation Pipeline Service.

Orchestrates all validation operations through a single, unified interface.
Replaces multiple scattered validate_entry implementations across the codebase.

Features:
- Single entry point for all entry validation
- Pluggable validator architecture (spelling, rules, structural, reference)
- Support for multiple input formats (dict, Entry objects, XML)
- Unified result format aggregating all validation types
- Smart caching integration with ValidationCacheService
- Backward compatible with existing validation code paths
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
import dataclasses
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Union, Callable

from app.validators.base import ValidationResult as ValidatorResult


logger = logging.getLogger(__name__)


class ValidationType(Enum):
    """Types of validation that can be performed on an entry."""
    SPELLING = auto()      # Spelling/grammar checking (Hunspell, LanguageTool)
    RULES = auto()         # Business rules validation (ValidationEngine)
    STRUCTURAL = auto()    # Data structure validation (schema, required fields)
    REFERENCE = auto()     # Cross-reference validation (relations, links)
    SEMANTIC = auto()      # Semantic validation (duplicate detection, consistency)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"      # Must fix - prevents save
    ERROR = "error"             # Should fix - affects functionality
    WARNING = "warning"         # Should consider - minor issues
    INFO = "info"               # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue from any validator type."""
    type: ValidationType
    severity: ValidationSeverity
    code: str
    message: str
    path: str
    field: Optional[str] = None
    suggestions: List[str] = dataclasses.field(default_factory=list)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'type': self.type.name,
            'severity': self.severity.value,
            'code': self.code,
            'message': self.message,
            'path': self.path,
            'field': self.field,
            'suggestions': self.suggestions,
            'metadata': self.metadata
        }


@dataclass
class PipelineValidationResult:
    """Complete validation result from the unified pipeline."""
    is_valid: bool
    issues: List[ValidationIssue]
    by_type: Dict[ValidationType, List[ValidationIssue]] = dataclasses.field(default_factory=dict)
    by_severity: Dict[ValidationSeverity, List[ValidationIssue]] = dataclasses.field(default_factory=dict)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    cached: bool = False
    validation_time_ms: Optional[float] = None

    @property
    def has_critical_issues(self) -> bool:
        """Check if result has any critical issues."""
        return any(
            issue.severity == ValidationSeverity.CRITICAL
            for issue in self.issues
        )

    @property
    def critical_count(self) -> int:
        """Count of critical issues."""
        return sum(
            1 for issue in self.issues
            if issue.severity == ValidationSeverity.CRITICAL
        )

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(
            1 for issue in self.issues
            if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(
            1 for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )

    @property
    def info_count(self) -> int:
        """Count of informational items."""
        return sum(
            1 for issue in self.issues
            if issue.severity == ValidationSeverity.INFO
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'valid': self.is_valid,
            'has_critical_issues': self.has_critical_issues,
            'critical_count': self.critical_count,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'issues': [issue.to_dict() for issue in self.issues],
            'by_type': {
                k.name: [i.to_dict() for i in v]
                for k, v in self.by_type.items()
            },
            'by_severity': {
                k.value: [i.to_dict() for i in v]
                for k, v in self.by_severity.items()
            },
            'cached': self.cached,
            'validation_time_ms': self.validation_time_ms,
            'metadata': self.metadata
        }


@dataclass
class ValidationOptions:
    """Options for controlling validation behavior."""
    # Which validation types to run (None = all)
    types: Optional[Set[ValidationType]] = None
    # Minimum severity to include in results
    min_severity: ValidationSeverity = ValidationSeverity.INFO
    # Enable caching
    use_cache: bool = True
    # Project ID for project-specific validation rules
    project_id: Optional[str] = None
    # User ID for user-specific dictionaries
    user_id: Optional[int] = None
    # Validation mode (save, delete, draft, all)
    validation_mode: str = "save"
    # Existing entry IDs for reference validation
    existing_entry_ids: Optional[Set[str]] = None
    # Language codes for validation
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    # Custom validator-specific options
    validator_options: Dict[str, Any] = dataclasses.field(default_factory=dict)


class ValidatorPlugin(ABC):
    """Abstract base class for validation plugins."""

    @property
    @abstractmethod
    def validation_type(self) -> ValidationType:
        """The type of validation this plugin performs."""
        ...

    @abstractmethod
    def validate(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> List[ValidationIssue]:
        """
        Validate entry data and return list of issues.

        Args:
            entry_data: Entry as dictionary
            options: Validation options

        Returns:
            List of validation issues found
        """
        ...

    def get_cache_key(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> Optional[str]:
        """
        Generate cache key for this validation.

        Return None to disable caching for this validator.

        Args:
            entry_data: Entry data
            options: Validation options

        Returns:
            Cache key string or None
        """
        return None

    def invalidate_cache(self, entry_id: str) -> int:
        """
        Invalidate cached results for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Number of cache entries invalidated
        """
        return 0


class UnifiedValidationPipeline:
    """
    Unified validation pipeline that orchestrates all validation types.

    This service provides a single entry point for all entry validation,
    replacing multiple scattered validate_entry implementations across
    the codebase.

    Example:
        pipeline = UnifiedValidationPipeline()
        result = pipeline.validate_entry(entry_dict, options)

        # Check if valid
        if result.is_valid:
            save_entry(entry_dict)

        # Get issues by type
        spelling_issues = result.by_type[ValidationType.SPELLING]
        rule_issues = result.by_type[ValidationType.RULES]
    """

    def __init__(
        self,
        cache_service: Optional[Any] = None,
        enable_spelling: bool = True,
        enable_rules: bool = True,
        enable_structural: bool = True,
        enable_reference: bool = True,
        enable_semantic: bool = False
    ):
        """
        Initialize the validation pipeline.

        Args:
            cache_service: Optional cache service for validation results
            enable_spelling: Enable spelling validation
            enable_rules: Enable business rules validation
            enable_structural: Enable structural validation
            enable_reference: Enable reference/cross-link validation
            enable_semantic: Enable semantic validation (disabled by default)
        """
        self.cache_service = cache_service
        self._plugins: Dict[ValidationType, List[ValidatorPlugin]] = {
            vtype: [] for vtype in ValidationType
        }
        self._plugin_instances: Dict[str, ValidatorPlugin] = {}

        # Track enabled types
        self._enabled_types: Set[ValidationType] = set()
        if enable_spelling:
            self._enabled_types.add(ValidationType.SPELLING)
        if enable_rules:
            self._enabled_types.add(ValidationType.RULES)
        if enable_structural:
            self._enabled_types.add(ValidationType.STRUCTURAL)
        if enable_reference:
            self._enabled_types.add(ValidationType.REFERENCE)
        if enable_semantic:
            self._enabled_types.add(ValidationType.SEMANTIC)

        # Statistics
        self._stats = {
            'total_validations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'by_type': {vtype: 0 for vtype in ValidationType}
        }

        # Initialize default validators
        self._init_default_plugins()

    def _init_default_plugins(self) -> None:
        """Initialize default validation plugins."""
        # These will be populated when specific validator implementations
        # are refactored to use the plugin interface
        pass

    def register_plugin(self, plugin: ValidatorPlugin) -> None:
        """
        Register a validation plugin.

        Args:
            plugin: ValidatorPlugin implementation
        """
        vtype = plugin.validation_type
        self._plugins[vtype].append(plugin)
        self._plugin_instances[plugin.__class__.__name__] = plugin
        logger.info(f"Registered {plugin.__class__.__name__} for {vtype.name}")

    def unregister_plugin(self, plugin_class: type) -> bool:
        """
        Unregister a validation plugin.

        Args:
            plugin_class: Class of the plugin to unregister

        Returns:
            True if plugin was found and removed
        """
        name = plugin_class.__name__
        if name not in self._plugin_instances:
            return False

        plugin = self._plugin_instances.pop(name)
        self._plugins[plugin.validation_type].remove(plugin)
        logger.info(f"Unregistered {name}")
        return True

    def validate_entry(
        self,
        entry_data: Union[Dict[str, Any], Any],
        options: Optional[ValidationOptions] = None
    ) -> PipelineValidationResult:
        """
        Validate an entry through the unified pipeline.

        This is the main entry point for all validation operations.
        Replaces validate_entry implementations in:
        - LayeredHunspellValidator
        - ValidationCacheService
        - ValidationEngine
        - API endpoints

        Args:
            entry_data: Entry data (dict, Entry object, or object with to_dict())
            options: Validation options (uses defaults if None)

        Returns:
            PipelineValidationResult with all validation issues
        """
        import time
        start_time = time.time()

        # Normalize options
        options = options or ValidationOptions()

        # Convert entry to dictionary
        data = self._normalize_entry_data(entry_data)
        if data is None:
            return PipelineValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    type=ValidationType.STRUCTURAL,
                    severity=ValidationSeverity.CRITICAL,
                    code="INVALID_ENTRY_DATA",
                    message="Could not convert entry data to dictionary",
                    path=""
                )]
            )

        # Determine which validation types to run
        types_to_run = options.types or self._enabled_types
        types_to_run = types_to_run.intersection(self._enabled_types)

        # Try cache lookup
        if options.use_cache and self.cache_service:
            cached_result = self._check_cache(data, options, types_to_run)
            if cached_result:
                cached_result.validation_time_ms = (time.time() - start_time) * 1000
                self._stats['cache_hits'] += 1
                return cached_result

        # Run all enabled validators
        all_issues: List[ValidationIssue] = []
        issues_by_type: Dict[ValidationType, List[ValidationIssue]] = {}
        issues_by_severity: Dict[ValidationSeverity, List[ValidationIssue]] = {
            sev: [] for sev in ValidationSeverity
        }

        for vtype in types_to_run:
            type_issues = self._run_validators(vtype, data, options)
            issues_by_type[vtype] = type_issues
            all_issues.extend(type_issues)
            self._stats['by_type'][vtype] += 1

            # Sort by severity
            for issue in type_issues:
                if issue.severity.value >= options.min_severity.value:
                    issues_by_severity[issue.severity].append(issue)

        # Determine overall validity
        has_critical = any(
            issue.severity == ValidationSeverity.CRITICAL
            for issue in all_issues
        )
        is_valid = not has_critical

        # Build result
        result = PipelineValidationResult(
            is_valid=is_valid,
            issues=all_issues,
            by_type=issues_by_type,
            by_severity=issues_by_severity,
            metadata={
                'entry_id': data.get('id'),
                'validation_types': [t.name for t in types_to_run],
                'options': {
                    'use_cache': options.use_cache,
                    'validation_mode': options.validation_mode
                }
            }
        )

        # Cache result
        if options.use_cache and self.cache_service:
            self._cache_result(data, options, types_to_run, result)

        # Update stats
        self._stats['total_validations'] += 1
        self._stats['cache_misses'] += 1
        result.validation_time_ms = (time.time() - start_time) * 1000

        return result

    def validate_xml(
        self,
        xml_string: str,
        options: Optional[ValidationOptions] = None
    ) -> PipelineValidationResult:
        """
        Validate a LIFT XML entry string.

        Parses XML to dictionary then runs through normal validation pipeline.

        Args:
            xml_string: LIFT XML string for single entry
            options: Validation options

        Returns:
            PipelineValidationResult
        """
        try:
            # Parse XML to Entry object
            from app.parsers.lift_parser import LIFTParser
            parser = LIFTParser(validate=False)
            entries = parser.parse_string(xml_string)

            if not entries:
                return PipelineValidationResult(
                    is_valid=False,
                    issues=[ValidationIssue(
                        type=ValidationType.STRUCTURAL,
                        severity=ValidationSeverity.CRITICAL,
                        code="EMPTY_XML",
                        message="No entries found in XML",
                        path=""
                    )]
                )

            # Validate the first entry
            return self.validate_entry(entries[0], options)

        except ImportError:
            return PipelineValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    type=ValidationType.STRUCTURAL,
                    severity=ValidationSeverity.CRITICAL,
                    code="XML_PARSER_UNAVAILABLE",
                    message="LIFT XML parser not available",
                    path=""
                )]
            )
        except Exception as e:
            return PipelineValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    type=ValidationType.STRUCTURAL,
                    severity=ValidationSeverity.CRITICAL,
                    code="XML_PARSE_ERROR",
                    message=f"Failed to parse XML: {str(e)}",
                    path=""
                )]
            )

    def validate_batch(
        self,
        entries: List[Union[Dict[str, Any], Any]],
        options: Optional[ValidationOptions] = None
    ) -> Dict[str, PipelineValidationResult]:
        """
        Validate multiple entries in batch.

        Args:
            entries: List of entry data
            options: Validation options

        Returns:
            Dict mapping entry_id -> PipelineValidationResult
        """
        results = {}
        for entry in entries:
            data = self._normalize_entry_data(entry)
            entry_id = data.get('id') if data else 'unknown'
            results[entry_id] = self.validate_entry(entry, options)
        return results

    def invalidate_entry(self, entry_id: str) -> int:
        """
        Invalidate all cached validation results for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Number of cache entries invalidated
        """
        count = 0
        for plugins in self._plugins.values():
            for plugin in plugins:
                count += plugin.invalidate_cache(entry_id)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            'total_validations': self._stats['total_validations'],
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'cache_hit_rate': (
                self._stats['cache_hits'] / max(1, self._stats['total_validations'])
            ),
            'by_type': {
                k.name: v for k, v in self._stats['by_type'].items()
            },
            'registered_plugins': list(self._plugin_instances.keys())
        }

    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._stats = {
            'total_validations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'by_type': {vtype: 0 for vtype in ValidationType}
        }

    def _normalize_entry_data(
        self,
        entry_data: Union[Dict[str, Any], Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert entry data to dictionary format.

        Handles:
        - Dictionary (returned as-is)
        - Objects with to_dict() method
        - Objects with __dict__
        - Dict-like objects

        Args:
            entry_data: Entry data in various formats

        Returns:
            Dictionary or None if conversion failed
        """
        if isinstance(entry_data, dict):
            return entry_data

        if hasattr(entry_data, 'to_dict') and callable(getattr(entry_data, 'to_dict')):
            try:
                return entry_data.to_dict()
            except Exception as e:
                logger.warning(f"to_dict() failed: {e}")
                return None

        if hasattr(entry_data, '__dict__'):
            try:
                return dict(entry_data.__dict__)
            except Exception as e:
                logger.warning(f"__dict__ conversion failed: {e}")
                return None

        # Try dict() constructor
        try:
            return dict(entry_data)
        except (TypeError, ValueError) as e:
            logger.warning(f"dict() conversion failed: {e}")
            return None

    def _run_validators(
        self,
        vtype: ValidationType,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> List[ValidationIssue]:
        """
        Run all validators of a specific type.

        Args:
            vtype: Validation type
            entry_data: Entry dictionary
            options: Validation options

        Returns:
            List of validation issues
        """
        issues = []
        for plugin in self._plugins.get(vtype, []):
            try:
                plugin_issues = plugin.validate(entry_data, options)
                issues.extend(plugin_issues)
            except Exception as e:
                logger.error(f"Validator {plugin.__class__.__name__} failed: {e}")
                issues.append(ValidationIssue(
                    type=vtype,
                    severity=ValidationSeverity.ERROR,
                    code="VALIDATOR_ERROR",
                    message=f"Validator failed: {str(e)}",
                    path="",
                    metadata={'validator': plugin.__class__.__name__}
                ))
        return issues

    def _check_cache(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions,
        types_to_run: Set[ValidationType]
    ) -> Optional[PipelineValidationResult]:
        """
        Check if validation result is in cache.

        Args:
            entry_data: Entry dictionary
            options: Validation options
            types_to_run: Set of validation types being run

        Returns:
            Cached result or None
        """
        # TODO: Implement cache lookup using cache_service
        # This will be implemented when integrating with ValidationCacheService
        return None

    def _cache_result(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions,
        types_to_run: Set[ValidationType],
        result: PipelineValidationResult
    ) -> None:
        """
        Cache validation result.

        Args:
            entry_data: Entry dictionary
            options: Validation options
            types_to_run: Set of validation types that were run
            result: Validation result to cache
        """
        # TODO: Implement caching using cache_service
        # This will be implemented when integrating with ValidationCacheService
        pass


# Global pipeline instance
_pipeline_instance: Optional[UnifiedValidationPipeline] = None


def get_validation_pipeline(
    cache_service: Optional[Any] = None,
    enable_spelling: bool = True,
    enable_rules: bool = True,
    enable_structural: bool = True,
    enable_reference: bool = True,
    enable_semantic: bool = False
) -> UnifiedValidationPipeline:
    """
    Get or create the global validation pipeline instance.

    Factory function that returns a singleton pipeline instance,
    creating it on first call with the specified options.

    Args:
        cache_service: Optional cache service
        enable_spelling: Enable spelling validation
        enable_rules: Enable rules validation
        enable_structural: Enable structural validation
        enable_reference: Enable reference validation
        enable_semantic: Enable semantic validation

    Returns:
        UnifiedValidationPipeline instance
    """
    global _pipeline_instance

    if _pipeline_instance is None:
        _pipeline_instance = UnifiedValidationPipeline(
            cache_service=cache_service,
            enable_spelling=enable_spelling,
            enable_rules=enable_rules,
            enable_structural=enable_structural,
            enable_reference=enable_reference,
            enable_semantic=enable_semantic
        )

    return _pipeline_instance


def reset_validation_pipeline() -> None:
    """Reset the global pipeline instance (useful for testing)."""
    global _pipeline_instance
    _pipeline_instance = None
