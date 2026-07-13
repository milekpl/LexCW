"""
API key model for machine-to-machine authentication.

Each key is tied to a project and has configurable scopes.
The raw key is shown once at creation; only the hash is stored.
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey

from app.models.workset_models import db


class ApiKey(db.Model):
    __tablename__ = "api_keys"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("project_settings.id", ondelete="CASCADE"), nullable=False
    )
    label = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(16), nullable=False, unique=True, index=True)
    scopes = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} prefix={self.key_prefix} project={self.project_id}>"

    def to_dict(self) -> dict:
        """Serialize for API responses — never exposes key_hash."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "label": self.label,
            "key_prefix": self.key_prefix,
            "scopes": self.scopes or [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
