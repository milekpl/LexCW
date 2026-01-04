"""
Unit tests for BulkQueryService condition parsing and XQuery building.
"""

import pytest
from app.services.bulk_query_service import BulkQueryService, Condition


class TestConditionParsing:
    """Tests for condition parsing from JSON to Condition objects."""

    def test_parse_simple_equals_condition(self):
        """Test parsing a simple equals condition."""
        data = {
            "field": "lexical_unit.en",
            "op": "equals",
            "value": "test"
        }

        service = BulkQueryService(None)
        condition = service.parse_condition(data)

        assert condition.field == "lexical_unit.en"
        assert condition.op == "equals"
        assert condition.value == "test"

    def test_parse_is_empty_condition(self):
        """Test parsing an is_empty condition."""
        data = {
            "field": "senses.0.definition.en",
            "op": "is_empty"
        }

        service = BulkQueryService(None)
        condition = service.parse_condition(data)

        assert condition.field == "senses.0.definition.en"
        assert condition.op == "is_empty"
        assert condition.value is None

    def test_parse_contains_condition(self):
        """Test parsing a contains condition."""
        data = {
            "field": "grammatical_info.trait",
            "op": "contains",
            "value": "verb"
        }

        service = BulkQueryService(None)
        condition = service.parse_condition(data)

        assert condition.op == "contains"
        assert condition.value == "verb"

    def test_parse_invalid_operator(self):
        """Test that invalid operators raise ValueError."""
        data = {
            "field": "lexical_unit.en",
            "op": "invalid_op",
            "value": "test"
        }

        service = BulkQueryService(None)

        with pytest.raises(ValueError, match="Invalid operator"):
            service.parse_condition(data)

    def test_parse_missing_field(self):
        """Test that missing field raises ValueError."""
        data = {
            "op": "equals",
            "value": "test"
        }

        service = BulkQueryService(None)

        with pytest.raises(ValueError, match="must have a 'field'"):
            service.parse_condition(data)

    def test_parse_and_condition(self):
        """Test parsing an AND compound condition."""
        data = {
            "and": [
                {"field": "lexical_unit.en", "op": "is_empty"},
                {"field": "grammatical_info.trait", "op": "equals", "value": "noun"}
            ]
        }

        service = BulkQueryService(None)
        condition = service.parse_condition(data)

        assert condition.op == "and"
        assert len(condition.value) == 2

    def test_parse_or_condition(self):
        """Test parsing an OR compound condition."""
        data = {
            "or": [
                {"field": "lexical_unit.en", "op": "starts_with", "value": "a"},
                {"field": "lexical_unit.en", "op": "starts_with", "value": "b"}
            ]
        }

        service = BulkQueryService(None)
        condition = service.parse_condition(data)

        assert condition.op == "or"
        assert len(condition.value) == 2

    def test_parse_related_condition(self):
        """Test parsing a related entry condition."""
        data = {
            "related": {
                "type": "synonym",
                "condition": {
                    "field": "senses.0.definition.en",
                    "op": "is_not_empty"
                }
            }
        }

        service = BulkQueryService(None)
        condition = service.parse_condition(data)

        assert condition.op == "related"
        assert condition.related_type == "synonym"
        # The nested condition is stored in the condition field
        assert condition.condition is not None
        assert isinstance(condition.condition, Condition)
        assert condition.condition.field == "senses.0.definition.en"

    def test_parse_related_with_target_in_field(self):
        """Test parsing related condition with target_in_field."""
        data = {
            "related": {
                "type": "see_also",
                "target_in_field": "ftflags"
            },
            "condition": {
                "field": "lexical_unit.en",
                "op": "contains",
                "value": "important"
            }
        }

        service = BulkQueryService(None)
        condition = service.parse_condition(data)

        assert condition.op == "related"
        assert condition.related_type == "see_also"
        assert condition.target_in_field == "ftflags"


class TestConditionValidation:
    """Tests for condition validation."""

    def test_validate_valid_condition(self):
        """Test validation of valid condition."""
        data = {
            "field": "lexical_unit.en",
            "op": "equals",
            "value": "test"
        }

        service = BulkQueryService(None)
        is_valid, errors = service.validate_condition(data)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_condition(self):
        """Test validation of invalid condition."""
        data = {
            "op": "equals",
            "value": "test"
        }

        service = BulkQueryService(None)
        is_valid, errors = service.validate_condition(data)

        assert is_valid is False
        assert len(errors) > 0


class TestXQueryBuilding:
    """Tests for XQuery generation from conditions."""

    def test_build_xquery_equals(self):
        """Test building XQuery for equals operator."""
        condition = Condition(
            field="lexical_unit.en",
            op="equals",
            value="test"
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert "lexical-unit" in xquery
        assert "text() = $" in xquery
        assert "p1" in params
        assert params["p1"] == "test"

    def test_build_xquery_contains(self):
        """Test building XQuery for contains operator."""
        condition = Condition(
            field="senses.0.definition.en",
            op="contains",
            value="quick"
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert "contains(text()" in xquery
        assert "quick" in params.values()

    def test_build_xquery_is_empty(self):
        """Test building XQuery for is_empty operator."""
        condition = Condition(
            field="senses.0.gloss.en",
            op="is_empty"
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert "not(" in xquery
        assert "text()" in xquery

    def test_build_xquery_is_not_empty(self):
        """Test building XQuery for is_not_empty operator."""
        condition = Condition(
            field="senses.0.gloss.en",
            op="is_not_empty"
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert "text()" in xquery

    def test_build_xquery_gt(self):
        """Test building XQuery for gt (greater than) operator."""
        condition = Condition(
            field="senses.0.rank",
            op="gt",
            value=5
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert "number(text())" in xquery
        assert ">" in xquery

    def test_build_xquery_starts_with(self):
        """Test building XQuery for starts_with operator."""
        condition = Condition(
            field="lexical_unit.en",
            op="starts_with",
            value="un"
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert "starts-with(text()" in xquery

    def test_build_xquery_and_condition(self):
        """Test building XQuery for AND compound condition."""
        condition = Condition(
            field="",
            op="and",
            value=[
                Condition("lexical_unit.en", "is_empty", None),
                Condition("grammatical_info.trait", "equals", "noun")
            ]
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert " and " in xquery

    def test_build_xquery_or_condition(self):
        """Test building XQuery for OR compound condition."""
        condition = Condition(
            field="",
            op="or",
            value=[
                Condition("lexical_unit.en", "starts_with", "a"),
                Condition("lexical_unit.en", "starts_with", "b")
            ]
        )

        service = BulkQueryService(None)
        xquery, params = service.build_xquery(condition)

        assert " or " in xquery


class TestFieldPathMapping:
    """Tests for field path to XQuery element name mapping."""

    def test_lexical_unit_mapping(self):
        """Test lexical_unit field mapping."""
        service = BulkQueryService(None)
        xpath = service._xquery_field_path("lexical_unit")

        assert "lexical-unit" in xpath

    def test_grammatical_info_mapping(self):
        """Test grammatical_info field mapping."""
        service = BulkQueryService(None)
        xpath = service._xquery_field_path("grammatical_info")

        assert "grammatical-info" in xpath

    def test_senses_mapping(self):
        """Test senses field mapping."""
        service = BulkQueryService(None)
        xpath = service._xquery_field_path("senses")

        assert "sense" in xpath
