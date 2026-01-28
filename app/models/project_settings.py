from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.models.workset_models import db

# Association table for project members (many-to-many, TODO: implement User model)
project_members = Table(
    "project_members",
    db.metadata,
    Column(
        "project_id",
        Integer,
        ForeignKey("project_settings.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
)


class ProjectSettings(db.Model):
    __tablename__ = "project_settings"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True)
    project_name = Column(String(255), unique=True, nullable=False)
    basex_db_name = Column(String(255), nullable=False)
    source_language = Column(JSON, nullable=False)
    target_languages = Column(JSON, nullable=False, default=list)
    backup_settings = Column(JSON, nullable=True, default=dict)
    settings_json = Column(
        JSON, nullable=False, default=dict
    )  # Add missing column to match database schema
    field_visibility_defaults = Column(
        JSON, nullable=True, default=dict
    )  # Project-level defaults for field visibility (sections and fields)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # TODO: Implement User model and relationships
    owner_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    owner = relationship("User", backref="owned_projects", foreign_keys=[owner_id])
    members: List["User"] = relationship(
        "User", secondary=project_members, backref="member_projects"
    )

    def __repr__(self) -> str:
        return f"<ProjectSettings id={self.id} name={self.project_name}>"

    @property
    def serialization_dict(self):
        return {
            "project_name": self.project_name,
            "source_language": self.source_language,
            "target_languages": self.target_languages,
            "backup_settings": self.backup_settings or {},
            "field_visibility_defaults": self.field_visibility_defaults or {},
        }


# User model for authentication and project ownership
class User(db.Model):
    __tablename__ = "users"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    username: str = Column(String(80), unique=True, nullable=False, index=True)
    email: str = Column(String(120), unique=True, nullable=False, index=True)
    password_hash: str = Column(String(255), nullable=False)
    first_name: str = Column(String(100), nullable=True)
    last_name: str = Column(String(100), nullable=True)
    is_active: bool = Column(db.Boolean, default=True, nullable=False)
    is_admin: bool = Column(db.Boolean, default=False, nullable=False)
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = Column(DateTime, nullable=True)
    avatar_url: Optional[str] = Column(String(500), nullable=True)
    bio: Optional[str] = Column(db.Text, nullable=True)
    preferences: dict = Column(JSON, nullable=True, default=dict)

    # Flask-Login integration
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} email={self.email}>"

    def to_dict(self, include_private=False):
        """Serialize user to dictionary."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email if include_private else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}"
            if self.first_name and self.last_name
            else self.username,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "avatar_url": self.avatar_url,
            "bio": self.bio if include_private else None,
        }
        return {k: v for k, v in data.items() if v is not None or include_private}
