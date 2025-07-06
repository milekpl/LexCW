import os
import json
import shutil
import unittest
from app.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary instance path for testing
        self.test_instance_path = os.path.join(os.path.dirname(__file__), 'temp_instance')
        if not os.path.exists(self.test_instance_path):
            os.makedirs(self.test_instance_path)
        self.settings_file = os.path.join(self.test_instance_path, 'project_settings.json')

    def tearDown(self):
        # Remove the temporary instance path after tests
        if os.path.exists(self.test_instance_path):
            shutil.rmtree(self.test_instance_path)

    def test_initialization_creates_file_with_defaults(self):
        """Test that ConfigManager creates a settings file with defaults if it doesn't exist."""
        self.assertFalse(os.path.exists(self.settings_file))
        manager = ConfigManager(self.test_instance_path)
        self.assertTrue(os.path.exists(self.settings_file))

        with open(self.settings_file, 'r') as f:
            settings = json.load(f)

        self.assertEqual(settings['project_name'], 'Default Project')
        self.assertEqual(settings['source_language']['code'], 'en')
        self.assertEqual(settings['target_language']['code'], 'es')
        self.assertEqual(manager.get_project_name(), 'Default Project')

    def test_loading_existing_settings(self):
        """Test that ConfigManager loads existing settings correctly."""
        custom_settings = {
            'project_name': 'My Test Project',
            'source_language': {'code': 'fr', 'name': 'French'},
            'target_language': {'code': 'de', 'name': 'German'}
        }
        with open(self.settings_file, 'w') as f:
            json.dump(custom_settings, f)

        manager = ConfigManager(self.test_instance_path)
        self.assertEqual(manager.get_project_name(), 'My Test Project')
        self.assertEqual(manager.get_source_language()['code'], 'fr')
        self.assertEqual(manager.get_target_language()['name'], 'German')

    def test_update_settings(self):
        """Test updating settings."""
        manager = ConfigManager(self.test_instance_path)
        manager.set_project_name('Updated Project Name')
        self.assertEqual(manager.get_project_name(), 'Updated Project Name')

        manager.set_source_language('pl', 'Polish')
        self.assertEqual(manager.get_source_language()['code'], 'pl')
        self.assertEqual(manager.get_source_language()['name'], 'Polish')

        with open(self.settings_file, 'r') as f:
            settings_on_disk = json.load(f)
        self.assertEqual(settings_on_disk['project_name'], 'Updated Project Name')
        self.assertEqual(settings_on_disk['source_language']['name'], 'Polish')

    def test_get_all_settings(self):
        """Test getting all settings."""
        manager = ConfigManager(self.test_instance_path)
        all_settings = manager.get_all_settings()
        self.assertIn('project_name', all_settings)
        self.assertIn('source_language', all_settings)
        self.assertIn('target_language', all_settings)

    def test_handling_corrupted_settings_file(self):
        """Test that defaults are loaded if the settings file is corrupted."""
        with open(self.settings_file, 'w') as f:
            f.write("this is not valid json")

        manager = ConfigManager(self.test_instance_path)
        # Should load default settings
        self.assertEqual(manager.get_project_name(), 'Default Project')
        self.assertEqual(manager.get_source_language()['code'], 'en')

        # And the corrupted file should be overwritten with defaults
        with open(self.settings_file, 'r') as f:
            settings = json.load(f)
        self.assertEqual(settings['project_name'], 'Default Project')

    def test_partial_settings_file_is_completed_with_defaults(self):
        """Test that a partially existing settings file gets missing default keys."""
        partial_settings = {
            'project_name': 'Partial Project'
            # Missing source_language and target_language
        }
        with open(self.settings_file, 'w') as f:
            json.dump(partial_settings, f)

        manager = ConfigManager(self.test_instance_path)
        self.assertEqual(manager.get_project_name(), 'Partial Project')
        # Defaults should be filled in
        self.assertEqual(manager.get_source_language()['code'], 'en')
        self.assertEqual(manager.get_target_language()['code'], 'es')

        loaded_settings = manager.get_all_settings()
        self.assertIn('source_language', loaded_settings)
        self.assertIn('target_language', loaded_settings)
        self.assertEqual(loaded_settings['source_language']['name'], 'English')

if __name__ == '__main__':
    unittest.main()
