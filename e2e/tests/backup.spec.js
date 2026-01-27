const { test, expect } = require('@playwright/test');
const AdmZip = require('adm-zip');

test('backup zip contains required artifacts', async ({ page, request, baseURL }) => {
  const base = process.env.BASE_URL || baseURL || 'http://127.0.0.1:5000';

  // Navigate to backup management page (template is served at /backup/management)
  await page.goto(base + '/backup/management');

  // Wait for the form to be visible to avoid intermittent timing issues
  await page.waitForSelector('#create-backup-btn', { state: 'visible', timeout: 10000 });

  // Fill description and include media
  await page.fill('#backup-description', 'e2e content test');
  const includeMedia = await page.$('#backup-include-media');
  if (includeMedia) await includeMedia.check();

  // Click create and wait for the create API response
  const [createResp] = await Promise.all([
    page.waitForResponse(r => r.url().endsWith('/api/backup/create') && r.status() === 200),
    page.click('#create-backup-btn')
  ]);

  const createJson = await createResp.json();
  expect(createJson.success).toBeTruthy();

  // Attempt to extract the backup id from the immediate response (some server setups
  // return it synchronously). If not present, poll the history endpoint until the
  // created backup appears (matching the description we submitted).
  let bid = createJson.data && (createJson.data.id || (createJson.data.file_path && createJson.data.file_path.split('/').pop()));
  if (!bid) {
    // Determine DB name from client-side global (set by the template)
    const dbName = await page.evaluate(() => window.CURRENT_DB_NAME || 'dictionary');

    for (let i = 0; i < 15 && !bid; i++) {
      const hr = await request.get(`${base}/api/backup/history?db_name=${encodeURIComponent(dbName)}`);
      if (hr.ok()) {
        const hj = await hr.json();
        const backups = hj.data || [];
        for (const b of backups) {
          const desc = (b.description || '').toString();
          if (desc.includes('e2e content test')) {
            bid = b.id || (b.file_path && b.file_path.split('/').pop());
            break;
          }
        }
      }
      if (!bid) await new Promise(r => setTimeout(r, 1000));
    }
  }

  expect(bid).toBeTruthy();

  // Wait for backup validation to be reported as valid (poll)
  const validateUrl = `${base}/api/backup/validate_id/${bid}`;
  let valid = false;
  for (let i = 0; i < 10; i++) {
    const vr = await request.get(validateUrl);
    if (vr.ok()) {
      const j = await vr.json();
      if (j.valid) { valid = true; break; }
    }
    await new Promise(r => setTimeout(r, 1000));
  }
  expect(valid).toBeTruthy();

  // Download the backup zip and inspect contents
  const dl = await request.get(`${base}/api/backup/download/${bid}`);
  expect(dl.ok()).toBeTruthy();
  const buffer = await dl.body();

  const zip = new AdmZip(buffer);
  const entries = zip.getEntries().map(e => e.entryName);

  // Required artifacts per docs/backup_contents.md
  expect(entries.some(n => n.endsWith('.lift'))).toBeTruthy();
  expect(entries.some(n => n.endsWith('.ranges.xml') || n.endsWith('lift-ranges'))).toBeTruthy();
  expect(entries.some(n => n.endsWith('.settings.json'))).toBeTruthy();
  expect(entries.some(n => n.endsWith('display_profiles.json'))).toBeTruthy();
  expect(entries.some(n => n.endsWith('.validation_rules.json') || n.endsWith('validation_rules.json'))).toBeTruthy();
  expect(entries.some(n => n.endsWith('.meta.json'))).toBeTruthy();
  expect(entries.some(n => n.includes('.media'))).toBeTruthy();

});
