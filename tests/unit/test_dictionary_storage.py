"""
Unit tests for dictionary storage service.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.services.dictionary_storage_service import (
    DictionaryStorageService,
    DictionaryMetadata
)


class TestDictionaryStorageService(unittest.TestCase):
    """Tests for DictionaryStorageService."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = DictionaryStorageService(base_path=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_ensure_directories(self):
        """Test that directories are created."""
        self.assertTrue(os.path.exists(
            os.path.join(self.temp_dir, 'uploads/dictionaries/projects')
        ))
        self.assertTrue(os.path.exists(
            os.path.join(self.temp_dir, 'uploads/dictionaries/users')
        ))

    def test_get_project_storage_path(self):
        """Test project storage path generation."""
        path = self.storage.get_project_storage_path(1, 'test-id')

        expected = os.path.join(
            self.temp_dir, 'uploads/dictionaries/projects/1/test-id'
        )
        self.assertEqual(path, expected)

    def test_get_user_storage_path(self):
        """Test user storage path generation."""
        path = self.storage.get_user_storage_path(1, 'test-id')

        expected = os.path.join(
            self.temp_dir, 'uploads/dictionaries/users/1/test-id'
        )
        self.assertEqual(path, expected)

    def test_is_valid_lang_code(self):
        """Test language code validation."""
        self.assertTrue(self.storage._is_valid_lang_code('en'))
        self.assertTrue(self.storage._is_valid_lang_code('en_US'))
        self.assertTrue(self.storage._is_valid_lang_code('seh-fonipa'))
        self.assertTrue(self.storage._is_valid_lang_code('zh-Hans'))

        self.assertFalse(self.storage._is_valid_lang_code(''))
        self.assertFalse(self.storage._is_valid_lang_code('e'))
        self.assertFalse(self.storage._is_valid_lang_code('123'))

    def test_validate_dic_format_valid(self):
        """Test validation of valid .dic file."""
        valid_content = """word1
word2
word3
"""
        # Should not raise
        self.storage._validate_dic_format(valid_content)

    def test_validate_dic_format_empty(self):
        """Test validation of empty .dic file."""
        with self.assertRaises(ValueError) as context:
            self.storage._validate_dic_format('')

        self.assertIn('Empty', str(context.exception))

    def test_validate_dic_format_with_comments(self):
        """Test validation of .dic file with comments."""
        content = """# This is a comment
word1
12345
word2
"""
        # Should not raise (comments and numbers are OK)
        self.storage._validate_dic_format(content)

    def test_validate_dic_format_accepts_ipa_unicode_entries(self):
        """Test validation accepts IPA Unicode symbols used in Hunspell dictionaries."""
        content = """5
iː/X
ɪ/X
tʃ/X
ˈ/X
,/X
"""
        # Should not raise for IPA symbols and separators
        self.storage._validate_dic_format(content)

    def test_validate_aff_format_valid(self):
        """Test validation of valid .aff file."""
        valid_content = """SET UTF-8
FLAG long
AF 0
AM ə>ə
"""
        # Should not raise
        self.storage._validate_aff_format(valid_content)

    def test_validate_aff_format_empty(self):
        """Test validation of empty .aff file."""
        with self.assertRaises(ValueError) as context:
            self.storage._validate_aff_format('')

        self.assertIn('Empty', str(context.exception))

    def test_validate_aff_format_missing_directives(self):
        """Test validation of .aff file without hunspell directives."""
        with self.assertRaises(ValueError) as context:
            self.storage._validate_aff_format('random text without hunspell rules')

        self.assertIn('hunspell directives', str(context.exception))

    def test_extract_dic_metadata(self):
        """Test metadata extraction from .dic file."""
        content = """word1
word2
word3
"""
        metadata = self.storage._extract_dic_metadata(content)

        self.assertEqual(metadata.word_count, 3)
        self.assertIsNotNone(metadata.lang_code)

    def test_extract_dic_metadata_with_comment(self):
        """Test metadata extraction with language hint in comment."""
        content = """# lang: en_US
word1
word2
"""
        metadata = self.storage._extract_dic_metadata(content)

        self.assertEqual(metadata.word_count, 2)

    def test_read_file_content_utf8(self):
        """Test reading UTF-8 file."""
        mock_file = MagicMock()
        mock_file.read.return_value = b'test content'
        mock_file.seek = MagicMock()

        content = self.storage._read_file_content(mock_file)
        self.assertEqual(content, 'test content')

    def test_dictionary_stats(self):
        """Test getting dictionary statistics."""
        stats = self.storage.get_dictionary_stats(999)

        self.assertEqual(stats['dictionary_count'], 0)
        self.assertEqual(stats['total_size'], 0)

    def test_cleanup_orphaned_files(self):
        """Test cleanup of orphaned dictionary directories with real DB context."""
        from app import create_app
        from app.models.workset_models import db
        from app.models.project_settings import ProjectSettings
        from app.models.dictionary_models import ProjectDictionary

        app = create_app('testing')
        project_name = "Dictionary Cleanup Test Project"

        with app.app_context():
            db.create_all()

            # Ensure no prior test project with the same name remains.
            existing = ProjectSettings.query.filter_by(project_name=project_name).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()

            project = ProjectSettings(
                project_name=project_name,
                basex_db_name='test_cleanup_dict_storage',
                source_language={'code': 'en', 'name': 'English'},
                target_languages=[],
                settings_json={}
            )
            db.session.add(project)
            db.session.commit()

            tracked_dict = ProjectDictionary.create_new(
                project_id=project.id,
                name='Tracked Dictionary',
                lang_code='en_US',
                dic_file='en_US.dic',
                aff_file='en_US.aff'
            )
            db.session.add(tracked_dict)
            db.session.commit()

            # Create one tracked directory and one orphan directory on disk.
            tracked_path = self.storage.get_project_storage_path(project.id, tracked_dict.id)
            orphan_path = self.storage.get_project_storage_path(project.id, 'orphan-dict-id')
            os.makedirs(tracked_path, exist_ok=True)
            os.makedirs(orphan_path, exist_ok=True)

            removed = self.storage.cleanup_orphaned_files(project.id)

            self.assertEqual(removed, 1)
            self.assertTrue(os.path.exists(tracked_path))
            self.assertFalse(os.path.exists(orphan_path))


class TestDictionaryMetadata(unittest.TestCase):
    """Tests for DictionaryMetadata dataclass."""

    def test_create(self):
        """Test creating metadata."""
        metadata = DictionaryMetadata(
            lang_code='en_US',
            word_count=1000,
            name='English (US)',
            encoding='utf-8'
        )

        self.assertEqual(metadata.lang_code, 'en_US')
        self.assertEqual(metadata.word_count, 1000)
        self.assertEqual(metadata.name, 'English (US)')


if __name__ == '__main__':
    unittest.main()
