"""
Dictionary Models for Hunspell Dictionary Management.

Provides models for project-scoped and user-personalized dictionaries.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.workset_models import db


class ProjectDictionary(db.Model):
    """
    Project-specific Hunspell dictionary.

    Each project can have multiple dictionaries for different languages.
    Dictionaries are stored as .dic and .aff file pairs.
    """
    __tablename__ = 'project_dictionaries'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    project_id = db.Column(
        db.Integer,
        db.ForeignKey('project_settings.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Dictionary metadata
    name = db.Column(db.String(255), nullable=False)
    lang_code = db.Column(db.String(20), nullable=False)  # en_US, seh-fonipa, etc.
    description = db.Column(db.Text, nullable=True)

    # File paths (relative to project dictionary directory)
    dic_file = db.Column(db.String(255), nullable=False)
    aff_file = db.Column(db.String(255), nullable=False)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)  # Fallback for unknown langs

    # Metadata
    uploaded_by = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer, nullable=True)  # bytes

    # Relationship
    project = db.relationship(
        'ProjectSettings',
        backref=db.backref('dictionaries', lazy='dynamic', cascade='all, delete-orphan')
    )

    __table_args__ = (
        db.UniqueConstraint(
            'project_id', 'lang_code',
            name='uq_project_lang_code'
        ),
        db.Index('ix_project_dicts_lang', 'lang_code'),
    )

    def __repr__(self) -> str:
        return f"<ProjectDictionary {self.lang_code}:{self.name}>"

    @property
    def storage_path(self) -> str:
        """Get the directory path for this dictionary's files."""
        return os.path.join(
            'uploads', 'dictionaries', 'projects',
            str(self.project_id), self.id
        )

    @property
    def dic_path(self) -> str:
        """Get the full path to the .dic file."""
        return os.path.join(self.storage_path, self.dic_file)

    @property
    def aff_path(self) -> str:
        """Get the full path to the .aff file."""
        return os.path.join(self.storage_path, self.aff_file)

    def to_summary(self) -> Dict[str, Any]:
        """Convert to summary dict for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'lang_code': self.lang_code,
            'description': self.description,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'file_size': self.file_size
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to full dict including file paths."""
        return {
            **self.to_summary(),
            'dic_file': self.dic_file,
            'aff_file': self.aff_file,
            'storage_path': self.storage_path,
            'uploaded_by': self.uploaded_by
        }

    @classmethod
    def create_new(
        cls,
        project_id: int,
        name: str,
        lang_code: str,
        dic_file: str,
        aff_file: str,
        uploaded_by: Optional[str] = None,
        description: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> 'ProjectDictionary':
        """Create a new dictionary with UUID."""
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            lang_code=lang_code,
            dic_file=dic_file,
            aff_file=aff_file,
            uploaded_by=uploaded_by,
            description=description,
            file_size=file_size,
            is_active=True,
            is_default=False
        )

    @classmethod
    def get_by_lang_code(cls, project_id: str, lang_code: str) -> Optional['ProjectDictionary']:
        """Get dictionary by language code for a project."""
        return cls.query.filter(
            cls.project_id == project_id,
            cls.lang_code == lang_code,
            cls.is_active == True
        ).first()

    @classmethod
    def get_default(cls, project_id: str) -> Optional['ProjectDictionary']:
        """Get the default dictionary for a project."""
        return cls.query.filter(
            cls.project_id == project_id,
            cls.is_default == True,
            cls.is_active == True
        ).first()

    @classmethod
    def get_ipa_dictionary(cls, project_id: str) -> Optional['ProjectDictionary']:
        """Get the IPA dictionary (seh-fonipa) for a project."""
        return cls.get_by_lang_code(project_id, 'seh-fonipa')

    @classmethod
    def get_for_language(
        cls,
        project_id: str,
        lang_code: str
    ) -> Optional['ProjectDictionary']:
        """
        Get dictionary for a specific language code.

        First tries exact match, then falls back to base language match.
        For example, en_GB falls back to en if en_GB not found.
        """
        # Try exact match
        dictionary = cls.get_by_lang_code(project_id, lang_code)
        if dictionary:
            return dictionary

        # Try base language match (e.g., en_US -> en)
        base_lang = lang_code.split('_')[0].split('-')[0]
        if base_lang != lang_code:
            return cls.get_by_lang_code(project_id, base_lang)

        return cls.get_default(project_id)

    def files_exist(self) -> bool:
        """Check if dictionary files exist on disk."""
        return os.path.exists(self.dic_path) and os.path.exists(self.aff_path)

    def delete_files(self) -> bool:
        """Delete dictionary files from disk."""
        try:
            import shutil
            storage = self.storage_path
            if os.path.exists(storage):
                shutil.rmtree(storage)
            return True
        except Exception:
            return False


