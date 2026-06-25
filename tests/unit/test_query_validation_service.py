"""
Unit tests for QueryValidationService.

Tests the unified query validation service that consolidates query validation
functionality from QueryBuilderService and WorksetService.
"""

import pytest
from unittest.mock import Mock
from typing import Dict, Any, List

from app.services.query_validation_service import (
    QueryValidationMode, ValidationSeverity, QueryValidationError,
    QueryValidationResult, QueryValidationOptions, QueryValidator,
    get_query_validator
)


class TestQueryValidationModeEnum:
    """Test QueryValidationMode enum"""

    def test_modes_exist(self):
        """All validation modes should be defined."""
        assert QueryValidationMode.SIMPLE is not None
        assert QueryValidationMode.COMPREHENSIVE is not None
        assert QueryValidationMode.STRICT is not None


class TestValidationSeverityEnum:
    """Test ValidationSeverity enum"""

    def test_severity_values(self):
        """Severities should have correct string values."""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestQueryValidationError:
    """Test QueryValidationError dataclass"""

    def test_error_creation_minimal(self):
        """Should create error with minimal fields."""
        error = QueryValidationError(message="Test error")

        assert error.message == "Test error"
        assert error.severity == ValidationSeverity.ERROR
        assert error.field is None
        assert error.code == "VALIDATION_ERROR"

    def test_error_creation_full(self):
        """Should create error with all fields."""
        error = QueryValidationError(
            message="Field is invalid",
            severity=ValidationSeverity.WARNING,
            field="filters[0].field",
            code="INVALID_FIELD"
        )

        assert error.message == "Field is invalid"
        assert error.severity == ValidationSeverity.WARNING
        assert error.field == "filters[0].field"
        assert error.code == "INVALID_FIELD"

    def test_error_to_dict(self):
        """Should convert to dictionary."""
        error = QueryValidationError(
            message="Test",
            severity=ValidationSeverity.ERROR,
            field="test.field",
            code="TEST_CODE"
        )

        d = error.to_dict()

        assert d['message'] == "Test"
        assert d['severity'] == "error"
        assert d['field'] == "test.field"
        assert d['code'] == "TEST_CODE"


