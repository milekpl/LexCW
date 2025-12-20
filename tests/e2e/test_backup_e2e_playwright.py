"""E2E Playwright test to ensure backup zip contains all required artifacts."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from playwright.sync_api import Page


@pytest.mark.integration
def test_backup_zip_contains_all_artifacts(page: Page, app_url: str, app) -> None:
    """Create a backup via the UI, download the ZIP, and assert required artifacts are present."""

    # Ensure uploads dir has at least one file so include_media copies something
    uploads = Path(app.instance_path) / 'uploads'
    uploads.mkdir(parents=True, exist_ok=True)
    sample_media = uploads / 'sample.txt'
    sample_media.write_text('media', encoding='utf-8')

    # Navigate to the backup page and create a backup
    page.goto(f"{app_url}/backup/management")
    page.wait_for_selector('#create-backup-btn', state='visible', timeout=10000)
    page.fill('#backup-description', 'e2e backup test')
    # Check include media if present
    include_el = page.query_selector('#backup-include-media')
    if include_el:
        include_el.check()

    # Click create and capture the API response
    with page.expect_response(lambda r: r.url.endswith('/api/backup/create') and r.status == 200) as resp_info:
        page.click('#create-backup-btn')
    create_resp = resp_info.value
    data = create_resp.json()
    assert data.get('success') is True
    b = data.get('data')
    assert b, 'Create did not return backup metadata'

    bid = b.get('id') or b.get('file_path') and Path(b.get('file_path')).name
    assert bid, 'Failed to determine backup id'

    # Poll validation endpoint for up to 10s
    valid = False
    for _ in range(10):
        vr = page.context.request.get(f"{app_url}/api/backup/validate_id/{bid}")
        if vr.ok:
            j = vr.json()
            if j.get('valid'):
                valid = True
                break
        page.wait_for_timeout(500)
    assert valid, 'Backup did not validate as a valid LIFT backup'

    # Download the zip
    dl = page.context.request.get(f"{app_url}/api/backup/download/{bid}")
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
