"""Debug test to see what's actually on the entry form page."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.integration
def test_debug_entry_form(page: Page, app_url: str) -> None:
    """Debug test to capture what's on the entry form."""
    # Go to add new entry page
    page.goto(f"{app_url}/entry/add")
    page.wait_for_load_state("networkidle")
    
    # Take a screenshot
    page.screenshot(path="/tmp/entry_form_debug.png")
    
    # Get page HTML
    html = page.content()
    with open("/tmp/entry_form_debug.html", "w") as f:
        f.write(html)
    
    # Check if annotations section exists
    annotations_section = page.locator('.annotations-section-entry')
    print(f"\nAnnotations section count: {annotations_section.count()}")
    
    # Check if add button exists
    add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
    print(f"Add annotation button count: {add_btn.count()}")
    
    # Check if any card exists
    cards = page.locator('.card')
    print(f"Total cards on page: {cards.count()}")
    
    # Print all card headers
    for i in range(cards.count()):
        card_header = cards.nth(i).locator('.card-header')
        if card_header.count() > 0:
            print(f"Card {i} header: {card_header.inner_text()}")
    
    assert True  # Always pass, we just want to see the output
