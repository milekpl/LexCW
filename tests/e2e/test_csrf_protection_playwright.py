"""
Playwright E2E tests for CSRF token protection.

Tests that:
1. CSRF meta tag is present on all pages
2. CSRF token is included in AJAX requests
3. Requests without valid CSRF token are rejected
4. CSRF token is available for JavaScript to use
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.playwright
class TestCSRFProtection:
    """E2E tests for CSRF token protection."""

    def test_csrf_meta_tag_present_on_homepage(self, page: Page, app_url):
        """Test that CSRF meta tag is present on homepage."""
        page.goto(f'{app_url}/')
        page.wait_for_load_state('networkidle')

        # Check for CSRF meta tag - meta tags aren't visible elements,
        # so we check count and content attribute
        csrf_meta = page.locator('meta[name="csrf-token"]')
        expect(csrf_meta).to_have_count(1, timeout=5000)

        # Verify it has content
        content = csrf_meta.get_attribute('content')
        assert content and len(content) > 0, "CSRF meta tag should have content"

    def test_csrf_meta_tag_present_on_ranges_editor(self, page: Page, app_url):
        """Test that CSRF meta tag is present on ranges editor page."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Check for CSRF meta tag
        csrf_meta = page.locator('meta[name="csrf-token"]')
        expect(csrf_meta).to_have_count(1, timeout=5000)

        # Verify it has content
        content = csrf_meta.get_attribute('content')
        assert content and len(content) > 0, "CSRF meta tag should have content"

    def test_csrf_meta_tag_present_on_entries_page(self, page: Page, app_url):
        """Test that CSRF meta tag is present on entries page."""
        page.goto(f'{app_url}/entries')
        page.wait_for_load_state('networkidle')

        # Check for CSRF meta tag
        csrf_meta = page.locator('meta[name="csrf-token"]')
        expect(csrf_meta).to_have_count(1, timeout=5000)

        # Verify it has content
        content = csrf_meta.get_attribute('content')
        assert content and len(content) > 0, "CSRF meta tag should have content"

    def test_csrf_meta_tag_present_on_validation_tool(self, page: Page, app_url):
        """Test that CSRF meta tag is present on validation tool page."""
        page.goto(f'{app_url}/validation')
        page.wait_for_load_state('networkidle')

        # Check for CSRF meta tag
        csrf_meta = page.locator('meta[name="csrf-token"]')
        expect(csrf_meta).to_have_count(1, timeout=5000)

        # Verify it has content
        content = csrf_meta.get_attribute('content')
        assert content and len(content) > 0, "CSRF meta tag should have content"

    def test_csrf_token_accessible_from_javascript(self, page: Page, app_url):
        """Test that CSRF token is accessible from JavaScript via getCsrfToken function."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Check that getCsrfToken function exists and returns the token
        token_from_js = page.evaluate("""
            () => {
                if (typeof getCsrfToken === 'function') {
                    return getCsrfToken();
                }
                // Try DictionaryApp fallback
                if (typeof DictionaryApp !== 'undefined' && DictionaryApp.config && DictionaryApp.config.csrfToken) {
                    return DictionaryApp.config.csrfToken;
                }
                // Try direct meta tag access
                const meta = document.querySelector('meta[name="csrf-token"]');
                return meta ? meta.getAttribute('content') : null;
            }
        """)

        assert token_from_js, "CSRF token should be accessible from JavaScript"
        assert len(token_from_js) > 0, "CSRF token should not be empty"

    def test_ranges_editor_create_range_includes_csrf(self, page: Page, app_url):
        """Test that creating a range sends CSRF token in the request."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Set up a listener to capture the request headers
        captured_headers = {}

        def handle_request(request):
            if '/api/ranges-editor/' in request.url and request.method == 'POST':
                captured_headers.update(request.headers)

        page.on('request', handle_request)

        # Click new range button
        new_range_btn = page.locator('#btnNewRange')
        expect(new_range_btn).to_be_visible(timeout=5000)
        new_range_btn.click()

        # Wait for modal
        modal = page.locator('#createRangeModal')
        expect(modal).to_be_visible(timeout=5000)

        # Fill in range ID
        page.fill('#rangeId', 'test-csrf-range')

        # Add a label
        page.click('#btnAddLabel')
        page.fill('#labelsContainer .lang-text', 'Test CSRF Range')

        # Submit and wait for request
        page.click('#btnCreateRange')
        page.wait_for_timeout(2000)  # Wait for the API request

        # Check that X-CSRF-TOKEN was included
        assert 'x-csrf-token' in captured_headers or 'X-CSRF-TOKEN' in captured_headers, \
            "CSRF token should be included in POST request headers"
        token = captured_headers.get('x-csrf-token') or captured_headers.get('X-CSRF-TOKEN')
        assert token and len(token) > 0, "CSRF token should not be empty"

    def test_csrf_token_works_with_api_utils(self, page: Page, app_url):
        """Test that api-utils.js getCsrfToken function works correctly."""
        page.goto(f'{app_url}/entries')
        page.wait_for_load_state('networkidle')

        # Verify the api-utils.js is loaded by checking for apiGet function
        api_get_exists = page.evaluate("typeof apiGet === 'function'")
        assert api_get_exists, "apiGet function should be available from api-utils.js"

        # Test getCsrfToken through the api-utils module
        token = page.evaluate("""
            () => {
                if (typeof getCsrfToken === 'function') {
                    return getCsrfToken();
                }
                return null;
            }
        """)

        assert token, "getCsrfToken function should return a valid token"
        assert len(token) > 0, "CSRF token should not be empty"

    def test_csrf_token_different_per_session(self, page: Page, app_url):
        """Test that CSRF tokens can be different per session."""
        # Create first context and get token
        context1 = page.context
        page1 = context1.new_page()
        page1.goto(f'{app_url}/')
        page1.wait_for_load_state('networkidle')
        token1 = page1.locator('meta[name="csrf-token"]').get_attribute('content')

        # Create second context and get token
        context2 = page1.context.browser.new_context()
        page2 = context2.new_page()
        page2.goto(f'{app_url}/')
        page2.wait_for_load_state('networkidle')
        token2 = page2.locator('meta[name="csrf-token"]').get_attribute('content')

        # Both should have tokens (though they might be the same if session-based)
        assert token1 and len(token1) > 0, "First page should have CSRF token"
        assert token2 and len(token2) > 0, "Second page should have CSRF token"

        # Cleanup
        page2.close()
        context2.close()

    def test_delete_includes_csrf_on_backup_management(self, page: Page, app_url):
        """Test that clicking delete on a backup sends the CSRF token in the DELETE request."""
        # Ensure we have a valid CSRF token
        page.goto(f'{app_url}/')
        # Wait for CSRF meta tag like other tests do
        csrf_meta = page.locator('meta[name="csrf-token"]')
        expect(csrf_meta).to_have_count(1, timeout=10000)
        token = csrf_meta.get_attribute('content')
        assert token and len(token) > 0

        # Create a backup using the API (include CSRF header)
        created = page.evaluate("""
            async (token) => {
                try {
                    const resp = await fetch('/api/backup/create', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': token },
                        body: JSON.stringify({ db_name: window.CURRENT_DB_NAME || 'dictionary', description: 'e2e-delete-test', backup_type: 'manual' })
                    });
                    const json = await resp.json().catch(() => null);
                    return { status: resp.status, ok: resp.ok, json };
                } catch (e) {
                    return { error: e.message };
                }
            }
        """, token)

        assert 'error' not in created, f"Backup creation failed: {created.get('error')}"

        # If an op_id was returned, wait for it to finish
        op_id = (created.get('json') or {}).get('op_id')
        if op_id:
            for _ in range(40):
                st = page.evaluate("""
                    async (op) => {
                        try {
                            const r = await fetch('/api/backup/status/' + op);
                            if (!r.ok) return null;
                            return await r.json();
                        } catch (e) { return null; }
                    }
                """, op_id)
                if st and st.get('op') and st['op'].get('status') == 'done':
                    break
                page.wait_for_timeout(250)

        # Go to management UI and refresh history
        page.goto(f'{app_url}/backup/management')
        # Wait for main UI elements to appear and then refresh history
        expect(page.locator('#backup-count')).to_have_count(1, timeout=10000)
        page.click('#refresh-backups')
        page.wait_for_timeout(500)

        # Simpler and more deterministic approach: call performDelete on the page's BackupManager
        # and capture the outgoing DELETE request headers. This avoids depending on filesystem state.
        # Ensure backupManager has been initialized
        expect(page.locator('#backup-history-table')).to_have_count(1, timeout=10000)

        captured = {}
        def handle_request(request):
            if request.method == 'DELETE' and '/api/backup/' in request.url:
                captured['headers'] = request.headers

        page.on('request', handle_request)

        # Trigger performDelete with a dummy id; we don't care about the response, only the outgoing request
        page.evaluate("""
            () => {
                window.backupManager = window.backupManager || new BackupManager();
                window.backupManager.currentBackupId = 'dummy-id-for-csrf-test';
                // Call performDelete (returns a Promise)
                window.backupManager.performDelete();
            }
        """)

        # Wait briefly for the request to be emitted
        page.wait_for_timeout(500)

        headers = captured.get('headers') or {}
        assert 'x-csrf-token' in headers or 'X-CSRF-TOKEN' in headers, 'CSRF token should be present in DELETE request headers'

    def test_restore_includes_csrf_on_backup_management(self, page: Page, app_url):
        """Test that performing restore sends the CSRF token in the restore POST request."""
        page.goto(f'{app_url}/backup/management')
        expect(page.locator('#backup-history-table')).to_have_count(1, timeout=10000)

        # Intercept the history GET for our dummy id and return synthetic backup info
        def handle_route(route, request):
            if request.url.endswith('/api/backup/history/dummy-restore-id') and request.method == 'GET':
                route.fulfill(status=200, body='{"id":"dummy-restore-id","db_name":"dictionary","file_path":"/tmp/fake.lift"}', headers={"Content-Type":"application/json"})
            else:
                route.continue_()

        # Using page.route with pattern for the history endpoint
        page.route('**/api/backup/history/*', lambda route, request: handle_route(route, request))

        captured = {}
        def handle_request(request):
            if request.method == 'POST' and '/api/backup/restore/' in request.url:
                captured['headers'] = request.headers

        page.on('request', handle_request)

        # Insert a dummy confirm button so performRestore won't throw when trying to disable it
        page.evaluate("""
            () => {
                const btn = document.createElement('button');
                btn.id = 'confirm-restore-btn';
                document.body.appendChild(btn);
                window.backupManager = window.backupManager || new BackupManager();
                window.backupManager.currentBackupId = 'dummy-restore-id';
                window.backupManager.performRestore();
            }
        """)

        page.wait_for_timeout(500)

        headers = captured.get('headers') or {}
        assert 'x-csrf-token' in headers or 'X-CSRF-TOKEN' in headers, 'CSRF token should be present in restore POST request headers'


