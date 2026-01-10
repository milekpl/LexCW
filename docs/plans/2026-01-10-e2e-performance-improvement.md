# E2E Test Performance and Isolation Improvement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce e2e test execution time by 60% through browser reuse, fixture isolation fixes, and parallel execution while ensuring proper test isolation.

**Architecture:** Convert browser context/page from function-scoped to session-scoped, remove conflicting database fixtures, optimize snapshot/restore logic, and enable parallel execution with isolated databases per worker.

**Tech Stack:** Playwright, pytest, BaseX, PostgreSQL

---

### Task 1: Analyze current test execution time baseline

**Files:**
- Test: `tests/e2e/test_ranges_ui_playwright.py`
- Test: `tests/e2e/test_all_ranges_dropdowns_playwright.py`

**Step 1: Run timing baseline**

```bash
cd /mnt/d/Dokumenty/slownik-wielki/flask-app
# Time 5 representative tests
time pytest tests/e2e/test_ranges_ui_playwright.py -v --tb=short 2>&1 | tail -20
```

Expected: Output shows ~30-60 seconds for 5 tests, ~2-4s per test

**Step 2: Log baseline timing**

```bash
echo "Baseline timing: $(date +%Y-%m-%d_%H:%M:%S)" > docs/plans/e2e_baseline_timing.txt
```

**Step 3: Commit**

```bash
git add docs/plans/
git commit -m "docs: add e2e baseline timing"
```

---

### Task 2: Create session-scoped browser context and page fixtures

**Files:**
- Modify: `tests/e2e/conftest.py:736-810`

**Step 1: Read current fixtures**

```python
# Current (function-scoped):
@pytest.fixture(scope="function")
def context(browser: Browser):
    context = browser.new_context()
    yield context
    context.close()

@pytest.fixture(scope="function")
def page(context: BrowserContext, flask_test_server):
    # ... current logic ...
    yield page
    page.close()
```

**Step 2: Write session-scoped versions with project caching**

```python
_session_project_selected = False

@pytest.fixture(scope="session", autouse=True)
def _setup_session_browser_context(request):
    """Ensure project selection happens once per session."""
    global _session_project_selected
    _session_project_selected = False
    yield request

@pytest.fixture(scope="session")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create a single browser context for the entire test session."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        java_script_enabled=True,
    )
    yield context
    context.close()

def _ensure_project_selected(page: Page, base_url: str):
    """Select project once per session, not per test."""
    global _session_project_selected

    if _session_project_selected:
        return

    try:
        page.goto(f"{base_url}/settings/projects", timeout=10000)
        select_button = page.locator("a.btn-success:has-text('Select')").first

        if select_button.count() > 0:
            select_button.click()
            page.wait_for_load_state("networkidle")
            # Close any wizard modals
            page.evaluate("""() => {
                const m1 = document.getElementById('projectSetupModal');
                if (m1) { const inst = bootstrap.Modal.getInstance(m1); if (inst) inst.hide(); }
                const m2 = document.getElementById('projectSetupModalSettings');
                if (m2) { const inst = bootstrap.Modal.getInstance(m2); if (inst) inst.hide(); }
            }""")
            _session_project_selected = True
    except Exception as e:
        pass

@pytest.fixture(scope="session")
def page(context: BrowserContext, flask_test_server) -> Generator[Page, None, None]:
    """Create a single page for the entire test session."""
    page = context.new_page()
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)

    base_url = flask_test_server

    # Select project ONCE per session
    _ensure_project_selected(page, base_url)

    # Clear field visibility localStorage once
    page.evaluate("""() => {
        Object.keys(localStorage).forEach(key => {
            if (key.includes('fieldVisibility') || key.includes('Visibility')) {
                localStorage.removeItem(key);
            }
        });
    }""")
    page.reload(wait_until="networkidle")

    page._base_url = base_url
    yield page
    page.close()
```

**Step 3: Run tests to verify fixtures work**

```bash
pytest tests/e2e/test_ranges_ui_playwright.py -v --tb=short 2>&1 | head -30
```

Expected: Tests pass, same behavior as before

**Step 4: Commit**

```bash
git add tests/e2e/conftest.py
git commit -m "feat(e2e): use session-scoped browser context and page"
```

---

### Task 3: Remove conflicting basex_test_connector from e2e tests

**Files:**
- Modify: `tests/e2e/test_all_ranges_dropdowns_playwright.py`
- Modify: `tests/e2e/test_ranges_ui_playwright.py`

**Step 1: Read test signatures**

```bash
# Check which tests use basex_test_connector
grep -n "basex_test_connector" tests/e2e/test_all_ranges_dropdowns_playwright.py
grep -n "basex_test_connector" tests/e2e/test_ranges_ui_playwright.py
```

