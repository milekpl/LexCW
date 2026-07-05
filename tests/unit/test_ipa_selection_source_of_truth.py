"""
Unit tests for IPA dictionary selection source-of-truth and project language service.
"""

import unittest
from unittest.mock import MagicMock, patch
from flask import Flask

from app.models.dictionary_models import ProjectDictionary
from app.services.validation_engine import ValidationEngine
from app.services.project_language_service import ProjectLanguageService


class TestIPASelectionSourceOfTruth(unittest.TestCase):
    """Tests for explicit ipa_dictionary_id resolution and fallback logic."""

    def setUp(self):
        """Create a test Flask application and push app context."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        """Pop app context."""
        self.ctx.pop()

    @patch('app.models.project_settings.ProjectSettings.query')
    @patch('app.models.dictionary_models.ProjectDictionary.query')
    def test_get_ipa_dictionary_uses_settings_id(self, mock_dict_query, mock_proj_query):
        """Test that get_ipa_dictionary uses ipa_dictionary_id from settings when present."""
        mock_project = MagicMock()
        mock_project.settings_json = {
            'spell_check': {
                'ipa_dictionary_id': 'dict-custom-ipa'
            }
        }
        mock_proj_query.get.return_value = mock_project

        custom_dict = ProjectDictionary(
            id='dict-custom-ipa',
            project_id=1,
            name='Custom IPA',
            lang_code='seh-fonipa'
        )
        mock_dict_query.filter.return_value.first.return_value = custom_dict

        result = ProjectDictionary.get_ipa_dictionary(1)
        self.assertEqual(result, custom_dict)
        mock_proj_query.get.assert_called_once_with(1)

    @patch('app.models.project_settings.ProjectSettings.query')
    @patch('app.models.dictionary_models.ProjectDictionary.get_by_lang_code')
    def test_get_ipa_dictionary_fallback_to_lang_code(self, mock_by_lang, mock_proj_query):
        """Test that get_ipa_dictionary falls back to seh-fonipa when settings dictionary id is missing."""
        mock_project = MagicMock()
        mock_project.settings_json = {'spell_check': {}}
        mock_proj_query.get.return_value = mock_project

        fallback_dict = ProjectDictionary(
            id='dict-seh-fonipa',
            project_id=1,
            name='Standard IPA',
            lang_code='seh-fonipa'
        )
        mock_by_lang.return_value = fallback_dict

        result = ProjectDictionary.get_ipa_dictionary(1)
        self.assertEqual(result, fallback_dict)
        mock_by_lang.assert_called_once_with(1, 'seh-fonipa')

    @patch('app.models.dictionary_models.ProjectDictionary.get_ipa_dictionary')
    def test_validation_engine_get_ipa_pattern_with_project_dict(self, mock_get_ipa):
        """Test that ValidationEngine._get_ipa_pattern utilizes ProjectDictionary.get_ipa_dictionary when project_id is set."""
        mock_dict = MagicMock()
        mock_dict.files_exist.return_value = True
        mock_dict.dic_path = 'dummy/path.dic'
        mock_get_ipa.return_value = mock_dict

        engine = ValidationEngine(project_id="1")

        with patch.object(engine, '_extract_chars_from_hunspell', return_value={'a', 'b', 'c'}) as mock_extract:
            pattern = engine._get_ipa_pattern({'name': 'IPA Rule'})
            self.assertIsNotNone(pattern)
            self.assertTrue(pattern.match('abc'))
            self.assertFalse(pattern.match('abcd'))
            mock_get_ipa.assert_called_with("1")
            mock_extract.assert_called_with(mock_dict)

    @patch('app.models.project_settings.ProjectSettings.query')
    @patch('app.models.dictionary_models.ProjectDictionary.query')
    def test_project_language_service_union(self, mock_dict_query, mock_proj_query):
        """Test that ProjectLanguageService returns union of source, target, admissible, and dictionary languages."""
        mock_project = MagicMock()
        mock_project.source_language = {'code': 'en'}
        mock_project.target_languages = [{'code': 'pl'}, 'fr']
        mock_project.admissible_languages = ['de']
        mock_proj_query.get.return_value = mock_project

        dict1 = MagicMock()
        dict1.lang_code = 'seh-fonipa'
        dict2 = MagicMock()
        dict2.lang_code = 'es'
        mock_dict_query.filter_by.return_value.all.return_value = [dict1, dict2]

        all_langs = ProjectLanguageService.get_all_language_codes(1)
        expected = {'en', 'pl', 'fr', 'de', 'seh-fonipa', 'es'}
        self.assertEqual(all_langs, expected)


if __name__ == '__main__':
    unittest.main()
