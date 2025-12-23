"""
Playwright E2E test for live preview auto-load functionality.

This test checks:
1. Live preview loads automatically on page load
2. Headword is rendered correctly
3. JavaScript errors are caught and logged
4. Console debug output is captured
"""

import re
from playwright.sync_api import expect, Page


def test_live_preview_auto_load_with_debug(page: Page):
    """Test that live preview loads automatically and renders headword."""
    
    # Navigate to an entry edit page
    page.goto("/entries/edit/test-entry-id")  # Replace with actual entry ID
    
    # Wait for page to load
    expect(page.locator("#entry-form")).to_be_visible()
    
    # Set up console error logging
    console_messages = []
    
    def handle_console(msg):
        if msg.type == 'error':
            console_messages.append(f"ERROR: {msg.text}")
        elif msg.type == 'log' and 'DEBUG' in msg.text:
            console_messages.append(f"DEBUG: {msg.text}")
        elif 'LivePreview' in msg.text:
            console_messages.append(f"INFO: {msg.text}")
    
    page.on("console", handle_console)
    
    # Check if live preview container exists
    preview_container = page.locator("#live-preview-container")
    expect(preview_container).to_be_visible()
    
    # Wait for initial preview to load (should be automatic)
    # If it doesn't load automatically, we'll see error messages
    
    # Check for headword in preview
    headword = preview_container.locator(".headword.lexical-unit")
    
    # If headword is found, test passes
    if headword.count() > 0:
        print("✅ Live preview loaded automatically with headword")
        print(f"Headword text: {headword.inner_text()}")
    else:
        print("❌ Live preview did not load automatically")
        print(f"Preview container HTML: {preview_container.inner_html()}")
    
    # Print any console messages
    if console_messages:
        print("\nConsole messages:")
        for msg in console_messages:
            print(f"  {msg}")
    else:
        print("\nNo relevant console messages")
    
    # Check for specific issues
    if "LivePreviewManager is undefined" in str(console_messages):
        print("\n🔍 Issue: LivePreviewManager not loaded")
    elif "Form element not found" in str(console_messages):
        print("\n🔍 Issue: Form element not found")
    elif "Preview container not found" in str(console_messages):
        print("\n🔍 Issue: Preview container not found")
    elif not console_messages:
        print("\n🔍 Issue: No debug output - check if JavaScript is running")
    
    # Assert that preview loaded correctly
    assert headword.count() > 0, "Live preview should load automatically with headword"


def test_live_preview_refresh_button(page: Page):
    """Test that refresh button works if auto-load fails."""
    
    # Navigate to entry edit page
    page.goto("/entries/edit/test-entry-id")
    
    # Click refresh button
    refresh_btn = page.locator("#refresh-preview-btn")
    refresh_btn.click()
    
    # Check if preview updates
    preview_container = page.locator("#live-preview-container")
    headword = preview_container.locator(".headword.lexical-unit")
    
    # Should have headword after refresh
    assert headword.count() > 0, "Refresh button should trigger preview update"


if __name__ == "__main__":
    # This would be run via pytest with Playwright plugin
    print("This test should be run with: pytest tests/e2e/test_live_preview_auto_load.py")