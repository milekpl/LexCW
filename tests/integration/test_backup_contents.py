"""Integration tests verifying backup contents are substantive, not placeholders."""

import json
from pathlib import Path


def test_backup_contains_real_contents(client, app):
    """Creating a backup should include substantive lift, ranges and settings content."""
    with app.app_context():
        payload = {'db_name': 'test_db', 'backup_type': 'manual', 'description': 'content check', 'include_media': True}

        resp = client.post('/api/backup/create', json=payload)
        assert resp.status_code in (200, 201)
        data = resp.get_json()
        assert data.get('success') is True
        b = data.get('data')
        assert b is not None

        fp = Path(b.get('file_path'))
        assert fp.exists(), f"Backup file missing: {fp}"

        # Lift must include at least one <entry>
        lift_text = fp.read_text(encoding='utf-8')
        assert '<entry' in lift_text, 'Lift file does not contain any entries'

        # Ranges file: canonical 'lift-ranges' (preferred)
        ranges_candidates = [
            fp.parent / 'lift-ranges',
            fp.with_name(fp.name + '.lift-ranges'),
            fp.with_name('.lift-ranges'),
        ]
        ranges_path = None
        for c in ranges_candidates:
            if c.exists():
                ranges_path = c
                break
        assert ranges_path is not None, 'No ranges file found alongside backup'
        ranges_text = ranges_path.read_text(encoding='utf-8')
        assert '<range' in ranges_text, 'Ranges file appears empty or placeholder'

        # Settings must contain at least one meaningful key/value
        settings_path = fp.with_name(fp.name + '.settings.json')
        assert settings_path.exists(), 'Settings file missing'
        settings = json.loads(settings_path.read_text(encoding='utf-8') or 'null')
        # Expect either a non-empty list or an object with project_name
        assert (isinstance(settings, list) and len(settings) > 0) or (isinstance(settings, dict) and settings), 'Settings file appears empty'

        # Display profiles should exist and include a profiles key
        dp_path = fp.with_name(fp.name + '.display_profiles.json')
        assert dp_path.exists(), 'Display profiles file missing'
        dp = json.loads(dp_path.read_text(encoding='utf-8') or '{}')
        assert isinstance(dp, dict) and 'profiles' in dp, 'Display profiles file missing profiles key'

        # Downloading should include these files and their content
        resp2 = client.get(f"/api/backup/download/{b.get('id')}")
        assert resp2.status_code == 200
        assert 'application/zip' in (resp2.content_type or '')
        import io, zipfile
        z = zipfile.ZipFile(io.BytesIO(resp2.data))
        names = z.namelist()
        # Strict expectations based on docs/backup_contents.md — fail hard if any missing
        assert any(n.endswith('.lift') for n in names), 'Zip missing .lift file'
        assert any(n.endswith('lift-ranges') for n in names), 'Zip missing lift-ranges'
        assert any(n.endswith('.settings.json') for n in names), 'Zip missing settings file'
        assert any(n.endswith('display_profiles.json') for n in names), 'Zip missing display_profiles'
        assert any(n.endswith('.validation_rules.json') or n.endswith('validation_rules.json') for n in names), 'Zip missing validation_rules.json'
        assert any(n.endswith('.meta.json') for n in names), 'Zip missing .meta.json'
        # Require media directory or at least one media entry when include_media=True
        # Accept either canonical '.media' or a backup-specific '<base>.lift.media' naming
        assert any('.media' in n for n in names), 'Zip missing .media directory or media files'
