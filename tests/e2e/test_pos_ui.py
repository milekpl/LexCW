"""End-to-end tests for Part of Speech (POS) functionality."""
import pytest
from playwright.sync_api import Page


def _get_base_url(flask_test_server):
    """Extract base URL from flask_test_server fixture."""
    if hasattr(flask_test_server, 'url'):
        return flask_test_server.url
    return flask_test_server


@pytest.mark.integration
def test_entry_pos_propagates_to_senses(page: Page, flask_test_server):
    """Test that setting POS on entry level propagates to all senses.

    This tests the reverse direction of inheritance - when user sets POS
    at the entry level, it should be applied to all senses that don't have
    a different POS already set.
    """
    base_url = _get_base_url(flask_test_server)
    page = page

    print("Opening entry form...")
    page.goto(f"{base_url}/entries/add")

    # Wait for page to load
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input.lexical-unit-text", timeout=10000)

    # Fill in lexical unit
    page.locator("input.lexical-unit-text").first.fill("test_propagation")

    # Add first sense
    if page.locator("#add-first-sense-btn").is_visible():
        page.click("#add-first-sense-btn")
    else:
        page.click("#add-sense-btn")

    page.wait_for_timeout(1000)

    # Wait for a real sense to appear
    page.locator('.sense-item:not(#default-sense-template):visible').first.wait_for(state='visible', timeout=5000)

    # Fill in sense definition
    sense_definition = page.locator(".sense-item .definition-text").first
    sense_definition.fill("First test definition")

    # Add second sense
    page.click("#add-sense-btn")
    page.wait_for_timeout(1000)

    # Fill in second sense definition
    sense_definitions = page.locator(".sense-item .definition-text")
    sense_definitions.nth(1).fill("Second test definition")

    # Now set POS at the entry level to "Adjective"
    # This should propagate to both senses
    page.wait_for_timeout(500)

    # Set entry-level POS using JavaScript and trigger propagation
    page.evaluate('document.getElementById("part-of-speech").value = "Adjective"')
    page.evaluate('document.getElementById("part-of-speech").dispatchEvent(new Event("change", {bubbles: true}))')

    # Wait for propagation to complete
    page.wait_for_timeout(1000)

    # Verify entry-level POS is set
    entry_pos_value = page.evaluate('document.getElementById("part-of-speech").value')
    print(f"Entry-level POS set to: {entry_pos_value}")
    assert entry_pos_value == "Adjective", f"Entry POS should be 'Adjective', got '{entry_pos_value}'"

    # Verify POS propagated to first sense
    sense_pos_selects = page.locator(".sense-item .dynamic-grammatical-info")
    first_sense_pos = sense_pos_selects.nth(0).get_attribute('value')
    print(f"First sense POS: {first_sense_pos}")
    assert first_sense_pos == "Adjective", f"First sense POS should inherit 'Adjective', got '{first_sense_pos}'"

    # Verify POS propagated to second sense
    second_sense_pos = sense_pos_selects.nth(1).get_attribute('value')
    print(f"Second sense POS: {second_sense_pos}")
    assert second_sense_pos == "Adjective", f"Second sense POS should inherit 'Adjective', got '{second_sense_pos}'"

    print("SUCCESS: Entry-level POS correctly propagated to all senses")


@pytest.mark.integration
def test_entry_pos_propagation_with_existing_sense_pos(page: Page, flask_test_server):
    """Test that entry-level POS propagation respects existing sense POS.

    When a sense already has a POS set, setting entry-level POS should
    not overwrite the sense's existing POS if it's different.
    """
    base_url = _get_base_url(flask_test_server)
    page = page

    print("Opening entry form...")
    page.goto(f"{base_url}/entries/add")

    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input.lexical-unit-text", timeout=10000)

    # Fill in lexical unit
    page.locator("input.lexical-unit-text").first.fill("test_propagation_mixed")

    # Add first sense and set its POS to "Verb"
    if page.locator("#add-first-sense-btn").is_visible():
        page.click("#add-first-sense-btn")
    else:
        page.click("#add-sense-btn")

    page.wait_for_timeout(1000)
    page.locator('.sense-item:not(#default-sense-template):visible').first.wait_for(state='visible', timeout=5000)

    sense_definition = page.locator(".sense-item .definition-text").first
    sense_definition.fill("First test definition")

    # Set first sense POS to Verb (using JavaScript)
    page.evaluate('document.querySelector(".sense-item .dynamic-grammatical-info").value = "Verb"')
    page.evaluate('document.querySelector(".sense-item .dynamic-grammatical-info").dispatchEvent(new Event("change", {bubbles: true}))')

    # Add second sense
    page.click("#add-sense-btn")
    page.wait_for_timeout(1000)

    sense_definitions = page.locator(".sense-item .definition-text")
    sense_definitions.nth(1).fill("Second test definition")

    # Now set entry-level POS to "Adjective"
    # First sense should remain "Verb", second sense should become "Adjective"
    page.evaluate('document.getElementById("part-of-speech").value = "Adjective"')
    page.evaluate('document.getElementById("part-of-speech").dispatchEvent(new Event("change", {bubbles: true}))')
    page.wait_for_timeout(1000)

    # Verify entry-level POS is "Adjective"
    entry_pos_value = page.locator("#part-of-speech").get_attribute('value')
    print(f"Entry-level POS: {entry_pos_value}")
    assert entry_pos_value == "Adjective", f"Entry POS should be 'Adjective', got '{entry_pos_value}'"

    # First sense should remain "Verb" (it was set before entry POS)
    sense_pos_selects = page.locator(".sense-item .dynamic-grammatical-info")
    first_sense_pos = sense_pos_selects.nth(0).get_attribute('value')
    print(f"First sense POS: {first_sense_pos}")
    assert first_sense_pos == "Verb", f"First sense POS should remain 'Verb', got '{first_sense_pos}'"

    # Second sense should become "Adjective" (inherited from entry)
    second_sense_pos = sense_pos_selects.nth(1).get_attribute('value')
    print(f"Second sense POS: {second_sense_pos}")
    assert second_sense_pos == "Adjective", f"Second sense POS should inherit 'Adjective', got '{second_sense_pos}'"

    print("SUCCESS: Entry-level POS propagation respects existing sense POS")
