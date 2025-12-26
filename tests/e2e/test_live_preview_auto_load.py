"""
Playwright E2E test for live preview auto-load functionality.

This test checks:
1. Live preview loads automatically on page load
2. Headword is rendered correctly
3. JavaScript errors are caught and logged
4. Console debug output is captured
"""

import re
import uuid
import requests
import time
from playwright.sync_api import expect, Page


def test_live_preview_auto_load_with_debug(page: Page, flask_test_server: str):
    """Test that live preview loads automatically and renders headword."""
    
    # Create a real entry first
    entry_id = f"preview_test_{uuid.uuid4().hex[:8]}"
    lift_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
  <lexical-unit><form lang="en"><text>PreviewHeadword</text></form></lexical-unit>
  <sense id="s1"><definition><form lang="en"><text>test</text></form></definition></sense>
</entry>'''
    
    requests.post(f"{flask_test_server}/api/xml/entries", data=lift_xml.encode('utf-8'), headers={'Content-Type': 'application/xml'})
    
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

    # Navigate to an entry edit page
    page.goto(f"{flask_test_server}/entries/{entry_id}/edit")
    
    # Wait for page to load
    expect(page.locator("#entry-form")).to_be_visible()
    
    # Wait for initial preview to load (should be automatic)
    # Check for headword in preview
    preview_container = page.locator("#live-preview-container")
    expect(preview_container).to_be_visible()
    
    # Wait for it to contain the headword text
    expect(preview_container).to_contain_text("PreviewHeadword", timeout=15000)
    
    # Check for headword element specifically if needed
    headword = preview_container.locator(".headword.lexical-unit")
    
    # Assert that preview loaded correctly
    assert headword.count() > 0, "Live preview should load automatically with headword"
    assert "PreviewHeadword" in headword.inner_text()


def test_live_preview_refresh_button(page: Page, flask_test_server: str):
    """Test that refresh button works if auto-load fails."""
    
    # Create a real entry first
    entry_id = f"refresh_test_{uuid.uuid4().hex[:8]}"
    lift_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
  <lexical-unit><form lang="en"><text>RefreshHeadword</text></form></lexical-unit>
  <sense id="s1"><definition><form lang="en"><text>test</text></form></definition></sense>
</entry>'''
    
    requests.post(f"{flask_test_server}/api/xml/entries", data=lift_xml.encode('utf-8'), headers={'Content-Type': 'application/xml'})

    # Navigate to entry edit page
    page.goto(f"{flask_test_server}/entries/{entry_id}/edit")
    
    # Click refresh button
    refresh_btn = page.locator("#refresh-preview-btn")
    refresh_btn.click()
    
    # Check if preview updates
    preview_container = page.locator("#live-preview-container")
    expect(preview_container).to_contain_text("RefreshHeadword", timeout=15000)
    
    headword = preview_container.locator(".headword.lexical-unit")
    assert "RefreshHeadword" in headword.inner_text()


if __name__ == "__main__":
    # This would be run via pytest with Playwright plugin
    print("This test should be run with: pytest tests/e2e/test_live_preview_auto_load.py")