# E2E Test Speed Optimization Plan

**Date:** 2026-01-10
**Status:** Ready for Implementation
**Priority:** High - Tests take 20+ minutes to run

## Executive Summary

Optimize e2e test suite from 20+ minutes to target 5-8 minutes through parallelization, reduced overhead, and smarter test execution.

## Current State

| Metric | Value |
|--------|-------|
| Test files | 32 |
| Test methods | 229 |
| Execution time | 20+ minutes |
| Workers | 2 (configurable) |
| Pass rate | 194/217 (89.4%) |
| Known failures | 23 tests (pollution-related) |
| Browser | Chromium only (good - no multi-browser overhead) |

## Optimization 1: Increase Parallel Workers

**File:** `e2e/playwright.config.js`

**Change:**
```javascript
// Before
workers: process.env.PLAYWRIGHT_WORKERS || 2,

// After
workers: process.env.PLAYWRIGHT_WORKERS || (process.env.NUMBER_OF_PROCESSORS ? parseInt(process.env.NUMBER_OF_PROCESSORS) : 4),
```

**Alternative (safer - explicit env var):**
```javascript
workers: process.env.PLAYWRIGHT_WORKERS || 4,  // Default to 4 workers
```

**Expected speedup:** 2x (from 2 to 4 workers)

**Risk:** Low - Playwright handles parallelization safely

**Verification:**
```bash
PLAYWRIGHT_WORKERS=4 python3 -m pytest tests/e2e/ --tb=no -q
```

## Optimization 2: Lightweight Browser Launch

**File:** `tests/e2e/conftest.py`

**Change:**
```python
@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for the session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-sync',
                '--disable-translate',
                '--metrics-recording-only',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
            ]
        )
        yield browser
        browser.close()
```

**Expected speedup:** 2-5 seconds per browser launch (minor since session-scoped)

**Risk:** Very low - these are standard headless optimizations

## Optimization 3: Expand Snapshot Skip Patterns

**File:** `tests/e2e/conftest.py`

**Change:** Add more read-only test patterns to `SNAPSHOT_SKIP_PATTERNS`

**Current patterns (17):**
```python
SNAPSHOT_SKIP_PATTERNS = [
    'test_grammatical_info_dropdown_populated',
    'test_domain_type_dropdown_populated',
    'test_usage_type_dropdown_populated',
    'test_semantic_domain_dropdown_populated',
    'test_relation_type_dropdown_populated',
    'test_variant_type_dropdown_populated',
    'test_all_ranges_api_accessible',
    'test_dynamic_lift_range_initialization',
    'test_ranges_loaded_via_api',
    'test_ranges_ui_populated',
    'test_dropdown_populated',
]
```

**Pattern analysis to add:**
- Tests that only `page.goto()` and verify text
- Tests that check dropdown options (don't modify data)
- Tests that verify API response without database changes

**Script to identify candidates:**
```bash
# Find tests that only use page.goto, page.locator, page.inner_text, etc.
grep -l "add_entry\|update_entry\|delete_entry\|click.*delete\|click.*save" tests/e2e/*.py | grep -v "test_" | head -20
```

**Expected speedup:** 5-10% (reduces BaseX EXPORT/IMPORT overhead)

**Risk:** Low - conservative addition, verify before adding

## Optimization 4: Add Fail-Fast for CI

**File:** `e2e/playwright.config.js`

**Change:**
```javascript
module.exports = {
  // ... existing config
  retries: process.env.CI ? 2 : 0,  // More retries in CI
  maxFailures: process.env.CI ? undefined : 0,  // Stop on first N failures locally
  // ... rest of config
};
```

**Or via CLI in CI:**
```bash
npx playwright test --fail-fast  # Stop on first failure
```

**Expected speedup:** Faster feedback in CI when tests fail

**Risk:** None - only affects failure behavior

## Optimization 5: CI Sharding Configuration

**File:** `.github/workflows/e2e-tests.yml` (or add to existing workflow)

**Change:**
```yaml
jobs:
  e2e-test-1:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E tests (shard 1/4)
        run: npx playwright test --shard=1/4

  e2e-test-2:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E tests (shard 2/4)
        run: npx playwright test --shard=2/4

  # ... shards 3/4 and 4/4

  combine-results:
    needs: [e2e-test-1, e2e-test-2, e2e-test-3, e2e-test-4]
    runs-on: ubuntu-latest
    steps:
      - name: Check all shards passed
        run: |
          if [ "${{ needs.e2e-test-1.result }}" != "success" ] || \
             [ "${{ needs.e2e-test-2.result }}" != "success" ] || \
             [ "${{ needs.e2e-test-3.result }}" != "success" ] || \
             [ "${{ needs.e2e-test-4.result }}" != "success" ]; then
            exit 1
          fi
```

**Expected speedup:** 4x in CI (4 parallel jobs)

**Risk:** None - CI-only change

## Implementation Order

| Order | Task | Effort | Impact | Verification |
|-------|------|--------|--------|--------------|
| 1 | Workers to 4 | Low | High | `PLAYWRIGHT_WORKERS=4 pytest tests/e2e/ --tb=no -q` |
| 2 | Lightweight browser | Low | Low | Verify browser launches successfully |
| 3 | Expand skip patterns | Medium | Medium | Compare timing with/without changes |
| 4 | CI sharding | Medium | High | Verify CI passes |
| 5 | Fail-fast | Low | Low | Verify fails fast on broken test |

## Expected Results

| Optimization | Before | After | Speedup |
|--------------|--------|-------|---------|
| Workers (2→4) | 20 min | 10 min | 2x |
| Snapshot skip (17→40) | 10 min | 9 min | 10% |
| Lightweight browser | 9 min | 8.5 min | 5% |
| CI sharding | 20 min (CI) | 5 min (CI) | 4x |
| **Combined (local)** | 20 min | **5-8 min** | **2.5-4x** |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| 23 failing tests get worse with parallelism | Run with `--fail-fast` to catch issues early |
| Browser args break tests | Test locally before committing |
| Sharding breaks CI | Run full suite locally before PR |
| Snapshot skip misses a modifying test | Verify by checking database state after tests |

## Testing the Changes

### Before Changes (Baseline)
```bash
time python3 -m pytest tests/e2e/ --tb=no -q
# Record: ~20+ minutes, 194 passed, 23 failed
```

### After Each Change
```bash
time PLAYWRIGHT_WORKERS=4 python3 -m pytest tests/e2e/ --tb=no -q
# Compare timing and pass/fail counts
```

### Debugging Failures
```bash
# Run with debug output
E2E_DEBUG_STATE=true PLAYWRIGHT_WORKERS=4 pytest tests/e2e/ -xvs
```

## Success Criteria

- [ ] Full suite runs in under 8 minutes locally
- [ ] Pass rate improves or stays same (≥89%)
- [ ] No new test failures introduced
- [ ] CI pipeline completes faster

## Future Optimizations (If Needed)

If the above doesn't achieve target time:

1. **Per-worker browser contexts** (requires refactoring page scope from session to function)
2. **Database connection pooling** for faster BaseX operations
3. **Test selection** - skip slow tests in PR checks, run full suite nightly
4. **Headless vs headed** - use headed for debugging, headless for speed

---

*Plan created: 2026-01-10*
*Based on analysis of e2e/test setup and fixture architecture*
