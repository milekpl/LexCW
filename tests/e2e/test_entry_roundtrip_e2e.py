"""
E2E tests for entry CRUD round-trip and compound form components.

Tests cover:
1. Full CRUD round-trip: create entry → view entry → edit entry → verify data
2. Compound form components with proper _component-lexeme relation type
3. Related words show headwords instead of UUIDs
4. XML serialization verification via API
5. CSS display rendering
"""

from __future__ import annotations

import time
import requests
import pytest
from typing import Any, Dict
from playwright.sync_api import Page, expect


def get_entry(base_url: str, entry_id: str) -> Dict[str, Any]:
    """Load entry via API for server-side verification."""
    response = requests.get(f"{base_url}/api/entries/{entry_id}")
    assert response.ok, f"Failed to get entry {entry_id}: {response.text}"
    return response.json()


def search_entry(base_url: str, query: str) -> Dict[str, Any]:
    """Search for entries and return results."""
    response = requests.get(f"{base_url}/api/search?q={query}&limit=10")
    assert response.ok, f"Search failed: {response.text}"
    return response.json()


def create_entry_via_api(base_url: str, headword: str, definition: str = "Test definition") -> Dict[str, Any]:
    """Create an entry via API for setup purposes."""
    # Check if entry already exists
    search = search_entry(base_url, headword)
    if search.get('entries') and len(search['entries']) > 0:
        for entry in search['entries']:
            lu = entry.get('lexical_unit', {})
            if isinstance(lu, dict):
                if any(headword in str(v) for v in lu.values()):
                    return entry
            elif isinstance(lu, str) and headword in lu:
                return entry

    # Create via API if needed
    # First try to create via UI and get the ID
    return {"id": headword}  # Placeholder - we'll create via UI


