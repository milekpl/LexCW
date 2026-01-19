"""
Validation Result Cache Models.

Database models for persistent storage of validation results.
Provides fallback when Redis is unavailable and long-term persistence.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models.workset_models import db


class ValidationResultCache(db.Model):
    """
    Persistent storage for validation results.

    Stores results from spell checkers (hunspell) and grammar checkers
    (LanguageTool) keyed by entry_id and date_modified for automatic
    invalidation when entries change.
    """
    __tablename__ = 'validation_result_cache'

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.String(255), nullable=False, index=True)
    date_modified = db.Column(db.String(50), nullable=False)  # ISO8601 timestamp

    # Validator type: 'hunspell', 'languagetool'
    validator_type = db.Column(db.String(50), nullable=False, index=True)

    # Language code for this validation
    lang_code = db.Column(db.String(20), nullable=True)

    # Content hash for cache key (SHA256, truncated)
    content_hash = db.Column(db.String(64), nullable=True)

    # Hunspell results
    hunspell_valid = db.Column(db.Boolean, nullable=True)
    hunspell_suggestions = db.Column(db.JSON, nullable=True)  # {word: [suggestions]}
    hunspell_misspellings = db.Column(db.JSON, nullable=True)  # [word1, word2]

    # LanguageTool results
    lt_target_lang = db.Column(db.String(20), nullable=True)
    lt_matches = db.Column(db.JSON, nullable=True)  # List of match dicts
    lt_bitext_quality = db.Column(db.JSON, nullable=True)  # Bitext assessment
    lt_errors = db.Column(db.JSON, nullable=True)  # Error list

    # Full cached result as JSON (for complete result caching)
    cached_result = db.Column(db.JSON, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)

    __table_args__ = (
        db.UniqueConstraint(
            'entry_id', 'validator_type', 'content_hash',
            name='uq_validation_cache_entry'
        ),
        db.Index('ix_validation_cache_lookup', 'entry_id', 'validator_type', 'lang_code'),
        db.Index('ix_validation_cache_expiry', 'expires_at'),
    )

    def __repr__(self) -> str:
        return f"<ValidationResultCache {self.validator_type}:{self.entry_id}>"

    @classmethod
    def get_cached_result(
        cls,
        entry_id: str,
        validator_type: str,
        content_hash: Optional[str] = None
    ) -> Optional['ValidationResultCache']:
        """
        Get cached result by entry_id and validator type.

        Args:
            entry_id: The entry identifier
            validator_type: Type of validator (hunspell, languagetool)
            content_hash: Optional content hash for exact match

        Returns:
            Cached entry or None if not found
        """
        query = cls.query.filter(
            cls.entry_id == entry_id,
            cls.validator_type == validator_type
        )
        if content_hash:
            query = query.filter(cls.content_hash == content_hash)
        return query.first()

    @classmethod
    def get_hunspell_result(
        cls,
        entry_id: str,
        date_modified: str,
        content_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get hunspell cached result.

        Args:
            entry_id: Entry identifier
            date_modified: Entry's date_modified timestamp
            content_hash: Hash of validated content

        Returns:
            Dict with 'valid', 'suggestions', 'misspellings' or None
        """
        cache_entry = cls.query.filter(
            cls.entry_id == entry_id,
            cls.validator_type == 'hunspell',
            cls.date_modified == date_modified,
            cls.content_hash == content_hash
        ).first()

        if cache_entry:
            return {
                'valid': cache_entry.hunspell_valid,
                'suggestions': cache_entry.hunspell_suggestions or {},
                'misspellings': cache_entry.hunspell_misspellings or []
            }
        return None

    @classmethod
    def get_languagetool_result(
        cls,
        entry_id: str,
        date_modified: str,
        content_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get LanguageTool cached result.

        Args:
            entry_id: Entry identifier
            date_modified: Entry's date_modified timestamp
            content_hash: Hash of validated content

        Returns:
            Dict with 'target_lang', 'matches', 'bitext_quality', 'errors' or None
        """
        cache_entry = cls.query.filter(
            cls.entry_id == entry_id,
            cls.validator_type == 'languagetool',
            cls.date_modified == date_modified,
            cls.content_hash == content_hash
        ).first()

        if cache_entry:
            return {
                'target_lang': cache_entry.lt_target_lang,
                'matches': cache_entry.lt_matches or [],
                'bitext_quality': cache_entry.lt_bitext_quality,
                'errors': cache_entry.lt_errors or []
            }
        return None

    @classmethod
    def save_hunspell_result(
        cls,
        entry_id: str,
        date_modified: str,
        content_hash: str,
        valid: bool,
        suggestions: Dict[str, List[str]],
        misspellings: List[str],
        ttl_days: int = 7
    ) -> 'ValidationResultCache':
        """
        Save hunspell validation result.

        Args:
            entry_id: Entry identifier
            date_modified: Entry's date_modified timestamp
            content_hash: Hash of validated content
            valid: Whether all words are valid
            suggestions: Dict of word -> suggestions list
            misspellings: List of misspelled words
            ttl_days: Days until cache expires

        Returns:
            Created/updated cache entry
        """
        expires_at = datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None

        existing = cls.query.filter(
            cls.entry_id == entry_id,
            cls.validator_type == 'hunspell',
            cls.date_modified == date_modified
        ).first()

        if existing:
            existing.hunspell_valid = valid
            existing.hunspell_suggestions = suggestions
            existing.hunspell_misspellings = misspellings
            existing.content_hash = content_hash
            existing.expires_at = expires_at
            db.session.commit()
            return existing

        cache_entry = cls(
            entry_id=entry_id,
            date_modified=date_modified,
            validator_type='hunspell',
            content_hash=content_hash,
            hunspell_valid=valid,
            hunspell_suggestions=suggestions,
            hunspell_misspellings=misspellings,
            expires_at=expires_at
        )
        db.session.add(cache_entry)
        db.session.commit()
        return cache_entry

    @classmethod
    def save_languagetool_result(
        cls,
        entry_id: str,
        date_modified: str,
        content_hash: str,
        target_lang: Optional[str],
        matches: List[Dict[str, Any]],
        bitext_quality: Optional[Dict[str, Any]] = None,
        errors: Optional[List] = None,
        ttl_days: int = 7
    ) -> 'ValidationResultCache':
        """
        Save LanguageTool validation result.

        Args:
            entry_id: Entry identifier
            date_modified: Entry's date_modified timestamp
            content_hash: Hash of validated content
            target_lang: Detected/used target language
            matches: List of rule matches
            bitext_quality: Bitext quality assessment dict
            errors: List of errors
            ttl_days: Days until cache expires

        Returns:
            Created/updated cache entry
        """
        expires_at = datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None

        existing = cls.query.filter(
            cls.entry_id == entry_id,
            cls.validator_type == 'languagetool',
            cls.date_modified == date_modified
        ).first()

        if existing:
            existing.lt_target_lang = target_lang
            existing.lt_matches = matches
            existing.lt_bitext_quality = bitext_quality
            existing.lt_errors = errors
            existing.content_hash = content_hash
            existing.expires_at = expires_at
            db.session.commit()
            return existing

        cache_entry = cls(
            entry_id=entry_id,
            date_modified=date_modified,
            validator_type='languagetool',
            content_hash=content_hash,
            lt_target_lang=target_lang,
            lt_matches=matches,
            lt_bitext_quality=bitext_quality,
            lt_errors=errors,
            expires_at=expires_at
        )
        db.session.add(cache_entry)
        db.session.commit()
        return cache_entry

    @classmethod
    def invalidate_entry(cls, entry_id: str) -> int:
        """
        Delete all cached results for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Number of deleted entries
        """
        deleted = cls.query.filter(
            cls.entry_id == entry_id
        ).delete()
        db.session.commit()
        return deleted

    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Delete all expired cache entries.

        Returns:
            Number of deleted entries
        """
        deleted = cls.query.filter(
            cls.expires_at < datetime.utcnow()
        ).delete()
        db.session.commit()
        return deleted

    @classmethod
    def get_entries_needing_validation(
        cls,
        entries: List[Dict[str, str]],  # List of {id, date_modified}
        validator_type: str
    ) -> List[str]:
        """
        Filter entries that need validation (not in cache).

        Args:
            entries: List of dicts with 'id' and 'date_modified' keys
            validator_type: Type of validator

        Returns:
            List of entry_ids that need fresh validation
        """
        missing_ids = []

        for entry in entries:
            entry_id = entry['id']
            date_modified = entry['date_modified']

            cached = cls.query.filter(
                cls.entry_id == entry_id,
                cls.validator_type == validator_type,
                cls.date_modified == date_modified
            ).first()

            if not cached:
                missing_ids.append(entry_id)

        return missing_ids

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'entry_id': self.entry_id,
            'date_modified': self.date_modified,
            'validator_type': self.validator_type,
            'lang_code': self.lang_code,
            'hunspell_valid': self.hunspell_valid,
            'hunspell_suggestions': self.hunspell_suggestions,
            'lt_target_lang': self.lt_target_lang,
            'lt_matches': self.lt_matches,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
