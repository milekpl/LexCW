from __future__ import annotations
import unittest
from app.config_manager import ConfigManager
from app.models.project_settings import ProjectSettings, db
from flask import Flask

class TestConfigManager(unittest.TestCase):
    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()
        self.config_manager = ConfigManager(app_instance_path='.')
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_get_all_settings(self) -> None:
        self.config_manager.create_settings(
            project_name='Project1',
            basex_db_name='db1'
        )
        self.config_manager.create_settings(
            project_name='Project2',
            basex_db_name='db2'
        )
        all_settings = self.config_manager.get_all_settings()
        self.assertEqual(len(all_settings), 2)
        names = {s.project_name for s in all_settings}
        self.assertIn('Project1', names)
        self.assertIn('Project2', names)

    def test_update_current_settings_persists_backup_settings(self) -> None:
        # Create initial default settings (will be the first project)
        settings = self.config_manager.create_settings(
            project_name='BackupTest',
            basex_db_name='db_backup'
        )

        new_backup = {
            'directory': '/tmp/backups',
            'schedule': 'daily',
            'retention': 7,
            'compression': False
        }

        # Call update_current_settings and ensure it returns the updated object
        updated = self.config_manager.update_current_settings({'backup_settings': new_backup})
        self.assertIsNotNone(updated)
        self.assertEqual(updated.backup_settings, new_backup)

        # Query the database directly to ensure persistence
        first = ProjectSettings.query.first()
        self.assertIsNotNone(first)
        self.assertEqual(first.backup_settings, new_backup)

if __name__ == '__main__':
    unittest.main()
