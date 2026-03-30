"""
E2E tests for example sentences CRUD functionality.

Tests cover:
1. Add single example to sense
2. Add example with translation
3. Add multiple examples
4. Example persistence via API
5. Example display in view page
6. Edit example
7. Delete example
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
    search = search_entry(base_url, headword)
    if search.get('entries') and len(search['entries']) > 0:
        for entry in search['entries']:
            lu = entry.get('lexical_unit', {})
            if isinstance(lu, dict):
                if any(headword in str(v) for v in lu.values()):
                    return entry
            elif isinstance(lu, str) and headword in lu:
                return entry

    data = {
        "lexical_unit": {"en": headword},
        "senses": [{"definition": {"en": definition}}]
    }
    response = requests.post(f"{base_url}/api/entries/", json=data)
    assert response.ok, f"Failed to create entry: {response.text}"
    return response.json()


@pytest.mark.integration
@pytest.mark.playwright
def test_add_single_example(page: Page, app_url: str) -> None:
    """Test adding a single example to a sense."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"example-single-{timestamp}"
    example_text = "The cat sat on the mat."

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Find and click add example button
    add_example_btn = page.locator('button.add-example-btn').first
    if add_example_btn.count() > 0:
        add_example_btn.click()
        page.wait_for_timeout(500)

    # Fill example text - look for textarea in example item (field name is .sentence, not .form)
    example_item = page.locator('.example-item').first
    if example_item.count() > 0:
        example_textarea = example_item.locator('textarea[name*="examples"][name*="sentence"]')
        if example_textarea.count() > 0:
            example_textarea.first.fill(example_text)

    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out

    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # Verify via API
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    assert len(senses) >= 1, "Expected at least 1 sense"

    examples = senses[0].get('examples', [])
    assert len(examples) >= 1, f"Example not found: {senses[0]}"

    # Check example content - API returns 'form' dict with flattened text (e.g., {'en': 'text'})
    example_form = examples[0].get('form', {})
    example_values = list(example_form.values()) if isinstance(example_form, dict) else []
    assert any(example_text in str(v) for v in example_values), f"Example text not found: {examples[0]}"


@pytest.mark.integration
@pytest.mark.playwright
def test_add_example_with_translation(page: Page, app_url: str) -> None:
    """Test adding an example with translation."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"example-translation-{timestamp}"
    example_text = "The quick brown fox jumps over the lazy dog."
    translation_text = "Szybki brązowy lis skacze nad leniwym psem."

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Add example
    add_example_btn = page.locator('button.add-example-btn').first
    if add_example_btn.count() > 0:
        add_example_btn.click()
        page.wait_for_timeout(500)

    # Fill example text
    example_item = page.locator('.example-item').first
    if example_item.count() > 0:
        example_textarea = example_item.locator('textarea[name*="examples"][name*="sentence"]')
        if example_textarea.count() > 0:
            example_textarea.first.fill(example_text)

        # Fill translation - look for translation field
        translation_input = example_item.locator('textarea[name*="examples"][name*="translation"]')
        if translation_input.count() > 0:
            translation_input.first.fill(translation_text)

    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out

    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # Verify via API
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    examples = senses[0].get('examples', [])

    assert len(examples) >= 1, "Example not found"

    # Check translation - API returns 'translations' dict with flattened text
    translations = examples[0].get('translations', {})
    translation_values = list(translations.values()) if isinstance(translations, dict) else []
    assert any(translation_text in str(v) for v in translation_values), \
        f"Translation not found: {examples[0]}"


@pytest.mark.integration
@pytest.mark.playwright
def test_add_multiple_examples(page: Page, app_url: str) -> None:
    """Test adding multiple examples to a single sense."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"example-multi-{timestamp}"
    example1 = "First example sentence."
    example2 = "Second example sentence."
    example3 = "Third example sentence."

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Add first example
    add_example_btn = page.locator('button.add-example-btn').first
    if add_example_btn.count() > 0:
        add_example_btn.click()
        page.wait_for_timeout(300)

    example_items = page.locator('.example-item')
    if example_items.count() > 0:
        example_items.first.locator('textarea[name*="examples"][name*="sentence"]').fill(example1)

    # Add second example
    add_example_btn.click()
    page.wait_for_timeout(300)

    example_items = page.locator('.example-item')
    if example_items.count() > 1:
        example_items.nth(1).locator('textarea[name*="examples"][name*="sentence"]').fill(example2)

    # Add third example
    add_example_btn.click()
    page.wait_for_timeout(300)

    example_items = page.locator('.example-item')
    if example_items.count() > 2:
        example_items.nth(2).locator('textarea[name*="examples"][name*="sentence"]').fill(example3)

    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out

    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # Verify via API - should have 3 examples
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    examples = senses[0].get('examples', [])

    assert len(examples) >= 3, f"Expected 3 examples, got {len(examples)}: {senses[0]}"


