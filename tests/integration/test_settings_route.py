import os
import sys
import json
import shutil
import unittest
from unittest.mock import patch
from flask import Flask

import pytest

# Add project root to sys.path to ensure correct module resolution for patching
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from app.config_manager import ConfigManager
@pytest.mark.integration
class TestSettingsRoute(unittest.TestCase):
    def setUp(self):
        # Set TESTING env var before create_app to prevent premature BaseX connection attempt
        os.environ['TESTING'] = 'true'
        # Ensure FLASK_ENV is also set for consistency if your config uses it
        os.environ['FLASK_ENV'] = 'testing'

        self.app = create_app(config_name='testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Ensure a fresh ConfigManager for each test using the app's instance_path
        self.test_instance_path = self.app.instance_path
        self.settings_file = os.path.join(self.test_instance_path, 'project_settings.json')

        # Clean up any existing settings file from previous tests
        if os.path.exists(self.settings_file):
            os.remove(self.settings_file)

        # Initialize ConfigManager directly for the app instance for testing
        self.app.config_manager = ConfigManager(self.test_instance_path)
        
        # Ensure database tables are created for testing
        from app.models.project_settings import db
        with self.app.app_context():
            db.create_all()
        
        self.app.config['PROJECT_SETTINGS'] = [s.settings_json for s in self.app.config_manager.get_all_settings()]

        # Reset the cache in the actual app.utils.language_utils module (if it's ever called unmocked)
        # This is less critical if the form's call is always mocked, but good for hygiene.
        from app.utils import language_utils
        language_utils._language_cache = None


    def tearDown(self):
        if os.path.exists(self.settings_file):
            os.remove(self.settings_file)
        
        # Clean up database
        from app.models.project_settings import db
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            
        self.app_context.pop()
        # Clear any environment variables set for testing
        if 'TESTING' in os.environ:
            del os.environ['TESTING']
        if 'FLASK_ENV' in os.environ:
            del os.environ['FLASK_ENV']


    @pytest.mark.integration
    def test_get_settings_page(self):
        """Test that the settings page loads correctly."""
        response = self.client.get('/settings/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Project Settings', response.data)
        self.assertIn(b'Default Project', response.data) # Default project name
        self.assertIn(b'Source Language (Vernacular)', response.data)

        # Check if default source language ('en', 'English') is selected
        html = response.data.lower()
        # Print all <option> lines for debugging
        option_lines = [line for line in html.split(b'\n') if b'<option' in line]
        print("[DEBUG] Option lines in HTML:")
        for line in option_lines:
            print(line)
        import re
        # Accept any display text for the selected 'en' option
        pattern = re.compile(br'<option[^>]*selected[^>]*value=["\"]en["\"][^>]*>[^<]+</option>')
        assert pattern.search(html), (
            f"No <option> for 'en' with selected attribute found.\nOption lines: {option_lines}")
        # Check if the display name used for the text input is from config (default 'English')
        self.assertIn(b'value="English"', response.data)


    # No longer need to patch here as setUp's patch should cover it for form instantiation
    @pytest.mark.integration
    def test_update_settings_successfully(self):
        """Test updating settings via POST request."""
        import json
        new_settings_data = {
            'project_name': 'My Awesome Dictionary',
            'source_language_code': 'pl',
            'source_language_name': 'Polish',
            'available_target_languages': json.dumps(['de']),  # JSON string format for searchable selector
            'csrf_token': 'testing_csrf_token'
        }

        response = self.client.post('/settings/', data=new_settings_data, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Settings updated successfully!', response.data)

        # Verify that the settings were actually saved by ConfigManager
        config_manager = self.app.config_manager
        self.assertEqual(config_manager.get_project_name(), 'My Awesome Dictionary')
        self.assertEqual(config_manager.get_source_language()['code'], 'pl')
        self.assertEqual(config_manager.get_source_language()['name'], 'Polish')
        
        # Target languages are now a list, get the first one
        target_languages = config_manager.get_target_languages()
        self.assertGreater(len(target_languages), 0, "Should have at least one target language")
        self.assertEqual(target_languages[0]['code'], 'de')

        # Also check that app.config was updated
        project_settings = self.app.config['PROJECT_SETTINGS']
        if project_settings and len(project_settings) > 0:
            settings_json = project_settings[0]
            self.assertEqual(settings_json['project_name'], 'My Awesome Dictionary')
            self.assertEqual(settings_json['source_language']['name'], 'Polish')
            self.assertIn('target_languages', settings_json)
            self.assertGreater(len(settings_json['target_languages']), 0)

    @pytest.mark.integration
    def test_update_backup_settings_via_form(self):
        """Test updating backup settings via POST request and verify persistence."""
        backup_data = {
            'project_name': 'Backup Project',
            'source_language_code': 'en',
            'source_language_name': 'English',
            'available_target_languages': '[]',
            'backup_directory': '/tmp/my_backups',
            'auto_backup_schedule': 'daily',
            'backup_retention': '5',
            'backup_compression': 'y',
            'backup_include_media': 'y',
            'csrf_token': 'testing_csrf_token'
        }

        resp = self.client.post('/settings/', data=backup_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Settings updated successfully!', resp.data)

        # Validate persisted backup settings
        cfg = self.app.config_manager
        backup_settings = cfg.get_backup_settings()
        self.assertEqual(backup_settings.get('directory'), '/tmp/my_backups')
        self.assertEqual(backup_settings.get('schedule'), 'daily')
        self.assertEqual(backup_settings.get('retention'), 5)
        self.assertEqual(backup_settings.get('compression'), True)
        self.assertEqual(backup_settings.get('include_media'), True)

    @pytest.mark.integration
    def test_settings_are_applied_immediately(self):
        """Test that updated settings are immediately available in the application."""
        new_settings_data = {
            'project_name': 'A New Project Name',
            'source_language_code': 'fr',
            'source_language_name': 'French',
            'target_language_code': 'es',
            'target_language_name': 'Spanish',
            'csrf_token': 'testing_csrf_token'
        }

        self.client.post('/settings/', data=new_settings_data, follow_redirects=True)

        # In a separate request, check if a view reflects the new settings
        response = self.client.get('/settings/')
        self.assertIn(b'A New Project Name', response.data)
        self.assertIn(b'value="French"', response.data)


    # No longer need to patch here
    @pytest.mark.integration
    def test_update_settings_validation_error(self):
        """Test form validation errors when updating settings."""
        invalid_data = {
            'project_name': '', # Empty project name should fail
            'source_language_code': 'fr',
            'source_language_name': 'French',
            'target_language_code': 'en',
            'target_language_name': 'English',
        }
        response = self.client.post('/settings/', data=invalid_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This field is required.', response.data)

        config_manager = self.app.config_manager
        self.assertEqual(config_manager.get_project_name(), 'Default Project')

    @pytest.mark.integration
    def test_language_choices_in_form(self):
        """Test that language choices are present in the form."""
        response = self.client.get('/settings/')
        self.assertEqual(response.status_code, 200)

        # Check for source language select dropdown (English will be selected by default)
        self.assertIn(b'<select class="form-select" id="source_language_code"', response.data)
        self.assertIn(b'value="en">English (en)</option>', response.data)
        self.assertIn(b'value="es">Spanish (es)</option>', response.data)
        self.assertIn(b'value="fr">French (fr)</option>', response.data)
        self.assertIn(b'value="de">German (de)</option>', response.data)
        
        # Check for target language searchable interface (new dict-based format)
        self.assertIn(b'name="available_target_languages"', response.data)
        self.assertIn(b'language-search-input', response.data)
        self.assertIn(b'selected-languages-list', response.data)
        
        # Verify we have multiple language options in the source language dropdown
        option_count = response.data.count(b'value="en">English (en)</option>')
        self.assertGreaterEqual(option_count, 1, "Should have English option in source language dropdown")
        
        # Check that searchable language selector exists
        selector_count = response.data.count(b'searchable-language-selector')
        self.assertGreaterEqual(selector_count, 1, "Should have searchable language selector for target languages")


if __name__ == '__main__':
    unittest.main()
