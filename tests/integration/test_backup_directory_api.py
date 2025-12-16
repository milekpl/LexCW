from __future__ import annotations
from pathlib import Path
import json


def test_clear_and_use_default_backup_dir(client, app):
    # Clear configured directory via API
    resp = client.post('/api/backup/dir', json={'directory': ''})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True

    # Get effective directory
    resp2 = client.get('/api/backup/dir')
    assert resp2.status_code == 200
    info = resp2.get_json()
    assert info.get('success') is True
    effective = info.get('effective_directory')
    assert effective is not None

    # Create a backup synchronously (TESTING mode returns immediate meta)
    payload = {'db_name': 'test_db', 'backup_type': 'manual', 'description': 'dir test', 'include_media': False}
    r = client.post('/api/backup/create', json=payload)
    assert r.status_code in (200, 201)
    j = r.get_json()
    assert j.get('success') is True
    b = j.get('data')
    assert b is not None

    fp = Path(b.get('file_path'))
    # Ensure backup file path is under the effective directory
    assert str(fp).startswith(str(Path(effective))), f"Backup file {fp} not under effective dir {effective}"
