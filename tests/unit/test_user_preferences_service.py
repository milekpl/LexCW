"""
Unit tests for UserPreferencesService
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.user_preferences_service import UserPreferencesService, DEFAULT_FIELD_VISIBILITY


class TestUserPreferencesService:
    """Tests for UserPreferencesService."""

    def test_get_field_visibility_user_not_found(self):
        """Test get_field_visibility returns defaults when user not found."""
        with patch('app.services.user_preferences_service.User') as mock_user:
            mock_user.query.get.return_value = None

            result = UserPreferencesService.get_field_visibility(user_id=999)

            assert result['sections'] == DEFAULT_FIELD_VISIBILITY['sections']
            assert result['fields'] == DEFAULT_FIELD_VISIBILITY['fields']
            assert result['source'] == 'default'

    def test_get_field_visibility_user_has_preferences(self):
        """Test get_field_visibility returns user preferences when set."""
        mock_user = Mock()
        mock_user.preferences = {
            'fieldVisibility': {
                'sections': {'basic-info': False, 'senses': True},
                'fields': {'basic-info': {'lexical-unit': False}}
            }
        }

        with patch('app.services.user_preferences_service.User') as mock_user_class:
            mock_user_class.query.get.return_value = mock_user

            result = UserPreferencesService.get_field_visibility(user_id=1)

            assert result['sections']['basic-info'] is False
            assert result['sections']['senses'] is True
            assert result['fields']['basic-info']['lexical-unit'] is False
            assert result['source'] == 'user'

    def test_get_field_visibility_user_no_preferences(self):
        """Test get_field_visibility falls back to defaults when user has no preferences."""
        mock_user = Mock()
        mock_user.preferences = None

        mock_project = Mock()
        mock_project.field_visibility_defaults = None

        with patch('app.services.user_preferences_service.User') as mock_user_class, \
             patch('app.services.user_preferences_service.ProjectSettings') as mock_project_class:
            mock_user_class.query.get.return_value = mock_user
            mock_project_class.query.get.return_value = mock_project

            result = UserPreferencesService.get_field_visibility(user_id=1, project_id=1)

            assert result['sections'] == DEFAULT_FIELD_VISIBILITY['sections']
            assert result['fields'] == DEFAULT_FIELD_VISIBILITY['fields']
            assert result['source'] == 'default'

    def test_get_field_visibility_project_defaults(self):
        """Test get_field_visibility returns project defaults when user has no preferences."""
        mock_user = Mock()
        mock_user.preferences = {}

        mock_project = Mock()
        mock_project.field_visibility_defaults = {
            'sections': {'basic-info': False},
            'fields': {'basic-info': {'lexical-unit': False}}
        }

        with patch('app.services.user_preferences_service.User') as mock_user_class, \
             patch('app.services.user_preferences_service.ProjectSettings') as mock_project_class:
            mock_user_class.query.get.return_value = mock_user
            mock_project_class.query.get.return_value = mock_project

            result = UserPreferencesService.get_field_visibility(user_id=1, project_id=1)

            assert result['sections']['basic-info'] is False
            assert result['fields']['basic-info']['lexical-unit'] is False
            assert result['source'] == 'project'

    def test_save_field_visibility_user_not_found(self):
        """Test save_field_visibility returns error when user not found."""
        with patch('app.services.user_preferences_service.User') as mock_user:
            mock_user.query.get.return_value = None

            success, error = UserPreferencesService.save_field_visibility(
                user_id=999,
                project_id=1,
                settings={'sections': {'basic-info': False}}
            )

            assert success is False
            assert error == 'User not found'

    def test_save_field_visibility_success(self):
        """Test save_field_visibility successfully saves settings."""
        mock_user = Mock()
        mock_user.preferences = {}

        with patch('app.services.user_preferences_service.User') as mock_user_class, \
             patch('app.services.user_preferences_service.db') as mock_db:
            mock_user_class.query.get.return_value = mock_user

            success, error = UserPreferencesService.save_field_visibility(
                user_id=1,
                project_id=1,
                settings={'sections': {'basic-info': False}, 'fields': {}}
            )

            assert success is True
            assert error is None
            mock_db.session.commit.assert_called_once()

    def test_reset_to_project_defaults_user_not_found(self):
        """Test reset_to_project_defaults returns error when user not found."""
        with patch('app.services.user_preferences_service.User') as mock_user:
            mock_user.query.get.return_value = None

            success, error = UserPreferencesService.reset_to_project_defaults(user_id=999)

            assert success is False
            assert error == 'User not found'

    def test_reset_to_project_defaults_success(self):
        """Test reset_to_project_defaults successfully clears user preferences."""
        mock_user = Mock()
        mock_user.preferences = {'fieldVisibility': {'sections': {'basic-info': False}}}

        with patch('app.services.user_preferences_service.User') as mock_user_class, \
             patch('app.services.user_preferences_service.db') as mock_db:
            mock_user_class.query.get.return_value = mock_user

            success, error = UserPreferencesService.reset_to_project_defaults(user_id=1)

            assert success is True
            assert error is None
            mock_db.session.commit.assert_called_once()

    def test_get_project_defaults_not_found(self):
        """Test get_project_defaults returns empty dict when project not found."""
        with patch('app.services.user_preferences_service.ProjectSettings') as mock_project_class:
            mock_project_class.query.get.return_value = None

            result = UserPreferencesService.get_project_defaults(project_id=999)

            assert result == {}

    def test_get_project_defaults_with_defaults(self):
        """Test get_project_defaults returns stored defaults."""
        mock_project = Mock()
        mock_project.field_visibility_defaults = {
            'sections': {'basic-info': False},
            'fields': {}
        }

        with patch('app.services.user_preferences_service.ProjectSettings') as mock_project_class:
            mock_project_class.query.get.return_value = mock_project

            result = UserPreferencesService.get_project_defaults(project_id=1)

            assert result['sections']['basic-info'] is False

    def test_save_project_defaults_not_found(self):
        """Test save_project_defaults returns error when project not found."""
        with patch('app.services.user_preferences_service.ProjectSettings') as mock_project_class:
            mock_project_class.query.get.return_value = None

            success, error = UserPreferencesService.save_project_defaults(
                project_id=999,
                settings={'sections': {}},
                admin_user_id=1
            )

            assert success is False
            assert error == 'Project not found'

    def test_save_project_defaults_success(self):
        """Test save_project_defaults successfully saves project defaults."""
        mock_project = Mock()
        mock_project.field_visibility_defaults = None

        with patch('app.services.user_preferences_service.ProjectSettings') as mock_project_class, \
             patch('app.services.user_preferences_service.db') as mock_db:
            mock_project_class.query.get.return_value = mock_project

            success, error = UserPreferencesService.save_project_defaults(
                project_id=1,
                settings={'sections': {'basic-info': False}, 'fields': {}},
                admin_user_id=1
            )

            assert success is True
            assert error is None
            mock_db.session.commit.assert_called_once()


class TestDefaultFieldVisibility:
    """Tests for DEFAULT_FIELD_VISIBILITY constant."""

    def test_default_sections_exist(self):
        """Test default sections are defined."""
        expected_sections = [
            'basic-info', 'custom-fields', 'notes', 'pronunciation',
            'variants', 'direct-variants', 'relations', 'annotations', 'senses'
        ]

        for section in expected_sections:
            assert section in DEFAULT_FIELD_VISIBILITY['sections']
            assert DEFAULT_FIELD_VISIBILITY['sections'][section] is True

    def test_default_fields_exist(self):
        """Test default fields are defined for each section."""
        for section_id, fields in DEFAULT_FIELD_VISIBILITY['fields'].items():
            assert isinstance(fields, dict)
            for field_id, visible in fields.items():
                assert isinstance(field_id, str)
                assert isinstance(visible, bool)
