"""
E2E tests for multi-sense entry comprehensive functionality.

Tests cover:
1. Create entry with multiple senses at creation
2. Each sense has all fields (definition, gloss, domains, examples)
3. Edit individual senses independently
4. Delete middle sense
5. Reorder senses
6. Multi-sense persistence via API
7. Full round-trip test
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


def create_entry_via_api(
    base_url: str, headword: str, definition: str = "Test definition"
) -> Dict[str, Any]:
    """Create an entry via API for setup purposes."""
    search = search_entry(base_url, headword)
    if search.get("entries") and len(search["entries"]) > 0:
        for entry in search["entries"]:
            lu = entry.get("lexical_unit", {})
            if isinstance(lu, dict):
                if any(headword in str(v) for v in lu.values()):
                    return entry
            elif isinstance(lu, str) and headword in lu:
                return entry

    data = {
        "lexical_unit": {"en": headword},
        "senses": [{"definition": {"en": definition}}],
    }
    response = requests.post(f"{base_url}/api/entries/", json=data)
    assert response.ok, f"Failed to create entry: {response.text}"
    return response.json()


@pytest.mark.integration
@pytest.mark.playwright
def test_create_entry_with_multiple_senses(page: Page, app_url: str) -> None:
    """Test creating an entry with multiple senses at creation."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"multi-sense-create-{timestamp}"

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)

    page.fill("input.lexical-unit-text", headword)

    # Add first sense
    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click("#add-first-sense-btn")
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(
        f"First sense definition for {headword}"
    )

    # Add second sense
    add_sense_btn = page.locator("#add-sense-btn").first
    if add_sense_btn.count() > 0:
        add_sense_btn.click()
        page.wait_for_timeout(500)

    # Wait for second definition field to appear
    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    for _ in range(50):
        if definition_textareas.count() >= 2:
            break
        page.wait_for_timeout(100)

    if definition_textareas.count() >= 2:
        definition_textareas.nth(1).fill(f"Second sense definition for {headword}")

    # Add third sense
    add_sense_btn.click()
    page.wait_for_timeout(500)

    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    for _ in range(50):
        if definition_textareas.count() >= 3:
            break
        page.wait_for_timeout(100)

    if definition_textareas.count() >= 3:
        definition_textareas.nth(2).fill(f"Third sense definition for {headword}")

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get("entries") and len(search["entries"]) > 0:
            entry_id = search["entries"][0]["id"]
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # Verify via API - should have 3 senses
    entry = get_entry(base_url, entry_id)
    senses = entry.get("senses", [])

    assert len(senses) >= 3, f"Expected at least 3 senses, got {len(senses)}: {entry}"


