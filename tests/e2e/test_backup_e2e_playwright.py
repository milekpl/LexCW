"""E2E Playwright test to ensure backup zip contains all required artifacts."""
from __future__ import annotations

import io
import json
import zipfile
import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import Page


@pytest.mark.integration
def test_backup_zip_contains_all_artifacts(page: Page, app_url: str) -> None:
    """Create a backup via the UI, download the ZIP, and assert required artifacts are present."""

    # Capture JS errors
    js_errors = []
    page.on("console", lambda msg: js_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: js_errors.append(f"Page error: {exc}"))

    # Ensure uploads dir has at least one file so include_media copies something
    # Create a temp file that will be used as sample media
    # The Flask app instance path is typically in /tmp, so create sample media there
    import os
    instance_path = Path(tempfile.gettempdir()) / 'flask_test_instance'
    uploads = instance_path / 'uploads'
    uploads.mkdir(parents=True, exist_ok=True)
    sample_media = uploads / 'sample.txt'
    sample_media.write_text('media', encoding='utf-8')

    # Navigate to the backup page and create a backup
    # The Flask server already has the correct BASEX_DATABASE environment variable set
    # from the setup_e2e_test_database fixture
    page.goto(f"{app_url}/backup/management")
    page.wait_for_selector('#create-backup-btn', state='visible', timeout=10000)

    # Check for JS errors after page load
    if js_errors:
        print(f"JS errors after page load: {js_errors}")
        js_errors.clear()

    page.fill('#backup-description', 'e2e backup test')
    # Check include media if present
    include_el = page.query_selector('#backup-include-media')
    if include_el:
        include_el.check()

    # Click the create button
    print("Clicking create backup button...")
    page.click('#create-backup-btn')

    # Wait for the backup to be created and appear in history (polling follows)
    # The Flask server has the correct database name from setup_e2e_test_database fixture
    import os
    e2e_db_name = os.environ.get('BASEX_DATABASE') or os.environ.get('TEST_DB_NAME', 'dictionary')
    print(f"Looking for backup in e2e database: {e2e_db_name}")
    
    backup_id = None
    
    for i in range(30):  # Wait up to 15 seconds
        page.wait_for_timeout(500)
        
        # Check the backup history for the e2e database
        resp = page.context.request.get(f"{app_url}/api/backup/history?db_name={e2e_db_name}")
        if resp.ok:
            data = resp.json()
            backups = data.get('data', [])
            if len(backups) > 0:
                print(f"Found {len(backups)} backups in {e2e_db_name}")
                # Look for our test backup
                for b in backups:
                    desc = b.get('description', '') or ''
                    if 'e2e backup test' in desc:
                        backup_id = b.get('id') or (b.get('file_path') and Path(b.get('file_path')).name)
                        print(f"Found backup: {backup_id}")
                        break
        
        if backup_id:
            break

    assert backup_id, f'Backup was not created or not found in history for database {e2e_db_name}'

    # Check for JS errors after click
    if js_errors:
        print(f"JS errors after click: {js_errors}")

    # Poll validation endpoint for up to 10s
    valid = False
    for _ in range(10):
        vr = page.context.request.get(f"{app_url}/api/backup/validate_id/{backup_id}")
        if vr.ok:
            j = vr.json()
            if j.get('valid'):
                valid = True
                break
        page.wait_for_timeout(500)
    assert valid, 'Backup did not validate as a valid LIFT backup'

    # Download the zip
    dl = page.context.request.get(f"{app_url}/api/backup/download/{backup_id}")
    assert dl.ok, f"Download failed: {dl.status}"
    buf = dl.body()
    z = zipfile.ZipFile(io.BytesIO(buf))
    names = z.namelist()

    # Required artifacts per docs/backup_contents.md
    assert any(n.endswith('.lift') for n in names), 'Zip missing .lift file'
    assert any(n.endswith('lift-ranges') for n in names), 'Zip missing lift-ranges'
    assert any(n.endswith('.settings.json') for n in names), 'Zip missing settings file'
    assert any(n.endswith('display_profiles.json') for n in names), 'Zip missing display_profiles'
    assert any(n.endswith('.validation_rules.json') or n.endswith('validation_rules.json') for n in names), 'Zip missing validation_rules.json'
    assert any(n.endswith('.meta.json') for n in names), 'Zip missing .meta.json'
    assert any('.media' in n for n in names), 'Zip missing .media directory or media files'
    
    # Clean up the backup file using the DELETE API endpoint
    delete_resp = page.context.request.delete(f"{app_url}/api/backup/{backup_id}")
    print(f"Backup cleanup status: {delete_resp.status}")
    assert delete_resp.ok, f"Failed to delete backup: {delete_resp.status}"