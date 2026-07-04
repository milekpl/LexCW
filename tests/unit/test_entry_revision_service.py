"""
Tests for app.services.entry_revision_service — currently zero coverage.

Covers:
- Pure helpers: _match_key, _truncate, _short, _summarize, _mk_change, _getmk,
  _item_label, _field_group
- Diff engine: _diff, _diff_lists, compute_change_report
- Humanizer: _humanize_paths
- Service class: save_revision, get_revisions, get_revision, get_stats
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest

from app.services.entry_revision_service import (
    STABLE_ID_FIELDS,
    _diff,
    _diff_lists,
    _field_group,
    _getmk,
    _humanize_paths,
    _item_label,
    _match_key,
    _mk_change,
    _short,
    _summarize,
    _truncate,
    compute_change_report,
)


# ======================================================================
# Pure helper tests — no mocking required
# ======================================================================


class TestMatchKey:
    def test_exact_match(self):
        assert _match_key('senses') == 'id'
        assert _match_key('relations') == 'ref'
        assert _match_key('pronunciations') == 'type'

    def test_child_of_known_path(self):
        assert _match_key('senses.subsenses') == 'id'
        assert _match_key('senses.examples') == 'id'
        assert _match_key('senses.relations') == 'ref'

    def test_unknown_path_returns_none(self):
        assert _match_key('lexical_unit') is None
        assert _match_key('notes') is None

    def test_unknown_child_of_known_path(self):
        # _match_key returns the parent's key for any child of a known prefix
        assert _match_key('senses.unknown_field') == 'id'

    def test_etymologies_returns_none(self):
        assert _match_key('etymologies') is None


class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate('hello', 10) == 'hello'

    def test_exact_length_unchanged(self):
        assert _truncate('12345', 5) == '12345'

    def test_long_string_truncated(self):
        result = _truncate('abcdefghijklmnopqrstuvwxyz', 10)
        assert result == 'abcdefghij…'
        assert len(result) == 11

    def test_empty_string(self):
        assert _truncate('', 10) == ''


class TestShort:
    def test_short_string_unchanged(self):
        assert _short('hello') == 'hello'

    def test_long_string_truncated(self):
        long = 'x' * 150
        result = _short(long)
        assert result.endswith('…')
        assert len(result) == 121  # 120 + ellipsis

    def test_dict_summary(self):
        d = {'a': 1, 'b': 2, 'c': 3}
        result = _short(d)
        assert result.startswith('{')
        assert result.endswith('}')

    def test_dict_many_keys(self):
        d = {str(i): i for i in range(10)}
        result = _short(d)
        assert '…' in result

    def test_list_summary(self):
        assert _short([1, 2, 3]) == '[3 items]'

    def test_none_passthrough(self):
        assert _short(None) is None

    def test_int_passthrough(self):
        assert _short(42) == 42


class TestSummarize:
    def test_added(self):
        s = _summarize('lexeme', 'added', None, 'hello')
        assert 'Added' in s
        assert 'lexeme' in s

    def test_removed(self):
        s = _summarize('lexeme', 'removed', 'hello', None)
        assert 'Removed' in s

    def test_modified(self):
        s = _summarize('lexeme', 'modified', 'old', 'new')
        assert 'Changed' in s
        assert 'old' in s
        assert 'new' in s

    def test_modified_none_before(self):
        s = _summarize('field', 'modified', None, 'val')
        assert '(empty)' in s


class TestMkChange:
    def test_builds_correct_dict(self):
        c = _mk_change('lexeme', 'modified', 'a', 'b')
        assert c['field_path'] == 'lexeme'
        assert c['kind'] == 'modified'
        assert c['before'] == 'a'
        assert c['after'] == 'b'
        assert 'summary' in c


class TestGetmk:
    def test_none_key_returns_id(self):
        obj = object()
        assert _getmk(obj, None) == str(id(obj))

    def test_dict_with_key(self):
        assert _getmk({'id': 'abc'}, 'id') == 'abc'

    def test_dict_missing_key(self):
        assert _getmk({'x': 1}, 'id') == ''

    def test_non_dict_returns_str(self):
        assert _getmk('scalar', 'id') == 'scalar'


class TestItemLabel:
    def test_non_dict_returns_index(self):
        assert _item_label(None, 3) == '3'
        assert _item_label([1, 2], 5) == '5'

    def test_flat_gloss(self):
        item = {'gloss': {'en': 'hello'}}
        label = _item_label(item, 1)
        assert '1' in label
        assert 'hello' in label

    def test_nested_definition(self):
        item = {'definition': {'en': {'text': 'a greeting'}}}
        label = _item_label(item, 2)
        assert '2' in label
        assert 'greeting' in label

    def test_long_text_truncated(self):
        item = {'gloss': {'en': 'x' * 100}}
        label = _item_label(item, 1)
        assert '…' in label

    def test_no_recognized_fields(self):
        item = {'custom_field': 'value'}
        assert _item_label(item, 4) == '4'


class TestFieldGroup:
    def test_simple_path(self):
        assert _field_group('lexeme') == 'lexeme'

    def test_two_levels(self):
        assert _field_group('senses.gloss') == 'senses.gloss'

    def test_deep_path_truncated(self):
        assert _field_group('senses.examples.form.text') == 'senses.examples'

    def test_with_array_index(self):
        assert _field_group('senses[abc].gloss') == 'senses.gloss'

    def test_multiple_indices(self):
        assert _field_group('senses[abc].examples[def].form') == 'senses.examples'


# ======================================================================
# Diff engine tests
# ======================================================================


class TestDiff:
    def test_identical_dicts_no_changes(self):
        changes = []
        _diff({'a': 1}, {'a': 1}, '', changes)
        assert changes == []

    def test_modified_value(self):
        changes = []
        _diff({'a': 1}, {'a': 2}, '', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'modified'
        assert changes[0]['field_path'] == 'a'

    def test_added_key(self):
        changes = []
        _diff({}, {'b': 2}, '', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'added'

    def test_removed_key(self):
        changes = []
        _diff({'a': 1}, {}, '', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'removed'

    def test_nested_dicts(self):
        changes = []
        _diff({'s': {'x': 1}}, {'s': {'x': 2}}, '', changes)
        assert len(changes) == 1
        assert changes[0]['field_path'] == 's.x'

    def test_depth_limit(self):
        # Build a path deeper than 8 levels
        a = {'l1': {'l2': {'l3': {'l4': {'l5': {'l6': {'l7': {'l8': {'l9': 1}}}}}}}}}
        b = {'l1': {'l2': {'l3': {'l4': {'l5': {'l6': {'l7': {'l8': {'l9': 2}}}}}}}}}
        changes = []
        _diff(a, b, '', changes)
        # Should produce a single modified at the deep path (depth limit kicks in)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'modified'

    def test_list_diff_unkeyed(self):
        changes = []
        _diff([1, 2, 3], [1, 2, 4], 'items', changes)
        assert len(changes) == 1
        assert changes[0]['field_path'] == 'items[2]'

    def test_list_diff_added(self):
        changes = []
        _diff([1], [1, 2], 'items', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'added'

    def test_list_diff_removed(self):
        changes = []
        _diff([1, 2], [1], 'items', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'removed'

    def test_scalar_vs_dict(self):
        changes = []
        _diff('text', {'a': 1}, 'field', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'modified'


class TestDiffLists:
    def test_keyed_list_match(self):
        a = [{'id': 's1', 'gloss': 'old'}]
        b = [{'id': 's1', 'gloss': 'new'}]
        changes = []
        _diff_lists(a, b, 'senses', changes)
        assert len(changes) == 1
        assert 'senses[s1]' in changes[0]['field_path']
        assert changes[0]['kind'] == 'modified'

    def test_keyed_list_add(self):
        a = [{'id': 's1'}]
        b = [{'id': 's1'}, {'id': 's2'}]
        changes = []
        _diff_lists(a, b, 'senses', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'added'
        assert 's2' in changes[0]['field_path']

    def test_keyed_list_remove(self):
        a = [{'id': 's1'}, {'id': 's2'}]
        b = [{'id': 's1'}]
        changes = []
        _diff_lists(a, b, 'senses', changes)
        assert len(changes) == 1
        assert changes[0]['kind'] == 'removed'

    def test_unkeyed_list_positional(self):
        a = [1, 2, 3]
        b = [1, 2, 4]
        changes = []
        _diff_lists(a, b, 'items', changes)
        assert len(changes) == 1
        assert changes[0]['field_path'] == 'items[2]'


# ======================================================================
# compute_change_report integration
# ======================================================================


class TestComputeChangeReport:
    def test_none_prev(self):
        assert compute_change_report(None, {'a': 1}) == []

    def test_identical(self):
        assert compute_change_report({'a': 1}, {'a': 1}) == []

    def test_modification(self):
        report = compute_change_report({'a': 1}, {'a': 2})
        assert len(report) == 1
        assert report[0]['kind'] == 'modified'

    def test_addition(self):
        report = compute_change_report({}, {'b': 2})
        assert len(report) == 1
        assert report[0]['kind'] == 'added'

    def test_removal(self):
        report = compute_change_report({'a': 1}, {})
        assert len(report) == 1
        assert report[0]['kind'] == 'removed'

    def test_sense_change_with_humanization(self):
        prev = {'senses': [{'id': 's1', 'gloss': {'en': 'old'}}]}
        curr = {'senses': [{'id': 's1', 'gloss': {'en': 'new'}}]}
        report = compute_change_report(prev, curr)
        assert len(report) >= 1
        # UUID should be humanized to a label
        assert 'senses[1' in report[0]['field_path']


# ======================================================================
# Humanize
# ======================================================================


class TestHumanizePaths:
    def test_replaces_sense_uuid(self):
        changes = [{'field_path': 'senses[abc-123].gloss.en', 'kind': 'modified',
                     'before': 'old', 'after': 'new', 'summary': ''}]
        snapshot = {'senses': [{'id': 'abc-123', 'gloss': {'en': 'hello'}}]}
        _humanize_paths(changes, snapshot)
        assert 'abc-123' not in changes[0]['field_path']
        assert 'senses[1' in changes[0]['field_path']

    def test_unknown_id_truncated(self):
        changes = [{'field_path': 'senses[unknown-id].gloss', 'kind': 'modified',
                     'before': 'a', 'after': 'b', 'summary': ''}]
        snapshot = {'senses': [{'id': 'other-id'}]}
        _humanize_paths(changes, snapshot)
        # Unknown ID should be truncated to 8 chars
        assert 'unknown' in changes[0]['field_path']

    def test_no_senses(self):
        changes = [{'field_path': 'lexeme', 'kind': 'modified',
                     'before': 'a', 'after': 'b', 'summary': ''}]
        _humanize_paths(changes, {'lexeme': 'test'})
        assert changes[0]['field_path'] == 'lexeme'


# ======================================================================
# Service tests — require SQLAlchemy mocking
# ======================================================================


class TestSaveRevision:
    @patch('app.services.entry_revision_service.db')
    @patch('app.services.entry_revision_service.EntryRevision')
    def test_first_revision(self, MockRevision, mock_db):
        mock_query = Mock()
        MockRevision.query = mock_query
        mock_query.with_entities.return_value.filter.return_value.scalar.return_value = None
        mock_query.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.func.max.return_value = Mock()

        from app.services.entry_revision_service import EntryRevisionService
        rev = EntryRevisionService.save_revision(
            'entry-1', {'lexeme': 'hello'}, user_id='user1'
        )

        MockRevision.assert_called_once()
        call_kwargs = MockRevision.call_args
        assert call_kwargs[1]['entry_id'] == 'entry-1'
        assert call_kwargs[1]['revision_number'] == 1
        assert call_kwargs[1]['snapshot'] == {'lexeme': 'hello'}
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @patch('app.services.entry_revision_service.db')
    @patch('app.services.entry_revision_service.EntryRevision')
    def test_subsequent_revision_increments(self, MockRevision, mock_db):
        mock_query = Mock()
        MockRevision.query = mock_query
        mock_query.with_entities.return_value.filter.return_value.scalar.return_value = 5
        prev_rev = Mock()
        prev_rev.snapshot = {'lexeme': 'old'}
        mock_query.filter.return_value.order_by.return_value.first.return_value = prev_rev

        from app.services.entry_revision_service import EntryRevisionService
        rev = EntryRevisionService.save_revision(
            'entry-1', {'lexeme': 'new'}, user_id='user1'
        )

        call_kwargs = MockRevision.call_args
        assert call_kwargs[1]['revision_number'] == 6


class TestGetRevisions:
    @patch('app.services.entry_revision_service.EntryRevision')
    def test_pagination(self, MockRevision):
        mock_q = Mock()
        MockRevision.query.filter_by.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.count.return_value = 50
        mock_q.offset.return_value = mock_q
        mock_q.limit.return_value = mock_q
        mock_q.all.return_value = [Mock() for _ in range(10)]

        from app.services.entry_revision_service import EntryRevisionService
        revisions, total = EntryRevisionService.get_revisions('entry-1', page=2, per_page=10)

        assert total == 50
        assert len(revisions) == 10
        mock_q.offset.assert_called_once_with(10)
        mock_q.limit.assert_called_once_with(10)


class TestGetRevision:
    @patch('app.services.entry_revision_service._humanize_paths')
    @patch('app.services.entry_revision_service.EntryRevision')
    def test_found_with_change_report(self, MockRevision, mock_humanize):
        rev = Mock()
        rev.change_report = [{'field_path': 'x', 'kind': 'modified'}]
        rev.snapshot = {'x': 'val'}
        MockRevision.query.filter_by.return_value.first.return_value = rev

        from app.services.entry_revision_service import EntryRevisionService
        result = EntryRevisionService.get_revision('entry-1', 1)

        assert result is rev
        mock_humanize.assert_called_once_with(rev.change_report, rev.snapshot)

    @patch('app.services.entry_revision_service.EntryRevision')
    def test_not_found(self, MockRevision):
        MockRevision.query.filter_by.return_value.first.return_value = None

        from app.services.entry_revision_service import EntryRevisionService
        assert EntryRevisionService.get_revision('entry-1', 99) is None


class TestGetStats:
    @patch('app.services.entry_revision_service.EntryRevision')
    def test_basic_stats(self, MockRevision):
        r1 = Mock()
        r1.entry_id = 'e1'
        r1.user_id = 'u1'
        r1.created_by = 'u1'
        r1.change_report = [{'field_path': 'lexeme', 'kind': 'modified'}]
        r1.timestamp_utc = datetime(2025, 1, 15, tzinfo=timezone.utc)

        r2 = Mock()
        r2.entry_id = 'e1'
        r2.user_id = 'u1'
        r2.created_by = 'u1'
        r2.change_report = [{'field_path': 'senses[abc].gloss', 'kind': 'modified'}]
        r2.timestamp_utc = datetime(2025, 1, 16, tzinfo=timezone.utc)

        mock_q = Mock()
        MockRevision.query = mock_q
        mock_q.filter.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.all.return_value = [r1, r2]

        from app.services.entry_revision_service import EntryRevisionService
        stats = EntryRevisionService.get_stats()

        assert stats['total_revisions'] == 2
        assert stats['unique_entries_touched'] == 1
        assert stats['unique_users'] == 1
        assert len(stats['timeline']) == 2
        assert stats['top_edited_entries'][0]['revisions'] == 2