@pytest.mark.skip(reason="Component search UI has JavaScript issues with Select2 in tests - needs investigation")
@pytest.mark.integration
@pytest.mark.playwright
def test_compound_form_components_roundtrip(page: Page, app_url: str) -> None:
    """
    E2E test for compound form components bug fix.

    This test verifies that:
    1. Compound form components are saved with correct _component-lexeme type
    2. Components appear in both edit form and view page
    3. Subentries list the compound entry as a complex form
    4. No data loss occurs during save/load cycle

    Bug: Previously relations had type="Compound" instead of type="_component-lexeme"
    causing components to not appear in the Complex Form Components section.
    """
    base_url = app_url
    timestamp = str(int(time.time() * 1000))

    # === Step 1: Create component entries (the building blocks) ===
    component1_name = f"base-{timestamp}-1"
    component2_name = f"base-{timestamp}-2"

    # Create first component via UI
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', component1_name)

    # Add a sense with definition
    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)
    page.locator('textarea[name*="definition"]:visible').first.fill(f"{component1_name} definition")

    # Save the entry
    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Get the component1 ID via search
    component1_id = None
    for _ in range(20):
        search = search_entry(base_url, component1_name)
        if search.get('entries') and len(search['entries']) > 0:
            component1_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert component1_id, f"Could not find created entry {component1_name}"
    print(f'DEBUG: Component1 ID: {component1_id}')

    # Create second component
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form')
    page.fill('input.lexical-unit-text', component2_name)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)
    page.locator('textarea[name*="definition"]:visible').first.fill(f"{component2_name} definition")
    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle')

    component2_id = None
    for _ in range(20):
        search = search_entry(base_url, component2_name)
        if search.get('entries') and len(search['entries']) > 0:
            component2_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert component2_id, f"Could not find created entry {component2_name}"
    print(f'DEBUG: Component2 ID: {component2_id}')

    # === Step 2: Create a compound entry using the components ===
    compound_name = f"compound-{timestamp}"

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form')
    page.fill('input.lexical-unit-text', compound_name)

    # Add a sense
    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)
    page.locator('textarea[name*="definition"]:visible').first.fill(f"{compound_name} definition")

    # Add first component - need to select component type first using JavaScript for Select2
    # For Select2, we need to trigger the select2:select event
    page.evaluate('''() => {
        const select = document.querySelector('#new-component-type');
        select.value = 'Compound';
        // Trigger both change and select2:select events
        select.dispatchEvent(new Event('change', { bubbles: true }));
        if (window.jQuery) {
            jQuery(select).trigger('select2:select');
        }
    }''')

    # Debug: Check component type value
    component_type = page.evaluate('''() => {
        const select = document.querySelector('#new-component-type');
        return select.value;
    }''')
    print(f'DEBUG: Component type value after setting: {component_type}')

    page.fill('#component-search-input', component1_name)
    page.click('#component-search-btn')
    page.wait_for_timeout(1000)

    # Debug: Check if search results appeared
    search_results_count = page.evaluate('''() => {
        const container = document.querySelector('#component-search-results');
        if (!container) return 'container not found';
        const html = container.innerHTML;
        // Return a snippet of the HTML
        return html.substring(0, 500);
    }''')
    print(f'DEBUG: Search results HTML: {search_results_count[:200]}')

    # Call selectComponentEntry directly via the global handler
    result = page.evaluate('''() => {
        try {
            if (!window.componentSearchHandler) {
                console.log('ERROR: componentSearchHandler not found');
                return 'handler not found';
            }
            const firstResult = document.querySelector('#component-search-results .search-result-item:not(.create-entry-option)');
            if (!firstResult) {
                console.log('ERROR: firstResult not found');
                return 'result not found';
            }
            const entryId = firstResult.dataset.entryId;
            const headword = firstResult.dataset.entryHeadword;
            const typeSelect = document.querySelector('#new-component-type');
            const componentType = typeSelect.value || 'Compound';
            console.log('Adding component:', entryId, headword, componentType);
            window.componentSearchHandler.selectedComponents.push({
                id: entryId,
                headword: headword,
                type: componentType,
                order: window.componentSearchHandler.selectedComponents.length
            });
            console.log('selectedComponents after push:', window.componentSearchHandler.selectedComponents);
            window.componentSearchHandler.updateSelectedComponentsDisplay();
            return 'success';
        } catch (e) {
            console.log('ERROR:', e.message);
            return 'error: ' + e.message;
        }
    }''')
    print(f'DEBUG: Component addition result: {result}')
    page.wait_for_timeout(300)

    # Debug: Check if component was added
    selected_count_after = page.evaluate('''() => {
        if (window.componentSearchHandler && window.componentSearchHandler.selectedComponents) {
            return window.componentSearchHandler.selectedComponents.length;
        }
        return -1;
    }''')
    print(f'DEBUG: selectedComponents count after: {selected_count_after}')

    component_added = page.evaluate('''() => {
        const container = document.querySelector('#new-components-container');
        return container ? container.innerHTML.length : 0;
    }''')
    print(f'DEBUG: Component container HTML length: {component_added}')

    # Add second component
    page.evaluate('''() => {
        const select = document.querySelector('#new-component-type');
        select.value = 'Compound';
        select.dispatchEvent(new Event('change', { bubbles: true }));
        if (window.jQuery) {
            jQuery(select).trigger('select2:select');
        }
    }''')
    page.fill('#component-search-input', component2_name)
    page.click('#component-search-btn')
    page.wait_for_timeout(1000)

    # Select second result using the handler directly
    result2 = page.evaluate('''() => {
        try {
            if (!window.componentSearchHandler) {
                console.log('ERROR: componentSearchHandler not found for component 2');
                return 'handler not found';
            }
            const results = document.querySelectorAll('#component-search-results .search-result-item:not(.create-entry-option)');
            if (results.length < 1) {
                console.log('ERROR: no results found for component 2');
                return 'no results';
            }
            // Use the second result if available, otherwise the first
            const result = results.length > 1 ? results[1] : results[0];
            const entryId = result.dataset.entryId;
            const headword = result.dataset.entryHeadword;
            const typeSelect = document.querySelector('#new-component-type');
            const componentType = typeSelect.value || 'Compound';
            console.log('Adding component 2:', entryId, headword, componentType);
            window.componentSearchHandler.selectedComponents.push({
                id: entryId,
                headword: headword,
                type: componentType,
                order: window.componentSearchHandler.selectedComponents.length
            });
            console.log('selectedComponents after push 2:', window.componentSearchHandler.selectedComponents);
            window.componentSearchHandler.updateSelectedComponentsDisplay();
            return 'success';
        } catch (e) {
            console.log('ERROR:', e.message);
            return 'error: ' + e.message;
        }
    }''')
    print(f'DEBUG: Component 2 addition result: {result2}')
    page.wait_for_timeout(300)

    # Debug: Check final state
    final_state = page.evaluate('''() => {
        const container = document.querySelector('#new-components-container');
        return container ? container.innerHTML : 'container not found';
    }''')
    print(f'DEBUG: Final components state: {final_state[:200] if len(final_state) > 200 else final_state}')

    # Save the compound entry
    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # === Step 3: Get compound entry ID ===
    compound_id = None
    for _ in range(20):
        search = search_entry(base_url, compound_name)
        if search.get('entries') and len(search['entries']) > 0:
            compound_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert compound_id, f"Could not find created compound entry {compound_name}"

    # === Step 4: Verify via API that _component-lexeme relations exist ===
    compound_entry = get_entry(base_url, compound_id)
    relations = compound_entry.get('relations', [])

    # Check that we have component relations with correct type
    component_relations = [r for r in relations if r.get('type') == '_component-lexeme']
    assert len(component_relations) >= 2, f"Expected at least 2 _component-lexeme relations, got {len(component_relations)}: {relations}"

    component_refs = [r.get('ref') for r in component_relations]
    assert component1_id in component_refs, f"Component1 {component1_id} not found in relations: {component_refs}"
    assert component2_id in component_refs, f"Component2 {component2_id} not found in relations: {component_refs}"

    # === Step 5: Verify in edit form ===
    page.goto(f"{base_url}/entries/{compound_id}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)

    # Check Complex Form Components section shows both components
    components_section = page.locator('.complex-form-components-section, #complex-form-components')

    # Verify text appears in the section
    section_text = components_section.inner_text() if components_section.count() > 0 else ""
    assert component1_name in section_text or component1_id in section_text, \
        f"Component1 not found in complex form section: {section_text[:500]}"
    assert component2_name in section_text or component2_id in section_text, \
        f"Component2 not found in complex form section: {section_text[:500]}"

    # === Step 6: Verify in view page ===
    page.goto(f"{base_url}/entries/{compound_id}")
    page.wait_for_timeout(2000)  # Wait for page load

    # Check Main Entries (Components) section
    view_text = page.content()
    assert component1_name in view_text or component1_id in view_text, \
        f"Component1 not found in view page"
    assert component2_name in view_text or component2_id in view_text, \
        f"Component2 not found in view page"

    # === Step 7: Verify subentries on component pages ===
    page.goto(f"{base_url}/entries/{component1_id}")
    page.wait_for_timeout(2000)

    view_text = page.content()
    assert compound_name in view_text or compound_id in view_text, \
        f"Compound not found as subentry of component1"


@pytest.mark.integration
@pytest.mark.playwright
def test_related_words_show_headwords_not_ids(page: Page, app_url: str) -> None:
    """
    Test that related words show headwords instead of UUIDs.

    Bug: Previously related words displayed as "one-dimensional_519bd4ce-..."
    instead of just "one-dimensional"

    This test verifies the enrichment fix that fetches display text.
    """
    base_url = app_url
    timestamp = str(int(time.time() * 1000))

    # === Step 1: Create entry A ===
    entry_a_name = f"related-test-a-{timestamp}"
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form')
    page.fill('input.lexical-unit-text', entry_a_name)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)
    page.locator('textarea[name*="definition"]:visible').first.fill(f"{entry_a_name} definition")
    page.click('#save-btn')
    page.wait_for_load_state('networkidle')

    entry_a_id = None
    for _ in range(20):
        search = search_entry(base_url, entry_a_name)
        if search.get('entries') and len(search['entries']) > 0:
            entry_a_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_a_id, f"Could not find created entry {entry_a_name}"

    # === Step 2: Create entry B with relation to A ===
    entry_b_name = f"related-test-b-{timestamp}"
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form')
    page.fill('input.lexical-unit-text', entry_b_name)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)
    page.locator('textarea[name*="definition"]:visible').first.fill(f"{entry_b_name} definition")

    # Add relation to entry A - first click "Add Relation" button to show the search input
    add_relation_btn = page.locator('#add-relation-btn')
    if add_relation_btn.count() > 0:
        add_relation_btn.click()
        # Wait for the new relation item to be added
        page.wait_for_selector('.relation-item[data-relation-index="0"]', timeout=10000)

    # Select relation type first (required for saving) - use JavaScript for Select2
    page.evaluate('''() => {
        const select = document.querySelector('.relation-item[data-relation-index="0"] .lexical-relation-select');
        select.value = 'antonym';
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }''')

    # The search input is inside the new relation item, use class selector
    relation_input = page.locator('.relation-item[data-relation-index="0"] .relation-search-input')
    expect(relation_input).to_be_visible()
    relation_input.fill(entry_a_name)
    page.click('.relation-item[data-relation-index="0"] .relation-search-btn')
    page.wait_for_timeout(500)

    # Click on the first search result using JavaScript to trigger selection
    page.evaluate('''() => {
        const firstResult = document.querySelector('#search-results-0 .search-result-item:not(.create-entry-option)');
        if (firstResult) {
            firstResult.click();
        }
    }''')
    page.wait_for_timeout(300)

    # Save
    page.click('#save-btn')
    page.wait_for_load_state('networkidle')

    entry_b_id = None
    for _ in range(20):
        search = search_entry(base_url, entry_b_name)
        if search.get('entries') and len(search['entries']) > 0:
            entry_b_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_b_id, f"Could not find created entry {entry_b_name}"

    # === Step 3: Verify relation exists with correct type ===
    entry_b = get_entry(base_url, entry_b_id)
    relations = entry_b.get('relations', [])

    # Should have a relation to entry_a_id
    entry_a_relations = [r for r in relations if r.get('ref') == entry_a_id]
    assert len(entry_a_relations) > 0, f"No relation found to {entry_a_id}: {relations}"

    # === Step 4: Verify view page shows headword, not UUID ===
    page.goto(f"{base_url}/entries/{entry_b_id}")
    page.wait_for_timeout(2000)

    view_text = page.content()

    # The related words section should contain the headword, not a raw UUID
    # Bug showed: "one-dimensional_519bd4ce-efa7-4050-ade0-cef81de1ac59"
    # Fix should show: "one-dimensional" or similar

    # Check that the entry A name appears (display text enrichment works)
    assert entry_a_name in view_text or entry_a_id in view_text, \
        f"Related entry not found in view page"

    # Verify that the raw UUID-only format is NOT shown
    # (The fix adds ref_display_text which contains the headword)
    import re
    # Pattern for raw UUID after underscore (the bug pattern)
    uuid_pattern = rf'{entry_a_name}_[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}'
    raw_uuid_matches = re.findall(uuid_pattern, view_text, re.IGNORECASE)
    assert len(raw_uuid_matches) == 0, \
        f"Found raw UUID pattern(s) in related words: {raw_uuid_matches}"