@pytest.mark.integration
@pytest.mark.playwright
def test_example_persists_via_api(page: Page, app_url: str) -> None:
    """Test that examples persist correctly via API."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"example-persist-{timestamp}"
    expected_example = "This example should persist correctly."

    # Create entry via API first
    entry_data = create_entry_via_api(base_url, headword)
    entry_id = entry_data.get('id') or entry_data.get('entry_id')
    assert entry_id, f"Could not get entry ID: {entry_data}"

    # Edit entry and add example via UI
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)

    # Add example
    add_example_btn = page.locator('button.add-example-btn').first
    if add_example_btn.count() > 0:
        add_example_btn.click()
        page.wait_for_timeout(500)

    example_item = page.locator('.example-item').first
    if example_item.count() > 0:
        example_textarea = example_item.locator('textarea[name*="examples"][name*="sentence"]')
        if example_textarea.count() > 0:
            example_textarea.first.fill(expected_example)

    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out

    with page.expect_response(
        lambda r: f"/api/xml/entries/{entry_id}" in r.url and r.request.method == "PUT",
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Verify via API
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    examples = senses[0].get('examples', [])

    assert len(examples) >= 1, f"Example not found: {senses[0]}"

    example_form = examples[0].get('form', {})
    example_values = list(example_form.values()) if isinstance(example_form, dict) else []
    assert any(expected_example in str(v) for v in example_values), \
        f"Expected example not found: {examples[0]}"


@pytest.mark.integration
@pytest.mark.playwright
def test_example_displays_in_view(page: Page, app_url: str) -> None:
    """Test that examples display correctly in the entry view page."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"example-view-{timestamp}"
    expected_example = "View this example in the entry display."

    # Create entry via API first
    entry_data = create_entry_via_api(base_url, headword)
    entry_id = entry_data.get('id') or entry_data.get('entry_id')
    assert entry_id, f"Could not get entry ID: {entry_data}"

    # Edit entry and add example
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)

    add_example_btn = page.locator('button.add-example-btn').first
    if add_example_btn.count() > 0:
        add_example_btn.click()
        page.wait_for_timeout(500)

    example_item = page.locator('.example-item').first
    if example_item.count() > 0:
        example_textarea = example_item.locator('textarea[name*="examples"][name*="sentence"]')
        if example_textarea.count() > 0:
            example_textarea.first.fill(expected_example)

    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out

    with page.expect_response(
        lambda r: f"/api/xml/entries/{entry_id}" in r.url and r.request.method == "PUT",
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Navigate to view page
    page.goto(f"{base_url}/entries/{entry_id}")
    page.wait_for_timeout(2000)

    # Verify example is displayed
    page_content = page.content()
    assert expected_example in page_content, f"Example '{expected_example}' not found in view page"


@pytest.mark.integration
@pytest.mark.playwright
def test_edit_example(page: Page, app_url: str) -> None:
    """Test editing an existing example via API."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"example-edit-{timestamp}"
    original_example = "Original example text."
    updated_example = "Updated example text."

    # Create entry with example via API
    # Note: Examples use legacy format {"en": "text"} not {"form": {"en": "text"}}
    data = {
        "lexical_unit": {"en": headword},
        "senses": [{
            "definition": {"en": f"Definition for {headword}"},
            "examples": [{"en": original_example}]
        }]
    }
    response = requests.post(f"{base_url}/api/entries/", json=data)
    assert response.ok, f"Failed to create entry: {response.text}"
    entry = response.json()
    entry_id = entry.get('id') or entry.get('entry_id')
    assert entry_id, f"Could not get entry ID: {entry}"

    # Verify original example is present
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    examples = senses[0].get('examples', [])
    example_form = examples[0].get('form', {})
    example_values = list(example_form.values()) if isinstance(example_form, dict) else []
    assert original_example in str(example_values), f"Original example not found: {examples[0]}"

    # Update example via API (use legacy format)
    data = {
        "senses": [{
            "definition": {"en": f"Definition for {headword}"},
            "examples": [{"en": updated_example}]
        }]
    }
    response = requests.put(f"{base_url}/api/entries/{entry_id}", json=data)
    assert response.ok, f"Failed to update entry: {response.text}"

    # Verify update
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    examples = senses[0].get('examples', [])
    example_form = examples[0].get('form', {})
    example_values = list(example_form.values()) if isinstance(example_form, dict) else []
    example_str = str(example_values)

    assert updated_example in example_str, f"Updated example not found: {examples[0]}"
    assert original_example not in example_str, f"Original example should be replaced: {examples[0]}"


@pytest.mark.integration
@pytest.mark.playwright
def test_delete_example(page: Page, app_url: str) -> None:
    """Test deleting an example from a sense."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"example-delete-{timestamp}"
    example_text = "Example to be deleted."

    # Create entry with example
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Add example
    add_example_btn = page.locator('button.add-example-btn').first
    if add_example_btn.count() > 0:
        add_example_btn.click()
        page.wait_for_timeout(500)

    example_item = page.locator('.example-item').first
    if example_item.count() > 0:
        example_textarea = example_item.locator('textarea[name*="examples"][name*="sentence"]')
        if example_textarea.count() > 0:
            example_textarea.first.fill(example_text)

    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out

    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, "Could not find created entry"

    # Verify example exists
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    examples_before = senses[0].get('examples', [])
    assert len(examples_before) >= 1, "Example should exist"

    # Edit and delete example - depends on UI implementation
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)

    # Remove the example - either by clicking remove button or clearing the field
    example_item = page.locator('.example-item').first
    if example_item.count() > 0:
        # Try to find remove button
        remove_btn = example_item.locator('button.remove-example-btn')
        if remove_btn.count() > 0:
            # Handle dialog if it appears
            page.on("dialog", lambda dialog: dialog.accept())
            remove_btn.first.click()
            page.wait_for_timeout(500)
        else:
            # Clear the text field instead
            example_textarea = example_item.locator('textarea[name*="examples"][name*="sentence"]')
            if example_textarea.count() > 0:
                example_textarea.first.clear()

    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out

    with page.expect_response(
        lambda r: f"/api/xml/entries/{entry_id}" in r.url and r.request.method == "PUT",
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Verify example is gone
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    examples_after = senses[0].get('examples', [])

    assert len(examples_after) == 0, f"Example should be deleted: {examples_after}"
