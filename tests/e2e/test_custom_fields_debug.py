"""Debug test for click handlers."""
import pytest
from playwright.sync_api import Page

@pytest.mark.integration
def test_debug_click_handlers(page: Page, app_url: str):
    """Debug test to check click handlers."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_load_state("load")
    
    # Fill in the entry
    lexical_unit = page.locator('input.lexical-unit-text').first
    if lexical_unit.is_visible():
        lexical_unit.fill("test-word")
    
    add_sense_btn = page.locator('#add-sense-btn')
    if add_sense_btn.is_visible():
        add_sense_btn.click()
        # Wait for a definition textarea to appear instead of sleeping
        page.wait_for_selector('textarea.definition-text:visible', timeout=3000)
    
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    # Alpine uses button text rather than class for add-language buttons
    page.wait_for_selector('button:has-text("Add Language")', timeout=3000)
    
    # Check for multiple buttons
    all_buttons = page.locator('button:has-text("Add Language")')
    print(f"Number of Add Language buttons: {all_buttons.count()}")
    
    # Check if any button is inside a template
    templates = page.locator('[id*="template"], .d-none, .template')
    print(f"Template-like elements: {templates.count()}")
    
    # Check the actual button element
    btn = page.locator('button:has-text("Add Language")').first
    btn_html = page.evaluate("""
        () => {
            const btn = document.querySelector('button:has-text("Add Language")');
            if (btn) {
                return {
                    outerHTML: btn.outerHTML,
                    parentElement: btn.parentElement?.tagName,
                    ancestors: getAncestors(btn)
                };
            }
            return null;
        }
        
        function getAncestors(elem) {
            const ancestors = [];
            let current = elem.parentElement;
            while (current) {
                ancestors.push({
                    tag: current.tagName,
                    classes: current.className,
                    id: current.id
                });
                current = current.parentElement;
            }
            return ancestors;
        }
    """)
    print(f"Button info: {btn_html}")