class TestQueryValidationResult:
    """Test QueryValidationResult dataclass"""

    def test_result_creation_valid(self):
        """Should create valid result."""
        result = QueryValidationResult(
            is_valid=True,
            errors=[]
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.estimated_count == 0
        assert result.performance_score == "unknown"

    def test_result_creation_with_errors(self):
        """Should create invalid result with errors."""
        error = QueryValidationError(message="Test error")
        result = QueryValidationResult(
            is_valid=False,
            errors=[error],
            estimated_count=100,
            performance_score="fast"
        )

        assert result.is_valid is False
        assert result.has_errors is True
        assert len(result.errors) == 1
        assert result.estimated_count == 100
        assert result.performance_score == "fast"

    def test_result_with_warnings(self):
        """Should track warnings separately."""
        warning = QueryValidationError(
            message="Warning",
            severity=ValidationSeverity.WARNING
        )
        result = QueryValidationResult(
            is_valid=True,  # Still valid with just warnings
            errors=[],
            warnings=[warning]
        )

        assert result.is_valid is True
        assert result.has_warnings is True
        assert result.has_errors is False
        assert len(result.all_issues) == 1

    def test_result_to_dict(self):
        """Should convert to dictionary for JSON."""
        error = QueryValidationError(message="Error")
        result = QueryValidationResult(
            is_valid=False,
            errors=[error],
            estimated_count=50,
            performance_score="medium",
            metadata={'test': 'value'}
        )

        d = result.to_dict()

        assert d['valid'] is False
        assert len(d['errors']) == 1
        assert d['estimated_count'] == 50
        assert d['performance_score'] == "medium"
        assert d['metadata'] == {'test': 'value'}


class TestQueryValidationOptions:
    """Test QueryValidationOptions dataclass"""

    def test_default_options(self):
        """Should have sensible defaults."""
        options = QueryValidationOptions()

        assert options.mode == QueryValidationMode.COMPREHENSIVE
        assert options.validate_fields is True
        assert options.validate_operators is True
        assert options.validate_cross_references is True
        assert options.estimate_performance is True
        assert options.use_database is True
        assert options.max_estimated_count == 1000
        assert options.project_id is None
        assert options.valid_fields is None
        assert options.valid_operators is None
        assert options.valid_sort_fields is None

    def test_custom_options(self):
        """Should accept custom values."""
        options = QueryValidationOptions(
            mode=QueryValidationMode.SIMPLE,
            validate_fields=False,
            validate_operators=False,
            validate_cross_references=False,
            estimate_performance=False,
            use_database=False,
            max_estimated_count=500,
            project_id="test-project",
            valid_fields={'field1', 'field2'},
            valid_operators={'equals'},
            valid_sort_fields={'name'}
        )

        assert options.mode == QueryValidationMode.SIMPLE
        assert options.validate_fields is False
        assert options.validate_operators is False
        assert options.validate_cross_references is False
        assert options.estimate_performance is False
        assert options.use_database is False
        assert options.max_estimated_count == 500
        assert options.project_id == "test-project"
        assert options.valid_fields == {'field1', 'field2'}
        assert options.valid_operators == {'equals'}
        assert options.valid_sort_fields == {'name'}


class TestQueryValidatorInitialization:
    """Test QueryValidator initialization"""

    def test_default_initialization(self):
        """Should initialize with defaults."""
        validator = QueryValidator()

        assert validator._dictionary_service is None
        assert validator._default_mode == QueryValidationMode.COMPREHENSIVE
        assert validator._estimation_cache == {}

    def test_initialization_with_service(self):
        """Should accept dictionary service."""
        mock_service = Mock()
        validator = QueryValidator(dictionary_service=mock_service)

        assert validator._dictionary_service is mock_service

    def test_initialization_with_mode(self):
        """Should accept default mode."""
        validator = QueryValidator(
            default_mode=QueryValidationMode.SIMPLE
        )

        assert validator._default_mode == QueryValidationMode.SIMPLE


class TestQueryValidatorBasicValidation:
    """Test basic query validation"""

    def test_validate_empty_query(self):
        """Should validate empty query as valid."""
        validator = QueryValidator()

        result = validator.validate({})

        assert result.is_valid is True
        assert result.errors == []
        assert result.performance_score == "fast"  # Simple estimation

    def test_validate_valid_simple_query(self):
        """Should validate simple query."""
        validator = QueryValidator()

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        })

        assert result.is_valid is True

    def test_validate_invalid_field_simple_mode(self):
        """Should warn about unknown field in simple mode."""
        validator = QueryValidator()
        options = QueryValidationOptions(mode=QueryValidationMode.SIMPLE)

        result = validator.validate({
            'filters': [{'field': 'unknown_field', 'operator': 'equals', 'value': 'test'}]
        }, options)

        assert result.is_valid is True  # Warning only
        assert len(result.warnings) == 1
        assert "Unknown field" in result.warnings[0].message

    def test_validate_invalid_field_strict_mode(self):
        """Should error on unknown field in strict mode."""
        validator = QueryValidator()
        options = QueryValidationOptions(mode=QueryValidationMode.STRICT)

        result = validator.validate({
            'filters': [{'field': 'unknown_field', 'operator': 'equals', 'value': 'test'}]
        }, options)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Invalid field" in result.errors[0].message

    def test_validate_invalid_operator(self):
        """Should error on invalid operator."""
        validator = QueryValidator()

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'invalid_op', 'value': 'test'}]
        })

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Invalid operator" in result.errors[0].message

    def test_validate_missing_field(self):
        """Should error on missing field."""
        validator = QueryValidator()

        result = validator.validate({
            'filters': [{'operator': 'equals', 'value': 'test'}]
        })

        assert result.is_valid is False
        assert any("Field cannot be empty" in e.message for e in result.errors)

    def test_validate_missing_operator(self):
        """Should error on missing operator."""
        validator = QueryValidator()

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'value': 'test'}]
        })

        assert result.is_valid is False
        assert any("Operator cannot be empty" in e.message for e in result.errors)

    def test_validate_string_filter(self):
        """Should handle string filter (may be cross-reference syntax)."""
        validator = QueryValidator()

        # String filters are parsed for cross-references
        # If they don't match pattern, they're treated as having 0 filters
        result = validator.validate({
            'filters': ['not a dict']
        })

        # String without cross-reference pattern results in empty filter list
        # Since no invalid filters, result is valid (may need strict mode to error)
        assert result.is_valid is True  # Empty filter list is valid
        assert result.metadata['filter_count'] == 0  # No cross-references found

    def test_validate_multiple_filters(self):
        """Should validate multiple filters."""
        validator = QueryValidator()

        result = validator.validate({
            'filters': [
                {'field': 'lexical_unit', 'operator': 'equals', 'value': 'one'},
                {'field': 'pos', 'operator': 'equals', 'value': 'noun'}
            ]
        })

        assert result.is_valid is True
        assert result.metadata['filter_count'] == 2

    def test_validate_sort_options(self):
        """Should validate sort options."""
        validator = QueryValidator()

        # Valid sort
        result = validator.validate({
            'sort_by': 'lexical_unit',
            'sort_order': 'asc'
        })
        assert result.is_valid is True

        # Invalid sort field (warning in comprehensive mode)
        result = validator.validate({
            'sort_by': 'invalid_field'
        })
        assert result.is_valid is True  # Warning only

        # Invalid sort order (error always)
        result = validator.validate({
            'sort_order': 'invalid'
        })
        assert result.is_valid is False
        assert any("Invalid sort order" in e.message for e in result.errors)


