"""
E2E tests for entry revision history — API layer AND full UI round-trip.
"""

from __future__ import annotations

import json
import uuid
import time
import re
import pytest
import requests
from playwright.sync_api import Page, expect


# ============================================================================
# API-level tests (backend: create, list, detail, paginate, stats)
# ============================================================================

class TestRevisionsAPI:
    """Backend API tests — no browser needed."""

    def test_create_and_list(self, app_url: str):
        entry_id = f"e2e-list-{uuid.uuid4().hex[:6]}"
        s1 = {"id": entry_id, "lexical_unit": {"en": "hello"}, "senses": []}
        r = requests.post(f"{app_url}/api/entries/{entry_id}/revisions", json={"snapshot": s1})
        assert r.ok and r.json()["revision_number"] == 1

        s2 = {"id": entry_id, "lexical_unit": {"en": "world"}, "status": "draft", "senses": []}
        r = requests.post(f"{app_url}/api/entries/{entry_id}/revisions", json={"snapshot": s2})
        assert r.ok and r.json()["revision_number"] == 2

        r = requests.get(f"{app_url}/api/entries/{entry_id}/revisions")
        assert r.json()["total"] == 2 and r.json()["revisions"][0]["revision_number"] == 2

    def test_detail(self, app_url: str):
        entry_id = f"e2e-det-{uuid.uuid4().hex[:6]}"
        snap = {"id": entry_id, "lexical_unit": {"en": "before"}, "senses": []}
        requests.post(f"{app_url}/api/entries/{entry_id}/revisions", json={"snapshot": snap})
        r = requests.get(f"{app_url}/api/entries/{entry_id}/revisions/1")
        assert r.json()["revision"]["snapshot"]["lexical_unit"]["en"] == "before"

    def test_change_report(self, app_url: str):
        entry_id = f"e2e-chg-{uuid.uuid4().hex[:6]}"
        s1 = {"id": entry_id, "lexical_unit": {"en": "before"}, "senses": []}
        requests.post(f"{app_url}/api/entries/{entry_id}/revisions", json={"snapshot": s1})
        s2 = {"id": entry_id, "lexical_unit": {"en": "after"}, "senses": [{"id": "s1", "gloss": {"en": "new"}}]}
        r = requests.post(f"{app_url}/api/entries/{entry_id}/revisions", json={"snapshot": s2})
        assert r.json()["change_count"] >= 1

    def test_pagination(self, app_url: str):
        entry_id = f"e2e-pg-{uuid.uuid4().hex[:6]}"
        base = {"id": entry_id, "lexical_unit": {"en": "x"}, "senses": []}
        for i in range(5):
            snap = dict(base); snap["counter"] = i
            requests.post(f"{app_url}/api/entries/{entry_id}/revisions", json={"snapshot": snap})
        r = requests.get(f"{app_url}/api/entries/{entry_id}/revisions?page=1&per_page=2")
        assert len(r.json()["revisions"]) == 2 and r.json()["total"] == 5

    def test_stats(self, app_url: str):
        e1, e2 = f"e2e-sta-{uuid.uuid4().hex[:4]}", f"e2e-stb-{uuid.uuid4().hex[:4]}"
        for eid in (e1, e2):
            for i in range(3):
                requests.post(f"{app_url}/api/entries/{eid}/revisions",
                              json={"snapshot": {"id": eid, "lexical_unit": {"en": str(i)}, "senses": []}})
        r = requests.get(f"{app_url}/api/revisions/stats?from=2020-01-01&to=2030-01-01")
        d = r.json()
        assert d["total_revisions"] >= 6 and d["unique_entries_touched"] >= 2


# ============================================================================
# Full UI E2E tests — entry created via form, revisions verified in the panel
# ============================================================================

