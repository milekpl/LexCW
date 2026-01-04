"""
Unit tests for BulkActionService action parsing and validation.
"""

import pytest
from app.services.bulk_action_service import BulkAction, BulkActionService, ActionType


class TestBulkActionParsing:
    """Tests for action parsing from JSON to BulkAction objects."""

    def test_parse_set_action(self):
        """Test parsing a set action."""
        data = {
            "action": "set",
            "field": "grammatical_info.trait",
            "value": "noun"
        }

        action = BulkAction.from_dict(data)

        assert action.action == "set"
        assert action.field == "grammatical_info.trait"
        assert action.value == "noun"

    def test_parse_clear_action(self):
        """Test parsing a clear action."""
        data = {
            "action": "clear",
            "field": "senses.0.definition.en"
        }

        action = BulkAction.from_dict(data)

        assert action.action == "clear"
        assert action.field == "senses.0.definition.en"

    def test_parse_append_action(self):
        """Test parsing an append action."""
        data = {
            "action": "append",
            "field": "lexical_unit.en",
            "value": " (archaic)"
        }

        action = BulkAction.from_dict(data)

        assert action.action == "append"
        assert action.value == " (archaic)"

    def test_parse_prepend_action(self):
        """Test parsing a prepend action."""
        data = {
            "action": "prepend",
            "field": "lexical_unit.en",
            "value": "["
        }

        action = BulkAction.from_dict(data)

        assert action.action == "prepend"
        assert action.value == "["

    def test_parse_add_relation_action(self):
        """Test parsing an add_relation action."""
        data = {
            "action": "add_relation",
            "relation_type": "synonym",
            "target_entry_id": "entry-123"
        }

        action = BulkAction.from_dict(data)

        assert action.action == "add_relation"
        assert action.relation_type == "synonym"
        assert action.target_entry_id == "entry-123"

    def test_parse_remove_relation_action(self):
        """Test parsing a remove_relation action."""
        data = {
            "action": "remove_relation",
            "relation_type": "antonym",
            "target_entry_id": "entry-456"
        }

        action = BulkAction.from_dict(data)

        assert action.action == "remove_relation"
        assert action.relation_type == "antonym"

    def test_parse_copy_from_related_action(self):
        """Test parsing a copy_from_related action."""
        data = {
            "action": "copy_from_related",
            "from_field": "senses.0.definition.en",
            "to_field": "senses.0.gloss.en",
            "relation_type": "synonym"
        }

        action = BulkAction.from_dict(data)

        assert action.action == "copy_from_related"
        assert action.from_field == "senses.0.definition.en"
        assert action.to_field == "senses.0.gloss.en"
        assert action.relation_type == "synonym"

    def test_parse_copy_with_target_in_field(self):
        """Test parsing copy_from_related with target_in_field."""
        data = {
            "action": "copy_from_related",
            "from_field": "lexical_unit.en",
            "to_field": "examples.0.text",
            "target_in_field": "ftflags"
        }

        action = BulkAction.from_dict(data)

        assert action.target_in_field == "ftflags"

    def test_parse_pipeline_action(self):
        """Test parsing a pipeline action with nested steps."""
        data = {
            "action": "pipeline",
            "steps": [
                {"action": "set", "field": "grammatical_info.trait", "value": "verb"},
                {"action": "add_relation", "relation_type": "see_also", "target_entry_id": "${parent.id}"}
            ]
        }

        action = BulkAction.from_dict(data)

        assert action.action == "pipeline"
        assert len(action.steps) == 2
        assert action.steps[0].action == "set"
        assert action.steps[1].action == "add_relation"

    def test_parse_action_with_ranges(self):
        """Test parsing action with ranges validation."""
        data = {
            "action": "set",
            "field": "grammatical_info.trait",
            "value": "noun",
            "ranges": {
                "allowed_values": ["noun", "verb", "adjective"]
            }
        }

        action = BulkAction.from_dict(data)

        assert action.ranges is not None
        assert "noun" in action.ranges["allowed_values"]


class TestActionValidation:
    """Tests for action validation."""

    def test_validate_set_action(self):
        """Test validation of valid set action."""
        action = BulkAction(
            action="set",
            field="grammatical_info.trait",
            value="noun"
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_set_action_missing_field(self):
        """Test validation fails when set action is missing field."""
        action = BulkAction(
            action="set",
            value="noun"
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is False
        assert any("requires a field" in e for e in errors)

    def test_validate_clear_action(self):
        """Test validation of valid clear action."""
        action = BulkAction(
            action="clear",
            field="senses.0.definition.en"
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is True

    def test_validate_add_relation_missing_type(self):
        """Test validation fails when add_relation is missing relation_type."""
        action = BulkAction(
            action="add_relation",
            target_entry_id="entry-123"
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is False
        assert any("requires relation_type" in e for e in errors)

    def test_validate_copy_from_related_missing_fields(self):
        """Test validation fails when copy_from_related is missing from_field."""
        action = BulkAction(
            action="copy_from_related",
            to_field="senses.0.definition.en"
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is False

    def test_validate_invalid_action_type(self):
        """Test validation fails for unknown action type."""
        action = BulkAction(
            action="invalid_action",
            field="lexical_unit.en"
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is False
        assert any("Invalid action type" in e for e in errors)


class TestActionRangesValidation:
    """Tests for ranges-based validation."""

    def test_validate_against_allowed_values(self):
        """Test validation respects allowed values from ranges."""
        action = BulkAction(
            action="set",
            field="grammatical_info.trait",
            value="adverb",  # Not in allowed list
            ranges={
                "allowed_values": ["noun", "verb", "adjective"]
            }
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is False
        assert any("not in allowed values" in e for e in errors)

    def test_validate_against_allowed_relation_types(self):
        """Test validation respects allowed relation types from ranges."""
        action = BulkAction(
            action="add_relation",
            relation_type="cousin",  # Not in allowed list
            target_entry_id="entry-123",
            ranges={
                "allowed_types": ["synonym", "antonym", "see_also"]
            }
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is False
        assert any("not in allowed types" in e for e in errors)

    def test_validate_passes_with_valid_ranges(self):
        """Test validation passes when value is in allowed ranges."""
        action = BulkAction(
            action="set",
            field="grammatical_info.trait",
            value="verb",
            ranges={
                "allowed_values": ["noun", "verb", "adjective"]
            }
        )

        service = BulkActionService(None)
        is_valid, errors = service.validate_action(action)

        assert is_valid is True