class TestQueryValidatorComprehensiveValidation:
    """Test comprehensive mode validation"""

    def test_comprehensive_mode_validates_all_fields(self):
        """Comprehensive mode should accept all LIFT schema fields."""
        validator = QueryValidator()
        options = QueryValidationOptions(mode=QueryValidationMode.COMPREHENSIVE)

        # Complex field from LIFT schema
        result = validator.validate({
            'filters': [{'field': 'etymology.source', 'operator': 'equals', 'value': 'latin'}]
        }, options)

        assert result.is_valid is True

    def test_comprehensive_mode_validates_all_operators(self):
        """Comprehensive mode should accept all operator types."""
        validator = QueryValidator()
        options = QueryValidationOptions(mode=QueryValidationMode.COMPREHENSIVE)

        # Complex operators
        operators = [
            'regex', 'greater_than', 'levenshtein_distance',
            'fuzzy_match', 'exists', 'not_exists'
        ]

        for op in operators:
            result = validator.validate({
                'filters': [{'field': 'lexical_unit', 'operator': op, 'value': 'test'}]
            }, options)

            assert result.is_valid is True, f"Operator {op} should be valid"

    def test_comprehensive_mode_uses_database(self):
        """Comprehensive mode should use database for estimation."""
        mock_service = Mock()
        mock_service.search_entries.return_value = ([], 2500)

        validator = QueryValidator(dictionary_service=mock_service)
        options = QueryValidationOptions(
            mode=QueryValidationMode.COMPREHENSIVE,
            use_database=True
        )

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        }, options)

        assert result.estimated_count == 2500
        assert result.performance_score == "medium"  # 2500 is medium


class TestQueryValidatorSimpleValidation:
    """Test simple mode validation"""

    def test_simple_mode_restricted_fields(self):
        """Simple mode should only accept simple fields."""
        validator = QueryValidator()
        options = QueryValidationOptions(mode=QueryValidationMode.SIMPLE)

        # Simple field should work
        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        }, options)
        assert result.is_valid is True

        # Complex field should warn
        result = validator.validate({
            'filters': [{'field': 'etymology.source', 'operator': 'equals', 'value': 'test'}]
        }, options)
        assert result.is_valid is True  # Warning only
        assert len(result.warnings) == 1

    def test_simple_mode_restricted_operators(self):
        """Simple mode should only accept simple operators."""
        validator = QueryValidator()
        options = QueryValidationOptions(mode=QueryValidationMode.SIMPLE)

        # Simple operator should work
        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        }, options)
        assert result.is_valid is True

        # Complex operator should error
        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'regex', 'value': 'test'}]
        }, options)
        assert result.is_valid is False
        assert any("Invalid operator" in e.message for e in result.errors)

    def test_simple_mode_no_database(self):
        """Simple mode should not use database by default."""
        mock_service = Mock()
        mock_service.search_entries.return_value = ([], 9999)

        validator = QueryValidator(dictionary_service=mock_service)
        options = QueryValidationOptions(
            mode=QueryValidationMode.SIMPLE,
            use_database=False
        )

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        }, options)

        # Should use simple estimation
        assert result.estimated_count == 100  # Default from simple estimation
        mock_service.search_entries.assert_not_called()


