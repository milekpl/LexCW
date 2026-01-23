"""
Unit tests for dictionary models.
"""

import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.models.dictionary_models import (
    ProjectDictionary,
    UserDictionary,
    SystemDictionary
)


class TestProjectDictionary(unittest.TestCase):
    """Tests for ProjectDictionary model."""

    def test_create_new(self):
        """Test creating a new dictionary."""
        dictionary = ProjectDictionary.create_new(
            project_id=1,
            name="English (US)",
            lang_code="en_US",
            dic_file="en_US.dic",
            aff_file="en_US.aff",
            uploaded_by="test_user"
        )

        self.assertIsNotNone(dictionary.id)
        self.assertEqual(dictionary.project_id, 1)
        self.assertEqual(dictionary.name, "English (US)")
        self.assertEqual(dictionary.lang_code, "en_US")
        self.assertEqual(dictionary.dic_file, "en_US.dic")
        self.assertEqual(dictionary.aff_file, "en_US.aff")
        self.assertTrue(dictionary.is_active)
        self.assertFalse(dictionary.is_default)

    def test_storage_path(self):
        """Test storage path generation."""
        dictionary = ProjectDictionary(
            id="test-id",
            project_id=1,
            name="Test",
            lang_code="en_US",
            dic_file="en_US.dic",
            aff_file="en_US.aff"
        )

        expected = os.path.join(
            'uploads', 'dictionaries', 'projects', '1', 'test-id'
        )
        self.assertEqual(dictionary.storage_path, expected)

    def test_to_summary(self):
        """Test summary serialization."""
        dictionary = ProjectDictionary(
            id="test-id",
            project_id=1,
            name="English (US)",
            lang_code="en_US",
            dic_file="en_US.dic",
            aff_file="en_US.aff",
            created_at=datetime(2026, 1, 19, 12, 0, 0)
        )

        summary = dictionary.to_summary()

        self.assertEqual(summary['id'], 'test-id')
        self.assertEqual(summary['name'], 'English (US)')
        self.assertEqual(summary['lang_code'], 'en_US')
        self.assertIn('created_at', summary)

    def test_files_exist(self):
        """Test file existence check."""
        dictionary = ProjectDictionary(
            id="test-id",
            project_id=1,
            name="Test",
            lang_code="en_US",
            dic_file="en_US.dic",
            aff_file="en_US.aff"
        )

        # File doesn't exist in test
        self.assertFalse(dictionary.files_exist())


class TestUserDictionary(unittest.TestCase):
    """Tests for UserDictionary model."""

    def test_create_custom_words(self):
        """Test creating a custom words dictionary."""
        dictionary = UserDictionary.create_custom_words(
            user_id=1,
            name="My Custom Words",
            lang_code="en_US",
            words=["lexicographic", "morpheme", "allomorph"]
        )

        self.assertIsNotNone(dictionary.id)
        self.assertEqual(dictionary.user_id, 1)
        self.assertEqual(dictionary.name, "My Custom Words")
        self.assertEqual(dictionary.lang_code, "en_US")
        self.assertEqual(len(dictionary.custom_words), 3)

    def test_add_word(self):
        """Test adding words to custom dictionary."""
        dictionary = UserDictionary(
            id="test-id",
            user_id=1,
            name="Test",
            lang_code="en_US",
            custom_words=["word1"]
        )

        dictionary.add_word("word2")
        self.assertEqual(len(dictionary.custom_words), 2)
        self.assertIn("word2", dictionary.custom_words)

        # Adding duplicate should not increase count
        dictionary.add_word("word2")
        self.assertEqual(len(dictionary.custom_words), 2)

    def test_remove_word(self):
        """Test removing words from custom dictionary."""
        dictionary = UserDictionary(
            id="test-id",
            user_id=1,
            name="Test",
            lang_code="en_US",
            custom_words=["word1", "word2", "word3"]
        )

        result = dictionary.remove_word("word2")
        self.assertTrue(result)
        self.assertNotIn("word2", dictionary.custom_words)
        self.assertEqual(len(dictionary.custom_words), 2)

        # Removing non-existent word
        result = dictionary.remove_word("word4")
        self.assertFalse(result)

    def test_get_all_words(self):
        """Test getting all words."""
        dictionary = UserDictionary(
            id="test-id",
            user_id=1,
            name="Test",
            lang_code="en_US",
            custom_words=["word1", "word2"]
        )

        words = dictionary.get_all_words()
        self.assertEqual(len(words), 2)


class TestSystemDictionary(unittest.TestCase):
    """Tests for SystemDictionary model."""

    def test_to_dict(self):
        """Test serialization."""
        dictionary = SystemDictionary(
            id="test-id",
            name="English (US)",
            lang_code="en_US",
            dic_path="/usr/share/hunspell/en_US.dic",
            aff_path="/usr/share/hunspell/en_US.aff",
            word_count=100000,
            is_available=True
        )

        result = dictionary.to_dict()

        self.assertEqual(result['lang_code'], 'en_US')
        self.assertEqual(result['word_count'], 100000)
        self.assertTrue(result['is_available'])


if __name__ == '__main__':
    unittest.main()
