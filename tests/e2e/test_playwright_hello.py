import re
import pytest
from playwright.sync_api import Page, expect

def test_playwright_hello(page: Page, app_url) -> None:
    page.goto(f"{app_url}/")
    # Title should be present and non-empty (accept a variety of titles)
    expect(page).to_have_title(re.compile(r".+"))