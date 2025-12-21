const { test, expect } = require('@playwright/test');

// Helper to resolve base URL consistently with Playwright config / env
function getBaseURL(baseURLFromFixture) {
  return process.env.BASE_URL || baseURLFromFixture || 'http://127.0.0.1:5000';
}

// Create or overwrite an entry via API
async function upsertEntry(request, base, entryJson) {
  const resp = await request.post(`${base}/api/entries`, {
    data: entryJson,
  });
  expect(resp.status()).toBeGreaterThanOrEqual(200);
  expect(resp.status()).toBeLessThan(300);
  const body = await resp.json();
  // /api/entries sometimes returns {entry_id: id} or full entry; normalize
  if (body && typeof body === 'object') {
    if (body.id) return body.id;
    if (body.entry_id) return body.entry_id;
  }
  return entryJson.id;
}

// Load entry via API for server-side verification
async function getEntry(request, base, id) {
  const resp = await request.get(`${base}/api/entries/${encodeURIComponent(id)}`);
  expect(resp.ok()).toBeTruthy();
  return resp.json();
}

/**
 * E2E regression for entry-level complex form/component relations.
 *
 * Scenario:
 * 1. Create two simple base entries A and B via the JSON API.
 * 2. Create a complex entry C via the HTML entry form that:
 *    - Adds A as a complex component via the "Complex Form Components" UI
 *    - Adds B as a variant via the "Variants" UI
 * 3. Save the form.
 * 4. Re-open entry C's edit form and verify:
 *    - The component relation(s) appear under the Complex Form Components card
 *    - The variant relation(s) appear under the Variants card
 *    - No _component-lexeme relations are rendered in the generic Relations box
 */