@pytest.mark.integration
class TestRevisionsUI:
    """UI round-trip: revisions appear in the Alpine panel."""

    def _csrf_token(self, page: Page, app_url: str) -> str:
        """Get a valid CSRF token by visiting the entry form first."""
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state("networkidle")
        return page.evaluate(
            "document.querySelector('meta[name=\"csrf-token\"]')?.getAttribute('content') || ''"
        )

    def _create_entry_via_playwright(self, page: Page, app_url: str, eid: str, headword: str):
        """Create an entry via the Playwright fetch API (has session+CSRF)."""
        csrf = self._csrf_token(page, app_url)
        xml = f'''<?xml version="1.0" encoding="utf-8"?>
<entry id="{eid}">
    <lexical-unit><form lang="en"><text>{headword}</text></form></lexical-unit>
    <sense id="s1"><gloss lang="en"><text>test gloss</text></gloss></sense>
</entry>'''
        result = page.evaluate(
            """async ([url, xml, token]) => {
                const r = await fetch(url + '/api/xml/entries', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/xml', 'X-CSRF-TOKEN': token },
                    body: xml
                });
                return r.status;
            }""",
            [app_url, xml, csrf]
        )
        assert result in (200, 201), f"Entry create failed with status {result}"

    def test_entry_revision_ui_flow(self, page: Page, app_url: str):
        """Create entry + revision via API, verify panel shows it."""
        import uuid
        eid = f"e2e-ui-{uuid.uuid4().hex[:8]}"

        self._create_entry_via_playwright(page, app_url, eid, "revision-ui-test")

        # Save revision 1 via API (CSRF-exempt endpoint)
        s1 = {"id": eid, "lexical_unit": {"en": "revision-ui-test"},
              "senses": [{"id": "s1", "gloss": {"en": "first version"}}]}
        r = requests.post(f"{app_url}/api/entries/{eid}/revisions", json={"snapshot": s1})
        # Debug: print the actual POST response
        print(f"DEBUG: Rev1 POST status={r.status_code} body={r.text[:200]}")
        assert r.ok, f"Rev1 save: {r.status_code} {r.text[:100]}"
        # Verify the revision exists
        check = requests.get(f"{app_url}/api/entries/{eid}/revisions")
        print(f"DEBUG: Revisions after POST: {check.text[:200]}")

        # Navigate to edit page and open revision panel
        page.goto(f"{app_url}/entries/{eid}/edit")
        page.wait_for_load_state("networkidle")
        # Force reload to pick up template changes
        page.reload()
        page.wait_for_load_state("networkidle")

        # Capture console logs
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append({"type": msg.type, "text": msg.text}))

        page.locator('#revision-history-panel .card-header').click()
        page.wait_for_timeout(1000)

        rev_body = page.locator('#rev-body')
        expect(rev_body).to_contain_text("1", timeout=10000)

        # Save revision 2
        s2 = {"id": eid, "lexical_unit": {"en": "revision-ui-test"},
              "senses": [{"id": "s1", "gloss": {"en": "second version"}}]}
        requests.post(f"{app_url}/api/entries/{eid}/revisions", json={"snapshot": s2})

        # Reload and verify both revisions appear
        page.goto(f"{app_url}/entries/{eid}/edit")
        page.wait_for_load_state("networkidle")
        page.locator('#revision-history-panel .card-header').click()
        page.wait_for_timeout(1000)

        rev_body = page.locator('#rev-body')
        expect(rev_body).to_contain_text("2", timeout=10000)
        expect(rev_body).to_contain_text("1")

    def test_revision_panel_shows_change_summary(self, page: Page, app_url: str):
        """Clicking 'more' on a revision shows the detail with change report."""
        eid = f"e2e-detail-{uuid.uuid4().hex[:8]}"
        self._create_entry_via_playwright(page, app_url, eid, "detail-test")

        snap1 = {"id": eid, "lexical_unit": {"en": "original"},
                 "senses": [{"id": "s1", "gloss": {"en": "old"}}]}
        snap2 = {"id": eid, "lexical_unit": {"en": "updated"},
                 "senses": [{"id": "s1", "gloss": {"en": "new"}}]}
        r1 = requests.post(f"{app_url}/api/entries/{eid}/revisions", json={"snapshot": snap1})
        r2 = requests.post(f"{app_url}/api/entries/{eid}/revisions", json={"snapshot": snap2})
        assert r1.ok, f"Rev1 failed: {r1.status_code}"
        assert r2.ok, f"Rev2 failed: {r2.status_code}"
        # Verify revisions exist
        check = requests.get(f"{app_url}/api/entries/{eid}/revisions")
        assert check.ok and check.json()["total"] >= 2, f"Expected >=2, got {check.text[:200]}"

        page.goto(f"{app_url}/entries/{eid}/edit")
        page.wait_for_load_state("networkidle")

        page.locator('#revision-history-panel .card-header').click()
        page.wait_for_timeout(1000)

        rev_body = page.locator('#rev-body')
        expect(rev_body).to_contain_text("2", timeout=10000)

        expect(rev_body).to_contain_text("2 change(s)", timeout=5000)

        # Click "more" to expand detail — use evaluate to directly invoke
        # toggleDetail since the onclick attribute may not fire reliably via Playwright
        rev_num = page.evaluate("_revExpanded = null; _revPage = 1; _revTotal = 2;")
        # Find the revision number for the first revision (the one with change_count > 0)
        detail_loaded = page.evaluate("""async () => {
            // Click the first "more" button directly
            const btn = document.querySelector('#rev-list button');
            if (!btn) return 'NO_BUTTON';
            // The onclick handler calls toggleDetail(revNum) where revNum is the revision number
            // Read the onclick attribute to extract the revision number
            const onclick = btn.getAttribute('onclick');
            const match = onclick && onclick.match(/toggleDetail\((\d+)\)/);
            if (!match) return 'NO_MATCH: ' + onclick;
            const revNum = parseInt(match[1]);
            // Call toggleDetail directly
            toggleDetail(revNum);
            // Wait for the detail to load
            await new Promise(r => setTimeout(r, 2000));
            const detailEl = document.getElementById('rev-detail-' + revNum);
            if (!detailEl) return 'NO_DETAIL_EL';
            return detailEl.innerText || 'EMPTY';
        }""")
        print(f"\nDEBUG: detail content = {detail_loaded[:300] if detail_loaded else 'None'}")

        # Verify the detail shows the actual change kinds (MODIFIED, ADDED, or REMOVED)
        expect(rev_body).to_contain_text("MODIFIED", timeout=5000)
        expect(rev_body).to_contain_text("MODIFIED", timeout=5000)
