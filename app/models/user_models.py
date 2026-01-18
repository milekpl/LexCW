"""
User management models for authentication, roles, and messaging.
"""

from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum

from app.models.workset_models import db


class UserRole(enum.Enum):
    """User roles for role-based access control."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ProjectRole(db.Model):
    """Association table for user project membership with roles."""

    __tablename__ = "project_roles"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: int = Column(
        Integer, ForeignKey("project_settings.id", ondelete="CASCADE"), nullable=False
    )
    role: str = Column(SQLEnum(UserRole), nullable=False, default=UserRole.MEMBER)
    granted_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    granted_by_user_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", foreign_keys=[user_id], backref="project_roles")
    project = relationship("ProjectSettings", backref="user_roles")
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])

    def __repr__(self) -> str:
        return f"<ProjectRole user_id={self.user_id} project_id={self.project_id} role={self.role.value}>"


class Message(db.Model):
    """Messages for entry discussions and collaboration."""

    __tablename__ = "messages"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    entry_id: str = Column(String(255), nullable=False, index=True)
    workset_id: Optional[int] = Column(
        Integer, ForeignKey("worksets.id", ondelete="CASCADE"), nullable=True
    )
    sender_user_id: int = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_user_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    parent_message_id: Optional[int] = Column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )
    message_text: str = Column(Text, nullable=False)
    is_read: bool = Column(Boolean, default=False, nullable=False)
    created_at: datetime = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Optional[datetime] = Column(
        DateTime, onupdate=lambda: datetime.now(timezone.utc)
    )

    sender = relationship(
        "User", foreign_keys=[sender_user_id], backref="sent_messages"
    )
    recipient = relationship(
        "User", foreign_keys=[recipient_user_id], backref="received_messages"
    )
    parent = relationship("Message", remote_side=[id], backref="replies")
    workset = relationship("Workset", backref="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} entry_id={self.entry_id} sender_id={self.sender_user_id}>"

    def to_dict(self, include_replies=False):
        """Serialize message to dictionary."""
        data = {
            "id": self.id,
            "entry_id": self.entry_id,
            "workset_id": self.workset_id,
            "sender": self.sender.to_dict() if self.sender else None,
            "recipient": self.recipient.to_dict() if self.recipient else None,
            "message_text": self.message_text,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "parent_message_id": self.parent_message_id,
        }

        if include_replies and hasattr(self, "replies"):
            data["replies"] = [
                reply.to_dict(include_replies=False) for reply in self.replies
            ]

        return data


class ActivityLog(db.Model):
    """Audit log for user actions on entries and other entities."""

    __tablename__ = "activity_logs"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    user_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: str = Column(String(50), nullable=False, index=True)
    entity_type: str = Column(String(50), nullable=False, index=True)
    entity_id: str = Column(String(255), nullable=False, index=True)
    project_id: Optional[int] = Column(
        Integer, ForeignKey("project_settings.id", ondelete="CASCADE"), nullable=True
    )
    changes: Optional[dict] = Column(JSON, nullable=True)
    description: Optional[str] = Column(Text, nullable=True)
    timestamp: datetime = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    ip_address: Optional[str] = Column(String(45), nullable=True)
    user_agent: Optional[str] = Column(String(500), nullable=True)

    user = relationship("User", backref="activity_logs")
    project = relationship("ProjectSettings", backref="activity_logs")

    def __repr__(self) -> str:
        return f"<ActivityLog id={self.id} action={self.action} entity={self.entity_type}:{self.entity_id}>"

    def to_dict(self):
        """Serialize activity log to dictionary."""
        return {
            "id": self.id,
            "user": self.user.to_dict() if self.user else {"username": "System"},
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "project_id": self.project_id,
            "changes": self.changes,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "ip_address": self.ip_address,
        }


class Notification(db.Model):
    """Notifications for users about messages, mentions, and activity."""

    __tablename__ = "notifications"
    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: str = Column(String(50), nullable=False)
    title: str = Column(String(255), nullable=False)
    message: str = Column(Text, nullable=False)
    link_url: Optional[str] = Column(String(500), nullable=True)
    is_read: bool = Column(Boolean, default=False, nullable=False)
    created_at: datetime = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    read_at: Optional[datetime] = Column(DateTime, nullable=True)
    related_message_id: Optional[int] = Column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )
    related_entry_id: Optional[str] = Column(String(255), nullable=True)

    user = relationship("User", backref="notifications")
    related_message = relationship("Message", backref="notifications")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} type={self.notification_type}>"

    def to_dict(self):
        """Serialize notification to dictionary."""
        return {
            "id": self.id,
            "notification_type": self.notification_type,
            "title": self.title,
            "message": self.message,
            "link_url": self.link_url,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "related_entry_id": self.related_entry_id,
        }
