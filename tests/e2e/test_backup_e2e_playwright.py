"""E2E Playwright test to ensure backup zip contains all required artifacts."""
from __future__ import annotations

import io
import json
import os
import uuid
import xml.etree.ElementTree as ET
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

@pytest.mark.integration
def test_backup_contains_real_entry_data(page: Page, app_url: str) -> None:
    """A real backup must contain the ACTUAL database content as an intact .lift.

    This runs through the REAL backup path (E2E_TESTING bypasses the TESTING
    stub): a probe entry is created in the live BaseX database, a backup is
    triggered via the UI, and the downloaded .lift must be a single, well-formed
    document that contains both the probe entry AND the gold seed entries.
    """
    entry_id = f"e2e_bkp_{uuid.uuid4().hex[:8]}"
    word = f"probe-{uuid.uuid4().hex[:6]}"
    definition = f"definition-{uuid.uuid4().hex[:6]}"

    # 1. Create a real entry in the live database (XML path — full fidelity)
    # NB: the e2e DB is namespace-less (matches pristine gold data), and the
    # XML entry API expects a single <entry> root element.
    entry_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry id="{entry_id}">
  <lexical-unit><form lang="en"><text>{word}</text></form></lexical-unit>
  <sense id="s1">
    <definition><form lang="en"><text>{definition}</text></form></definition>
  </sense>
</entry>'''
    resp = page.context.request.post(
        f"{app_url}/api/entries",
        data=entry_xml.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.ok, (
        f"Could not create probe entry: {resp.status} {resp.text()[:300]}"
    )

    try:
        # 2. Trigger a REAL backup through the UI
        page.goto(f"{app_url}/backup/management")
        page.wait_for_selector('#create-backup-btn', state='visible', timeout=10000)
        page.fill('#backup-description', 'e2e real data backup')
        page.click('#create-backup-btn')

        # 3. Find the backup in history
        e2e_db_name = os.environ.get('BASEX_DATABASE') or os.environ.get(
            'TEST_DB_NAME', 'dictionary'
        )
        backup_id = None
        for _ in range(30):  # Wait up to 15s
            page.wait_for_timeout(500)
            resp = page.context.request.get(
                f"{app_url}/api/backup/history?db_name={e2e_db_name}"
            )
            if resp.ok:
                for b in resp.json().get('data', []):
                    if 'e2e real data backup' in (b.get('description') or ''):
                        backup_id = b.get('id')
                        break
            if backup_id:
                break
        assert backup_id, 'Real backup was not created / not found in history'

        # 4. Download the ZIP and extract the .lift
        dl = page.context.request.get(f"{app_url}/api/backup/download/{backup_id}")
        assert dl.ok, f"Download failed: {dl.status}"
        z = zipfile.ZipFile(io.BytesIO(dl.body()))
        lift_names = [n for n in z.namelist() if n.endswith('.lift')]
        assert lift_names, 'Zip contains no real .lift backup'
        lift_text = z.read(lift_names[0]).decode('utf-8')

        # 5. The .lift must be ONE well-formed document ...
        ET.fromstring(lift_text)
        assert '<lift' in lift_text, 'Backup .lift is not a LIFT document'

        # ... and must contain the probe entry's real data ...
        assert entry_id in lift_text, 'Backup .lift is missing the probe entry id'
        assert word in lift_text, 'Backup .lift is missing the probe lexical unit'
        assert definition in lift_text, (
            'Backup .lift is missing the probe definition'
        )

        # ... and the gold seed entries (whole DB serialized, not just the probe)
        assert 'test_entry_1' in lift_text, 'Backup .lift is missing gold entry 1'
        assert 'test_entry_2' in lift_text, 'Backup .lift is missing gold entry 2'

        # Clean up the backup file
        delete_resp = page.context.request.delete(
            f"{app_url}/api/backup/{backup_id}"
        )
        assert delete_resp.ok, f"Failed to delete backup: {delete_resp.status}"
    finally:
        # Remove the probe entry so it never leaks into other tests
        try:
            page.context.request.delete(f"{app_url}/api/entries/{entry_id}")
        except Exception:
            pass


@pytest.mark.integration
def test_restore_via_stable_button_restores_entry(page: Page, app_url: str) -> None:
    """Restore from the UI must bring a deleted real entry back.

    Exercises the stable restore button (#restore-backup-btn in the backup
    details panel): create a real entry -> backup -> delete the entry ->
    restore from the UI -> the entry must be back with its original data.
    """
    entry_id = f"e2e_rst_{uuid.uuid4().hex[:8]}"
    word = f"restore-probe-{uuid.uuid4().hex[:6]}"

    # 1. Create a real entry in the live database (XML path)
    entry_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry id="{entry_id}">
  <lexical-unit><form lang="en"><text>{word}</text></form></lexical-unit>
  <sense id="s1">
    <definition><form lang="en"><text>{word}-definition</text></form></definition>
  </sense>
</entry>'''
    resp = page.context.request.post(
        f"{app_url}/api/entries",
        data=entry_xml.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.ok, f"Could not create probe entry: {resp.status} {resp.text()[:300]}"

    try:
        # 2. Create a REAL backup via the UI
        page.goto(f"{app_url}/backup/management")
        page.wait_for_selector('#create-backup-btn', state='visible', timeout=10000)
        page.fill('#backup-description', 'e2e restore backup')
        page.click('#create-backup-btn')

        e2e_db_name = os.environ.get('BASEX_DATABASE') or os.environ.get(
            'TEST_DB_NAME', 'dictionary'
        )
        backup_id = None
        for _ in range(30):  # Wait up to 15s
            page.wait_for_timeout(500)
            resp = page.context.request.get(
                f"{app_url}/api/backup/history?db_name={e2e_db_name}"
            )
            if resp.ok:
                for b in resp.json().get('data', []):
                    if 'e2e restore backup' in (b.get('description') or ''):
                        backup_id = b.get('id')
                        break
            if backup_id:
                break
        assert backup_id, 'Backup was not created / not found in history'

        # 3. Delete the entry and confirm it is gone
        del_resp = page.context.request.delete(f"{app_url}/api/entries/{entry_id}")
        assert del_resp.ok, f"Could not delete probe entry: {del_resp.status}"
        gone = page.context.request.get(f"{app_url}/api/entries/{entry_id}")
        assert gone.status == 404, (
            f"Expected 404 after delete, got {gone.status}"
        )

        # 4. Restore from the UI via the stable restore button
        page.on('dialog', lambda dialog: dialog.accept())
        row = page.locator(
            f'#backup-history-body tr:has([data-backup-id="{backup_id}"])'
        )
        row.locator('.view-btn').first.click()
        page.wait_for_selector('#restore-backup-btn', state='visible', timeout=5000)
        page.click('#restore-backup-btn')

        # 5. The entry must reappear with its original data
        restored = False
        for _ in range(30):  # Wait up to 15s
            page.wait_for_timeout(500)
            resp = page.context.request.get(f"{app_url}/api/entries/{entry_id}")
            if resp.ok:
                restored = True
                assert word in resp.text(), (
                    'Restored entry is missing its lexical unit'
                )
                break
        assert restored, 'Restored entry did not reappear after UI restore'

        # Clean up the backup file
        delete_resp = page.context.request.delete(
            f"{app_url}/api/backup/{backup_id}"
        )
        assert delete_resp.ok, f"Failed to delete backup: {delete_resp.status}"
    finally:
        # Remove the probe entry so it never leaks into other tests
        try:
            page.context.request.delete(f"{app_url}/api/entries/{entry_id}")
        except Exception:
            pass
