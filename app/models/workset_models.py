from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped

db = SQLAlchemy()


class Workset(db.Model):
    __tablename__ = "worksets"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(255), nullable=False)
    query: dict = Column(JSON, nullable=False)
    total_entries: int = Column(Integer, default=0)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # User tracking fields
    created_by_user_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    description: Optional[str] = Column(db.Text, nullable=True)

    entries: List[WorksetEntry] = relationship(
        "WorksetEntry", back_populates="workset", cascade="all, delete-orphan"
    )
    created_by = relationship(
        "User", backref="worksets", foreign_keys=[created_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<Workset id={self.id} name={self.name}>"


class WorksetEntry(db.Model):
    __tablename__ = "workset_entries"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    workset_id: int = Column(
        Integer, ForeignKey("worksets.id", ondelete="CASCADE"), nullable=False
    )
    entry_id: str = Column(String(255), nullable=False)

    # Curation metadata (added by migration)
    status: Optional[str] = Column(String(50), nullable=True)
    position: Optional[int] = Column(Integer, nullable=True)
    is_favorite: Optional[bool] = Column(db.Boolean, default=False)
    notes: Optional[str] = Column(db.Text, nullable=True)
    modified_at: Optional[datetime] = Column(DateTime, nullable=True)

    # User tracking
    modified_by_user_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes_author_user_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    workset: Workset = relationship("Workset", back_populates="entries")
    modified_by = relationship(
        "User", foreign_keys=[modified_by_user_id], backref="modified_workset_entries"
    )
    notes_author = relationship(
        "User", foreign_keys=[notes_author_user_id], backref="authored_notes"
    )

    def __repr__(self) -> str:
        return f"<WorksetEntry id={self.id} workset_id={self.workset_id} entry_id={self.entry_id}>"


# User tracking implemented - connects users to worksets and entry curation actions
