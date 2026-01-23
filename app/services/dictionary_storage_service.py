"""
Dictionary Storage Service.

Handles file storage and retrieval for hunspell dictionaries.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models.dictionary_models import ProjectDictionary, UserDictionary


logger = logging.getLogger(__name__)


@dataclass
class DictionaryMetadata:
    """Metadata extracted from a hunspell dictionary file."""
    lang_code: str
    word_count: int
    name: str
    encoding: str = 'utf-8'


class DictionaryStorageService:
    """
    Service for managing dictionary file storage.

    Handles:
    - Creating storage directories
    - Saving uploaded dictionary files
    - Validating .dic and .aff file formats
    - Extracting metadata from dictionary files
    - Cleaning up dictionary files
    """

    # Base storage directories
    PROJECT_DICT_DIR = 'uploads/dictionaries/projects'
    USER_DICT_DIR = 'uploads/dictionaries/users'

    # Maximum file sizes
    MAX_DIC_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_AFF_SIZE = 2 * 1024 * 1024   # 2 MB

    # Allowed encodings
    ENCODINGS = ['utf-8', 'latin-1', 'cp1252']

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize storage service.

        Args:
            base_path: Base path for storage (defaults to app root)
        """
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent.parent
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure base storage directories exist."""
        project_dir = self.base_path / self.PROJECT_DICT_DIR
        user_dir = self.base_path / self.USER_DICT_DIR

        project_dir.mkdir(parents=True, exist_ok=True)
        user_dir.mkdir(parents=True, exist_ok=True)

    def get_project_storage_path(self, project_id: int, dict_id: str) -> str:
        """Get the full storage path for a project dictionary."""
        return str(self.base_path / self.PROJECT_DICT_DIR / str(project_id) / dict_id)

    def get_user_storage_path(self, user_id: int, dict_id: str) -> str:
        """Get the full storage path for a user dictionary."""
        return str(self.base_path / self.USER_DICT_DIR / str(user_id) / dict_id)

    def validate_and_save_project_dictionary(
        self,
        project_id: int,
        dic_file: Any,  # FileStorage
        aff_file: Optional[Any] = None,
        name: Optional[str] = None,
        lang_code: Optional[str] = None
    ) -> Tuple[ProjectDictionary, List[str]]:
        """
        Validate and save a project dictionary.

        Args:
            project_id: Project ID
            dic_file: Uploaded .dic file
            aff_file: Uploaded .aff file (optional for custom words only)
            name: Optional dictionary name
            lang_code: Optional language code

        Returns:
            Tuple of (ProjectDictionary, list of warnings)

        Raises:
            ValueError: If validation fails
        """
        warnings = []

        # Validate .dic file
        dic_content = self._read_file_content(dic_file)
        self._validate_dic_format(dic_content)

        # Extract metadata from .dic
        extracted_metadata = self._extract_dic_metadata(dic_content)

        if not lang_code:
            lang_code = extracted_metadata.lang_code
        if not name:
            name = extracted_metadata.name

        # Validate language code format
        if not self._is_valid_lang_code(lang_code):
            raise ValueError(f"Invalid language code: {lang_code}")

        # Check file sizes
        dic_size = len(dic_content.encode(extracted_metadata.encoding))
        if dic_size > self.MAX_DIC_SIZE:
            raise ValueError(f".dic file too large: {dic_size} bytes (max {self.MAX_DIC_SIZE})")

        # Create dictionary record
        dict_id = str(uuid.uuid4())
        storage_path = self.get_project_storage_path(project_id, dict_id)
        storage_path.mkdir(parents=True, exist_ok=True)

        # Save .dic file
        dic_filename = f'{lang_code}.dic'
        dic_path = storage_path / dic_filename
        with open(dic_path, 'w', encoding=extracted_metadata.encoding) as f:
            f.write(dic_content)

        # Handle .aff file
        aff_filename = None
        if aff_file:
            aff_content = self._read_file_content(aff_file)
            self._validate_aff_format(aff_content)

            aff_size = len(aff_content.encode('utf-8'))
            if aff_size > self.MAX_AFF_SIZE:
                raise ValueError(f".aff file too large: {aff_size} bytes (max {self.MAX_AFF_SIZE})")

            aff_filename = f'{lang_code}.aff'
            aff_path = storage_path / aff_filename
            with open(aff_path, 'w', encoding='utf-8') as f:
                f.write(aff_content)

        # Create database record
        dictionary = ProjectDictionary.create_new(
            project_id=project_id,
            name=name,
            lang_code=lang_code,
            dic_file=dic_filename,
            aff_file=aff_filename,
            file_size=dic_size
        )

        return dictionary, warnings

    def validate_and_save_user_dictionary(
        self,
        user_id: int,
        dic_file: Optional[Any] = None,
        aff_file: Optional[Any] = None,
        custom_words: Optional[List[str]] = None,
        name: Optional[str] = None,
        lang_code: Optional[str] = None
    ) -> Tuple[UserDictionary, List[str]]:
        """
        Validate and save a user dictionary.

        Args:
            user_id: User ID
            dic_file: Uploaded .dic file (optional)
            aff_file: Uploaded .aff file (optional)
            custom_words: List of custom words (alternative to files)
            name: Optional dictionary name
            lang_code: Language code (required)

        Returns:
            Tuple of (UserDictionary, list of warnings)

        Raises:
            ValueError: If validation fails
        """
        warnings = []

        if not lang_code:
            raise ValueError("Language code is required for user dictionaries")

        if not self._is_valid_lang_code(lang_code):
            raise ValueError(f"Invalid language code: {lang_code}")

        # Handle file-based dictionary
        if dic_file:
            dic_content = self._read_file_content(dic_file)
            self._validate_dic_format(dic_content)
            extracted_metadata = self._extract_dic_metadata(dic_content)

            if not name:
                name = extracted_metadata.name
            if not lang_code:
                lang_code = extracted_metadata.lang_code

            dict_id = str(uuid.uuid4())
            storage_path = self.get_user_storage_path(user_id, dict_id)
            storage_path.mkdir(parents=True, exist_ok=True)

            # Save files
            dic_filename = f'{lang_code}.dic'
            dic_path = storage_path / dic_filename
            with open(dic_path, 'w', encoding=extracted_metadata.encoding) as f:
                f.write(dic_content)

            if aff_file:
                aff_content = self._read_file_content(aff_file)
                self._validate_aff_format(aff_content)

                aff_filename = f'{lang_code}.aff'
                aff_path = storage_path / aff_filename
                with open(aff_path, 'w', encoding='utf-8') as f:
                    f.write(aff_content)

            dictionary = UserDictionary(
                id=dict_id,
                user_id=user_id,
                name=name or f'Dictionary ({lang_code})',
                lang_code=lang_code,
                dic_file=dic_filename,
                aff_file=aff_filename if aff_file else None
            )

        # Handle custom words
        elif custom_words:
            dictionary = UserDictionary.create_custom_words(
                user_id=user_id,
                name=name or f'Custom words ({lang_code})',
                lang_code=lang_code,
                words=custom_words
            )

        else:
            raise ValueError("Either dic_file or custom_words must be provided")

        return dictionary, warnings

    def delete_dictionary_files(self, dictionary: ProjectDictionary) -> bool:
        """Delete dictionary files from storage."""
        try:
            storage_path = Path(dictionary.storage_path)
            if storage_path.exists():
                shutil.rmtree(storage_path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete dictionary files: {e}")
            return False

    def _read_file_content(self, file: Any) -> str:
        """Read file content with encoding detection."""
        # Try different encodings
        for encoding in self.ENCODINGS:
            try:
                file.seek(0)
                content = file.read().decode(encoding)
                return content
            except UnicodeDecodeError:
                continue

        # Last resort: read as bytes and replace invalid chars
        file.seek(0)
        content = file.read().decode('utf-8', errors='replace')
        return content

    def _validate_dic_format(self, content: str) -> None:
        """Validate .dic file format."""
        if not content or not content.strip():
            raise ValueError("Empty .dic file")

        lines = content.strip().split('\n')

        # Check that lines look like words (not binary data)
        non_word_lines = 0
        for line in lines[:100]:  # Check first 100 lines
            line = line.strip()
            if not line:
                continue
            # Skip comments and numeric entries
            if line.startswith('#') or line.isdigit():
                continue
            # Check for valid word characters
            if not re.match(r"^[\w'\-/]+$", line):
                non_word_lines += 1

        if non_word_lines > len(lines) * 0.1:  # More than 10% invalid
            raise ValueError("Invalid .dic file format: contains non-word characters")

    def _validate_aff_format(self, content: str) -> None:
        """Validate .aff file format."""
        if not content.strip():
            raise ValueError("Empty .aff file")

        # Check for valid hunspell affix rules
        valid_prefixes = ('SET', 'FLAG', 'AF', 'AM', 'PFX', 'SFX', 'REP', 'MAP')
        lines = content.split('\n')[:50]  # Check first 50 lines

        has_valid_prefix = any(
            line.strip().upper().startswith(valid_prefixes)
            for line in lines
        )

        if not has_valid_prefix:
            raise ValueError("Invalid .aff file format: missing hunspell directives")

    def _extract_dic_metadata(self, content: str) -> DictionaryMetadata:
        """Extract metadata from .dic file."""
        lines = content.strip().split('\n')

        # Count words (non-comment, non-empty lines)
        word_count = 0
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.isdigit():
                word_count += 1

        # Try to detect language code from filename hint or first word
        # This is a best-effort detection
        lang_code = 'unknown'

        # Common language code patterns
        for line in lines[:10]:
            line = line.strip()
            if line.startswith('#'):
                # Look for language hint in comment
                match = re.search(r'lang\s*[:=]\s*([a-zA-Z_]+)', line, re.IGNORECASE)
                if match:
                    lang_code = match.group(1).replace(' ', '_')
                    break

        # Default name based on language code
        name = f"Dictionary ({lang_code})"

        return DictionaryMetadata(
            lang_code=lang_code,
            word_count=word_count,
            name=name,
            encoding='utf-8'
        )

    def _is_valid_lang_code(self, code: str) -> bool:
        """Check if string looks like a valid language code."""
        import re
        # RFC 4646 format: en, en_US, seh-fonipa, zh-Hans
        # Accept both underscores and hyphens as separators, case-insensitive
        return bool(re.match(r'^[a-zA-Z]{2,3}([-_][a-zA-Z0-9]+)*$', code))

    def get_dictionary_stats(self, project_id: int) -> Dict[str, Any]:
        """Get storage statistics for a project's dictionaries."""
        project_dir = self.base_path / self.PROJECT_DICT_DIR / str(project_id)

        if not project_dir.exists():
            return {
                'dictionary_count': 0,
                'total_size': 0,
                'storage_path': str(project_dir)
            }

        total_size = 0
        dict_count = 0

        for dict_dir in project_dir.iterdir():
            if dict_dir.is_dir():
                dict_count += 1
                for file in dict_dir.rglob('*'):
                    if file.is_file():
                        total_size += file.stat().st_size

        return {
            'dictionary_count': dict_count,
            'total_size': total_size,
            'storage_path': str(project_dir)
        }

    def cleanup_orphaned_files(self, project_id: int) -> int:
        """
        Clean up dictionary files that don't have database records.

        Args:
            project_id: Project ID

        Returns:
            Number of directories removed
        """
        from app.models.dictionary_models import ProjectDictionary

        project_dir = self.base_path / self.PROJECT_DICT_DIR / str(project_id)

        if not project_dir.exists():
            return 0

        # Get existing dictionary IDs
        existing_ids = set(
            d.id for d in
            ProjectDictionary.query.filter_by(project_id=project_id).all()
        )

        # Remove orphaned directories
        removed = 0
        for dict_dir in project_dir.iterdir():
            if dict_dir.is_dir() and dict_dir.name not in existing_ids:
                shutil.rmtree(dict_dir)
                removed += 1

        return removed


# Singleton instance
dictionary_storage = DictionaryStorageService()


def get_storage_service() -> DictionaryStorageService:
    """Get the global storage service instance."""
    return dictionary_storage
