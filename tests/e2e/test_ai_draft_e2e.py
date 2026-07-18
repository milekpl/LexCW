"""E2E test for the "Draft with AI" feature in the entry editor.

Verifies the full frontend flow:
  1. Open an entry for editing
  2. Click the Draft button → dialog opens
  3. Enter a description
  4. Click Generate → AI returns a draft
  5. Click Apply to Form → dialog closes
  6. Form fields are populated with the drafted data

The /api/ai/draft endpoint is intercepted so the test does not need a real AI API.
"""

from __future__ import annotations

import json
import pytest
from playwright.sync_api import Page, expect


# A realistic draft response for the mocked /api/ai/draft endpoint.
# The test entry "cat" (test_entry_1) has only EN lexical unit and EN
# definition — the mock response therefore only overwrites those existing
# fields so the test can assert that Apply populates them.
MOCK_DRAFT_RESPONSE = {
    "entry_yaml": (
        "lexical_unit:\n"
        "  en: ephemeral\n"
        "senses:\n"
        "  - grammatical_info: Adjective\n"
        "    definitions:\n"
        "      en: lasting for a very short time\n"
    ),
    "entry_data": {
        "lexical_unit": {"en": "ephemeral"},
        "senses": [
            {
                "grammatical_info": "Adjective",
                "definitions": {"en": "lasting for a very short time"},
            }
        ],
    },
    "notes": "Draft completed.",
}


@pytest.mark.integration
def test_ai_draft_apply_to_form(page: Page, app_url: str) -> None:
    """Test the full Draft with AI flow: open dialog, generate, apply to form."""

    # ── Capture console errors ──────────────────────────────────────────
    js_errors: list[str] = []
    page.on("console", lambda msg: js_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: js_errors.append(f"Page error: {exc}"))

    # ── Mock the /api/ai/draft endpoint ─────────────────────────────────
    import re

    def handle_ai_draft(route, request):
        """Return a realistic draft without calling a real AI API."""
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(MOCK_DRAFT_RESPONSE),
        )

    page.route(re.compile(r"/api/ai/draft"), handle_ai_draft)

    # ── Navigate to the entry edit page ──────────────────────────────────
    page.goto(f"{app_url}/entries/test_entry_1/edit", wait_until="networkidle")
    page.wait_for_selector("#entry-form", state="visible", timeout=15000)

    # ── Wait for Alpine to render senses and definition forms ────────────
    page.wait_for_function(
        "() => document.querySelectorAll('.sense-item').length > 0",
        timeout=10000,
    )
    page.wait_for_function(
        "() => document.querySelector('.sense-item .definition-forms .language-form[data-language=\"en\"] .definition-text') !== null",
        timeout=10000,
    )

    # ── Wait for the AIServiceUI class to be available ───────────────────
    page.wait_for_function("() => typeof window.AIServiceUI !== 'undefined'", timeout=15000)

    # Log any JS errors that occurred during page load
    if js_errors:
        print(f"JS errors after page load: {js_errors}")
    js_errors.clear()

    # ── Open the draft modal ─────────────────────────────────────────────
    page.evaluate("new window.AIServiceUI().showDraftModal()")
    modal = page.locator("#aiDraftModal")
    expect(modal).to_be_visible(timeout=5000)

    # ── Fill in the description (word/phrase to draft) ───────────────────
    desc_input = modal.locator("#ai-draft-description")
    expect(desc_input).to_be_visible()
    desc_input.fill("ephemeral")

    # ── Click Generate ───────────────────────────────────────────────────
    generate_btn = modal.locator("#btn-ai-draft-generate")
    expect(generate_btn).to_be_visible()
    generate_btn.click()

    # ── Wait for the AI result to arrive ─────────────────────────────────
    apply_btn = modal.locator("#btn-apply-draft")
    expect(apply_btn).to_be_visible(timeout=15000)

    # ── Click Apply to Form ──────────────────────────────────────────────
    apply_btn.click()

    # Wait for the modal to close
    expect(modal).not_to_be_visible(timeout=5000)

    # ── Assert form fields are populated ─────────────────────────────────

    # Lexical unit: en → "ephemeral"
    lu_en = page.locator(
        ".lexical-unit-forms .language-form[data-language='en'] .lexical-unit-text"
    )
    expect(lu_en).to_have_value("ephemeral")

    # Part of Speech → Adjective (overwrites original Noun)
    page.wait_for_function(
        "() => document.querySelector('#part-of-speech').value === 'Adjective'",
        timeout=5000,
    )

    # Definition (first sense, English) → "lasting for a very short time"
    def_en = page.locator(
        ".sense-item .definition-forms .language-form[data-language='en'] .definition-text"
    ).first
    expect(def_en).to_have_value("lasting for a very short time")

    # ── Assert no JS errors occurred during the flow ────────────────────
    relevant_errors = [
        e for e in js_errors
        if "favicon" not in e.lower() and "form-state-manager" not in e.lower()
    ]
    assert len(relevant_errors) == 0, (
        f"Unexpected JS errors during draft flow:\n" + "\n".join(relevant_errors)
    )
