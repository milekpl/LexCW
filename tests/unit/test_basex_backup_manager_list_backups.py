import json
from pathlib import Path
from app.services.basex_backup_manager import BaseXBackupManager


def test_list_backups_deduplicates_when_meta_missing_id(tmp_path):
    # Arrange: create a backup directory with a .lift file and a .meta.json missing 'id'
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    filename = 'dup_db_backup_20250103_120000.lift'
    lift_path = backup_dir / filename
    lift_path.write_text('<lift version="0.13"></lift>', encoding='utf-8')

    # meta file without 'id'
    meta = {
        'db_name': 'dup_db',
        'description': 'with_meta',
        'status': 'completed',
        'type': 'full',
        'timestamp': '2025-01-03T12:00:00'
    }
    meta_path = Path(str(lift_path) + '.meta.json')
    meta_path.write_text(json.dumps(meta), encoding='utf-8')

    mgr = BaseXBackupManager(basex_connector=None, backup_directory=str(backup_dir))

    # Act
    results = mgr.list_backups()

    # Assert: only one entry for this filename
    found = [b for b in results if b.get('filename') == filename]
    assert len(found) == 1
    assert found[0].get('description') == 'with_meta'