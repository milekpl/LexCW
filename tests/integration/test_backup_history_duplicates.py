import json
from pathlib import Path


def test_history_deduplicates_meta_without_id(client, app):
    with app.app_context():
        from flask import current_app
        from app.services.basex_backup_manager import BaseXBackupManager

        backup_manager = current_app.injector.get(BaseXBackupManager)
        backup_dir = backup_manager.get_backup_directory()

        filename = 'dup_integ_db_backup_20250103_121000.lift'
        lift_path = backup_dir / filename
        lift_path.write_text('<lift version="0.13"></lift>', encoding='utf-8')

        # meta without id
        meta = {
            'db_name': 'dup_integ_db',
            'description': 'with_meta',
            'status': 'completed',
            'type': 'full',
            'timestamp': '2025-01-03T12:10:00'
        }
        meta_path = Path(str(lift_path) + '.meta.json')
        meta_path.write_text(json.dumps(meta), encoding='utf-8')

        resp = client.get('/api/backup/history')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        items = data.get('data', [])
        found = [b for b in items if b.get('filename') == filename]
        assert len(found) == 1
        assert found[0].get('description') == 'with_meta'