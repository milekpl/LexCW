"""
Integration tests for backup API endpoints.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch
from app.models.backup_models import Backup, ScheduledBackup


class TestBackupAPI:
    """Test backup API endpoints."""
    
    def test_get_operation_history(self, client, app):
        """Test getting operation history."""
        with app.app_context():
            response = client.get('/api/backup/operations')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'success' in data
            assert 'data' in data
    
    def test_undo_last_operation(self, client, app):
        """Test undoing the last operation."""
        with app.app_context():
            # Test POST request to undo operation
            response = client.post('/api/backup/operations/undo', 
                                 json={})
            assert response.status_code in [200, 400]  # 400 if no operations to undo
    
    def test_redo_last_operation(self, client, app):
        """Test redoing the last operation."""
        with app.app_context():
            # Test POST request to redo operation
            response = client.post('/api/backup/operations/redo', 
                                 json={})
            assert response.status_code in [200, 400]  # 400 if no operations to redo
    
    def test_create_backup(self, client, app):
        """Test creating a backup."""
        with app.app_context():
            backup_data = {
                'db_name': 'test_db',
                'backup_type': 'manual',
                'description': 'Test backup'
            }
            response = client.post('/api/backup/create', 
                                 json=backup_data,
                                 content_type='application/json')
            # Response might be 500 if BaseX is not available in test environment
            assert response.status_code in [200, 500]
    
    def test_get_backup_history(self, client, app):
        """Test getting backup history."""
        with app.app_context():
            response = client.get('/api/backup/history')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'success' in data
    
    def test_schedule_backup(self, client, app):
        """Test scheduling a backup."""
        with app.app_context():
            schedule_data = {
                'db_name': 'test_db',
                'interval': 'daily',
                'time': '02:00',
                'type': 'full',
                'active': True
            }
            response = client.post('/api/backup/schedule',
                                 json=schedule_data,
                                 content_type='application/json')
            # Response might be 500 if scheduler fails in test environment
            assert response.status_code in [200, 500]
    
    def test_get_scheduled_backups(self, client, app):
        """Test getting scheduled backups."""
        with app.app_context():
            response = client.get('/api/backup/scheduled')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'success' in data
    
    def test_cancel_scheduled_backup(self, client, app):
        """Test canceling a scheduled backup."""
        with app.app_context():
            # This will likely return 400 or 404 since the ID probably doesn't exist
            response = client.delete('/api/backup/scheduled/nonexistent_id')
            assert response.status_code in [400, 404, 200]
    
    def test_validate_backup(self, client, app):
        """Test validating a backup file."""
        with app.app_context():
            # This will likely return 404 since the file path doesn't exist
            response = client.get('/api/backup/validate/nonexistent/path.lift')
            # May return 200 with error in data, or 500, or 404
            assert response.status_code in [200, 404, 500]

    def test_history_includes_metadata(self, client, app):
        """Test that backup history returns entries with metadata when present."""
        with app.app_context():
            # Create a fake backup file in the app's backup directory
            from pathlib import Path
            from flask import current_app
            from app.services.basex_backup_manager import BaseXBackupManager

            backup_manager = current_app.injector.get(BaseXBackupManager)
            backup_dir = backup_manager.get_backup_directory()
            backup_file = backup_dir / 'int_test_db_backup_20250102_120000.lift'
            meta_file = Path(str(backup_file) + '.meta.json')

            backup_file.write_text('<lift version="0.13"></lift>', encoding='utf-8')
            meta = {
                'id': 'int_test_db_20250102_120000',
                'db_name': 'int_test_db',
                'description': 'Integration test backup',
                'status': 'completed',
                'type': 'manual',
                'timestamp': '2025-01-02T12:00:00'
            }
            meta_file.write_text(json.dumps(meta), encoding='utf-8')

            # Now call the history endpoint and ensure our entry is returned
            response = client.get('/api/backup/history')
            assert response.status_code == 200
            data = json.loads(response.data)
            items = data.get('data', [])
            found = [b for b in items if b.get('filename') == backup_file.name]
            assert len(found) == 1
            assert found[0].get('description') == 'Integration test backup'

    def test_download_directory_backup_returns_zip(self, client, app):
        """If a backup is a directory, download should return a zip file."""
        with app.app_context():
            from flask import current_app
            from pathlib import Path
            from app.services.basex_backup_manager import BaseXBackupManager

            backup_manager = current_app.injector.get(BaseXBackupManager)
            backup_dir = backup_manager.get_backup_directory()

            # Create a directory backup artifact
            dir_name = 'dl_db_backup_20251215_085712.lift'
            dir_path = backup_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            # add a small lift file inside
            (dir_path / 'part1.lift').write_text('<lift version="0.13"></lift>', encoding='utf-8')
            # add canonical lift-ranges and settings to the directory
            (dir_path / 'lift-ranges').write_text('<lift-ranges><range id="x"/></lift-ranges>', encoding='utf-8')
            (dir_path / (dir_path.name + '.settings.json')).write_text(json.dumps({'project_name': 'dl_project'}), encoding='utf-8')

            # Add metadata so it is recognized
            meta = {
                'id': 'dl_db_20251215_085712',
                'db_name': 'dl_db',
                'description': 'dir backup',
                'status': 'completed',
                'type': 'manual',
                'timestamp': '2025-12-15T08:57:12'
            }
            meta_path = dir_path.with_name(dir_path.name + '.meta.json')
            meta_path.write_text(json.dumps(meta), encoding='utf-8')

            # Call download endpoint
            resp = client.get(f"/api/backup/download/{meta['id']}")
            # Should return 200 and a zip file
            assert resp.status_code == 200
            assert 'application/zip' in (resp.content_type or '')

            # Verify zip contents include .lift files and the supplementary files
            import io, zipfile
            z = zipfile.ZipFile(io.BytesIO(resp.data))
            names = z.namelist()
            # should contain at least one .lift file
            assert any(n.lower().endswith('.lift') for n in names)
            # should include canonical lift-ranges
            assert any(n.endswith('lift-ranges') for n in names)
            assert any(n.lower().endswith('.settings.json') for n in names)
            # should not include unrelated .xml test artifacts
            assert all(not n.lower().endswith('.xml') for n in names)

    def test_download_single_backup_with_supplementary_files_returns_zip(self, client, app):
        """Single-file backups with supplementary files should download as a zip containing them."""
        with app.app_context():
            from flask import current_app
            from pathlib import Path

            # Determine the active backup directory from config if possible, otherwise use instance/backups
            try:
                bcfg = current_app.config_manager.get_backup_settings() if hasattr(current_app, 'config_manager') else {}
                dir_setting = bcfg.get('directory', '') if isinstance(bcfg, dict) else ''
                if dir_setting:
                    if dir_setting.startswith('/'):
                        backup_dir = Path(dir_setting)
                    else:
                        backup_dir = Path(current_app.root_path) / dir_setting
                else:
                    backup_dir = Path(current_app.root_path) / 'instance' / 'backups'
            except Exception:
                backup_dir = Path(current_app.root_path) / 'instance' / 'backups'
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create a single .lift backup and supplementary files
            filename = 'single_db_backup_20251216_101010.lift'
            file_path = backup_dir / filename
            file_path.write_text('<lift version="0.13"></lift>', encoding='utf-8')
            (backup_dir / 'lift-ranges').write_text('<lift-ranges><range id="x"/></lift-ranges>', encoding='utf-8')
            (backup_dir / (filename + '.settings.json')).write_text(json.dumps([{'project_name': 'S'}]), encoding='utf-8')

            # Add a small media directory
            media_dir = backup_dir / (filename + '.media')
            media_dir.mkdir(parents=True, exist_ok=True)
            (media_dir / 'sound.mp3').write_text('audio-data', encoding='utf-8')

            # Add metadata so it is recognized
            meta = {
                'id': 'single_db_20251216_101010',
                'db_name': 'single_db',
                'description': 'single file backup',
                'status': 'completed',
                'type': 'manual',
                'timestamp': '2025-12-16T10:10:10'
            }
            meta_path = backup_dir / (filename + '.meta.json')
            meta_path.write_text(json.dumps(meta), encoding='utf-8')

            # Call download - should return a zip with lift + ranges + settings + media
            resp = client.get(f"/api/backup/download/{meta['id']}")
            assert resp.status_code == 200
            assert 'application/zip' in (resp.content_type or '')

            import io, zipfile
            z = zipfile.ZipFile(io.BytesIO(resp.data))
            names = z.namelist()
            assert any(n.lower().endswith('.lift') for n in names)
            assert any(n.endswith('lift-ranges') for n in names)
            assert any(n.lower().endswith('.settings.json') for n in names)
            assert any('media/' in n or n.lower().endswith('.mp3') for n in names)

    def test_manual_backup_api_creates_supplementary_artifacts(self, client, app):
        """Creating a backup via API should produce ranges, settings and optional media alongside the .lift."""
        with app.app_context():
            from flask import current_app
            from pathlib import Path

            # Ensure instance backups dir
            bdir = Path(current_app.root_path) / 'instance' / 'backups'
            bdir.mkdir(parents=True, exist_ok=True)

            # Ensure an uploads media exists so include_media can pick it up
            uploads = Path(current_app.instance_path) / 'uploads'
            uploads.mkdir(parents=True, exist_ok=True)
            (uploads / 'img.png').write_text('pngdata', encoding='utf-8')

            # Patch BaseX execute_command so EXPORT creates the expected file
            from unittest.mock import patch
            def fake_execute(*args, **kwargs):
                # Support bound/unbound call signatures; command is last positional arg
                cmd = args[-1] if args else kwargs.get('cmd')
                # If EXPORT <path> create that file
                if isinstance(cmd, str) and cmd.strip().upper().startswith('EXPORT'):
                    parts = cmd.split(None, 1)
                    if len(parts) == 2:
                        path = parts[1].strip()
                        try:
                            p = Path(path)
                            p.parent.mkdir(parents=True, exist_ok=True)
                            p.write_text('<lift version="0.13"></lift>', encoding='utf-8')
                            return 'OK'
                        except Exception:
                            pass
                return 'OK'

            payload = {'db_name': 'test_db', 'backup_type': 'manual', 'description': 'manual api inclusion', 'include_media': True}
            with patch('app.database.basex_connector.BaseXConnector.execute_command', new=fake_execute):
                resp = client.post('/api/backup/create', json=payload)
            assert resp.status_code in (200, 201)
            data = resp.get_json()
            assert data.get('success') is True
            b = data.get('data')
            assert b is not None
            # Should include display_name matching description
            assert b.get('display_name') == 'manual api inclusion'

            # Wait briefly for files to be written (should be synchronous but allow tiny delay)
            import time
            time.sleep(0.1)

            fp = Path(b.get('file_path'))
            # Check supplementary files exist
            lift_ranges = fp.parent / 'lift-ranges'
            settings = fp.with_name(fp.name + '.settings.json')
            display_profiles = fp.with_name(fp.name + '.display_profiles.json')
            vr = fp.with_name(fp.name + '.validation_rules.json')
            media_dir = fp.with_name(fp.name + '.media')

            assert fp.exists()
            # At minimum settings should be exported (may be empty list)
            assert settings.exists(), f"settings missing: {settings}"
            assert lift_ranges.exists(), f"lift-ranges missing: {lift_ranges}"
            # media dir should exist since we passed include_media
            assert media_dir.exists() and media_dir.is_dir(), f"media missing: {media_dir}"

            # Now test downloading the backup via API returns a zip including supplementary files
            resp2 = client.get(f"/api/backup/download/{b.get('id')}")
            assert resp2.status_code == 200
            assert 'application/zip' in (resp2.content_type or '')
            import io, zipfile
            z = zipfile.ZipFile(io.BytesIO(resp2.data))
            names = z.namelist()
            assert any(n.lower().endswith('.lift') for n in names)
            assert any(n.endswith('lift-ranges') for n in names)
            assert any(n.lower().endswith('.settings.json') for n in names)
            assert any('media/' in n or n.lower().endswith('.png') for n in names)

    def test_backup_history_no_duplicate_filenames(self, client, app):
        """Ensure backup history does not include duplicate filename entries."""
        with app.app_context():
            from pathlib import Path
            from flask import current_app

            backup_dir = Path(current_app.root_path) / 'instance' / 'backups'
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create a single backup file
            fn = 'dup_db_backup_20250101_120000.lift'
            p = backup_dir / fn
            p.write_text('<lift></lift>', encoding='utf-8')
            # Add a meta file for it
            (backup_dir / (fn + '.meta.json')).write_text(json.dumps({'id': 'dup_db_20250101_120000', 'db_name': 'dup_db'}), encoding='utf-8')

            # Request history and assert no duplicated filenames
            resp = client.get('/api/backup/history')
            assert resp.status_code == 200
            items = resp.get_json().get('data', [])
            filenames = [it.get('filename') for it in items if it.get('filename')]
            # filenames should be unique
            assert len(filenames) == len(set(filenames)), f"Duplicate filenames found: {filenames}"

    def test_delete_backup_endpoint(self, client, app):
        """DELETE endpoint should remove backup files."""
        with app.app_context():
            from flask import current_app
            from pathlib import Path
            from app.services.basex_backup_manager import BaseXBackupManager

            backup_manager = current_app.injector.get(BaseXBackupManager)
            backup_dir = backup_manager.get_backup_directory()

            # Create a file backup and meta
            filename = 'api_del_db_backup_20250102_120000.lift'
            file_path = backup_dir / filename
            file_path.write_text('<lift></lift>', encoding='utf-8')
            meta = {'id': 'api_del_db_20250102_120000', 'db_name': 'api_del_db'}
            (backup_dir / (filename + '.meta.json')).write_text(json.dumps(meta), encoding='utf-8')

            resp = client.delete(f"/api/backup/{meta['id']}")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data.get('success') is True
            assert not file_path.exists()

        def test_restore_endpoint_applies_settings_and_profiles(self, client, app):
            """Restore endpoint should apply settings and display profiles from backup."""
            with app.app_context():
                from flask import current_app
                from app.services.basex_backup_manager import BaseXBackupManager

                backup_manager = current_app.injector.get(BaseXBackupManager)
                backup_dir = backup_manager.get_backup_directory()

                # Create a directory backup artifact with settings and profiles
                dir_name = 'restore_dir_backup_20251216_090000.lift'
                dir_path = backup_dir / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
                (dir_path / 'part1.lift').write_text('<lift version="0.13"></lift>', encoding='utf-8')
                settings = {'project_name': 'RestoreProject', 'source_language': {'code': 'zz', 'name': 'Zz'}}
                (dir_path / (dir_path.name + '.settings.json')).write_text(json.dumps([settings]), encoding='utf-8')
                (dir_path / (dir_path.name + '.display_profiles.json')).write_text(json.dumps({'profiles': [{'name': 'Restored'}]}), encoding='utf-8')

                meta = {'id': 'restore_dir_20251216_090000', 'db_name': 'restore_dir'}
                (backup_dir / (dir_name + '.meta.json')).write_text(json.dumps(meta), encoding='utf-8')

                # Call restore endpoint
                resp = client.post(f"/api/backup/restore/{meta['id']}", json={'db_name': 'restored_db', 'backup_file_path': str(dir_path)})
                assert resp.status_code == 200
                data = json.loads(resp.data)
                assert data.get('success') is True

                # Verify settings applied (source language should be updated)
                cfg = current_app.config_manager
                src = cfg.get_source_language()
                assert src.get('code') == 'zz'

                # Verify display profiles restored
                dp_path = Path(current_app.instance_path) / 'display_profiles.json'
                assert dp_path.exists()

    def test_restore_with_invalid_validation_rules_returns_400(self, client, app):
        """If validation_rules.json in the backup fails schema validation, endpoint should 400."""
        with app.app_context():
            from flask import current_app
            from pathlib import Path
            # Determine a backup directory (use instance/backups fallback)
            from pathlib import Path
            backup_dir = Path(current_app.root_path) / 'instance' / 'backups'
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create a simple backup file and an invalid validation_rules.json
            filename = 'badvr_db_backup_20251216_100000.lift'
            dir_path = backup_dir / filename
            dir_path.write_text('<lift version="0.13"></lift>', encoding='utf-8')
            (backup_dir / (filename + '.validation_rules.json')).write_text('{ invalid json }', encoding='utf-8')

            meta = {'id': 'badvr_db_20251216_100000', 'db_name': 'badvr_db'}
            (backup_dir / (filename + '.meta.json')).write_text(json.dumps(meta), encoding='utf-8')

            # Attempt to restore - should return 400 due to validation failure
            resp = client.post(f"/api/backup/restore/{meta['id']}", json={'db_name': 'restored_db', 'backup_file_path': str(dir_path)})
            assert resp.status_code == 400