**Step 2: Remove basex_test_connector from test signatures**

```python
# Before:
def test_grammatical_info_dropdown_populated(self, page: Page, app_url, basex_test_connector):

# After:
def test_grammatical_info_dropdown_populated(self, page: Page, app_url):
```

**Step 3: Run tests to verify they pass without the fixture**

```bash
pytest tests/e2e/test_all_ranges_dropdowns_playwright.py -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass, database isolation preserved

**Step 4: Commit**

```bash
git add tests/e2e/test_all_ranges_dropdowns_playwright.py tests/e2e/test_ranges_ui_playwright.py
git commit -m "fix(e2e): remove basex_test_connector from test signatures"
```

---

### Task 4: Optimize snapshot/restore to skip when unnecessary

**Files:**
- Modify: `tests/e2e/conftest.py:595-681`

**Step 1: Read current snapshot/restore logic**

```python
@pytest.fixture(scope="function", autouse=True)
def _db_snapshot_restore(request):
    # Currently: Always creates snapshot before, restores after
```

**Step 2: Write optimized version that skips when tests don't modify DB**

```python
SNAPSHOT_SKIP_PATTERNS = [
    'test_grammatical_info_dropdown_populated',
    'test_domain_type_dropdown_populated',
    'test_usage_type_dropdown_populated',
    'test_semantic_domain_dropdown_populated',
    # Add read-only tests that don't modify database
]

@pytest.fixture(scope="function", autouse=True)
def _db_snapshot_restore(request):
    test_db = os.environ.get('TEST_DB_NAME')
    if not test_db:
        yield
        return

    test_name = request.node.name
    should_skip = any(pattern in test_name for pattern in SNAPSHOT_SKIP_PATTERNS)

    if should_skip:
        # Skip snapshot for read-only tests
        yield
        return

    # Original snapshot logic for tests that modify database
    backup_path = None
    # ... rest of original implementation ...
```

**Step 3: Run tests to verify behavior**

```bash
pytest tests/e2e/test_ranges_ui_playwright.py::TestRangesUIPlaywright::test_grammatical_info_dropdown_populated -v --tb=short
```

Expected: Test passes without snapshot overhead

**Step 4: Commit**

```bash
git add tests/e2e/conftest.py
git commit -m "feat(e2e): optimize snapshot/restore for read-only tests"
```

---

### Task 5: Enable parallel execution in Playwright config

**Files:**
- Modify: `e2e/playwright.config.js`

**Step 1: Read current config**

```javascript
module.exports = {
  testDir: './tests',
  timeout: 60_000,
  use: {
    headless: true,
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:5000'
  }
};
```

**Step 2: Add workers configuration**

```javascript
module.exports = {
  testDir: './tests',
  timeout: 60_000,
  workers: process.env.PLAYWRIGHT_WORKERS || 2,  // Parallel workers
  use: {
    headless: true,
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:5000',
    actionTimeout: 5000,
  },
  reporter: 'list',
};
```

**Step 3: Test parallel execution**

```bash
PLAYWRIGHT_WORKERS=4 pytest tests/e2e/test_ranges_ui_playwright.py -v --tb=short 2>&1 | tail -20
```

Expected: Tests run in parallel (faster execution)

**Step 4: Commit**

```bash
git add e2e/playwright.config.js
git commit -m "feat(e2e): enable parallel execution with workers config"
```

---

### Task 6: Add database isolation per Playwright worker

**Files:**
- Modify: `e2e/playwright.config.js`
- Modify: `tests/e2e/conftest.py:402-593`

**Step 1: Create worker-scoped database fixture**

```python
import os
import uuid

_worker_id = None

@pytest.fixture(scope="session")
def _playwright_worker_id() -> str:
    """Get unique ID for this Playwright worker."""
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'gw0')
    global _worker_id
    if _worker_id is None:
        _worker_id = worker_id
    return _worker_id

@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database_per_worker(request, _playwright_worker_id):
    """Set up isolated database per Playwright worker."""
    worker_db_name = f"test_e2e_{_worker_id}_{uuid.uuid4().hex[:6]}"

    # Store original values
    original_test_db = os.environ.get('TEST_DB_NAME')
    original_basex_db = os.environ.get('BASEX_DATABASE')

    # Set worker-specific database
    os.environ['TEST_DB_NAME'] = worker_db_name
    os.environ['BASEX_DATABASE'] = worker_db_name

    # ... rest of original setup logic ...

    yield

    # Cleanup worker-specific database
    # ... original cleanup ...

    # Restore original values
    if original_test_db:
        os.environ['TEST_DB_NAME'] = original_test_db
    elif 'TEST_DB_NAME' in os.environ:
        del os.environ['TEST_DB_NAME']
    # ... restore other env vars ...
