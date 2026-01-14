# Entry-Level POS to Sense Propagation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** When user sets Part of Speech at the entry level, it should propagate to all senses that don't have a POS already set. This is the reverse of existing inheritance (sense → entry).

**Architecture:** Extend the existing `entry-form.js` event handlers to listen for entry-level `#part-of-speech` changes and propagate the value down to sense-level `.dynamic-grammatical-info` selects that have no value.

**Tech Stack:**
- JavaScript (vanilla, no framework)
- Flask templates (Jinja2)
- Playwright E2E tests

---

### Task 1: Add `propagatePosToSenses()` function

**Files:**
- Modify: `app/static/js/entry-form.js`

**Step 1: Write failing test**

This is already written in `tests/e2e/test_pos_ui.py::test_entry_pos_propagates_to_senses`. Run it to confirm it fails:

```bash
cd /mnt/d/Dokumenty/slownik-wielki/flask-app
.venv/bin/python -m pytest tests/e2e/test_pos_ui.py::test_entry_pos_propagates_to_senses -v --tb=short
```

Expected: FAIL - sense POS values remain empty after setting entry-level POS

**Step 2: Implement `propagatePosToSenses()` function**

Add this function before `setupGrammaticalInheritanceListeners()` in `entry-form.js`:

```javascript
/**
 * Propagate entry-level POS to senses that don't have a POS set.
 * Called when user changes the entry-level #part-of-speech select.
 */
function propagatePosToSenses() {
    const entryPosSelect = document.getElementById('part-of-speech');
    if (!entryPosSelect) return;

    const entryPos = entryPosSelect.value;
    if (!entryPos) return;  // Don't propagate empty values

    const sensePosSelects = document.querySelectorAll('#senses-container .dynamic-grammatical-info');

    sensePosSelects.forEach(senseSelect => {
        // Only set POS on senses that don't have a value yet
        if (!senseSelect.value || senseSelect.value.trim() === '') {
            senseSelect.value = entryPos;

            // Trigger change event so any listeners update UI state
            const event = new Event('change', { bubbles: true });
            senseSelect.dispatchEvent(event);
        }
    });

    // After propagation, update inheritance state to reflect new sense values
    updateGrammaticalCategoryInheritance();
}
```

**Step 3: Hook up the event listener**

In `setupGrammaticalInheritanceListeners()`, add a listener for entry-level POS:

```javascript
// Listen for entry-level POS changes and propagate to senses
entryForm.addEventListener('change', function(e) {
    if (e.target.id === 'part-of-speech') {
        propagatePosToSenses();
    }
});
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/e2e/test_pos_ui.py::test_entry_pos_propagates_to_senses -v --tb=short
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/static/js/entry-form.js
git commit -m "feat: add entry-to-sense POS propagation"
```

---

### Task 2: Add test for existing sense POS preservation

**Files:**
- Test: `tests/e2e/test_pos_ui.py::test_entry_pos_propagation_with_existing_sense_pos`

**Step 1: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/e2e/test_pos_ui.py::test_entry_pos_propagation_with_existing_sense_pos -v --tb=short
```

Expected: FAIL - current code may or may not preserve existing values

**Step 2: Verify the function preserves existing sense POS**

The `propagatePosToSenses()` function from Task 1 already checks `if (!senseSelect.value || senseSelect.value.trim() === '')` before setting, which means it should preserve existing values.

**Step 3: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/e2e/test_pos_ui.py::test_entry_pos_propagation_with_existing_sense_pos -v --tb=short
```

Expected: PASS

**Step 4: Commit**

```bash
git commit -m "test: verify POS propagation respects existing sense values"
```

---

### Task 3: Run all POS tests to verify no regressions

**Files:**
- Test: `tests/e2e/test_pos_ui.py`

**Step 1: Run all POS tests**

```bash
.venv/bin/python -m pytest tests/e2e/test_pos_ui.py -v --tb=short
```

Expected: All 4 tests pass
- `test_pos_inheritance_ui` (existing)
- `test_entry_pos_propagates_to_senses` (new)
- `test_entry_pos_propagation_with_existing_sense_pos` (new)

**Step 2: Commit**

```bash
git commit -m "test: run all POS inheritance tests"
```

---

### Implementation Notes

1. **Why only set empty senses?**
   - If a sense already has POS set, user explicitly chose it
   - Propagating entry-level POS would override user intent
   - This matches the behavior tested in `test_entry_pos_propagation_with_existing_sense_pos`

2. **Why trigger change event?**
   - The sense POS select may have other listeners
   - Setting `.value` directly doesn't trigger DOM events
   - Dispatching `change` ensures UI state updates correctly

3. **Why call `updateGrammaticalCategoryInheritance()` after?**
   - After propagation, senses now have values
   - Entry-level inheritance logic should be re-evaluated
   - This ensures consistent state between entry and senses

---

**Plan complete and saved to `docs/plans/2026-01-06-pos-entry-to-sense-propagation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Manual Execution** - You implement the changes yourself following the plan

**Which approach?**
