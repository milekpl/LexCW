"""Display profile models for CSS-based entry rendering.

This module defines SQLAlchemy models for managing display profiles,
which control how LIFT entries are rendered with CSS styling.
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.workset_models import db


class DisplayProfile(db.Model):
    """Display profile for controlling entry rendering with CSS.
    
    A display profile defines:
    - Which LIFT elements to display
    - CSS classes for each element
    - Element ordering and visibility
    - Prefixes/suffixes for elements
    """
    
    __tablename__ = 'display_profiles'
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(255), unique=True, nullable=False, index=True)
    description: Optional[str] = Column(Text, nullable=True)
    
    # Custom CSS styles for this profile
    custom_css: Optional[str] = Column(Text, nullable=True)
    
    # Global display settings
    show_subentries: bool = Column(Boolean, default=False, nullable=False)
    number_senses: bool = Column(Boolean, default=True, nullable=False)  # Auto-number senses with CSS
    
    # Profile metadata
    is_default: bool = Column(Boolean, default=False, nullable=False)
    is_system: bool = Column(Boolean, default=False, nullable=False)  # System profiles can't be deleted
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                                   onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Ownership (optional, for future multi-user support)
    owner_id: Optional[int] = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    elements: List['ProfileElement'] = relationship(
        'ProfileElement',
        back_populates='profile',
        cascade='all, delete-orphan',
        order_by='ProfileElement.display_order'
    )
    
    def __repr__(self) -> str:
        return f'<DisplayProfile id={self.id} name={self.name}>'
    
    def to_dict(self) -> dict:
        """Convert profile to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'custom_css': self.custom_css,
            'show_subentries': self.show_subentries,
            'number_senses': self.number_senses,
            'is_default': self.is_default,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'elements': [elem.to_dict() for elem in self.elements] if self.elements else []
        }
    
    def to_config(self) -> dict:
        """Convert profile to configuration format for CSS mapping service."""
        return {
            'name': self.name,
            'description': self.description,
            'elements': {
                elem.lift_element: {
                    'css_class': elem.css_class,
                    'visibility': elem.visibility,
                    'order': elem.display_order,
                    'prefix': elem.prefix or '',
                    'suffix': elem.suffix or ''
                }
                for elem in self.elements
            }
        }


class ProfileElement(db.Model):
    """Element configuration within a display profile.
    
    Defines how a specific LIFT element should be rendered:
    - CSS classes to apply
    - Visibility setting (always/if-content/never)
    - Display order
    - Text prefix/suffix
    """
    
    __tablename__ = 'profile_elements'
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    profile_id: int = Column(Integer, ForeignKey('display_profiles.id', ondelete='CASCADE'), 
                             nullable=False, index=True)
    
    # LIFT element configuration
    lift_element: str = Column(String(100), nullable=False)  # e.g., "lexical-unit", "sense"
    css_class: str = Column(String(255), nullable=False, default='')
    visibility: str = Column(String(50), nullable=False, default='if-content')  # always/if-content/never
    display_order: int = Column(Integer, nullable=False, default=0)
    
    # Language-specific configuration
    language_filter: str = Column(String(10), nullable=False, default='*')  # '*' for all, 'en', 'pl', etc.
    
    # Optional text decorations
    prefix: Optional[str] = Column(String(100), nullable=True)
    suffix: Optional[str] = Column(String(100), nullable=True)
    
    # Additional configuration (JSON for future extensibility)
    config: Optional[dict] = Column(JSON, nullable=True)
    
    # Relationships
    profile: 'DisplayProfile' = relationship('DisplayProfile', back_populates='elements')
    
    def __repr__(self) -> str:
        return f'<ProfileElement id={self.id} element={self.lift_element} order={self.display_order}>'
    
    def to_dict(self) -> dict:
        """Convert element to dictionary representation."""
        return {
            'id': self.id,
            'profile_id': self.profile_id,
            'lift_element': self.lift_element,
            'css_class': self.css_class,
            'visibility': self.visibility,
            'display_order': self.display_order,
            'language_filter': self.language_filter,
            'prefix': self.prefix,
            'suffix': self.suffix,
            'config': self.config
        }