```

**Step 2: Update playwright config for isolation**

```javascript
const os = require('os');

module.exports = {
  testDir: './tests',
  timeout: 60_000,
  workers: 2,  // Limited workers for database isolation
  use: {
    headless: true,
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:5000',
  },
  projects: [
    {
      name: 'e2e',
      testMatch: 'tests/e2e/**/*.py',
      dependencies: ['setup-db'],
    },
  ],
};
```

**Step 3: Test parallel execution with isolation**

```bash
PLAYWRIGHT_WORKERS=2 pytest tests/e2e/test_ranges_ui_playwright.py -v --tb=short 2>&1 | tail -30
```

Expected: Tests pass, no database conflicts between workers

**Step 4: Commit**

```bash
git add tests/e2e/conftest.py e2e/playwright.config.js
git commit -m "feat(e2e): add per-worker database isolation"
```

---

### Task 7: Measure performance improvement

**Files:**
- Modify: `docs/plans/e2e_baseline_timing.txt`

**Step 1: Run full e2e test suite**

```bash
cd /mnt/d/Dokumenty/slownik-wielki/flask-app
time pytest tests/e2e/ -v --tb=short 2>&1 | tee /tmp/e2e_after.txt
```

**Step 2: Compare timing**

```bash
echo "=== Before optimizations ==="
cat docs/plans/e2e_baseline_timing.txt

echo ""
echo "=== After optimizations ==="
tail -20 /tmp/e2e_after.txt
```

**Step 3: Document improvement**

```bash
echo "After optimization: $(date +%Y-%m-%d_%H:%M:%S)" >> docs/plans/e2e_baseline_timing.txt
cat docs/plans/e2e_baseline_timing.txt
```

**Step 4: Commit**

```bash
git add docs/plans/
git commit -m "docs: document e2e performance improvement"
```

---

### Task 8: Create test isolation verification test

**Files:**
- Create: `tests/e2e/test_isolation_verification.py`

**Step 1: Write verification test**

```python
"""
Test to verify e2e test isolation is working correctly.
Run this to verify no cross-test pollution occurs.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.playwright
class TestIsolationVerification:
    """Verify that tests don't pollute each other's state."""

    def test_first_creates_entry(self, page: Page, app_url):
        """Create an entry - subsequent tests should not see it."""
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state("networkidle")

        # Fill in lexical unit
        page.fill('input[name="lexical-unit-en"]', 'isolation_test_entry')

        # Add sense with definition
        if page.locator('#add-first-sense-btn').count() > 0:
            page.click('#add-first-sense-btn')

        page.fill('textarea[name*="definition"]', 'Test definition')

        # Save entry
        page.click('button[type="submit"]')
        page.wait_for_url("**/entries/**")

        # Verify entry was created
        expect(page.locator("text=isolation_test_entry")).to_be_visible(timeout=10000)

    def test_second_cannot_see_first_entry(self, page: Page, app_url):
        """This test should start with pristine database - no isolation_test_entry."""
        page.goto(f"{app_url}/entries")
        page.wait_for_load_state("networkidle")

        # Verify isolation - the entry from previous test should not exist
        isolation_entry = page.locator("text=isolation_test_entry")
        count = isolation_entry.count()

        # This should be 0 if isolation is working
        assert count == 0, f"Found {count} instances of isolation_test_entry - isolation broken!"

    def test_third_verifies_pristine_state(self, page: Page, app_url):
        """Verify we still have our original test entries."""
        page.goto(f"{app_url}/entries")
        page.wait_for_load_state("networkidle")

        # Original pristine entries should exist
        expect(page.locator("text=test")).to_be_visible(timeout=5000)
        expect(page.locator("text=component")).to_be_visible(timeout=5000)
        expect(page.locator("text=variant")).to_be_visible(timeout=5000)
```

**Step 2: Run isolation verification**

```bash
pytest tests/e2e/test_isolation_verification.py -v --tb=short
```

Expected: All tests pass, proving isolation works

**Step 3: Commit**

```bash
git add tests/e2e/test_isolation_verification.py
git commit -m "test(e2e): add isolation verification test"
```

---

### Summary of Expected Improvements

| Optimization | Estimated Time Savings |
|--------------|------------------------|
| Session-scoped context/page | ~60-90s for 60 tests |
| Remove basex_test_connector conflict | ~30s (fixes DB recreation) |
| Skip snapshot for read-only tests | ~20s |
| Parallel execution (2 workers) | ~50% overall reduction |
| **Total Estimated Improvement** | **~60-70% faster** |
