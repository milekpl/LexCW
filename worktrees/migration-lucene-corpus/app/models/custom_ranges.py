"""Custom ranges models for storing undefined SIL Fieldworks ranges."""

from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.workset_models import db


class CustomRange(db.Model):
    """Custom range definition for storing undefined ranges from SIL Fieldworks."""
    __tablename__ = 'custom_ranges'
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, nullable=False)
    range_type = Column(String(50), nullable=False, 
                       comment="Type of range: 'relation' or 'trait'")
    range_name = Column(String(255), nullable=False,
                       comment="Name of the range (e.g., 'lexical-relation', trait name)")
    element_id = Column(String(255), nullable=False,
                       comment="ID of the range element")
    element_label = Column(Text,
                          comment="Label for the range element")
    element_description = Column(Text,
                                comment="Description for the range element")
    parent_range = Column(String(255),
                         comment="Parent range this element belongs to")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    values = relationship(
        'CustomRangeValue', 
        backref='custom_range', 
        lazy=True,
        cascade='all, delete-orphan'
    )

    # Add check constraint for range_type
    __table_args__ = (
        CheckConstraint("range_type IN ('relation', 'trait')", name='check_range_type'),
    )

    def __repr__(self) -> str:
        return f'<CustomRange id={self.id} type={self.range_type} name={self.range_name}>'

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'range_type': self.range_type,
            'range_name': self.range_name,
            'element_id': self.element_id,
            'element_label': self.element_label,
            'element_description': self.element_description,
            'parent_range': self.parent_range,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'values': [val.to_dict() for val in self.values]
        }


class CustomRangeValue(db.Model):
    """Values for custom ranges."""
    __tablename__ = 'custom_range_values'
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True)
    custom_range_id = Column(Integer, ForeignKey('custom_ranges.id', ondelete='CASCADE'), 
                           nullable=False)
    value = Column(String(255), nullable=False,
                  comment="Value of the range element")
    label = Column(Text,
                  comment="Label for the value")
    description = Column(Text,
                        comment="Description for the value")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f'<CustomRangeValue id={self.id} range_id={self.custom_range_id} value={self.value}>'

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'custom_range_id': self.custom_range_id,
            'value': self.value,
            'label': self.label,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }