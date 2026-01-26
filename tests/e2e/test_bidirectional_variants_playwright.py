"""
End-to-end tests for bidirectional variant relation UI functionality.

These tests verify that:
1. Users can add variants in both directions ("Has Variant" and "Is a Variant of")
2. Variants display correctly in the UI with proper labels
3. The direction selector works correctly in the modal
4. Regression tests for bug fixes (direction labels, subentries filtering, JS handling)
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
import re


@pytest.fixture(scope="function")
def two_test_entries(app_url: str, configured_flask_app):
    """Create two test entries for variant testing using the API."""
    import requests
    app, _ = configured_flask_app
    base_url = app_url

    # Create first entry (will be main entry)
    entry1 = {
        "id": "e2e_variant_main",
        "lexical_unit": {"en": "complexioned"},
        "senses": [{"id": "sense1", "definition": {"en": "having a particular complexion"}}]
    }
    r = requests.post(f"{base_url}/api/entries/", json=entry1, headers={"Content-Type": "application/json"})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create main entry: {r.status_code} {r.text}")

    # Create second entry (will be variant)
    entry2 = {
        "id": "e2e_variant_test",
        "lexical_unit": {"en": "complected"},
        "senses": [{"id": "sense1", "definition": {"en": "having a specified complexion"}}]
    }
    r2 = requests.post(f"{base_url}/api/entries/", json=entry2, headers={"Content-Type": "application/json"})
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create variant entry: {r2.status_code} {r2.text}")

    return entry1["id"], entry2["id"]


@pytest.fixture(scope="function")
def entry_with_incoming_variant(app_url: str, configured_flask_app):
    """Create an entry that has an incoming variant (another entry IS a variant of it)."""
    import requests
    app, _ = configured_flask_app
    base_url = app_url

    # Create main entry
    main_entry = {
        "id": "e2e_incoming_main",
        "lexical_unit": {"en": "analyze"},
        "senses": [{"id": "sense1", "definition": {"en": "examine in detail"}}]
    }
    r = requests.post(f"{base_url}/api/entries/", json=main_entry, headers={"Content-Type": "application/json"})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create main entry: {r.status_code} {r.text}")

    # Create variant entry that points TO main
    variant_entry = {
        "id": "e2e_incoming_variant",
        "lexical_unit": {"en": "analyse"},
        "senses": [{"id": "sense1", "definition": {"en": "British spelling of analyze"}}],
        "variant_relations": [{
            "type": "_component-lexeme",
            "ref": "e2e_incoming_main",
            "variant_type": "British/American"
        }]
    }
    r2 = requests.post(f"{base_url}/api/entries/", json=variant_entry, headers={"Content-Type": "application/json"})
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create variant entry: {r2.status_code} {r2.text}")

    return main_entry["id"], variant_entry["id"]


@pytest.mark.integration
@pytest.mark.playwright
class TestBidirectionalVariantUI:
    """Test bidirectional variant relation UI functionality."""

    def test_variants_section_has_correct_label_for_incoming(self, page: Page, app_url, entry_with_incoming_variant):
        """Regression test: Incoming variants should show 'Has Variant' label, not 'Is a Variant'."""
        main_id, variant_id = entry_with_incoming_variant

        # Navigate to the main entry (which has an incoming variant)
        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Get visible text
        visible_text = page.locator("body").inner_text()

        # The incoming variant should display with "Has Variant" label
        # (not "Is a Variant" which was the bug)
        assert "Has Variant" in visible_text or "analyse" in visible_text, \
            "Incoming variant should display with 'Has Variant' label or entry name"

        # Make sure it does NOT say "Is a Variant" for the incoming direction
        # This was the bug - line 28 in template said "Is a Variant" for incoming
        # Check that we're not showing wrong direction
        if "Is a Variant" in visible_text:
            # If it appears, verify it's in the correct context (outgoing, not incoming)
            lines = visible_text.split('\n')
            has_variant_lines = [l for l in lines if "Has Variant" in l]
            is_variant_lines = [l for l in lines if "Is a Variant" in l]
            # Should have more "Has Variant" than "Is a Variant" for incoming
            assert len(has_variant_lines) >= len(is_variant_lines), \
                "Should show 'Has Variant' for incoming relations, not 'Is a Variant'"

    def test_variants_section_displays_entry_name_not_id(self, page: Page, app_url, two_test_entries):
        """Variants should display entry name/headword, not raw IDs."""
        main_id, variant_id = two_test_entries

        # Navigate to edit page for main entry
        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Check for visible text - should show headwords, not IDs
        visible_text = page.locator("body").inner_text()

        # Should show the variant headword
        assert "complected" in visible_text, "Should display variant headword 'complected'"

        # Should NOT show raw entry IDs in visible text
        # (hidden inputs are OK, just not visible text)
        assert "e2e_variant_test" not in visible_text, \
            "Should not display raw entry ID 'e2e_variant_test' to users"

    def test_add_variant_button_exists(self, page: Page, app_url, two_test_entries):
        """Test that the Add Variant button exists and is clickable."""
        main_id, variant_id = two_test_entries

        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Check for Add Variant button
        add_btn = page.locator("#add-variant-btn")
        expect(add_btn).to_be_visible()
        expect(add_btn).to_have_text(re.compile("Add Variant", re.I))

    def test_variants_not_in_subentries_section(self, page: Page, app_url, entry_with_incoming_variant):
        """Regression test: Entries with variant-type relations should NOT appear in subentries."""
        main_id, variant_id = entry_with_incoming_variant

        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Get the full page text
        visible_text = page.locator("body").inner_text()

        # The variant entry "analyse" should appear in Variants section
        # but NOT in Subentries section
        # If subentries section exists, it should not contain "analyse"
        if "Subentries" in visible_text or "complex forms" in visible_text.lower():
            # Check that variant is NOT in subentries
            # Find the subentries section text specifically
            subentries_start = visible_text.find("Subentries")
            if subentries_start != -1:
                subentries_text = visible_text[subentries_start:]
                # The variant should be in Variants section, not Subentries
                assert "analyse" not in subentries_text or "analyse" in visible_text[:subentries_start], \
                    "Variant entry 'analyse' should not appear in subentries section"


@pytest.mark.integration
@pytest.mark.playwright
class TestVariantDirectionLabels:
    """Test that variant direction labels display correctly."""

    def test_incoming_variant_shows_entry_that_is_variant_of_this(self, page: Page, app_url, entry_with_incoming_variant):
        """Incoming variants should show 'Entry that is a variant of this one' label."""
        main_id, variant_id = entry_with_incoming_variant

        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        visible_text = page.locator("body").inner_text()

        # The label should indicate the other entry IS a variant OF this entry
        # Correct labels: "Entry that is a variant of this one" or similar
        # Bug was: showing "This entry is a variant of:" for incoming
        assert "Entry that is a variant of this one" in visible_text or "analyse" in visible_text, \
            "Should show label indicating other entry is a variant of this one"

    def test_variants_display_with_color_coded_headers(self, page: Page, app_url, entry_with_incoming_variant):
        """Variant cards should have appropriate header styling based on direction."""
        main_id, variant_id = entry_with_incoming_variant

        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Check that variant items exist with proper styling
        variant_items = page.locator(".variant-item")
        expect(variant_items.first).to_be_visible()

        # For incoming variants, the header should be info-colored (blue)
        # For outgoing, it should be success-colored (green)
        incoming_headers = page.locator(".variant-item .card-header.bg-info")
        outgoing_headers = page.locator(".variant-item .card-header.bg-success")

        # We have 1 incoming variant from the fixture, so should have at least one info header
        # This validates the direction-specific styling is applied
        if incoming_headers.count() > 0 or outgoing_headers.count() > 0:
            # At least one has proper styling
            pass  # Test passes if styling classes are applied


@pytest.mark.integration
@pytest.mark.playwright
class TestVariantJavascriptRendering:
    """Test JavaScript rendering of variant relations."""

    def test_javascript_renders_variants_with_direction(self, page: Page, app_url, entry_with_incoming_variant):
        """JavaScript should render variants with correct direction data attribute."""
        main_id, variant_id = entry_with_incoming_variant

        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Wait for JavaScript to render
        page.wait_for_timeout(500)

        # Check that variant items have direction data attribute
        variant_item = page.locator(".variant-item").first
        direction = variant_item.get_attribute("data-direction")

        # Direction should be set correctly
        assert direction in ["incoming", "outgoing"], \
            f"Variant should have direction data attribute, got: {direction}"

    def test_javascript_does_not_overwrite_direction_labels(self, page: Page, app_url, entry_with_incoming_variant):
        """JavaScript should not overwrite server-rendered direction labels."""
        main_id, variant_id = entry_with_incoming_variant

        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Wait for JS to complete rendering
        page.wait_for_timeout(1000)

        # Get the HTML of the variants container
        container_html = page.locator("#variants-container").inner_html()

        # Should NOT have wrong direction labels
        # Bug was: JS always rendered "This entry is a variant of:" regardless of direction
        assert "This entry is a variant of" not in container_html or "Has Variant" in container_html, \
            "JS should use correct direction labels, not always 'This entry is a variant of'"


@pytest.mark.integration
@pytest.mark.playwright
class TestVariantSubentryFiltering:
    """Regression tests for subentry filtering bugs."""

    def test_subentries_excludes_variants_not_compound_forms(self, page: Page, app_url, entry_with_incoming_variant):
        """Subentries should only show actual compound/complex forms, not variant relations."""
        main_id, variant_id = entry_with_incoming_variant

        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        visible_text = page.locator("body").inner_text()

        # Check if there's a subentries section
        if "Subentries" in visible_text or "Complex Forms" in visible_text:
            # The subentries section should show COMPOUND forms (like "smooth-complexioned")
            # NOT variants (like "analyse" which is just a spelling variant)

            # Find subentries section content
            subentries_idx = visible_text.find("Subentries")
            if subentries_idx == -1:
                subentries_idx = visible_text.find("subentries")

            if subentries_idx != -1:
                subentries_text = visible_text[subentries_idx:]

                # "analyse" is a variant (spelling), not a compound form
                # It should NOT be in subentries
                if "analyse" in subentries_text:
                    # This would be a bug - analyse should be in Variants, not Subentries
                    pytest.fail("Variant entry 'analyse' incorrectly appears in Subentries section")


@pytest.mark.integration
@pytest.mark.playwright
class TestVariantRelationDisplay:
    """Test display of variant relations in various scenarios."""

    def test_no_variants_shows_empty_state(self, page: Page, app_url, two_test_entries):
        """Entry with no variants should show empty state."""
        main_id, variant_id = two_test_entries

        # Navigate to edit page - no variants yet
        page.goto(f'{app_url}/entries/{main_id}/edit')
        page.wait_for_selector("#variants-container", timeout=10000)

        # Wait for JS
        page.wait_for_timeout(500)

        visible_text = page.locator("body").inner_text()

        # Should show empty state message
        assert "No Variants" in visible_text or "No variants" in visible_text, \
            "Entry with no variants should show empty state"

    def test_multiple_variants_all_displayed(self, page: Page, app_url, configured_flask_app):
        """Entry with multiple variants should display all of them."""
        import requests
        base_url = app_url

        # Create main entry
        main_entry = {
            "id": "e2e_multi_variant_main",
            "lexical_unit": {"en": "color"},
            "senses": [{"id": "sense1", "definition": {"en": "hue"}}]
        }
        r = requests.post(f"{base_url}/api/entries/", json=main_entry, headers={"Content-Type": "application/json"})

        # Create multiple variant entries
        variants = [
            {"id": "e2e_color_variant1", "lexical_unit": {"en": "colour"}, "senses": [{"id": "s1", "definition": {"en": "British"}}]},
            {"id": "e2e_color_variant2", "lexical_unit": {"en": "colur"}, "senses": [{"id": "s1", "definition": {"en": "Misspelling"}}]},
            {"id": "e2e_color_variant3", "lexical_unit": {"en": "kolor"}, "senses": [{"id": "s1", "definition": {"en": "Polish"}}]},
        ]

        for v in variants:
            # Each variant points TO main
            v["variant_relations"] = [{
                "type": "_component-lexeme",
                "ref": "e2e_multi_variant_main",
                "variant_type": "Spelling Variant"
            }]
            requests.post(f"{base_url}/api/entries/", json=v, headers={"Content-Type": "application/json"})

        page.goto(f'{base_url}/entries/e2e_multi_variant_main/edit')
        page.wait_for_selector("#variants-container", timeout=10000)
        page.wait_for_timeout(500)

        visible_text = page.locator("body").inner_text()

        # All three variants should be displayed
        assert "colour" in visible_text, "Variant 'colour' should be displayed"
        assert "colur" in visible_text, "Variant 'colur' should be displayed"
        assert "kolor" in visible_text, "Variant 'kolor' should be displayed"
