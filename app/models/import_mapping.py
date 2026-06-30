"""Import mapping models for SFM/CSV → LIFT import.

Defines how Shoebox (SFM) markers or CSV columns map to LIFT elements,
so lexicographers can import non-LIFT data into the dictionary.
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.models.workset_models import db


FIELD_TYPES = (
    "normal",
    "cross-ref-source",   # \lf
    "cross-ref-target",   # \lv
    "variant-target",     # \mn
    "variant-type",       # \vt
)


class ImportMapping(db.Model):
    __tablename__ = "import_mappings"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(255), nullable=False, index=True)
    file_type: str = Column(String(10), nullable=False, default="sfm")
    description: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    owner_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    field_mappings: List[ImportFieldMapping] = relationship(
        "ImportFieldMapping",
        back_populates="mapping",
        cascade="all, delete-orphan",
    )
    language_mappings: List[ImportLanguageMapping] = relationship(
        "ImportLanguageMapping",
        back_populates="mapping",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ImportMapping id={self.id} name={self.name} type={self.file_type}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "file_type": self.file_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "field_mappings": [fm.to_dict() for fm in self.field_mappings],
            "language_mappings": [lm.to_dict() for lm in self.language_mappings],
        }


class ImportFieldMapping(db.Model):
    __tablename__ = "import_field_mappings"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    mapping_id: int = Column(
        Integer,
        ForeignKey("import_mappings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_marker: str = Column(String(100), nullable=False)
    lift_element: str = Column(String(100), nullable=False)
    level: str = Column(String(50), nullable=False, default="entry")
    lang: Optional[str] = Column(String(10), nullable=True)
    is_key: bool = Column(Boolean, default=False, nullable=False)
    field_type: str = Column(String(30), nullable=False, default="normal")

    mapping: ImportMapping = relationship(
        "ImportMapping", back_populates="field_mappings"
    )

    def __repr__(self) -> str:
        return (
            f"<ImportFieldMapping id={self.id}"
            f" marker={self.field_marker!r}"
            f" → {self.lift_element}"
            f" @ {self.level}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mapping_id": self.mapping_id,
            "field_marker": self.field_marker,
            "lift_element": self.lift_element,
            "level": self.level,
            "lang": self.lang,
            "is_key": self.is_key,
            "field_type": self.field_type,
        }


class ImportLanguageMapping(db.Model):
    __tablename__ = "import_language_mappings"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    mapping_id: int = Column(
        Integer,
        ForeignKey("import_mappings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_lang: str = Column(String(50), nullable=False)
    target_lang: str = Column(String(10), nullable=False)

    mapping: ImportMapping = relationship(
        "ImportMapping", back_populates="language_mappings"
    )

    def __repr__(self) -> str:
        return (
            f"<ImportLanguageMapping id={self.id}"
            f" {self.source_lang} → {self.target_lang}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mapping_id": self.mapping_id,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
        }