class UserDictionary(db.Model):
    """
    User-specific dictionary entries.

    Users can add custom words or upload their own dictionaries
    that apply across all projects they have access to.
    """
    __tablename__ = 'user_dictionaries'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Dictionary metadata
    name = db.Column(db.String(255), nullable=False)
    lang_code = db.Column(db.String(20), nullable=False)

    # File paths (user-specific storage)
    dic_file = db.Column(db.String(255), nullable=True)
    aff_file = db.Column(db.String(255), nullable=True)

    # Custom words (alternative to file-based)
    custom_words = db.Column(db.JSON, nullable=True)  # List of strings

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationship
    user = db.relationship(
        'User',
        backref=db.backref('dictionaries', lazy='dynamic', cascade='all, delete-orphan')
    )

    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'lang_code', 'name',
            name='uq_user_lang_name'
        ),
        db.Index('ix_user_dicts_lang', 'lang_code'),
    )

    def __repr__(self) -> str:
        return f"<UserDictionary {self.user_id}:{self.lang_code}:{self.name}>"

    @property
    def storage_path(self) -> str:
        """Get the directory path for this dictionary's files."""
        return os.path.join(
            'uploads', 'dictionaries', 'users',
            str(self.user_id), self.id
        )

    def to_summary(self) -> Dict[str, Any]:
        """Convert to summary dict for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'lang_code': self.lang_code,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'word_count': len(self.custom_words) if self.custom_words else None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to full dict."""
        return {
            **self.to_summary(),
            'dic_file': self.dic_file,
            'aff_file': self.aff_file,
            'custom_words': self.custom_words
        }

    @classmethod
    def create_custom_words(
        cls,
        user_id: int,
        name: str,
        lang_code: str,
        words: List[str]
    ) -> 'UserDictionary':
        """Create a custom words dictionary."""
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            lang_code=lang_code,
            custom_words=list(set(words))  # Deduplicate
        )

    @classmethod
    def get_by_lang_code(cls, user_id: int, lang_code: str) -> List['UserDictionary']:
        """Get all dictionaries for a user and language."""
        return cls.query.filter(
            cls.user_id == user_id,
            cls.lang_code == lang_code,
            cls.is_active == True
        ).all()

    def add_word(self, word: str) -> None:
        """Add a word to custom words list."""
        if not self.custom_words:
            self.custom_words = []
        if word not in self.custom_words:
            self.custom_words.append(word)

    def add_words(self, words: List[str]) -> None:
        """Add multiple words."""
        for word in words:
            self.add_word(word)

    def remove_word(self, word: str) -> bool:
        """Remove a word from custom words list."""
        if self.custom_words and word in self.custom_words:
            self.custom_words.remove(word)
            return True
        return False

    def get_all_words(self) -> List[str]:
        """Get all custom words."""
        return self.custom_words or []


class SystemDictionary(db.Model):
    """
    Server-installed system dictionaries.

    These are hunspell dictionaries installed on the server
    (e.g., via apt package manager).
    """
    __tablename__ = 'system_dictionaries'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    lang_code = db.Column(db.String(20), nullable=False, unique=True)
    dic_path = db.Column(db.String(512), nullable=False)  # Full path to .dic
    aff_path = db.Column(db.String(512), nullable=False)  # Full path to .aff
    is_available = db.Column(db.Boolean, default=True)
    word_count = db.Column(db.Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<SystemDictionary {self.lang_code}:{self.name}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'lang_code': self.lang_code,
            'is_available': self.is_available,
            'word_count': self.word_count
        }
