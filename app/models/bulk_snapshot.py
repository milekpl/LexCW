"""BulkOperationSnapshot — pre-bulk-op entry snapshots for compensating rollback."""
from datetime import datetime, timezone
from app.models.workset_models import db


class BulkOperationSnapshot(db.Model):
    __tablename__ = 'bulk_operation_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    bulk_op_id = db.Column(db.Text, nullable=False, index=True)
    entry_id = db.Column(db.Text, nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    created_utc = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('bulk_op_id', 'entry_id', name='uq_bulk_op_entry'),
    )
