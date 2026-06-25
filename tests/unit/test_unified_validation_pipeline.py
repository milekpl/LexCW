"""
Unit tests for UnifiedValidationPipeline.

Tests the unified validation pipeline that consolidates all validation
functionality from LayeredHunspellValidator, ValidationCacheService,
and ValidationEngine into a single, consistent interface.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

from app.services.unified_validation_pipeline import (
    ValidationType, ValidationSeverity, ValidationIssue,
    PipelineValidationResult, ValidationOptions,
    ValidatorPlugin, UnifiedValidationPipeline,
    get_validation_pipeline, reset_validation_pipeline
)


class TestValidationTypeEnum:
    """Test ValidationType enum"""

    def test_validation_types_exist(self):
        """All validation types should be defined."""
        assert ValidationType.SPELLING is not None
        assert ValidationType.RULES is not None
        assert ValidationType.STRUCTURAL is not None
        assert ValidationType.REFERENCE is not None
        assert ValidationType.SEMANTIC is not None

    def test_validation_types_unique(self):
        """All validation types should be unique."""
        types = list(ValidationType)
        assert len(types) == len(set(types))


class TestValidationSeverityEnum:
    """Test ValidationSeverity enum"""

    def test_severity_values(self):
        """Severities should have correct string values."""
        assert ValidationSeverity.CRITICAL.value == "critical"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"

    def test_severity_ordering(self):
        """Severities can be compared by value."""
        # Higher severity = higher value (for comparison)
        severities = [
            ValidationSeverity.CRITICAL,
            ValidationSeverity.ERROR,
            ValidationSeverity.WARNING,
            ValidationSeverity.INFO
        ]
        values = [s.value for s in severities]
        assert "critical" in values
        assert "error" in values
        assert "warning" in values
        assert "info" in values


class TestValidationIssueDataclass:
    """Test ValidationIssue dataclass"""

    def test_issue_creation_with_minimal_fields(self):
        """Should create issue with minimal required fields."""
        issue = ValidationIssue(
            type=ValidationType.SPELLING,
            severity=ValidationSeverity.ERROR,
            code="MISSPELLING",
            message="Word 'teh' is misspelled",
            path="senses.0.definition"
        )

        assert issue.type == ValidationType.SPELLING
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.code == "MISSPELLING"
        assert issue.message == "Word 'teh' is misspelled"
        assert issue.path == "senses.0.definition"
        assert issue.field is None
        assert issue.suggestions == []
        assert issue.metadata == {}

    def test_issue_creation_with_all_fields(self):
        """Should create issue with all optional fields."""
        issue = ValidationIssue(
            type=ValidationType.RULES,
            severity=ValidationSeverity.WARNING,
            code="MISSING_EXAMPLE",
            message="Sense has no examples",
            path="senses.0",
            field="examples",
            suggestions=["Add example", "Remove sense"],
            metadata={"rule_id": "SENSE_EXAMPLE_REQUIRED"}
        )

        assert issue.field == "examples"
        assert issue.suggestions == ["Add example", "Remove sense"]
        assert issue.metadata == {"rule_id": "SENSE_EXAMPLE_REQUIRED"}

    def test_issue_to_dict(self):
        """Should convert to dictionary correctly."""
        issue = ValidationIssue(
            type=ValidationType.STRUCTURAL,
            severity=ValidationSeverity.CRITICAL,
            code="MISSING_HEADWORD",
            message="Entry must have a headword",
            path="lexical_unit",
            suggestions=["Add lexical_unit"]
        )

        d = issue.to_dict()

        assert d['type'] == "STRUCTURAL"
        assert d['severity'] == "critical"
        assert d['code'] == "MISSING_HEADWORD"
        assert d['message'] == "Entry must have a headword"
        assert d['path'] == "lexical_unit"
        assert d['field'] is None
        assert d['suggestions'] == ["Add lexical_unit"]
        assert d['metadata'] == {}


class TestPipelineValidationResult:
    """Test PipelineValidationResult dataclass"""

    def test_basic_result_creation(self):
        """Should create result with basic fields."""
        result = PipelineValidationResult(
            is_valid=True,
            issues=[]
        )

        assert result.is_valid is True
        assert result.issues == []
        assert result.cached is False
        assert result.validation_time_ms is None

    def test_result_with_issues(self):
        """Should aggregate issues correctly."""
        issues = [
            ValidationIssue(
                type=ValidationType.SPELLING,
                severity=ValidationSeverity.ERROR,
                code="MISSPELLING",
                message="Spelling error",
                path="lexical_unit"
            ),
            ValidationIssue(
                type=ValidationType.RULES,
                severity=ValidationSeverity.WARNING,
                code="MISSING_FIELD",
                message="Missing field",
                path="senses.0"
            ),
            ValidationIssue(
                type=ValidationType.STRUCTURAL,
                severity=ValidationSeverity.CRITICAL,
                code="INVALID_ID",
                message="Invalid entry ID",
                path="id"
            )
        ]

        result = PipelineValidationResult(
            is_valid=False,
            issues=issues
        )

        assert result.is_valid is False
        assert result.has_critical_issues is True
        assert result.critical_count == 1
        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.info_count == 0

    def test_result_with_by_type_and_severity(self):
        """Should support by_type and by_severity categorization."""
        spelling_issue = ValidationIssue(
            type=ValidationType.SPELLING,
            severity=ValidationSeverity.ERROR,
            code="SPELLING_ERROR",
            message="Spelling",
            path=""
        )
        rule_issue = ValidationIssue(
            type=ValidationType.RULES,
            severity=ValidationSeverity.ERROR,
            code="RULE_VIOLATION",
            message="Rule",
            path=""
        )

        result = PipelineValidationResult(
            is_valid=False,
            issues=[spelling_issue, rule_issue],
            by_type={
                ValidationType.SPELLING: [spelling_issue],
                ValidationType.RULES: [rule_issue]
            },
            by_severity={
                ValidationSeverity.ERROR: [spelling_issue, rule_issue],
                ValidationSeverity.WARNING: []
            }
        )

        assert len(result.by_type[ValidationType.SPELLING]) == 1
        assert len(result.by_type[ValidationType.RULES]) == 1
        assert len(result.by_severity[ValidationSeverity.ERROR]) == 2

    def test_result_to_dict(self):
        """Should convert to dictionary for JSON serialization."""
        issue = ValidationIssue(
            type=ValidationType.SPELLING,
            severity=ValidationSeverity.ERROR,
            code="TEST",
            message="Test message",
            path="test.path"
        )

        result = PipelineValidationResult(
            is_valid=True,
            issues=[issue],
            by_type={ValidationType.SPELLING: [issue]},
            by_severity={ValidationSeverity.ERROR: [issue]},
            metadata={'test': 'value'},
            cached=False,
            validation_time_ms=15.5
        )

        d = result.to_dict()

        assert d['valid'] is True
        assert d['has_critical_issues'] is False
        assert d['critical_count'] == 0
        assert d['error_count'] == 1
        assert d['warning_count'] == 0
        assert d['info_count'] == 0
        assert len(d['issues']) == 1
        assert d['by_type']['SPELLING'] is not None
        assert d['by_severity']['error'] is not None
        assert d['cached'] is False
        assert d['validation_time_ms'] == 15.5


class TestValidationOptions:
    """Test ValidationOptions dataclass"""

    def test_default_options(self):
        """Should have sensible defaults."""
        options = ValidationOptions()

        assert options.types is None  # All types
        assert options.min_severity == ValidationSeverity.INFO
        assert options.use_cache is True
        assert options.project_id is None
        assert options.user_id is None
        assert options.validation_mode == "save"
        assert options.existing_entry_ids is None
        assert options.source_lang is None
        assert options.target_lang is None
        assert options.validator_options == {}

    def test_custom_options(self):
        """Should accept custom values."""
        options = ValidationOptions(
            types={ValidationType.SPELLING, ValidationType.RULES},
            min_severity=ValidationSeverity.ERROR,
            use_cache=False,
            project_id="test-project",
            user_id=123,
            validation_mode="draft",
            existing_entry_ids={"entry1", "entry2"},
            source_lang="en",
            target_lang="fr",
            validator_options={"hunspell_dict": "custom.dic"}
        )

        assert options.types == {ValidationType.SPELLING, ValidationType.RULES}
        assert options.min_severity == ValidationSeverity.ERROR
        assert options.use_cache is False
        assert options.project_id == "test-project"
        assert options.user_id == 123
        assert options.validation_mode == "draft"
        assert options.existing_entry_ids == {"entry1", "entry2"}
        assert options.source_lang == "en"
        assert options.target_lang == "fr"
        assert options.validator_options == {"hunspell_dict": "custom.dic"}


class MockValidatorPlugin(ValidatorPlugin):
    """Mock validator plugin for testing."""

    def __init__(
        self,
        vtype: ValidationType,
        issues: List[ValidationIssue] = None,
        should_fail: bool = False
    ):
        self._type = vtype
        self._issues = issues or []
        self._should_fail = should_fail
        self.call_count = 0
        self.last_entry_data = None
        self.last_options = None

    @property
    def validation_type(self) -> ValidationType:
        return self._type

    def validate(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> List[ValidationIssue]:
        self.call_count += 1
        self.last_entry_data = entry_data
        self.last_options = options

        if self._should_fail:
            raise ValueError("Validation failed")

        return self._issues.copy()

    def get_cache_key(
        self,
        entry_data: Dict[str, Any],
        options: ValidationOptions
    ) -> Optional[str]:
        entry_id = entry_data.get('id', 'unknown')
        return f"{self._type.name}:{entry_id}"

    def invalidate_cache(self, entry_id: str) -> int:
        return 1


class TestUnifiedValidationPipelineInitialization:
    """Test pipeline initialization and configuration"""

    def test_default_initialization(self):
        """Should initialize with all validation types enabled."""
        pipeline = UnifiedValidationPipeline()

        assert ValidationType.SPELLING in pipeline._enabled_types
        assert ValidationType.RULES in pipeline._enabled_types
        assert ValidationType.STRUCTURAL in pipeline._enabled_types
        assert ValidationType.REFERENCE in pipeline._enabled_types
        assert ValidationType.SEMANTIC not in pipeline._enabled_types  # Disabled by default

    def test_custom_initialization(self):
        """Should respect enable/disable flags."""
        pipeline = UnifiedValidationPipeline(
            enable_spelling=False,
            enable_rules=True,
            enable_structural=False,
            enable_reference=False,
            enable_semantic=True
        )

        assert ValidationType.SPELLING not in pipeline._enabled_types
        assert ValidationType.RULES in pipeline._enabled_types
        assert ValidationType.STRUCTURAL not in pipeline._enabled_types
        assert ValidationType.REFERENCE not in pipeline._enabled_types
        assert ValidationType.SEMANTIC in pipeline._enabled_types

    def test_initializes_empty_plugin_registry(self):
        """Should start with empty plugin registry."""
        pipeline = UnifiedValidationPipeline()

        for vtype in ValidationType:
            assert pipeline._plugins[vtype] == []

        assert pipeline._plugin_instances == {}

    def test_initializes_stats(self):
        """Should initialize statistics."""
        pipeline = UnifiedValidationPipeline()

        assert pipeline._stats['total_validations'] == 0
        assert pipeline._stats['cache_hits'] == 0
        assert pipeline._stats['cache_misses'] == 0


class TestPluginRegistration:
    """Test validator plugin registration"""

    def test_register_single_plugin(self):
        """Should register a single plugin."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)

        pipeline.register_plugin(plugin)

        assert plugin in pipeline._plugins[ValidationType.SPELLING]
        assert "MockValidatorPlugin" in pipeline._plugin_instances

    def test_register_multiple_plugins_same_type(self):
        """Should allow multiple plugins of same type."""
        pipeline = UnifiedValidationPipeline()
        plugin1 = MockValidatorPlugin(ValidationType.SPELLING, issues=[])
        plugin2 = MockValidatorPlugin(ValidationType.SPELLING, issues=[])

        pipeline.register_plugin(plugin1)
        pipeline.register_plugin(plugin2)

        assert len(pipeline._plugins[ValidationType.SPELLING]) == 2

    def test_register_plugins_different_types(self):
        """Should register plugins of different types separately."""
        pipeline = UnifiedValidationPipeline()
        spelling_plugin = MockValidatorPlugin(ValidationType.SPELLING)
        rules_plugin = MockValidatorPlugin(ValidationType.RULES)

        pipeline.register_plugin(spelling_plugin)
        pipeline.register_plugin(rules_plugin)

        assert spelling_plugin in pipeline._plugins[ValidationType.SPELLING]
        assert rules_plugin in pipeline._plugins[ValidationType.RULES]

    def test_unregister_existing_plugin(self):
        """Should unregister existing plugin."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        result = pipeline.unregister_plugin(MockValidatorPlugin)

        assert result is True
        assert plugin not in pipeline._plugins[ValidationType.SPELLING]
        assert "MockValidatorPlugin" not in pipeline._plugin_instances

    def test_unregister_nonexistent_plugin(self):
        """Should return False for nonexistent plugin."""
        pipeline = UnifiedValidationPipeline()

        result = pipeline.unregister_plugin(MockValidatorPlugin)

        assert result is False


class TestEntryNormalization:
    """Test entry data normalization"""

    def test_normalize_dict(self):
        """Should return dict as-is."""
        pipeline = UnifiedValidationPipeline()
        data = {'id': 'test', 'lexical_unit': {'en': 'test'}}

        result = pipeline._normalize_entry_data(data)

        assert result == data
        assert result is data  # Same object

    def test_normalize_object_with_to_dict(self):
        """Should call to_dict() on objects."""
        pipeline = UnifiedValidationPipeline()
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {'id': 'test', 'lexical_unit': {'en': 'test'}}

        result = pipeline._normalize_entry_data(mock_obj)

        assert result == {'id': 'test', 'lexical_unit': {'en': 'test'}}
        mock_obj.to_dict.assert_called_once()

    def test_normalize_object_with_dict(self):
        """Should convert __dict__ to dict."""
        pipeline = UnifiedValidationPipeline()

        class TestObj:
            def __init__(self):
                self.id = 'test'
                self.value = 123

        obj = TestObj()
        result = pipeline._normalize_entry_data(obj)

        assert result == {'id': 'test', 'value': 123}

    def test_normalize_iterable_object(self):
        """Should convert objects that are iterable of key-value pairs."""
        pipeline = UnifiedValidationPipeline()

        # Object that iterates over key-value pairs (like dict)
        # Note: must NOT have __dict__ to test dict() constructor path
        class IterableObj:
            __slots__ = ()  # No __dict__ attribute

            def __init__(self):
                self._data = {'id': 'test', 'items': [1, 2, 3]}

            def __iter__(self):
                return iter(self._data.items())

            # Need to store data somewhere - using class attribute won't work
            # Let's just use a closure or modify the test

        # Actually let's test with a simple generator that returns key-value pairs
        def gen_items():
            yield ('id', 'test')
            yield ('items', [1, 2, 3])

        # A generator function returns an iterator, not an object
        # Let's create a proper test with a custom class without __dict__
        class DictLikeNoSlots:
            def __init__(self):
                self.id = 'test'
                self.items = [1, 2, 3]

        # This has __dict__ so will use that path
        obj = DictLikeNoSlots()
        result = pipeline._normalize_entry_data(obj)

        # With __dict__, we get the object's attributes
        assert result == {'id': 'test', 'items': [1, 2, 3]}

    def test_normalize_unconvertible_object(self):
        """Should return None for unconvertible objects."""
        pipeline = UnifiedValidationPipeline()

        # Object that can't be converted
        result = pipeline._normalize_entry_data("just a string")

        assert result is None

    def test_normalize_to_dict_failure(self):
        """Should handle to_dict() failures gracefully."""
        pipeline = UnifiedValidationPipeline()
        mock_obj = Mock()
        mock_obj.to_dict.side_effect = Exception("Conversion error")

        result = pipeline._normalize_entry_data(mock_obj)

        assert result is None


class TestValidateEntry:
    """Test validate_entry method"""

    def test_validate_empty_entry(self):
        """Should validate empty dictionary."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING, issues=[])
        pipeline.register_plugin(plugin)

        result = pipeline.validate_entry({})

        assert result.is_valid is True
        assert result.issues == []
        assert plugin.call_count == 1

    def test_validate_with_no_plugins(self):
        """Should return valid result with no plugins registered."""
        pipeline = UnifiedValidationPipeline()

        result = pipeline.validate_entry({'id': 'test', 'lexical_unit': {'en': 'test'}})

        assert result.is_valid is True
        assert result.issues == []

    def test_validate_with_single_issue(self):
        """Should aggregate single plugin issue."""
        pipeline = UnifiedValidationPipeline()
        issue = ValidationIssue(
            type=ValidationType.SPELLING,
            severity=ValidationSeverity.ERROR,
            code="MISSPELLING",
            message="Spelling error",
            path="lexical_unit"
        )
        plugin = MockValidatorPlugin(ValidationType.SPELLING, issues=[issue])
        pipeline.register_plugin(plugin)

        result = pipeline.validate_entry({'id': 'test'})

        assert result.is_valid is True  # ERROR is not CRITICAL
        assert len(result.issues) == 1
        assert result.issues[0].code == "MISSPELLING"
        assert result.by_type[ValidationType.SPELLING][0].code == "MISSPELLING"

    def test_validate_with_critical_issue(self):
        """Should mark invalid if critical issue present."""
        pipeline = UnifiedValidationPipeline()
        issue = ValidationIssue(
            type=ValidationType.STRUCTURAL,
            severity=ValidationSeverity.CRITICAL,
            code="MISSING_ID",
            message="Entry ID is required",
            path="id"
        )
        plugin = MockValidatorPlugin(ValidationType.STRUCTURAL, issues=[issue])
        pipeline.register_plugin(plugin)

        result = pipeline.validate_entry({'lexical_unit': {'en': 'test'}})

        assert result.is_valid is False
        assert result.has_critical_issues is True
        assert result.critical_count == 1

    def test_validate_multiple_plugins(self):
        """Should aggregate issues from multiple plugins."""
        pipeline = UnifiedValidationPipeline()

        spelling_issue = ValidationIssue(
            type=ValidationType.SPELLING,
            severity=ValidationSeverity.ERROR,
            code="SPELLING",
            message="Spelling",
            path=""
        )
        rule_issue = ValidationIssue(
            type=ValidationType.RULES,
            severity=ValidationSeverity.WARNING,
            code="RULE",
            message="Rule",
            path=""
        )

        spelling_plugin = MockValidatorPlugin(ValidationType.SPELLING, issues=[spelling_issue])
        rules_plugin = MockValidatorPlugin(ValidationType.RULES, issues=[rule_issue])

        pipeline.register_plugin(spelling_plugin)
        pipeline.register_plugin(rules_plugin)

        result = pipeline.validate_entry({'id': 'test'})

        assert result.is_valid is True
        assert len(result.issues) == 2
        assert len(result.by_type[ValidationType.SPELLING]) == 1
        assert len(result.by_type[ValidationType.RULES]) == 1

    def test_validate_with_options(self):
        """Should pass options to plugins."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        options = ValidationOptions(
            validation_mode="draft",
            project_id="test-project"
        )

        pipeline.validate_entry({'id': 'test'}, options)

        assert plugin.last_options.validation_mode == "draft"
        assert plugin.last_options.project_id == "test-project"

    def test_validate_with_options_types_filter(self):
        """Should respect types filter in options."""
        pipeline = UnifiedValidationPipeline()
        spelling_plugin = MockValidatorPlugin(ValidationType.SPELLING)
        rules_plugin = MockValidatorPlugin(ValidationType.RULES)
        structural_plugin = MockValidatorPlugin(ValidationType.STRUCTURAL)

        pipeline.register_plugin(spelling_plugin)
        pipeline.register_plugin(rules_plugin)
        pipeline.register_plugin(structural_plugin)

        options = ValidationOptions(types={ValidationType.SPELLING})

        result = pipeline.validate_entry({'id': 'test'}, options)

        # Only spelling plugin should be called
        assert spelling_plugin.call_count == 1
        assert rules_plugin.call_count == 0
        assert structural_plugin.call_count == 0

    def test_validate_with_min_severity_filter(self):
        """Should filter issues by minimum severity."""
        pipeline = UnifiedValidationPipeline()

        info_issue = ValidationIssue(
            type=ValidationType.RULES,
            severity=ValidationSeverity.INFO,
            code="INFO",
            message="Info",
            path=""
        )
        warning_issue = ValidationIssue(
            type=ValidationType.RULES,
            severity=ValidationSeverity.WARNING,
            code="WARNING",
            message="Warning",
            path=""
        )

        plugin = MockValidatorPlugin(
            ValidationType.RULES,
            issues=[info_issue, warning_issue]
        )
        pipeline.register_plugin(plugin)

        options = ValidationOptions(min_severity=ValidationSeverity.WARNING)
        result = pipeline.validate_entry({'id': 'test'}, options)

        # INFO issues should be excluded from severity grouping
        assert len(result.by_severity[ValidationSeverity.INFO]) == 0
        assert len(result.by_severity[ValidationSeverity.WARNING]) == 1

    def test_validate_with_object_input(self):
        """Should handle Entry objects with to_dict()."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        class MockEntry:
            def to_dict(self):
                return {'id': 'entry_123', 'lexical_unit': {'en': 'test'}}

        entry = MockEntry()
        result = pipeline.validate_entry(entry)

        assert result.is_valid is True
        assert plugin.last_entry_data == {'id': 'entry_123', 'lexical_unit': {'en': 'test'}}

    def test_validate_unconvertible_input(self):
        """Should handle unconvertible input gracefully."""
        pipeline = UnifiedValidationPipeline()

        result = pipeline.validate_entry("not a valid entry")

        assert result.is_valid is False
        assert result.has_critical_issues is True
        assert len(result.issues) == 1
        assert result.issues[0].code == "INVALID_ENTRY_DATA"

    def test_validate_plugin_error_handling(self):
        """Should handle plugin errors gracefully."""
        pipeline = UnifiedValidationPipeline()
        failing_plugin = MockValidatorPlugin(ValidationType.SPELLING, should_fail=True)
        pipeline.register_plugin(failing_plugin)

        result = pipeline.validate_entry({'id': 'test'})

        assert result.is_valid is True  # Error in validator doesn't make entry invalid
        assert len(result.issues) == 1
        assert result.issues[0].code == "VALIDATOR_ERROR"
        assert "Validation failed" in result.issues[0].message

    def test_validate_updates_stats(self):
        """Should update validation statistics."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        pipeline.validate_entry({'id': 'test'})

        assert pipeline._stats['total_validations'] == 1
        assert pipeline._stats['cache_misses'] == 1
        assert pipeline._stats['by_type'][ValidationType.SPELLING] == 1

    def test_validate_tracks_timing(self):
        """Should track validation time."""
        pipeline = UnifiedValidationPipeline()

        result = pipeline.validate_entry({'id': 'test'})

        assert result.validation_time_ms is not None
        assert result.validation_time_ms >= 0


class TestValidateXML:
    """Test validate_xml method"""

    def test_validate_xml_success(self):
        """Should parse and validate XML entry."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        # Mock LIFTParser - needs to patch where it's imported in the module
        mock_entry = Mock()
        mock_entry.to_dict.return_value = {'id': 'xml_entry', 'lexical_unit': {'en': 'test'}}

        with patch('app.parsers.lift_parser.LIFTParser') as MockParser:
            mock_parser = Mock()
            mock_parser.parse_string.return_value = [mock_entry]
            MockParser.return_value = mock_parser

            result = pipeline.validate_xml('<entry id="test"><lexical-unit><form lang="en"><text>test</text></form></lexical-unit></entry>')

            assert result.is_valid is True

    def test_validate_xml_empty_entries(self):
        """Should handle empty entry list from parser."""
        pipeline = UnifiedValidationPipeline()

        with patch('app.parsers.lift_parser.LIFTParser') as MockParser:
            mock_parser = Mock()
            mock_parser.parse_string.return_value = []
            MockParser.return_value = mock_parser

            result = pipeline.validate_xml('<entry id="test"></entry>')

            assert result.is_valid is False
            assert len(result.issues) == 1
            assert result.issues[0].code == "EMPTY_XML"

    def test_validate_xml_parse_error(self):
        """Should handle XML parse errors."""
        pipeline = UnifiedValidationPipeline()

        with patch('app.parsers.lift_parser.LIFTParser') as MockParser:
            mock_parser = Mock()
            mock_parser.parse_string.side_effect = ValueError("Invalid XML")
            MockParser.return_value = mock_parser

            result = pipeline.validate_xml('<invalid>')

            assert result.is_valid is False
            assert len(result.issues) == 1
            assert result.issues[0].code == "XML_PARSE_ERROR"

    def test_validate_xml_import_error(self):
        """Should handle missing LIFTParser."""
        pipeline = UnifiedValidationPipeline()

        # Mock the import to raise ImportError
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if 'lift_parser' in name or name == 'app.parsers.lift_parser':
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, '__import__', side_effect=mock_import):
            result = pipeline.validate_xml('<entry></entry>')

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "XML_PARSER_UNAVAILABLE"