test('entry complex components and variants persist in correct sections', async ({ page, request, baseURL }) => {
  const base = getBaseURL(baseURL);

  // --- Arrange: create base and variant target entries via API ---
  const timestamp = Date.now();
  const componentEntryId = `e2e_component_${timestamp}`;
  const variantTargetEntryId = `e2e_variant_target_${timestamp}`;
  const complexEntryId = `e2e_complex_${timestamp}`;

  // Base component entry
  await upsertEntry(request, base, {
    id: componentEntryId,
    lexical_unit: { en: `component-${timestamp}` },
    senses: [
      {
        id: 'sense_component',
        glosses: { en: 'component entry for complex form' },
      },
    ],
  });

  // Variant target entry
  await upsertEntry(request, base, {
    id: variantTargetEntryId,
    lexical_unit: { en: `variant-target-${timestamp}` },
    senses: [
      {
        id: 'sense_variant_target',
        glosses: { en: 'variant target entry' },
      },
    ],
  });

  // Ensure search index can find the created entries by waiting briefly
  await new Promise((r) => setTimeout(r, 500));

  // --- Act 1: open Add New Entry form and create complex entry via UI ---
  // Entries list is at /entries; "Add New Entry" typically links to /entries/add
  await page.goto(`${base}/entries`);

  // Click on Add New Entry (button or link). Use text selector to avoid brittle IDs.
  const addEntrySelector = 'text="Add New Entry"';
  await page.click(addEntrySelector);

  // We should now be on the entry form; fill minimal lexical unit so save is allowed.
  await page.waitForSelector('#entry-form');

  // The lexical unit source language field is required; target the first input.
  const headwordInput = page.locator('.lexical-unit-forms input.lexical-unit-text').first();
  await headwordInput.fill(`complex-${timestamp}`);

  // Optionally set citation form to make the entry easier to identify in search results
  await page.fill('#citation-form', `complex-entry-${timestamp}`);

  // --- Add a complex form component using the UI section ---
  // 1) Choose a component type from the dynamic complex-form-type select
  const componentTypeSelect = page.locator('#new-component-type');
  await componentTypeSelect.waitFor();

  // Wait for dynamic LIFT range options to load; pick the first real option if any
  await componentTypeSelect.click();
  const firstOption = componentTypeSelect.locator('option:not([value=""])').first();
  if (await firstOption.isVisible()) {
    const value = await firstOption.getAttribute('value');
    await componentTypeSelect.selectOption(value || '');
  }

  // 2) Search for the base component entry by headword text
  await page.fill('#component-search-input', `component-${timestamp}`);
  await page.click('#component-search-btn');

  // Search results container for components
  const componentResults = page.locator('#component-search-results');
  await componentResults.waitFor({ state: 'visible' });

  // Click the first result (which should correspond to our component entry)
  const firstComponentResult = componentResults.locator('.search-result-item, .list-group-item').first();
  await firstComponentResult.click();

  // After selecting, the new component should appear in #new-components-container
  const newComponentsContainer = page.locator('#new-components-container');
  await expect(newComponentsContainer).toContainText(`component-${timestamp}`);

  // --- Add a variant relation using the Variants UI section ---
  // Create a new blank variant block
  await page.click('#add-variant-btn');

  // The new variant item should appear; we target the last .variant-item
  const variantItems = page.locator('.variant-item');
  await expect(variantItems).toHaveCount(1);

  const variantItem = variantItems.last();

  // Select variant type from its dynamic-lift-range select
  const variantTypeSelect = variantItem.locator('select[data-range-id="variant-type"]');
  await variantTypeSelect.waitFor();

  const firstVariantTypeOption = variantTypeSelect.locator('option:not([value=""])').first();
  if (await firstVariantTypeOption.isVisible()) {
    const value = await firstVariantTypeOption.getAttribute('value');
    await variantTypeSelect.selectOption(value || '');
  }

  // Use the variant search interface to connect to variantTargetEntryId
  const variantSearchInput = variantItem.locator('input.variant-search-input');
  const variantSearchButton = variantItem.locator('button.variant-search-btn');

  await variantSearchInput.fill(`variant-target-${timestamp}`);
  await variantSearchButton.click();

  const variantResults = page.locator('#variant-search-results-0');
  await variantResults.waitFor({ state: 'visible' });

  const firstVariantResult = variantResults.locator('.search-result-item, .list-group-item').first();
  await firstVariantResult.click();

  // Basic smoke check that the variant UI shows the chosen target
  await expect(variantItem).toContainText(`variant-target-${timestamp}`);

  // --- Save the entry via the form submit button ---
  // Try a generic save button selector commonly used: text "Save Entry"
  const saveButton = page.locator('button:has-text("Save Entry"), button:has-text("Save")').first();
  await saveButton.click();

  // Wait for navigation or success indicator – assume redirect back to entries list or view
  await page.waitForLoadState('networkidle');

  // --- Verify via API that C exists and capture its id (may be auto-generated) ---
  // If server overwrote id, we still expect `complexEntryId` or some entry containing our headword.
  let finalComplexId = complexEntryId;

  // Attempt to get by explicit id first; if 404, search via /api/search
  let complexEntry;
  try {
    complexEntry = await getEntry(request, base, complexEntryId);
  } catch (e) {
    // Fallback: use search by headword text to resolve actual stored id
    const searchResp = await request.get(`${base}/api/search?q=complex-${timestamp}&limit=5`);
    expect(searchResp.ok()).toBeTruthy();
    const data = await searchResp.json();
    const found = (data.entries || []).find((e) => {
      return (
        e.lexical_unit &&
        ((e.lexical_unit.en && e.lexical_unit.en === `complex-${timestamp}`) ||
          JSON.stringify(e.lexical_unit).includes(`complex-${timestamp}`))
      );
    });
    expect(found).toBeTruthy();
    finalComplexId = found.id;
    complexEntry = found;
  }

  expect(finalComplexId).toBeTruthy();

  // Sanity check: relations in raw JSON should include component/variant relations
  // but we primarily validate placement in the rendered form.

  // --- Act 2: reopen the complex entry form and assert UI placement ---
  await page.goto(`${base}/entries/${encodeURIComponent(finalComplexId)}/edit`);
  await page.waitForSelector('#entry-form');

  // 1) Complex Form Components card should list our component entry
  const componentsSection = page.locator('div.card:has-text("Complex Form Components")');
  await expect(componentsSection).toContainText('Complex Form Components');
  await expect(componentsSection).toContainText(`component-${timestamp}`);

  // 2) Variants card should list our variant target entry
  const variantsSection = page.locator('div.variants-section');
  await expect(variantsSection).toContainText('Variants');
  await expect(variantsSection).toContainText(`variant-target-${timestamp}`);

  // 3) Generic Relations box should NOT show any _component-lexeme relation rows
  const relationsSection = page.locator('div.relations-section');
  await expect(relationsSection).toContainText('Relations');

  // Ensure that no relation row in this box contains the component headword text
  // If the bug regresses, the component relation might leak into this box.
  const relationsText = await relationsSection.textContent();
  expect(relationsText).not.toContain(`component-${timestamp}`);

  // Additionally, ensure that no visible relation-item card in this box mentions _component-lexeme
  const relationItems = relationsSection.locator('.relation-item');
  const count = await relationItems.count();
  for (let i = 0; i < count; i++) {
    const txt = await relationItems.nth(i).textContent();
    expect(txt).not.toContain('_component-lexeme');
  }
});
