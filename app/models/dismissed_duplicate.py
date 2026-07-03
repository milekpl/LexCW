from __future__ import annotations
from datetime import datetime, timezone
from app.models.workset_models import db


class DismissedDuplicate(db.Model):
    __tablename__ = "dismissed_duplicates"
    __allow_unmapped__ = True

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project_settings.id"), nullable=False)
    group_id = db.Column(db.String(255), nullable=False)
    dismissed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("project_id", "group_id", name="uq_project_group"),
    )

    def __repr__(self) -> str:
        return f"<DismissedDuplicate project={self.project_id} group={self.group_id}>"