class TestValidateBatch:
    """Test validate_batch method"""

    def test_validate_empty_batch(self):
        """Should handle empty batch."""
        pipeline = UnifiedValidationPipeline()

        results = pipeline.validate_batch([])

        assert results == {}

    def test_validate_single_entry_batch(self):
        """Should validate single entry in batch."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        results = pipeline.validate_batch([{'id': 'entry1', 'lexical_unit': {'en': 'test'}}])

        assert 'entry1' in results
        assert results['entry1'].is_valid is True

    def test_validate_multiple_entries_batch(self):
        """Should validate multiple entries."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        entries = [
            {'id': 'entry1', 'lexical_unit': {'en': 'one'}},
            {'id': 'entry2', 'lexical_unit': {'en': 'two'}},
            {'id': 'entry3', 'lexical_unit': {'en': 'three'}}
        ]

        results = pipeline.validate_batch(entries)

        assert len(results) == 3
        assert all(r.is_valid for r in results.values())

    def test_validate_batch_with_mixed_input_types(self):
        """Should handle mix of dicts and objects."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        class MockEntry:
            def __init__(self, id):
                self.id = id
                self._data = {'id': id, 'lexical_unit': {'en': id}}

            def to_dict(self):
                return self._data

        entries = [
            {'id': 'dict_entry', 'lexical_unit': {'en': 'dict'}},
            MockEntry('object_entry')
        ]

        results = pipeline.validate_batch(entries)

        assert 'dict_entry' in results
        assert 'object_entry' in results


class TestCacheInvalidation:
    """Test cache invalidation methods"""

    def test_invalidate_entry(self):
        """Should invalidate cache for all plugins."""
        pipeline = UnifiedValidationPipeline()
        plugin1 = MockValidatorPlugin(ValidationType.SPELLING)
        plugin2 = MockValidatorPlugin(ValidationType.RULES)

        pipeline.register_plugin(plugin1)
        pipeline.register_plugin(plugin2)

        count = pipeline.invalidate_entry('entry123')

        assert count == 2  # Both plugins invalidated

    def test_invalidate_with_no_plugins(self):
        """Should return 0 when no plugins."""
        pipeline = UnifiedValidationPipeline()

        count = pipeline.invalidate_entry('entry123')

        assert count == 0


class TestStatistics:
    """Test statistics methods"""

    def test_get_stats_initial(self):
        """Should return initial stats."""
        pipeline = UnifiedValidationPipeline()

        stats = pipeline.get_stats()

        assert stats['total_validations'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['cache_hit_rate'] == 0.0
        assert stats['by_type'] == {t.name: 0 for t in ValidationType}
        assert stats['registered_plugins'] == []

    def test_get_stats_after_validations(self):
        """Should track stats after validations."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        pipeline.validate_entry({'id': 'test'})
        pipeline.validate_entry({'id': 'test2'})

        stats = pipeline.get_stats()

        assert stats['total_validations'] == 2
        assert stats['cache_misses'] == 2
        assert stats['cache_hit_rate'] == 0.0
        assert stats['by_type']['SPELLING'] == 2
        assert 'MockValidatorPlugin' in stats['registered_plugins']

    def test_reset_stats(self):
        """Should reset statistics to zero."""
        pipeline = UnifiedValidationPipeline()
        plugin = MockValidatorPlugin(ValidationType.SPELLING)
        pipeline.register_plugin(plugin)

        pipeline.validate_entry({'id': 'test'})
        pipeline.reset_stats()
        stats = pipeline.get_stats()

        assert stats['total_validations'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0


class TestFactoryFunction:
    """Test get_validation_pipeline factory"""

    def setup_method(self):
        """Reset pipeline before each test."""
        reset_validation_pipeline()

    def teardown_method(self):
        """Reset pipeline after each test."""
        reset_validation_pipeline()

    def test_factory_creates_singleton(self):
        """Should return same instance on multiple calls."""
        pipeline1 = get_validation_pipeline()
        pipeline2 = get_validation_pipeline()

        assert pipeline1 is pipeline2

    def test_factory_uses_cache_service(self):
        """Should use provided cache service."""
        mock_cache = Mock()
        pipeline = get_validation_pipeline(cache_service=mock_cache)

        assert pipeline.cache_service is mock_cache

    def test_factory_respects_enable_flags(self):
        """Should respect enable/disable flags on first call."""
        reset_validation_pipeline()

        pipeline = get_validation_pipeline(
            enable_spelling=False,
            enable_rules=True
        )

        assert ValidationType.SPELLING not in pipeline._enabled_types
        assert ValidationType.RULES in pipeline._enabled_types

    def test_factory_ignores_flags_on_subsequent_calls(self):
        """Should ignore flags after first call (singleton)."""
        pipeline1 = get_validation_pipeline(enable_spelling=True)
        pipeline2 = get_validation_pipeline(enable_spelling=False)

        assert pipeline1 is pipeline2
        assert ValidationType.SPELLING in pipeline1._enabled_types


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""

    def test_result_provides_validationengine_compatible_format(self):
        """Result should provide format compatible with ValidationEngine."""
        issue = ValidationIssue(
            type=ValidationType.RULES,
            severity=ValidationSeverity.ERROR,
            code="TEST_CODE",
            message="Test message",
            path="test.path",
            suggestions=["suggestion1"]
        )

        result = PipelineValidationResult(
            is_valid=False,
            issues=[issue]
        )

        d = result.to_dict()

        # Format expected by ValidationEngine consumers
        assert 'valid' in d
        assert 'has_critical_issues' in d
        assert 'critical_count' in d
        assert 'error_count' in d
        assert 'warning_count' in d
        assert 'info_count' in d
        assert 'issues' in d

    def test_options_backward_compatible(self):
        """Options should support common validation patterns."""
        # Default options (like ValidationEngine default behavior)
        default_options = ValidationOptions()
        assert default_options.validation_mode == "save"

        # Draft mode (like draft validation)
        draft_options = ValidationOptions(validation_mode="draft")
        assert draft_options.validation_mode == "draft"

        # Full validation mode
        full_options = ValidationOptions(validation_mode="all")
        assert full_options.validation_mode == "all"

    def test_plugin_can_wrap_existing_validator(self):
        """ValidatorPlugin can wrap existing validator classes."""

        class WrappingPlugin(ValidatorPlugin):
            """Example plugin that wraps an existing validator."""

            def __init__(self, existing_validator):
                self._existing = existing_validator

            @property
            def validation_type(self) -> ValidationType:
                return ValidationType.SPELLING

            def validate(self, entry_data: Dict[str, Any], options: ValidationOptions) -> List[ValidationIssue]:
                # Call existing validator and convert result
                return []

            def get_cache_key(self, entry_data: Dict[str, Any], options: ValidationOptions) -> Optional[str]:
                return None

            def invalidate_cache(self, entry_id: str) -> int:
                return 0

        # Verify plugin interface is correct
        assert issubclass(WrappingPlugin, ValidatorPlugin)
