"""
Unit tests for BulkRollbackService — pre-op snapshot + compensating restore.
"""
import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.services.bulk_rollback_service import BulkRollbackService


class TestBulkRollbackService:
    """BulkRollbackService should snapshot entries before bulk ops and restore on rollback."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_entry(self, entry_id: str, headword: str = 'test',
                    **kwargs) -> Mock:
        """Create a mock Entry domain object with update_from_dict."""
        entry = Mock()
        entry.id = entry_id
        entry.lexical_unit = {'en': headword}
        entry.to_dict.return_value = {'id': entry_id, 'lexical_unit': {'en': headword}}
        for k, v in kwargs.items():
            setattr(entry, k, v)
        return entry

    def _make_dict_service(self, entries: list[Mock]) -> Mock:
        """Create a mock DictionaryService that returns entries by id."""
        mock_dict = Mock()

        def _get_entry(eid):
            for e in entries:
                if e.id == eid:
                    return e
            return None

        mock_dict.get_entry.side_effect = _get_entry
        return mock_dict

    # ------------------------------------------------------------------
    # Snapshot recording
    # ------------------------------------------------------------------

    def test_record_snapshot_stores_entry_state(self, db_app):
        """record_snapshot should persist entry snapshot keyed by bulk_op_id."""
        with db_app.app_context():
            service = BulkRollbackService()
            entry = {'id': 'e1', 'lexical_unit': {'en': 'test'}, 'senses': []}

            service.record_snapshot('op-1', entry)

            rows = service._get_snapshots('op-1')
            assert len(rows) == 1
            assert rows[0]['entry_id'] == 'e1'
            assert rows[0]['snapshot']['lexical_unit'] == {'en': 'test'}

    def test_record_snapshot_multiple_entries(self, db_app):
        """record_snapshot should persist multiple entries under the same op."""
        with db_app.app_context():
            service = BulkRollbackService()
            entries = [
                {'id': 'e1', 'lexical_unit': {'en': 'alpha'}},
                {'id': 'e2', 'lexical_unit': {'en': 'beta'}},
            ]

            for e in entries:
                service.record_snapshot('op-2', e)

            rows = service._get_snapshots('op-2')
            assert len(rows) == 2
            assert {r['entry_id'] for r in rows} == {'e1', 'e2'}

    def test_record_snapshot_replaces_prior_snapshot(self, db_app):
        """record_snapshot for the same entry_id + bulk_op_id should update, not duplicate."""
        with db_app.app_context():
            service = BulkRollbackService()
            entry = {'id': 'e1', 'lexical_unit': {'en': 'v1'}}
            service.record_snapshot('op-3', entry)
            entry['lexical_unit']['en'] = 'v2'
            service.record_snapshot('op-3', entry)

            rows = service._get_snapshots('op-3')
            assert len(rows) == 1

    def test_record_snapshot_requires_id(self, db_app):
        """record_snapshot should skip entries without an id."""
        with db_app.app_context():
            service = BulkRollbackService()
            service.record_snapshot('op-4', {'lexical_unit': {'en': 'no-id'}})

            rows = service._get_snapshots('op-4')
            assert len(rows) == 0

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def test_rollback_restores_all_snapshots(self, db_app):
        """rollback should restore each snapshot via dictionary_service.update_entry()."""
        with db_app.app_context():
            mock_dict = Mock()
            entry = self._make_entry('e1', 'restored')
            mock_dict.get_entry.return_value = entry

            service = BulkRollbackService(dictionary_service=mock_dict)
            snapshot = {'id': 'e1', 'lexical_unit': {'en': 'restored'}, 'senses': []}
            service.record_snapshot('op-r1', snapshot)

            result = service.rollback('op-r1')

            assert result['restored'] == 1
            assert result['failed'] == 0
            # update_entry should have been called with the entry
            assert mock_dict.update_entry.called
            # update_from_dict should have been called on the entry
            entry.update_from_dict.assert_called_once_with(snapshot)

    def test_rollback_multiple_entries(self, db_app):
        """rollback should restore multiple entries."""
        with db_app.app_context():
            entries_list = [self._make_entry(f'e{i}', f'word{i}') for i in range(3)]
            mock_dict = self._make_dict_service(entries_list)

            service = BulkRollbackService(dictionary_service=mock_dict)
            for i in range(3):
                service.record_snapshot('op-r2', {
                    'id': f'e{i}',
                    'lexical_unit': {'en': f'word{i}'},
                })

            result = service.rollback('op-r2')

            assert result['restored'] == 3
            assert mock_dict.update_entry.call_count == 3

    def test_rollback_unknown_op_returns_empty(self, db_app):
        """rollback for a non-existent operation_id should return zero counts."""
        with db_app.app_context():
            service = BulkRollbackService()
            result = service.rollback('op-nonexistent')

            assert result['restored'] == 0
            assert result['failed'] == 0

    def test_rollback_handles_entry_not_found(self, db_app):
        """rollback should skip entries that no longer exist (not fail the whole op)."""
        with db_app.app_context():
            mock_dict = Mock()
            entry = self._make_entry('e2', 'found')
            mock_dict.get_entry.side_effect = [None, entry]

            service = BulkRollbackService(dictionary_service=mock_dict)
            service.record_snapshot('op-r3', {'id': 'e1', 'lexical_unit': {'en': 'lost'}})
            service.record_snapshot('op-r3', {'id': 'e2', 'lexical_unit': {'en': 'found'}})

            result = service.rollback('op-r3')

            assert result['restored'] == 1
            assert result['failed'] == 0
            assert result['skipped'] == 1

    def test_rollback_continues_on_error(self, db_app):
        """rollback should continue restoring other entries if one fails."""
        with db_app.app_context():
            mock_dict = Mock()
            entries = [self._make_entry(f'e{i}', f'word{i}') for i in range(3)]

            def _get_entry(eid):
                for e in entries:
                    if e.id == eid:
                        return e
                return None

            mock_dict.get_entry.side_effect = _get_entry

            def _failing_update(entry_obj):
                if entry_obj.id == 'e0':
                    raise RuntimeError("Update failed")

            mock_dict.update_entry.side_effect = _failing_update

            service = BulkRollbackService(dictionary_service=mock_dict)
            for i in range(3):
                service.record_snapshot('op-r4', {
                    'id': f'e{i}',
                    'lexical_unit': {'en': f'word{i}'},
                })

            result = service.rollback('op-r4')

            assert result['restored'] == 2
            assert result['failed'] == 1

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def test_delete_snapshots_removes_operation_data(self, db_app):
        """delete_snapshots should remove persisted snapshots for an operation."""
        with db_app.app_context():
            service = BulkRollbackService()
            service.record_snapshot('op-c1', {'id': 'e1', 'lexical_unit': {'en': 'gone'}})
            assert len(service._get_snapshots('op-c1')) == 1

            service.delete_snapshots('op-c1')

            assert len(service._get_snapshots('op-c1')) == 0

    # ------------------------------------------------------------------
    # Integration with existing bulk operations
    # ------------------------------------------------------------------

    def test_bulk_snapshot_from_entry_dict(self, db_app):
        """record_snapshot should accept a dict from DictionaryService.get_entry().to_dict()."""
        with db_app.app_context():
            mock_dict = Mock()
            entry = self._make_entry('e1', 'hello')
            mock_dict.get_entry.return_value = entry

            service = BulkRollbackService(dictionary_service=mock_dict)
            entry_data = service._snapshot_entry('e1')
            assert entry_data is not None
            assert entry_data['lexical_unit'] == {'en': 'hello'}

    def test_bulk_snapshot_entry_not_found(self, db_app):
        """_snapshot_entry should return None if entry doesn't exist."""
        with db_app.app_context():
            mock_dict = Mock()
            mock_dict.get_entry.return_value = None

            service = BulkRollbackService(dictionary_service=mock_dict)
            result = service._snapshot_entry('nonexistent')
            assert result is None

    def test_record_bulk_op_snapshots(self, db_app):
        """record_bulk_op_snapshots should snapshot all provided entry IDs."""
        with db_app.app_context():
            mock_dict = Mock()
            entries = [self._make_entry(f'e{i}', f'word{i}') for i in range(3)]

            def _get_entry(eid):
                for e in entries:
                    if e.id == eid:
                        return e
                return None

            mock_dict.get_entry.side_effect = _get_entry

            service = BulkRollbackService(dictionary_service=mock_dict)
            snapshotted = service.record_bulk_op_snapshots('op-bulk1', ['e0', 'e1', 'e2'])

            assert snapshotted == 3
            rows = service._get_snapshots('op-bulk1')
            assert len(rows) == 3

    def test_record_bulk_op_snapshots_skips_missing(self, db_app):
        """record_bulk_op_snapshots should skip entries that don't exist."""
        with db_app.app_context():
            mock_dict = Mock()
            mock_dict.get_entry.return_value = None

            service = BulkRollbackService(dictionary_service=mock_dict)
            snapshotted = service.record_bulk_op_snapshots('op-bulk2', ['e1', 'e2'])

            assert snapshotted == 0
