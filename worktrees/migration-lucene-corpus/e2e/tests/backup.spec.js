const { test, expect } = require('@playwright/test');
const AdmZip = require('adm-zip');

test('backup zip contains required artifacts', async ({ page, request, baseURL }) => {
  const base = process.env.BASE_URL || baseURL || 'http://127.0.0.1:5000';

  // Navigate to backup page
  await page.goto(base + '/backup/');

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
  const bid = createJson.data && (createJson.data.id || createJson.data.file_path && createJson.data.file_path.split('/').pop());
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
