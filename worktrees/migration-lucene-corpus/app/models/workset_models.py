from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped

db = SQLAlchemy()

class Workset(db.Model):
    __tablename__ = 'worksets'
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(255), nullable=False)
    query: dict = Column(JSON, nullable=False)
    total_entries: int = Column(Integer, default=0)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entries: List[WorksetEntry] = relationship('WorksetEntry', back_populates='workset', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Workset id={self.id} name={self.name}>'

class WorksetEntry(db.Model):
    __tablename__ = 'workset_entries'
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    workset_id: int = Column(Integer, ForeignKey('worksets.id', ondelete='CASCADE'), nullable=False)
    entry_id: str = Column(String(255), nullable=False)

    workset: Workset = relationship('Workset', back_populates='entries')

    def __repr__(self) -> str:
        return f'<WorksetEntry id={self.id} workset_id={self.workset_id} entry_id={self.entry_id}>'

# Future: Add user_id ForeignKey to Workset when user accounts are implemented