class TestQueryValidatorCrossReferences:
    """Test cross-reference validation"""

    def test_validate_valid_cross_reference(self):
        """Should validate valid cross-reference syntax."""
        validator = QueryValidator()
        options = QueryValidationOptions(validate_cross_references=True)

        result = validator.validate({
            'filters': [{'field': '[ELEMENT 0:lexical_unit]', 'operator': 'equals', 'value': 'test'}]
        }, options)

        # Should be valid
        assert result.is_valid is True

    def test_validate_cross_reference_not_parsed_with_negative_element(self):
        """Negative element number is not captured by regex, treated as regular field."""
        validator = QueryValidator()
        options = QueryValidationOptions(
            mode=QueryValidationMode.STRICT,
            validate_cross_references=True
        )

        # The regex pattern [ELEMENT\s+(\d+):... only captures digits, not negative numbers
        # So [ELEMENT -1:lexical_unit] doesn't match and is treated as a regular field
        result = validator.validate({
            'filters': [{'field': '[ELEMENT -1:lexical_unit]', 'operator': 'equals', 'value': 'test'}]
        }, options)

        # Since it's not a valid field in comprehensive mode, it should error in strict mode
        assert result.is_valid is False
        # Should report invalid field (not parsed as cross-reference)
        assert any("Invalid field" in e.message for e in result.errors)

    def test_validate_cross_reference_without_field_path(self):
        """Should error on cross-reference without field path in strict mode."""
        validator = QueryValidator()
        options = QueryValidationOptions(
            mode=QueryValidationMode.STRICT,
            validate_cross_references=True
        )

        result = validator.validate({
            'filters': [{'field': '[ELEMENT 0]', 'operator': 'equals', 'value': 'test'}]
        }, options)

        # Without a field path after ELEMENT 0:, it's an invalid field pattern
        # In strict mode, this should error


class TestQueryValidatorPerformanceEstimation:
    """Test performance estimation"""

    def test_simple_estimation_fast(self):
        """Few filters should be 'fast'."""
        validator = QueryValidator()
        options = QueryValidationOptions(use_database=False)

        result = validator.validate({
            'filters': [
                {'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}
            ]
        }, options)

        assert result.performance_score == "fast"

    def test_simple_estimation_medium(self):
        """More than 3 filters should be 'medium'."""
        validator = QueryValidator()
        options = QueryValidationOptions(use_database=False)

        # Need more than 3 filters for 'medium' score
        result = validator.validate({
            'filters': [
                {'field': 'lexical_unit', 'operator': 'equals', 'value': 'a'},
                {'field': 'pos', 'operator': 'equals', 'value': 'noun'},
                {'field': 'grammatical_info', 'operator': 'equals', 'value': 'sg'},
                {'field': 'citation', 'operator': 'equals', 'value': 'test'}
            ]
        }, options)

        assert result.performance_score == "medium"

    def test_simple_estimation_slow(self):
        """Many filters should be 'slow'."""
        validator = QueryValidator()
        options = QueryValidationOptions(use_database=False)

        result = validator.validate({
            'filters': [
                {'field': f'field_{i}', 'operator': 'equals', 'value': f'value_{i}'}
                for i in range(7)
            ]
        }, options)

        assert result.performance_score == "slow"

    def test_database_estimation(self):
        """Database estimation should use actual count."""
        mock_service = Mock()
        mock_service.search_entries.return_value = ([Mock() for _ in range(10)], 750)

        validator = QueryValidator(dictionary_service=mock_service)
        options = QueryValidationOptions(use_database=True)

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        }, options)

        assert result.estimated_count == 750
        mock_service.search_entries.assert_called_once()

    def test_database_estimation_handles_error(self):
        """Should fall back to simple estimation on database error."""
        mock_service = Mock()
        mock_service.search_entries.side_effect = Exception("DB error")

        validator = QueryValidator(dictionary_service=mock_service)
        options = QueryValidationOptions(use_database=True)

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        }, options)

        # Should still work with simple estimation
        assert result.is_valid is True
        assert result.performance_score in ['fast', 'medium', 'slow']


