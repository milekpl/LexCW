"""
Unified Query Validation Service.

Consolidates query validation functionality from QueryBuilderService and WorksetService
into a single, consistent interface. Provides support for both simple and comprehensive
validation modes with pluggable estimation strategies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Callable


class QueryValidationMode(Enum):
    """Validation modes for query validation."""
    SIMPLE = auto()        # Basic validation (fast, no DB lookup)
    COMPREHENSIVE = auto() # Full validation including database estimation
    STRICT = auto()        # Comprehensive with strict field validation


class ValidationSeverity(Enum):
    """Severity levels for query validation errors."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class QueryValidationError:
    """A single query validation error."""
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    field: Optional[str] = None
    code: str = "VALIDATION_ERROR"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'message': self.message,
            'severity': self.severity.value,
            'field': self.field,
            'code': self.code
        }


@dataclass
class QueryValidationResult:
    """Result from query validation."""
    is_valid: bool
    errors: List[QueryValidationError]
    warnings: List[QueryValidationError] = field(default_factory=list)
    estimated_count: int = 0
    performance_score: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        """Check if validation has any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if validation has any warnings."""
        return len(self.warnings) > 0

    @property
    def all_issues(self) -> List[QueryValidationError]:
        """Get all issues (errors and warnings)."""
        return self.errors + self.warnings

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'valid': self.is_valid,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'estimated_count': self.estimated_count,
            'performance_score': self.performance_score,
            'metadata': self.metadata
        }


@dataclass
class QueryValidationOptions:
    """Options for query validation."""
    mode: QueryValidationMode = QueryValidationMode.COMPREHENSIVE
    validate_fields: bool = True
    validate_operators: bool = True
    validate_cross_references: bool = True
    estimate_performance: bool = True
    use_database: bool = True
    max_estimated_count: int = 1000
    project_id: Optional[str] = None
    # Custom valid fields (if None, uses default comprehensive list)
    valid_fields: Optional[Set[str]] = None
    # Custom valid operators (if None, uses default comprehensive list)
    valid_operators: Optional[Set[str]] = None
    # Custom valid sort fields (if None, uses default list)
    valid_sort_fields: Optional[Set[str]] = None


