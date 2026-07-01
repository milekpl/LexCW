"""
EntryRevision — SQLAlchemy model for per-entry edit history.

Each explicit form submission (save) produces one row capturing the
serializer-ready JSON snapshot + a structured field-level change report.
"""

from datetime import datetime, timezone
from app.models.workset_models import db


class EntryRevision(db.Model):
    __tablename__ = 'entry_revisions'

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Text, nullable=False, index=True)
    revision_number = db.Column(db.Integer, nullable=False)
    timestamp_utc = db.Column(db.DateTime, nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Text, nullable=True)
    snapshot = db.Column(db.JSON, nullable=False)
    change_report = db.Column(db.JSON, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('entry_id', 'revision_number', name='uq_entry_rev'),
    )

    def to_dict(self, include_snapshot: bool = False) -> dict:
        d = {
            'revision_number': self.revision_number,
            'timestamp_utc': self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            'created_by': self.created_by,
            'change_count': len(self.change_report) if self.change_report else 0,
        }
        if include_snapshot:
            d['snapshot'] = self.snapshot
            d['change_report'] = self.change_report
        return d