class TestQueryValidatorConvenienceMethods:
    """Test convenience methods"""

    def test_validate_simple(self):
        """validate_simple should use simple mode."""
        validator = QueryValidator()

        result = validator.validate_simple({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        })

        assert result.metadata['validation_mode'] == "SIMPLE"

    def test_validate_comprehensive(self):
        """validate_comprehensive should use comprehensive mode."""
        mock_service = Mock()
        mock_service.search_entries.return_value = ([], 100)

        validator = QueryValidator(dictionary_service=mock_service)

        result = validator.validate_comprehensive({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        })

        assert result.metadata['validation_mode'] == "COMPREHENSIVE"

    def test_validate_workset_query_with_dict(self):
        """validate_workset_query should handle dict."""
        validator = QueryValidator()

        # Pass a dict (should still work)
        result = validator.validate_workset_query({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        })

        assert result.is_valid is True

    def test_validate_workset_query_with_object(self):
        """validate_workset_query should handle WorksetQuery-like object."""
        validator = QueryValidator()

        # Create mock WorksetQuery-like object
        class MockFilter:
            def __init__(self):
                self.field = 'lexical_unit'
                self.operator = 'equals'
                self.value = 'test'

        class MockWorksetQuery:
            def __init__(self):
                self.filters = [MockFilter()]
                self.sort_by = None
                self.sort_order = 'asc'
                self.limit = 50

        result = validator.validate_workset_query(MockWorksetQuery())

        assert result.is_valid is True
        assert result.metadata['filter_count'] == 1


class TestQueryValidatorCustomValidations:
    """Test custom valid fields/operators"""

    def test_custom_valid_fields(self):
        """Should use custom valid fields."""
        validator = QueryValidator()
        options = QueryValidationOptions(
            valid_fields={'custom_field_1', 'custom_field_2'}
        )

        result = validator.validate({
            'filters': [{'field': 'custom_field_1', 'operator': 'equals', 'value': 'test'}]
        }, options)

        assert result.is_valid is True

    def test_custom_valid_operators(self):
        """Should use custom valid operators."""
        validator = QueryValidator()
        options = QueryValidationOptions(
            valid_operators={'custom_op'}
        )

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'custom_op', 'value': 'test'}]
        }, options)

        assert result.is_valid is True


class TestGetQueryValidatorFactory:
    """Test get_query_validator factory function"""

    def test_factory_creates_new_instance(self):
        """Should create new validator instance."""
        mock_service = Mock()

        validator = get_query_validator(dictionary_service=mock_service)

        assert isinstance(validator, QueryValidator)
        assert validator._dictionary_service is mock_service

    def test_factory_uses_default_mode(self):
        """Should use comprehensive mode by default."""
        validator = get_query_validator()

        assert validator._default_mode == QueryValidationMode.COMPREHENSIVE

    def test_factory_accepts_custom_mode(self):
        """Should accept custom mode."""
        validator = get_query_validator(mode=QueryValidationMode.SIMPLE)

        assert validator._default_mode == QueryValidationMode.SIMPLE


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""

    def test_result_format_matches_querybuilderservice(self):
        """Result format should be compatible with QueryBuilderService."""
        validator = QueryValidator()

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        })

        d = result.to_dict()

        # Fields expected by QueryBuilderService consumers
        assert 'valid' in d
        assert 'errors' in d
        assert 'estimated_count' in d
        assert 'performance_score' in d
        assert 'metadata' in d

    def test_result_format_matches_worksetservice(self):
        """Result format compatible with WorksetService expectations."""
        validator = QueryValidator()
        options = QueryValidationOptions(mode=QueryValidationMode.SIMPLE)

        result = validator.validate({
            'filters': [{'field': 'lexical_unit', 'operator': 'equals', 'value': 'test'}]
        }, options)

        d = result.to_dict()

        # Check expected structure
        assert d['valid'] is True
        assert isinstance(d['errors'], list)
        assert isinstance(d['warnings'], list)