class QueryValidator:
    """
    Unified query validation service.

    Consolidates query validation from QueryBuilderService and WorksetService
    into a single consistent interface.

    Features:
    - Multiple validation modes (SIMPLE, COMPREHENSIVE, STRICT)
    - Pluggable field/operator validation
    - Performance estimation with database lookup or estimation
    - Cross-reference validation
    - Backward-compatible with existing APIs

    Example:
        validator = QueryValidator()

        # Validate from dict (like QueryBuilderService)
        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'contains', 'value': 'test'}],
            'sort_by': 'lexical_unit'
        })

        # Validate from WorksetQuery object (like WorksetService)
        result = validator.validate_workset_query(workset_query)
    """

    # Comprehensive LIFT schema fields (from QueryBuilderService)
    COMPREHENSIVE_VALID_FIELDS: Set[str] = {
        # Entry-level fields
        'lexical_unit', 'lexical_unit.lang', 'headword',
        'grammatical_info', 'pos', 'pronunciation', 'pronunciation.ipa',
        'citation', 'note', 'custom_field',

        # Etymology fields
        'etymology.source', 'etymology.type', 'etymology.form', 'etymology.gloss',

        # Relation fields
        'relation.type', 'relation.ref', 'relation.target',

        # Variant fields
        'variant.form', 'variant.type',

        # Sense-level fields
        'sense.definition', 'sense.gloss', 'sense.grammatical_info',
        'sense.semantic_domain', 'sense.note', 'sense.custom_field',

        # Example fields
        'sense.example', 'sense.example.translation',

        # Cross-entry comparison fields
        'similar_headword', 'contains_headword', 'normalized_headword',
        'duplicate_candidate', 'compound_component'
    }

    # Simple fields (from WorksetService)
    SIMPLE_VALID_FIELDS: Set[str] = {
        'lexical_unit', 'pos', 'created_at', 'updated_at',
        'grammatical_info', 'citation', 'note'
    }

    # Comprehensive operators (from QueryBuilderService)
    COMPREHENSIVE_VALID_OPERATORS: Set[str] = {
        # Basic string operators
        'equals', 'contains', 'starts_with', 'ends_with',
        'regex', 'not_equals', 'not_contains',

        # Numerical operators
        'greater_than', 'less_than', 'greater_equal', 'less_equal',
        'gt', 'lt', 'gte', 'lte',  # aliases

        # List operators
        'in', 'not_in', 'contains_any', 'contains_all',

        # Similarity operators for duplicate detection
        'similar_to', 'levenshtein_distance', 'phonetic_similar',
        'normalized_equals', 'fuzzy_match',

        # Cross-entry comparison operators
        'headword_contained_in', 'contains_as_component',
        'shares_root_with', 'same_pos_as',

        # Existence operators
        'exists', 'not_exists', 'is_empty', 'is_not_empty'
    }

    # Simple operators (from WorksetService)
    SIMPLE_VALID_OPERATORS: Set[str] = {
        'equals', 'contains', 'starts_with', 'in', 'gt', 'lt'
    }

    # Comprehensive sort fields
    COMPREHENSIVE_SORT_FIELDS: Set[str] = {
        'lexical_unit', 'pos', 'date_created', 'date_modified',
        'grammatical_info', 'headword'
    }

    # Simple sort fields
    SIMPLE_SORT_FIELDS: Set[str] = {
        'lexical_unit', 'pos', 'created_at', 'updated_at'
    }

    # Cross-reference pattern (from QueryBuilderService)
    CROSS_REF_PATTERN = re.compile(
        r'\[ELEMENT\s+(\d+):([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\]'
    )

    def __init__(
        self,
        dictionary_service=None,
        default_mode: QueryValidationMode = QueryValidationMode.COMPREHENSIVE
    ):
        """
        Initialize query validator.

        Args:
            dictionary_service: Optional dictionary service for DB lookups
            default_mode: Default validation mode
        """
        self._dictionary_service = dictionary_service
        self._default_mode = default_mode
        self._estimation_cache: Dict[str, int] = {}

    def validate(
        self,
        query_data: Dict[str, Any],
        options: Optional[QueryValidationOptions] = None
    ) -> QueryValidationResult:
        """
        Validate query from dictionary format (QueryBuilderService style).

        Args:
            query_data: Query dictionary with filters, sort options, etc.
            options: Validation options (uses defaults if None)

        Returns:
            QueryValidationResult
        """
        options = options or QueryValidationOptions()
        errors: List[QueryValidationError] = []
        warnings: List[QueryValidationError] = []

        # Get valid sets based on mode
        valid_fields = self._get_valid_fields(options)
        valid_operators = self._get_valid_operators(options)
        valid_sort_fields = self._get_valid_sort_fields(options)

        # Validate filters
        filters = self._extract_filters(query_data)

        for i, filter_data in enumerate(filters):
            if not isinstance(filter_data, dict):
                errors.append(QueryValidationError(
                    message=f"Filter {i+1}: Invalid filter format",
                    field=f"filters[{i}]",
                    code="INVALID_FILTER_FORMAT"
                ))
                continue

            field = filter_data.get('field')
            operator = filter_data.get('operator')
            value = filter_data.get('value')

            # Validate field
            if options.validate_fields:
                if not field:
                    errors.append(QueryValidationError(
                        message=f"Filter {i+1}: Field cannot be empty",
                        field=f"filters[{i}].field",
                        code="EMPTY_FIELD"
                    ))
                elif field not in valid_fields:
                    if options.mode == QueryValidationMode.STRICT:
                        errors.append(QueryValidationError(
                            message=f"Filter {i+1}: Invalid field '{field}'",
                            field=f"filters[{i}].field",
                            code="INVALID_FIELD"
                        ))
                    else:
                        warnings.append(QueryValidationError(
                            message=f"Filter {i+1}: Unknown field '{field}'",
                            severity=ValidationSeverity.WARNING,
                            field=f"filters[{i}].field",
                            code="UNKNOWN_FIELD"
                        ))

            # Validate operator
            if options.validate_operators:
                if not operator:
                    errors.append(QueryValidationError(
                        message=f"Filter {i+1}: Operator cannot be empty",
                        field=f"filters[{i}].operator",
                        code="EMPTY_OPERATOR"
                    ))
                elif operator not in valid_operators:
                    errors.append(QueryValidationError(
                        message=f"Filter {i+1}: Invalid operator '{operator}'",
                        field=f"filters[{i}].operator",
                        code="INVALID_OPERATOR"
                    ))

            # Validate value
            if value is None or value == '':
                # Only error if we have a field and operator
                if field and operator:
                    warnings.append(QueryValidationError(
                        message=f"Filter {i+1}: Value is empty",
                        severity=ValidationSeverity.WARNING,
                        field=f"filters[{i}].value",
                        code="EMPTY_VALUE"
                    ))

        # Validate cross-references (if enabled)
        if options.validate_cross_references:
            cross_ref_errors = self._validate_cross_references(filters)
            errors.extend(cross_ref_errors)

        # Validate sort options
        sort_by = query_data.get('sort_by')
        if sort_by and sort_by not in valid_sort_fields:
            if options.mode == QueryValidationMode.STRICT:
                errors.append(QueryValidationError(
                    message=f"Invalid sort field: '{sort_by}'",
                    field="sort_by",
                    code="INVALID_SORT_FIELD"
                ))
            else:
                warnings.append(QueryValidationError(
                    message=f"Unknown sort field: '{sort_by}'",
                    severity=ValidationSeverity.WARNING,
                    field="sort_by",
                    code="UNKNOWN_SORT_FIELD"
                ))

        sort_order = query_data.get('sort_order', 'asc')
        if sort_order not in ['asc', 'desc']:
            errors.append(QueryValidationError(
                message=f"Invalid sort order: '{sort_order}' (must be 'asc' or 'desc')",
                field="sort_order",
                code="INVALID_SORT_ORDER"
            ))

        # Estimate performance
        estimated_count = 0
        performance_score = "unknown"

        if options.estimate_performance:
            if options.use_database and self._dictionary_service:
                estimated_count, performance_score = self._estimate_from_database(
                    query_data, filters
                )
            else:
                estimated_count, performance_score = self._estimate_simple(filters)

        return QueryValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            estimated_count=estimated_count,
            performance_score=performance_score,
            metadata={
                'filter_count': len(filters),
                'validation_mode': options.mode.name,
                'cross_references_validated': options.validate_cross_references
            }
        )

    def validate_workset_query(
        self,
        query: Any,  # WorksetQuery type
        options: Optional[QueryValidationOptions] = None
    ) -> QueryValidationResult:
        """
        Validate query from WorksetQuery object (WorksetService style).

        Args:
            query: WorksetQuery object
            options: Validation options (uses SIMPLE mode by default for worksets)

        Returns:
            QueryValidationResult
        """
        # Use SIMPLE mode by default for workset queries
        options = options or QueryValidationOptions(
            mode=QueryValidationMode.SIMPLE,
            use_database=False  # Workset queries don't use DB lookup
        )

        # Convert WorksetQuery to dict format
        query_data = self._workset_query_to_dict(query)

        return self.validate(query_data, options)

    def validate_simple(
        self,
        query_data: Dict[str, Any]
    ) -> QueryValidationResult:
        """
        Quick validation without database lookup (WorksetService style).

        Args:
            query_data: Query dictionary

        Returns:
            QueryValidationResult
        """
        options = QueryValidationOptions(
            mode=QueryValidationMode.SIMPLE,
            use_database=False,
            validate_cross_references=False
        )
        return self.validate(query_data, options)

    def validate_comprehensive(
        self,
        query_data: Dict[str, Any]
    ) -> QueryValidationResult:
        """
        Full validation with database lookup (QueryBuilderService style).

        Args:
            query_data: Query dictionary

        Returns:
            QueryValidationResult
        """
        options = QueryValidationOptions(
            mode=QueryValidationMode.COMPREHENSIVE,
            use_database=True,
            validate_cross_references=True
        )
        return self.validate(query_data, options)

    # =====================================================================
    # Helper Methods
    # =====================================================================

    def _get_valid_fields(self, options: QueryValidationOptions) -> Set[str]:
        """Get valid fields based on options."""
        if options.valid_fields:
            return options.valid_fields
        if options.mode == QueryValidationMode.SIMPLE:
            return self.SIMPLE_VALID_FIELDS
        return self.COMPREHENSIVE_VALID_FIELDS

    def _get_valid_operators(self, options: QueryValidationOptions) -> Set[str]:
        """Get valid operators based on options."""
        if options.valid_operators:
            return options.valid_operators
        if options.mode == QueryValidationMode.SIMPLE:
            return self.SIMPLE_VALID_OPERATORS
        return self.COMPREHENSIVE_VALID_OPERATORS

    def _get_valid_sort_fields(self, options: QueryValidationOptions) -> Set[str]:
        """Get valid sort fields based on options."""
        if options.valid_sort_fields:
            return options.valid_sort_fields
        if options.mode == QueryValidationMode.SIMPLE:
            return self.SIMPLE_SORT_FIELDS
        return self.COMPREHENSIVE_SORT_FIELDS

    def _extract_filters(self, query_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract filters from query data, parsing cross-references."""
        filters = query_data.get('filters', [])

        # Parse cross-references if present
        parsed_filters = []
        for f in filters:
            if isinstance(f, str):
                # Check for cross-reference syntax
                parsed_filters.extend(self._parse_cross_references(f))
            else:
                parsed_filters.append(f)

        return parsed_filters

    def _parse_cross_references(self, value: str) -> List[Dict[str, Any]]:
        """Parse cross-reference syntax from filter values."""
        matches = self.CROSS_REF_PATTERN.findall(value)
        filters = []
        for element_num, field_path in matches:
            filters.append({
                'cross_reference': True,
                'element': int(element_num),
                'field': field_path
            })
        return filters

    def _validate_cross_references(
        self,
        filters: List[Dict[str, Any]]
    ) -> List[QueryValidationError]:
        """Validate cross-references in filters."""
        errors = []

        for i, f in enumerate(filters):
            if not f.get('cross_reference'):
                continue

            element = f.get('element')
            field = f.get('field')

            if element is None or element < 0:
                errors.append(QueryValidationError(
                    message=f"Filter {i+1}: Invalid element number in cross-reference",
                    field=f"filters[{i}].element",
                    code="INVALID_CROSS_REF_ELEMENT"
                ))

            if not field or '.' not in field:
                errors.append(QueryValidationError(
                    message=f"Filter {i+1}: Cross-reference field must contain a path",
                    field=f"filters[{i}].field",
                    code="INVALID_CROSS_REF_FIELD"
                ))

        return errors

    def _workset_query_to_dict(self, query: Any) -> Dict[str, Any]:
        """Convert WorksetQuery object to dictionary format."""
        # Handle both WorksetQuery objects and dicts
        if hasattr(query, 'to_dict'):
            return query.to_dict()

        if isinstance(query, dict):
            return query

        # Extract fields from WorksetQuery-like object
        result = {}

        if hasattr(query, 'filters'):
            filters = []
            for f in query.filters:
                if hasattr(f, 'to_dict'):
                    filters.append(f.to_dict())
                elif hasattr(f, 'field') and hasattr(f, 'operator'):
                    filters.append({
                        'field': f.field,
                        'operator': f.operator,
                        'value': getattr(f, 'value', None)
                    })
            result['filters'] = filters

        if hasattr(query, 'sort_by'):
            result['sort_by'] = query.sort_by

        if hasattr(query, 'sort_order'):
            result['sort_order'] = query.sort_order

        if hasattr(query, 'limit'):
            result['limit'] = query.limit

        return result

    def _estimate_simple(
        self,
        filters: List[Dict[str, Any]]
    ) -> tuple[int, str]:
        """Simple estimation without database (WorksetService style)."""
        filter_count = len(filters)

        # Simple heuristic-based estimation
        estimated_count = 100

        if filter_count <= 3:
            performance_score = 'fast'
        elif filter_count <= 6:
            performance_score = 'medium'
        else:
            performance_score = 'slow'
            estimated_count = 50

        return estimated_count, performance_score

    def _estimate_from_database(
        self,
        query_data: Dict[str, Any],
        filters: List[Dict[str, Any]]
    ) -> tuple[int, str]:
        """Estimate from database (QueryBuilderService style)."""
        if not self._dictionary_service:
            return self._estimate_simple(filters)

        try:
            # Build search params (simplified)
            search_params = self._build_search_params(filters)

            # Query database for estimate
            entries, estimated_count = self._dictionary_service.search_entries(
                query=search_params.get('query', ''),
                fields=search_params.get('fields'),
                limit=1000,
                offset=0,
                advanced_filters=search_params.get('advanced_filters'),
            )

            # Calculate performance score
            filter_count = len(filters)
            if estimated_count > 5000 or filter_count > 5:
                performance_score = 'slow'
            elif estimated_count > 1000 or filter_count > 2:
                performance_score = 'medium'
            else:
                performance_score = 'fast'

            return estimated_count, performance_score

        except Exception:
            # Fall back to simple estimation
            return self._estimate_simple(filters)

    def _build_search_params(
        self,
        filters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build search params from filters (simplified from QueryBuilderService)."""
        params = {
            'query': '',
            'fields': [],
            'advanced_filters': {}
        }

        for f in filters:
            field = f.get('field')
            value = f.get('value')

            if not field or value is None:
                continue

            # Simple heuristic: if field is lexical_unit, add to query string
            if field in ['lexical_unit', 'headword']:
                if params['query']:
                    params['query'] += ' '
                params['query'] += str(value)
            else:
                # Add to advanced filters
                params['advanced_filters'][field] = value
                params['fields'].append(field)

        return params


# Convenience factory function
def get_query_validator(
    dictionary_service=None,
    mode: QueryValidationMode = QueryValidationMode.COMPREHENSIVE
) -> QueryValidator:
    """
    Get a QueryValidator instance.

    Args:
        dictionary_service: Optional dictionary service for DB lookups
        mode: Default validation mode

    Returns:
        QueryValidator instance
    """
    return QueryValidator(dictionary_service, mode)
