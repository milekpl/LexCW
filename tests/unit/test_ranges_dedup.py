"""Unit tests for range-element duplicate detection / de-duplication."""
import pytest

from app.services.ranges_dedup import (
    dedupe_exact_duplicates,
    find_id_conflicts,
    summarize_duplicates,
)

pytestmark = pytest.mark.unit


def _ids(values):
    return [v.get('id') for v in values]


class TestDedupeExact:
    def test_removes_same_id_same_guid_siblings(self):
        values = [
            {'id': 'Noun', 'guid': 'g-noun'},
            {'id': 'Pronoun', 'guid': 'g-pro'},
            {'id': 'Pronoun', 'guid': 'g-pro'},  # exact dup (FieldWorks bug)
        ]
        cleaned, removed = dedupe_exact_duplicates(values)
        assert removed == 1
        assert _ids(cleaned) == ['Noun', 'Pronoun']

    def test_keeps_same_id_different_guid(self):
        values = [
            {'id': 'Pronoun', 'guid': 'g-1'},
            {'id': 'Pronoun', 'guid': 'g-2'},  # NOT exact — different guid
        ]
        cleaned, removed = dedupe_exact_duplicates(values)
        assert removed == 0
        assert len(cleaned) == 2

    def test_dedupes_within_children_recursively(self):
        values = [{
            'id': 'Pro-form', 'guid': 'g-pf',
            'children': [
                {'id': 'Pronoun', 'guid': 'g-pro'},
                {'id': 'Pronoun', 'guid': 'g-pro'},  # exact dup nested
            ],
        }]
        cleaned, removed = dedupe_exact_duplicates(values)
        assert removed == 1
        assert _ids(cleaned[0]['children']) == ['Pronoun']

    def test_falls_back_to_value_when_no_id(self):
        values = [
            {'value': 'x', 'guid': 'g'},
            {'value': 'x', 'guid': 'g'},
        ]
        cleaned, removed = dedupe_exact_duplicates(values)
        assert removed == 1

    def test_does_not_mutate_input(self):
        values = [{'id': 'A', 'guid': 'g'}, {'id': 'A', 'guid': 'g'}]
        dedupe_exact_duplicates(values)
        assert len(values) == 2  # original untouched

    def test_empty_and_none(self):
        assert dedupe_exact_duplicates([]) == ([], 0)
        assert dedupe_exact_duplicates(None) == ([], 0)


class TestIdConflicts:
    def test_flags_same_id_different_guid(self):
        values = [
            {'id': 'Pronoun', 'guid': 'g-1'},
            {'id': 'Pronoun', 'guid': 'g-2'},
            {'id': 'Noun', 'guid': 'g-n'},
        ]
        conflicts = find_id_conflicts(values)
        assert len(conflicts) == 1
        assert conflicts[0]['id'] == 'Pronoun'
        assert conflicts[0]['guids'] == ['g-1', 'g-2']

    def test_exact_duplicates_are_not_conflicts(self):
        # same id AND same guid -> exact dup, NOT an id conflict
        values = [{'id': 'X', 'guid': 'g'}, {'id': 'X', 'guid': 'g'}]
        assert find_id_conflicts(values) == []

    def test_finds_conflicts_in_hierarchy(self):
        values = [{
            'id': 'top', 'guid': 'g-top',
            'children': [{'id': 'Pronoun', 'guid': 'g-2'}],
        }, {'id': 'Pronoun', 'guid': 'g-1'}]
        conflicts = find_id_conflicts(values)
        assert len(conflicts) == 1 and conflicts[0]['id'] == 'Pronoun'


class TestSummary:
    def test_summary_reports_both_kinds(self):
        values = [
            {'id': 'A', 'guid': 'g'}, {'id': 'A', 'guid': 'g'},      # exact dup
            {'id': 'B', 'guid': 'g1'}, {'id': 'B', 'guid': 'g2'},    # conflict
        ]
        s = summarize_duplicates(values)
        assert s['exact_duplicate_count'] == 1
        assert len(s['id_conflicts']) == 1
        assert s['has_duplicates'] is True

    def test_clean_range_has_no_duplicates(self):
        values = [{'id': 'A', 'guid': 'g1'}, {'id': 'B', 'guid': 'g2'}]
        s = summarize_duplicates(values)
        assert s['has_duplicates'] is False
