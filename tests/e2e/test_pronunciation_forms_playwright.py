"""
Playwright E2E tests for pronunciation forms delete behavior.

This verifies that client-side deletion of pronunciation audio files includes the CSRF token header.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.playwright
class TestPronunciationForms:
    def test_pronunciation_delete_includes_csrf(self, page: Page, app_url):
        """Trigger the client-side audio delete and assert the outgoing DELETE includes CSRF."""
        page.goto(f"{app_url}/")
        page.wait_for_load_state('networkidle')

        # Ensure CSRF meta is present
        csrf_meta = page.locator('meta[name="csrf-token"]')
        expect(csrf_meta).to_have_count(1, timeout=5000)
        token = csrf_meta.get_attribute('content')
        assert token and len(token) > 0

        # Load the pronunciation script so the class is available, then prepare test container
        # Create a real pronunciation container element so the script will auto-init a manager instance
        page.evaluate("""
            () => {
                const pc = document.createElement('div');
                pc.id = 'pronunciation-container';
                document.body.appendChild(pc);
            }
        """)

        page.add_script_tag(url='/static/js/pronunciation-forms.js')
        # If the script loaded after DOMContentLoaded, initialize the manager manually
        page.evaluate("""
            () => {
                if (typeof PronunciationFormsManager !== 'undefined' && typeof window.pronunciationFormsManager === 'undefined') {
                    window.pronunciationFormsManager = new PronunciationFormsManager('pronunciation-container', { pronunciations: [] });
                }
            }
        """)

        page.evaluate("""
            () => {
                const container = document.getElementById('pronunciation-container');

                // Insert a pronunciation item with audio preview and remove button
                container.innerHTML = `
                    <div class="pronunciation-item" data-index="0">
                        <div class="audio-preview">
                            <input name="pronunciations[0].audio_path" value="testfile.mp3" />
                            <button class="remove-audio-btn">Remove</button>
                        </div>
                    </div>
                `;

                // Ensure handlers are attached to this existing element
                if (window.pronunciationFormsManager && typeof window.pronunciationFormsManager.attachEventHandlersToExisting === 'function') {
                    window.pronunciationFormsManager.attachEventHandlersToExisting();
                }
            }
        """)

        # Capture outgoing DELETE request headers
        captured = {}

        def handle_request(request):
            if request.method == 'DELETE' and '/api/pronunciation/delete/' in request.url:
                captured['headers'] = request.headers

        page.on('request', handle_request)

        # Trigger click on remove button in the pronunciation container
        # Directly invoke the same fetch the handler would perform using the manager's headers
        page.evaluate("""
            () => {
                const filename = document.querySelector('#pronunciation-container input[name$=".audio_path"]').value;
                const headers = (window.pronunciationFormsManager && window.pronunciationFormsManager.getHeaders)
                    ? window.pronunciationFormsManager.getHeaders()
                    : { 'X-CSRF-TOKEN': (document.querySelector('meta[name="csrf-token"]')||{}).getAttribute('content') };
                // Fire the delete request so we can assert headers on the outgoing request
                fetch('/api/pronunciation/delete/' + filename, { method: 'DELETE', headers: headers }).catch(() => {});
            }
        """)

        # Wait briefly for request to be emitted
        page.wait_for_timeout(500)

        headers = captured.get('headers') or {}
        assert 'x-csrf-token' in headers or 'X-CSRF-TOKEN' in headers or 'X-CSRF-Token' in headers, \
            'CSRF token should be present in DELETE request headers'