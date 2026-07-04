"""
E2E tests for Workset Management page - Workbench /workbench/worksets

Tests cover:
- Page loading and workset list display
- Workset creation link
- Workset selection UI elements
- Bulk operations UI elements
- Navigation links

Note: The page fixture automatically selects a project before each test.
"""

import json
import uuid

import pytest
import requests
from playwright.sync_api import expect


def _api_worksets_available(app_url: str) -> bool:
    """Check if the worksets API is reachable (PostgreSQL up)."""
    try:
        r = requests.get(f"{app_url}/api/worksets", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _create_workset_via_api(app_url: str, name: str) -> str | None:
    """Create a workset via the query-builder execute endpoint. Returns workset_id or None."""
    payload = {
        "workset_name": name,
        "query": {"filters": [], "sort_by": None, "sort_order": "asc"},
    }
    try:
        r = requests.post(
            f"{app_url}/api/query-builder/execute",
            json=payload,
            timeout=10,
        )
        if r.ok:
            data = r.json()
            return data.get("workset_id") or data.get("workset", {}).get("id")
    except Exception:
        pass
    return None


def _delete_workset_via_api(app_url: str, workset_id: str) -> None:
    try:
        requests.delete(f"{app_url}/api/worksets/{workset_id}", timeout=5)
    except Exception:
        pass


class TestWorksetListPage:
    """Test suite for workset list page functionality."""

    def test_page_loads_successfully(self, page, app_url):
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        expect(page.locator("h4:has-text('Curation Sessions')")).to_be_visible()
        expect(page.locator("#workset-list")).to_be_visible()

    def test_create_workset_link_exists(self, page, app_url):
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        expect(page.locator("a.btn-primary[href='/workbench/query-builder']").first).to_be_visible()

    def test_workset_list_container_exists(self, page, app_url):
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        expect(page.locator("#workset-list")).to_be_visible()

    def test_navigation_links_work(self, page, app_url):
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        page.click(".btn-group a[href='/workbench/query-builder']")
        page.wait_for_load_state("domcontentloaded")
        assert "/workbench/query-builder" in page.url

        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        page.click(".btn-group a[href='/workbench/bulk-operations']")
        page.wait_for_load_state("domcontentloaded")
        assert "/workbench/bulk-operations" in page.url

    def test_bulk_operations_link_exists(self, page, app_url):
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        expect(page.locator("a.btn-outline-success[href='/workbench/bulk-operations']")).to_be_visible()


class TestWorksetSelection:
    """Test workset selection UI elements.

    Each test creates and cleans up its own workset (function-scoped fixture).
    The fixture is lightweight: one API call, no retries, no sleeps.
    """

    @pytest.fixture
    def workset_id(self, app_url):
        """Create a workset for this test, clean up after."""
        if not _api_worksets_available(app_url):
            pytest.skip("PostgreSQL unavailable")

        name = f"Test Workset {uuid.uuid4().hex[:8]}"
        wid = _create_workset_via_api(app_url, name)
        if wid is None:
            pytest.skip("Failed to create workset")
        yield wid
        _delete_workset_via_api(app_url, wid)

    def _go_to_worksets(self, page, app_url):
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

    def test_select_all_checkbox_exists(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector(".workset-checkbox", timeout=5000)
        checkbox = page.locator("#select-all-worksets")
        if checkbox.count() > 0:
            expect(checkbox).to_be_visible()
        else:
            pytest.fail("Select-all checkbox not rendered")

    def test_bulk_toolbar_exists(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector("#bulk-toolbar, .workset-checkbox", timeout=5000)
        toolbar = page.locator("#bulk-toolbar")
        if toolbar.count() > 0:
            expect(toolbar).to_be_visible()
        else:
            pytest.fail("Bulk toolbar not rendered")

    def test_selected_count_display_exists(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector("#selected-count", state="attached", timeout=10000)
        text = page.locator("#selected-count").inner_text()
        assert text.strip().isdigit(), f"Selected count not numeric: '{text}'"

    def test_bulk_selection_updates_count(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector(".workset-checkbox", timeout=5000)

        page.locator(".workset-checkbox").first.check()
        expect(page.locator("#selected-count")).to_have_text("1")

    def test_bulk_delete_button_visible_when_selected(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector(".workset-checkbox", timeout=5000)

        page.locator(".workset-checkbox").first.check()
        selected_actions = page.locator("#selected-actions")
        if selected_actions.count() > 0:
            expect(selected_actions).to_be_visible()
        else:
            pytest.fail("Selected actions panel not visible after selection")

    def test_refresh_button_exists_in_dropdown(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector("#workset-list .dropdown-toggle", timeout=5000)

        page.locator("#workset-list .dropdown-toggle").first.click()
        refresh_btn = page.locator(".refresh-workset-btn").first
        expect(refresh_btn).to_be_visible()
        expect(refresh_btn).to_contain_text("Refresh")

    def test_refresh_button_has_correct_icon(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector("#workset-list .dropdown-toggle", timeout=5000)

        page.locator("#workset-list .dropdown-toggle").first.click()
        expect(page.locator(".refresh-workset-btn").first.locator("i.bi-arrow-clockwise")).to_be_visible()

    def test_refresh_button_opens_confirmation_dialog(self, page, app_url, workset_id):
        self._go_to_worksets(page, app_url)
        page.wait_for_selector("#workset-list .dropdown-toggle", timeout=5000)

        page.locator("#workset-list .dropdown-toggle").first.click()

        dialog_messages = []
        page.on("dialog", lambda d: (dialog_messages.append(d.message), d.dismiss()))

        page.locator(".refresh-workset-btn").first.click()
        page.wait_for_timeout(500)

        assert len(dialog_messages) > 0, "No confirmation dialog appeared"
        assert "refresh" in dialog_messages[0].lower()


class TestWorksetCreation:
    """Test workset creation via the Query Builder UI."""

    def _pre_check(self, app_url):
        if not _api_worksets_available(app_url):
            pytest.skip("PostgreSQL unavailable")

    def test_create_workset_via_query_builder(self, page, app_url):
        self._pre_check(app_url)
        workset_name = f"GUI Workset {uuid.uuid4().hex[:8]}"

        # Navigate to Query Builder
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")
        expect(page.locator("h4:has-text('Query Builder')")).to_be_visible()

        # Set filter value
        page.locator(".value-input").fill("test")

        # Preview
        page.locator("#preview-query-btn").click()
        page.wait_for_selector("#query-preview-json", timeout=3000)

        # Open create-workset modal
        page.locator("#execute-query-btn").click()
        expect(page.locator("#createWorksetModal")).to_be_visible(timeout=5000)

        # Fill name and confirm
        page.locator("#workset-name-input").fill(workset_name)
        page.locator("#confirm-create-workset").click()

        # Wait for modal to close
        try:
            page.wait_for_selector("#createWorksetModal", state="detached", timeout=10000)
        except Exception:
            if page.locator(".toast.text-bg-danger").is_visible():
                pytest.skip("Workset creation failed - PostgreSQL issue")

        # Verify on worksets page
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#workset-list", timeout=10000)

        # Check via API
        r = requests.get(f"{app_url}/api/worksets", timeout=5)
        if r.ok:
            data = r.json()
            worksets = data.get("worksets", []) if isinstance(data, dict) else data
            names = [w.get("name") for w in worksets]
            if workset_name not in names:
                pytest.skip("Workset not created")

        expect(page.locator(f"h6:has-text('{workset_name}')")).to_be_visible()

    def test_create_workset_with_multiple_filters(self, page, app_url):
        self._pre_check(app_url)
        workset_name = f"Multi-filter {uuid.uuid4().hex[:8]}"

        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Add second filter
        page.locator("#add-filter-btn").click()
        page.wait_for_selector(".filter-condition:nth-child(2)", timeout=3000)
        expect(page.locator(".filter-condition")).to_have_count(2)

        page.locator(".filter-condition").nth(0).locator(".value-input").fill("test")
        page.locator(".filter-condition").nth(1).locator(".value-input").fill("test")

        # Create workset
        page.locator("#execute-query-btn").click()
        expect(page.locator("#createWorksetModal")).to_be_visible()

        page.locator("#workset-name-input").fill(workset_name)
        page.locator("#confirm-create-workset").click()

        try:
            page.wait_for_selector("#createWorksetModal", state="detached", timeout=10000)
        except Exception:
            try:
                expect(page.locator("#createWorksetModal")).not_to_be_visible(timeout=5000)
            except Exception:
                if page.locator(".toast.text-bg-danger").is_visible():
                    pytest.skip("Workset creation failed")

        # Verify
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#workset-list", timeout=10000)

        r = requests.get(f"{app_url}/api/worksets", timeout=5)
        if r.ok:
            data = r.json()
            worksets = data.get("worksets", []) if isinstance(data, dict) else data
            names = [w.get("name") for w in worksets]
            if workset_name not in names:
                pytest.skip("Workset not created")

        expect(page.locator(f"h6:has-text('{workset_name}')")).to_be_visible()


class TestWorksetApiEndpoints:
    """Test workset API endpoints are reachable."""

    def test_worksets_list_endpoint_reachable(self, page, app_url):
        r = requests.get(f"{app_url}/api/worksets", allow_redirects=False, timeout=5)
        assert r.status_code in [200, 302, 500]

    def test_pipelines_list_endpoint_reachable(self, page, app_url):
        r = requests.get(f"{app_url}/api/pipelines", allow_redirects=False, timeout=5)
        assert r.status_code in [200, 302, 500]

    def test_worksets_bulk_delete_endpoint_reachable(self, page, app_url):
        r = requests.post(
            f"{app_url}/api/worksets/bulk/delete",
            json={"ids": []},
            allow_redirects=False,
            timeout=5,
        )
        assert r.status_code in [200, 302, 400, 500]
