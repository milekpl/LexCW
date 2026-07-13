"""
BulkRollbackService — pre-bulk-op entry snapshots and compensating restore.

Snapshots each entry's full state (via ``entry.to_dict()``) before a bulk
operation modifies it.  On rollback, the snapshots are written back via
``dictionary_service.update_entry()``.

Because each BaseX update is its own ACID transaction, there is no way to
roll back a multi-entry bulk operation at the database level.  This service
provides the next-best thing: *compensating writes* that restore each entry
to its pre-bulk state, grouped under a ``bulk_op_id`` so a rollback undoes
an entire bulk operation at once.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4
from datetime import datetime

from app.models.workset_models import db
from app.models.bulk_snapshot import BulkOperationSnapshot
from app.services.dictionary_service import DictionaryService

logger = logging.getLogger(__name__)


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    restored: int = 0
    failed: int = 0
    skipped: int = 0


class BulkRollbackService:
    """Snapshot entry state before bulk ops and restore on rollback."""

    def __init__(self, dictionary_service: Optional[DictionaryService] = None):
        self._dictionary_service = dictionary_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def generate_op_id() -> str:
        """Generate a unique, human-readable operation ID."""
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        short = uuid4().hex[:8]
        return f'bulk-{ts}-{short}'

    def record_snapshot(self, bulk_op_id: str, entry_data: dict) -> bool:
        """Persist a single entry snapshot under *bulk_op_id*.

        Returns True if a snapshot was recorded, False if the entry lacked an id.
        """
        entry_id = entry_data.get('id')
        if not entry_id:
            logger.warning('record_snapshot skipped entry with no id')
            return False

        # Upsert: remove old snapshot for this (op, entry) pair, then insert.
        BulkOperationSnapshot.query.filter_by(
            bulk_op_id=bulk_op_id,
            entry_id=entry_id,
        ).delete()
        db.session.flush()

        snap = BulkOperationSnapshot(
            bulk_op_id=bulk_op_id,
            entry_id=entry_id,
            snapshot=entry_data,
        )
        db.session.add(snap)
        db.session.commit()
        return True

    def record_bulk_op_snapshots(self, bulk_op_id: str,
                                 entry_ids: list[str]) -> int:
        """Snapshot every entry in *entry_ids* under *bulk_op_id*.

        Returns the number of successful snapshots.
        """
        count = 0
        for eid in entry_ids:
            data = self._snapshot_entry(eid)
            if data is not None:
                if self.record_snapshot(bulk_op_id, data):
                    count += 1
        return count

    def _snapshot_entry(self, entry_id: str) -> Optional[dict]:
        """Fetch a single entry and return its dict representation."""
        if not self._dictionary_service:
            return None
        try:
            entry = self._dictionary_service.get_entry(entry_id)
            if entry is None:
                return None
            return self._get_entry_snapshot(entry)
        except Exception as exc:
            logger.error('snapshot failed for entry %s: %s', entry_id, exc)
            return None

    def rollback(self, bulk_op_id: str) -> dict:
        """Restore every entry snapshotted under *bulk_op_id*.

        Returns dict with keys ``restored``, ``failed``, ``skipped``.
        """
        rows = self._get_snapshots(bulk_op_id)
        result = RollbackResult()

        for row in rows:
            entry_id = row['entry_id']
            snapshot = row['snapshot']

            try:
                self._restore_entry(snapshot)
                result.restored += 1
                logger.info('rollback: restored entry %s', entry_id)
            except LookupError:
                result.skipped += 1
                logger.warning('rollback: entry %s not found, skipping', entry_id)
            except Exception as exc:
                logger.error('rollback: failed to restore entry %s: %s',
                             entry_id, exc)
                result.failed += 1

        # Clean up snapshots
        self.delete_snapshots(bulk_op_id)

        return {
            'restored': result.restored,
            'failed': result.failed,
            'skipped': result.skipped,
            'total': len(rows),
        }

    def delete_snapshots(self, bulk_op_id: str) -> None:
        """Remove all snapshots for a bulk operation."""
        BulkOperationSnapshot.query.filter_by(
            bulk_op_id=bulk_op_id,
        ).delete()
        db.session.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_entry_snapshot(self, entry) -> Optional[dict]:
        """Get a snapshot dict from an entry object."""
        if hasattr(entry, 'to_dict'):
            return entry.to_dict()
        if isinstance(entry, dict):
            return entry
        return None

    def _restore_entry(self, snapshot: dict) -> None:
        """Write snapshot data back to the database.

        Raises:
            KeyError: If the snapshot has no id.
            LookupError: If the entry does not exist in the database.
        """
        if not self._dictionary_service:
            return
        entry_id = snapshot.get('id')
        if not entry_id:
            raise KeyError('Snapshot has no id')
        entry = self._dictionary_service.get_entry(entry_id)
        if entry is None:
            raise LookupError(f'Entry {entry_id} not found')
        entry.update_from_dict(snapshot)
        self._dictionary_service.update_entry(entry)

    def _get_snapshots(self, bulk_op_id: str) -> list[dict]:
        """Return all snapshot rows for a bulk operation as plain dicts."""
        rows = BulkOperationSnapshot.query.filter_by(
            bulk_op_id=bulk_op_id,
        ).order_by(BulkOperationSnapshot.id).all()
        return [
            {
                'entry_id': r.entry_id,
                'snapshot': r.snapshot,
                'created_utc': r.created_utc.isoformat() if r.created_utc else None,
            }
            for r in rows
        ]