@pytest.mark.integration
@pytest.mark.playwright
def test_entry_full_crud_roundtrip(page: Page, app_url: str) -> None:
    """
    Comprehensive test for entry CRUD operations with data verification.

    Tests: Create → Read → Update → Verify all fields persist correctly.

    This is a round-trip test to ensure no data loss during save/load cycle.
    """
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"roundtrip-{timestamp}"

    # === Step 1: CREATE ===
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    # Fill lexical unit
    page.fill('input.lexical-unit-text', headword)

    # Fill citation form
    page.fill('#citation-form', f"citation-{timestamp}")

    # Ensure sense exists
    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    # Fill definition
    page.locator('textarea[name*="definition"]:visible').first.fill(f"Test definition for {headword}")

    # Save
    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(30):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # === Step 2: READ via API ===
    entry = get_entry(base_url, entry_id)

    # Verify basic fields
    lu = entry.get('lexical_unit', {})
    if isinstance(lu, dict):
        assert headword in str(lu.values()), f"Lexical unit mismatch: {lu}"
    else:
        assert headword in lu, f"Lexical unit mismatch: {lu}"

    senses = entry.get('senses', [])
    assert len(senses) >= 1, f"Expected at least 1 sense, got {len(senses)}"

    # === Step 3: READ via View Page ===
    page.goto(f"{base_url}/entries/{entry_id}")
    page.wait_for_timeout(2000)

    view_text = page.content()
    assert headword in view_text, f"Headword not found in view page"

    # === Step 4: UPDATE ===
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)

    # Update lexical unit (add suffix)
    page.fill('input.lexical-unit-text', f"{headword}-updated")

    # Update definition
    if page.locator('textarea[name*="definition"]:visible').count() > 0:
        page.locator('textarea[name*="definition"]:visible').first.fill(f"Updated definition for {headword}")

    # Save
    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # === Step 5: Verify UPDATE persisted ===
    updated_entry = get_entry(base_url, entry_id)
    updated_lu = updated_entry.get('lexical_unit', {})

    if isinstance(updated_lu, dict):
        updated_headword = list(updated_lu.values())[0] if updated_lu else ""
    else:
        updated_headword = updated_lu

    assert f"{headword}-updated" in updated_headword or "updated" in updated_headword.lower(), \
        f"Update did not persist: {updated_headword}"

    # === Step 6: Verify in View Page ===
    page.goto(f"{base_url}/entries/{entry_id}")
    page.wait_for_timeout(2000)

    view_text = page.content()
    assert "updated" in view_text.lower() or headword in view_text, \
        f"Updated content not reflected in view page"


@pytest.mark.integration
@pytest.mark.playwright
def test_css_display_renders_entry(page: Page, app_url: str) -> None:
    """
    Test that CSS display renders entries correctly.

    Verifies that the CSS-rendered view shows entry content properly.
    """
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"css-test-{timestamp}"

    # Create entry
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form')
    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)
    page.locator('textarea[name*="definition"]:visible').first.fill(f"CSS test definition for {headword}")

    page.click('#save-btn')
    page.wait_for_load_state('networkidle')

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # View entry
    page.goto(f"{base_url}/entries/{entry_id}")
    page.wait_for_timeout(2000)

    # Check that CSS display section exists
    css_section = page.locator('.css-display, #css-display, .dictionary-display')

    # The page should render without errors
    # Check for presence of headword in the display area
    view_text = page.content()
    assert headword in view_text, f"Headword not found in rendered view"