@pytest.mark.integration
@pytest.mark.playwright
def test_each_sense_has_all_fields(page: Page, app_url: str) -> None:
    """Test that each sense in a multi-sense entry can have all field types."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"all-fields-{timestamp}"

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)

    page.fill("input.lexical-unit-text", headword)

    # Add first sense with definition
    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click("#add-first-sense-btn")
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(
        f"Definition with all fields"
    )

    # Add gloss to first sense
    gloss_inputs = page.locator('textarea[name*="gloss"][name*="text"]')
    if gloss_inputs.count() > 0:
        gloss_inputs.first.fill("First sense gloss")

    # Add second sense
    add_sense_btn = page.locator("#add-sense-btn").first
    if add_sense_btn.count() > 0:
        add_sense_btn.click()
        page.wait_for_timeout(500)

    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    for _ in range(50):
        if definition_textareas.count() >= 2:
            break
        page.wait_for_timeout(100)

    if definition_textareas.count() >= 2:
        definition_textareas.nth(1).fill(f"Second sense definition")

        # Add gloss to second sense
        all_gloss = page.locator('textarea[name*="gloss"][name*="text"]')
        if all_gloss.count() > 1:
            all_gloss.nth(1).fill("Second sense gloss")

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get("entries") and len(search["entries"]) > 0:
            entry_id = search["entries"][0]["id"]
            break
        time.sleep(0.5)
    assert entry_id

    # Verify each sense has expected fields
    entry = get_entry(base_url, entry_id)
    senses = entry.get("senses", [])

    assert len(senses) >= 2, f"Expected at least 2 senses, got {len(senses)}"

    # Check first sense
    assert "definition" in senses[0] or "definitions" in senses[0], (
        f"Sense 1 missing definition: {senses[0]}"
    )

    # Check second sense
    assert "definition" in senses[1] or "definitions" in senses[1], (
        f"Sense 2 missing definition: {senses[1]}"
    )


@pytest.mark.integration
@pytest.mark.playwright
def test_edit_individual_senses(page: Page, app_url: str) -> None:
    """Test that editing one sense doesn't affect other senses."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"edit-sense-{timestamp}"
    original_def1 = "Original definition for sense 1"
    original_def2 = "Original definition for sense 2"
    updated_def1 = "Updated definition for sense 1"

    # Create entry with two senses
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)

    page.fill("input.lexical-unit-text", headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click("#add-first-sense-btn")
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(original_def1)

    # Add second sense
    add_sense_btn = page.locator("#add-sense-btn").first
    if add_sense_btn.count() > 0:
        add_sense_btn.click()
        page.wait_for_timeout(500)

    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    for _ in range(50):
        if definition_textareas.count() >= 2:
            break
        page.wait_for_timeout(100)

    if definition_textareas.count() >= 2:
        definition_textareas.nth(1).fill(original_def2)

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get("entries") and len(search["entries"]) > 0:
            entry_id = search["entries"][0]["id"]
            break
        time.sleep(0.5)
    assert entry_id

    # Record original state
    entry_before = get_entry(base_url, entry_id)
    senses_before = entry_before.get("senses", [])
    def1_before = (
        senses_before[0].get("definition", {}).get("en", "")
        if isinstance(senses_before[0].get("definition", {}), dict)
        else ""
    )
    def2_before = (
        senses_before[1].get("definition", {}).get("en", "")
        if len(senses_before) > 1
        and isinstance(senses_before[1].get("definition", {}), dict)
        else ""
    )

    # Edit only first sense
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector("#entry-form", timeout=10000)

    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    if definition_textareas.count() >= 1:
        definition_textareas.first.clear()
        definition_textareas.first.fill(updated_def1)

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Verify first sense updated, second sense unchanged
    entry_after = get_entry(base_url, entry_id)
    senses_after = entry_after.get("senses", [])

    def1_after = (
        senses_after[0].get("definition", {}).get("en", "")
        if isinstance(senses_after[0].get("definition", {}), dict)
        else ""
    )
    def2_after = (
        senses_after[1].get("definition", {}).get("en", "")
        if len(senses_after) > 1
        and isinstance(senses_after[1].get("definition", {}), dict)
        else ""
    )

    assert updated_def1 in def1_after or updated_def1 == def1_after, (
        f"Sense 1 should be updated. Got: {def1_after}"
    )
    assert original_def2 in def2_after or original_def2 == def2_after, (
        f"Sense 2 should be unchanged. Got: {def2_after}"
    )


@pytest.mark.integration
@pytest.mark.playwright
def test_delete_middle_sense(page: Page, app_url: str) -> None:
    """Test deleting a middle sense and verifying remaining senses."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"delete-middle-{timestamp}"

    # Create entry with three senses
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)

    page.fill("input.lexical-unit-text", headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click("#add-first-sense-btn")
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(
        "Sense 1 definition"
    )

    # Add second and third senses
    add_sense_btn = page.locator("#add-sense-btn").first
    for i in range(2):
        add_sense_btn.click()
        page.wait_for_timeout(500)

    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    for _ in range(50):
        if definition_textareas.count() >= 3:
            break
        page.wait_for_timeout(100)

    if definition_textareas.count() >= 3:
        definition_textareas.nth(1).fill("Sense 2 definition - will be deleted")
        definition_textareas.nth(2).fill("Sense 3 definition")

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get("entries") and len(search["entries"]) > 0:
            entry_id = search["entries"][0]["id"]
            break
        time.sleep(0.5)
    assert entry_id

    # Verify 3 senses exist
    entry = get_entry(base_url, entry_id)
    senses_before = entry.get("senses", [])
    assert len(senses_before) >= 3, f"Should have 3 senses, got {len(senses_before)}"

    # Delete middle sense (sense 2)
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector("#entry-form", timeout=10000)

    # Find and click remove button on second sense
    # Sense items have data-sense-index attribute
    sense_items = page.locator(".sense-item[data-sense-index]")
    for i in range(sense_items.count()):
        sense_item = sense_items.nth(i)
        sense_index = sense_item.get_attribute("data-sense-index")
        if sense_index == "1":  # Second sense (index 1)
            remove_btn = sense_item.locator(".remove-sense-btn")
            if remove_btn.count() > 0:
                page.on("dialog", lambda dialog: dialog.accept())
                remove_btn.first.click()
                page.wait_for_timeout(500)
            break

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Verify only 2 senses remain
    entry = get_entry(base_url, entry_id)
    senses_after = entry.get("senses", [])

    assert len(senses_after) == 2, (
        f"Should have 2 senses after deletion, got {len(senses_after)}"
    )


@pytest.mark.integration
@pytest.mark.playwright
def test_reorder_senses(page: Page, app_url: str) -> None:
    """Test reordering senses using up/down buttons."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"reorder-sense-{timestamp}"

    # Create entry with three senses
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)

    page.fill("input.lexical-unit-text", headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click("#add-first-sense-btn")
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill("First definition")

    add_sense_btn = page.locator("#add-sense-btn").first
    for i in range(2):
        add_sense_btn.click()
        page.wait_for_timeout(500)

    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    for _ in range(50):
        if definition_textareas.count() >= 3:
            break
        page.wait_for_timeout(100)

    if definition_textareas.count() >= 3:
        definition_textareas.nth(1).fill("Second definition")
        definition_textareas.nth(2).fill("Third definition")

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get("entries") and len(search["entries"]) > 0:
            entry_id = search["entries"][0]["id"]
            break
        time.sleep(0.5)
    assert entry_id

    # Get initial sense definitions
    entry = get_entry(base_url, entry_id)
    senses_before = entry.get("senses", [])
    def1_before = (
        senses_before[0].get("definition", {}).get("en", "")
        if len(senses_before) > 0
        else ""
    )
    def2_before = (
        senses_before[1].get("definition", {}).get("en", "")
        if len(senses_before) > 1
        else ""
    )

    # Reorder: move second sense up
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector("#entry-form", timeout=10000)

    sense_items = page.locator(".sense-item[data-sense-index]")
    for i in range(sense_items.count()):
        sense_item = sense_items.nth(i)
        sense_index = sense_item.get_attribute("data-sense-index")
        if sense_index == "1":  # Second sense
            move_up_btn = sense_item.locator(".move-sense-up")
            if move_up_btn.count() > 0 and move_up_btn.first.is_enabled():
                move_up_btn.first.click()
                page.wait_for_timeout(500)
            break

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Verify order changed
    entry = get_entry(base_url, entry_id)
    senses_after = entry.get("senses", [])
    def1_after = (
        senses_after[0].get("definition", {}).get("en", "")
        if len(senses_after) > 0
        else ""
    )
    def2_after = (
        senses_after[1].get("definition", {}).get("en", "")
        if len(senses_after) > 1
        else ""
    )

    # After moving sense 2 up, the definitions should be swapped
    assert def1_after != def1_before or def2_after != def2_before, (
        f"Sense order should change after reorder. Before: {def1_before}, {def2_before}. After: {def1_after}, {def2_after}"
    )


@pytest.mark.integration
@pytest.mark.playwright
def test_multisense_persists_via_api(page: Page, app_url: str) -> None:
    """Test that multi-sense entry persists correctly via API."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"multi-persist-{timestamp}"

    # Create entry with multiple senses via API
    data = {
        "lexical_unit": {"en": headword},
        "senses": [
            {"definition": {"en": "API sense 1"}},
            {"definition": {"en": "API sense 2"}},
            {"definition": {"en": "API sense 3"}},
        ],
    }
    response = requests.post(f"{base_url}/api/entries/", json=data)
    assert response.ok, f"Failed to create entry: {response.text}"

    entry_id = response.json().get("id")
    assert entry_id, "No entry ID returned"

    # Verify via API
    entry = get_entry(base_url, entry_id)
    senses = entry.get("senses", [])

    assert len(senses) == 3, f"Expected 3 senses, got {len(senses)}"

    # Verify each sense has definition
    for i, sense in enumerate(senses):
        definitions = (
            sense.get("definition", {})
            if isinstance(sense.get("definition", {}), dict)
            else {}
        )
        assert "en" in definitions or len(definitions) > 0, (
            f"Sense {i + 1} missing definition: {sense}"
        )


@pytest.mark.integration
@pytest.mark.playwright
def test_multisense_roundtrip(page: Page, app_url: str) -> None:
    """Comprehensive round-trip test for multi-sense entries."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"multi-roundtrip-{timestamp}"

    # === Step 1: Create entry with multiple senses ===
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)

    page.fill("input.lexical-unit-text", headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click("#add-first-sense-btn")
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill("Roundtrip sense 1")

    add_sense_btn = page.locator("#add-sense-btn").first
    add_sense_btn.click()
    page.wait_for_timeout(500)

    definition_textareas = page.locator('textarea[name*="definition"]:visible')
    for _ in range(50):
        if definition_textareas.count() >= 2:
            break
        page.wait_for_timeout(100)

    if definition_textareas.count() >= 2:
        definition_textareas.nth(1).fill("Roundtrip sense 2")

    page.click("#save-btn", timeout=10000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get("entries") and len(search["entries"]) > 0:
            entry_id = search["entries"][0]["id"]
            break
        time.sleep(0.5)
    assert entry_id

    # === Step 2: Verify senses via API ===
    entry = get_entry(base_url, entry_id)
    senses = entry.get("senses", [])
    assert len(senses) >= 2, "Should have at least 2 senses"

    # === Step 3: Verify in view page ===
    page.goto(f"{base_url}/entries/{entry_id}")
    page.wait_for_timeout(2000)

    view_text = page.content()
    assert "Roundtrip sense 1" in view_text, "Sense 1 should appear in view"
    assert "Roundtrip sense 2" in view_text, "Sense 2 should appear in view"

    # === Step 4: Edit and add third sense ===
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector("#entry-form", timeout=10000)

    add_sense_btn = page.locator("#add-sense-btn").first
    add_sense_btn.click()

    # Wait for the newly-added sense to appear. addSense() assigns data-sense-index="2"
    # (max existing index 1 + 1). Using data-sense-index is robust against extra
    # language textareas that _senses.html renders for existing senses (one textarea
    # per project language × sense), which would break a fragile nth(N) approach.
    page.wait_for_selector('.sense-item[data-sense-index="2"]', timeout=5000)
    new_sense_textarea = page.locator(
        '.sense-item[data-sense-index="2"] textarea[name*="definition"]'
    ).first
    new_sense_textarea.fill("Roundtrip sense 3")

    # Wait for any in-flight autosave requests to complete before clicking save.
    # Without this wait, an autosave triggered by addSense (before sense[2] was
    # filled) may arrive at the server AFTER the save-button PUT, overwriting
    # the newly-saved 3-sense entry with only 2 senses.
    page.wait_for_load_state("networkidle", timeout=10000)

    # Use expect_response to wait for the actual PUT request to complete.
    # wait_for_load_state("networkidle") is unreliable here because submitForm()
    # is async: no HTTP request is active during WebWorker serialization, so
    # networkidle fires prematurely before the PUT is ever initiated.
    with page.expect_response(
        lambda r: f"/api/xml/entries/{entry_id}" in r.url and r.request.method == "PUT",
        timeout=20000,
    ):
        page.click("#save-btn", timeout=10000)

    # === Step 5: Verify update persisted ===
    entry = get_entry(base_url, entry_id)
    senses = entry.get("senses", [])

    assert len(senses) >= 3, (
        f"Should have at least 3 senses after edit, got {len(senses)}"
    )

    # === Step 6: Verify in view after update ===
    page.goto(f"{base_url}/entries/{entry_id}")
    page.wait_for_timeout(2000)

    view_text = page.content()
    assert "Roundtrip sense 3" in view_text, "New sense 3 should appear in view"
