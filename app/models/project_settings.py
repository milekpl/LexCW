from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.models.workset_models import db

# Association table for project members (many-to-many, TODO: implement User model)
project_members = Table(
    'project_members', db.metadata,
    Column('project_id', Integer, ForeignKey('project_settings.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)

class ProjectSettings(db.Model):
    __tablename__ = 'project_settings'
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True)
    project_name = Column(String(255), unique=True, nullable=False)
    basex_db_name = Column(String(255), nullable=False)
    source_language = Column(JSON, nullable=False)
    target_languages = Column(JSON, nullable=False, default=list)
    backup_settings = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # TODO: Implement User model and relationships
    owner_id: Optional[int] = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    owner = relationship('User', backref='owned_projects', foreign_keys=[owner_id])
    members: List['User'] = relationship('User', secondary=project_members, backref='member_projects')

    def __repr__(self) -> str:
        return f'<ProjectSettings id={self.id} name={self.project_name}>'

    @property
    def settings_json(self):
        return {
            'project_name': self.project_name,
            'source_language': self.source_language,
            'target_languages': self.target_languages,
            'backup_settings': self.backup_settings or {}
        }

# TODO: Define User model for project ownership and membership
class User(db.Model):
    __tablename__ = 'users'
    id: int = db.Column(db.Integer, primary_key=True)
    # Add any other required fields if needed