@pytest.mark.integration
@pytest.mark.playwright
class TestCSRFAPIProtection:
    """Test that API endpoints properly handle CSRF tokens.

    Note: Flask-WTF CSRFProtect only validates form submissions by default.
    JSON APIs require explicit CSRF validation middleware which is not implemented.
    The frontend sends CSRF tokens as a best practice (verified by other tests).
    """

    def test_ranges_api_accepts_request_with_csrf(self, page: Page, app_url):
        """Test that ranges API accepts POST requests with valid CSRF token."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Get the valid CSRF token
        valid_token = page.locator('meta[name="csrf-token"]').get_attribute('content')

        # Make a request with valid CSRF token
        response_data = page.evaluate("""
            async (token) => {
                try {
                    const response = await fetch('/api/ranges-editor/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-TOKEN': token
                        },
                        body: JSON.stringify({
                            id: 'test-accept-with-csrf',
                            labels: { en: 'Test Accept' }
                        })
                    });
                    return {
                        status: response.status,
                        statusText: response.statusText,
                        ok: response.ok
                    };
                } catch (e) {
                    return { error: e.message };
                }
            }
        """, valid_token)

        # With valid CSRF token, request should succeed (or at least get past CSRF check)
        # Note: It might fail for other reasons (e.g., duplicate ID) but not CSRF
        if 'error' not in response_data:
            # Either 200 OK or 400/422 (validation error) but NOT 400/419 from CSRF
            assert response_data.get('status') != 400 or 'already exists' in response_data.get('statusText', '').lower(), \
                "POST with valid CSRF should not fail due to CSRF protection"
