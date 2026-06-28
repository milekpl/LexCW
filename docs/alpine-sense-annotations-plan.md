# Plan — Restore annotation editing UI in Alpine (REGRESSION fix)

**Status:** Ready to execute | **Author:** review/verification pass (Claude Opus 4.8)
**Scope:** Restore TWO pieces of annotation editing that the Alpine migration **dropped**, and
**re-enable the existing tests that were skipped** because of it.

## 0. Read first — this is a REGRESSION, not a new feature

These were working, tested features before the Alpine refactor. The migration removed their UI
and left the e2e tests skipped. Proof (current tree):

- `tests/e2e/test_annotations_playwright.py` SKIPS:
  - `test_add_sense_level_annotation` / `test_remove_sense_level_annotation` —
    *"Sense-level annotation UI not yet ported to Alpine senseTree"*
  - `test_add_language_to_annotation_content` / `test_remove_language_from_annotation_content` /
    `test_duplicate_language_codes_are_prevented` — *"Multilingual annotation content not in Alpine component"*
- `tests/integration/test_annotations_integration.py::test_sense_level_annotation_persistence`
  **still passes** — the model/serializer layer round-trips sense annotations fine. **So the data
  layer is ready; only the UI is missing.** (There's also a `.bak` of the original integration test.)

**Two gaps to close:**

1. **Sense-level annotation editing UI** — entirely missing. `senseTree` carries
   `sense.annotations` in state (`addSense()` seeds `annotations: []`), the adapter emits them
   (`adaptSense`, `alpine-to-serializer.js:152`), and the serializer writes them
   (`lift-xml-serializer.js:354`). Only the `_senses.html` UI + senseTree methods + one
   `normalize-entry.js` line are missing. (Same class as the illustration/reversal §16.1 gaps —
   the legacy `#sense-template` had a `data-container-type="sense"` annotation block, deleted in
   the migration and never re-added.)

2. **Multilingual annotation *content*** — missing from **BOTH** the entry and sense annotation
   UIs. The entry component (`entry-annotations.js`) holds `content: {}` in state but
   `_entry_annotations.html` renders **no content forms** (only name/value/who/when). LIFT allows
   `<annotation>` to contain multilingual `<form>` content (registry: `annotation` → `form`
   children). Restore an "Add Language" content editor on the annotation UI used by both.

This is a **sense-level fold-in** like §16.1 (no new component/`sectionReader`/`registerAlpineSection`
for the sense part — senses already ride the merge harness) PLUS a small enhancement to the shared
annotation markup for the content forms. You edit `sense-tree.js`, `_senses.html`,
`entry-annotations.js` + `_entry_annotations.html` (for content), `normalize-entry.js`, and
**re-enable** the skipped tests.

## 1. The four lessons that this kind of task keeps tripping on

These caused real bugs every prior section. Honour them.

1. **Sync to the current tree first.** Earlier passes worked off a stale checkout and silently
   re-broke deleted things (script tags → 404 three separate times) and reverted cleanup. Before
   editing, confirm your base has: the deleted clone templates gone, `multilingual-sense-fields.js`
   deleted, the §16.2 entry components present, `MergeHarness.buildSerializerInput`, and
   `scripts/audit_serialization.py`. If any are missing, you're on a stale base — stop and re-sync.
2. **Verify the adapter/normalize SHAPE — passthrough is not correct** (the etymology trap).
   Check what `serializeAnnotation` consumes vs. what `normalizeSense` produces (see §3). Add/keep
   a golden unit test.
3. **Round-trip persistence test is mandatory** (the pronunciation trap): add a sense annotation
   via the REAL UI → `submitForm()` → reload via API → assert it's in the saved LIFT XML, and
   assert exactly one annotation control (no duplicate-binding).
4. **Do not reintroduce a legacy path.** There is no legacy sense-annotation JS to delete (it went
   with `#sense-template`); just don't add `name=` attributes and don't wire a `document`-delegated
   handler. After your change, run `python scripts/audit_serialization.py` — it must stay at its
   current count (the only suspect is the documented live-preview fallback).

## 2. Implementation

### 2.1 `normalize-entry.js` — normalize sense annotations (one line)

`normalizeSense` currently does `annotations: safeArray(raw.annotations)` (raw passthrough — no
stable `id`, so `x-for :key` breaks, and the shape may not match). Change it to use the existing
`normalizeAnnotation` (same as the entry-level path at line ~377):

```javascript
// in normalizeSense (~line 171)
annotations: safeArray(raw.annotations).map(normalizeAnnotation),
```

`normalizeAnnotation` already yields `{ id, name, value, who, when, content }` — the shape the UI
and `serializeAnnotation` need.

### 2.2 `sense-tree.js` — add/remove methods

`addSense()` already seeds `annotations: []` (keep). Add component methods next to the existing
`addRelation`/`removeRelation` (mirror them exactly — annotations are an array of objects with
stable ids):

```javascript
addAnnotation: function (sense) {
  if (!sense.annotations) sense.annotations = [];
  sense.annotations.push({
    id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
      ? window.AlpineNormalize.generateId()
      : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
    name: '', value: '', who: '', when: '', content: {}
  });
},
removeAnnotation: function (sense, annId) {
  if (!sense.annotations) return;
  var i = sense.annotations.findIndex(function (a) { return a.id === annId; });
  if (i !== -1) sense.annotations.splice(i, 1);
},
```

**Do NOT seed** an annotation in `addSense` — annotations are optional (like reversals/illustrations).

### 2.3 `_senses.html` — the UI block

Add an Annotations section inside the sense card body, modelled on the existing sense **Relations**
block (same card/x-for/remove pattern). Place it near the other optional sense sections
(reversals/illustrations). Pattern:

```html
<div class="mb-3 sense-annotations-section">
  <div class="d-flex justify-content-between align-items-center mb-2">
    <label class="form-label mb-0"><i class="fas fa-clipboard-list"></i> Annotations</label>
    <button type="button" class="btn btn-sm btn-outline-warning add-annotation-btn"
            @click.prevent="addAnnotation(sense)">
      <i class="fas fa-plus"></i> Add Annotation
    </button>
  </div>
  <template x-for="(ann, ai) in sense.annotations" :key="ann.id">
    <div class="annotation-item card mb-2 border-warning">
      <div class="card-body py-2">
        <div class="row g-2">
          <div class="col-md-4">
            <input type="text" class="form-control form-control-sm annotation-name-input"
                   x-model="ann.name" placeholder="name (e.g. editorial-status)">
          </div>
          <div class="col-md-4">
            <input type="text" class="form-control form-control-sm" x-model="ann.value"
                   placeholder="value">
          </div>
          <div class="col-md-3">
            <input type="text" class="form-control form-control-sm" x-model="ann.who"
                   placeholder="who">
          </div>
          <div class="col-md-1 d-flex align-items-center">
            <button type="button" class="btn btn-sm btn-outline-danger remove-annotation-btn"
                    @click.prevent="removeAnnotation(sense, ann.id)">×</button>
          </div>
        </div>
      </div>
    </div>
  </template>
  <div class="text-muted small" x-show="!sense.annotations || sense.annotations.length === 0">
    No annotations yet.
  </div>
</div>
```

**No `name=` attributes** anywhere. Keep `when` read-only/auto if the entry-annotations UI does
(check `_entry_annotations.html` for parity — match it so entry and sense annotations behave the same).

> **Class-name caution:** `.add-annotation-btn` / `.remove-annotation-btn` / `.annotation-name-input`
> are the same classes the *entry* annotation UI uses. That is FINE here (no legacy `document`
> delegation listens on them anymore — `entry-form.js`'s annotation cluster + the sense
> click-delegation block were deleted in §16.3). Just be aware tests that select these globally may
> now match both the entry and sense controls; scope sense selectors within `.sense-item`.

### 2.4 Multilingual annotation content (gap #2 — affects entry AND sense annotation UIs)

The serializer is **already ready**: `serializeAnnotation` (`lift-xml-serializer.js:587-595`)
reads `annotationData.content` as a `{lang: text}` dict and emits `<form lang><text>` children.
The Alpine annotation state already has `content: {}` (entry-annotations.js); it's just never
edited. Add a multilingual content editor — model it the SAME way as other multilingual lists
(array-of-objects with stable ids, NOT a bare dict — a lang-keyed dict breaks `x-for :key` and
loses focus on language change; convert array→dict at the adapter boundary, exactly like
`glossForms`→`glosses`):

- **State:** give each annotation `contentForms: [{id, lang, text}]` (in `normalizeAnnotation`,
  derive it from the `content` dict via the existing `dictToForms` helper; keep `content` for
  back-compat or drop it). Add `addRow`/`removeRow`-style helpers (reuse the senseTree `addRow`
  for the sense one; the entry-annotations component needs its own, mirroring lexical-unit's).
- **UI:** an "Add Language" button + `x-for` over `contentForms` (lang `<select>` + text input),
  identical to the gloss/note multilingual pattern. **Prevent duplicate language codes** (the
  `addRow` helper already picks the next *unused* language — that satisfies
  `test_duplicate_language_codes_are_prevented`).
- **Adapter:** in the annotation adapter path, emit `content: {lang: text}` from `contentForms`
  (mirror `formsToFlatDict`). Do this for BOTH the entry annotations (`alpineStateToSerializerInput`
  notes/annotation handling) and sense annotations (`adaptSense`).

Apply the content editor to BOTH `_entry_annotations.html` and the new sense block so entry and
sense annotations behave identically (the skipped content tests use the entry section selectors).

## 3. Adapter / serializer — verify, don't assume

- `adaptSense` (`alpine-to-serializer.js:152`) already passes `result.annotations = sense.annotations`.
  Confirm `serializeAnnotation` (`lift-xml-serializer.js:564`) reads `name`/`value`/`who`/`when` as
  attributes — it does. So the sense state shape `{name,value,who,when}` round-trips with no adapter
  change. **Add a golden unit test** (in `tests/unit/alpine-adapter.test.js`): a sense with one
  annotation → `normalizeSense`/`alpineStateToSerializerInput` → `serializeEntry` emits
  `<sense>…<annotation name="…" value="…"/></sense>`.

## 4. Tests — RE-ENABLE the skipped ones (don't just write new)

The whole point is to restore tested behavior, so the gate is the **existing** suite going from
skipped → passing. In `tests/e2e/test_annotations_playwright.py`, **remove the `pytest.skip(...)`**
from each of these and implement the body (the skip lines tell you what they cover; mirror the
entry-level tests in the same file, scoping sense selectors within `.sense-item`):

- `test_add_sense_level_annotation`, `test_remove_sense_level_annotation` — add/remove a sense
  annotation via `.sense-item .add-annotation-btn` / `.remove-annotation-btn`.
- `test_add_language_to_annotation_content`, `test_remove_language_from_annotation_content`,
  `test_duplicate_language_codes_are_prevented` — exercise the new multilingual content editor
  ("Add Language" on an annotation → a content `{lang: text}` row; duplicate lang prevented).
- `test_annotation_content_is_editable` (if skipped) — type into a content form, assert the value.

Keep the entry-level tests in that file passing (don't regress them).

Plus:
- **Unit golden test** (§3): `npx jest tests/unit/alpine-adapter.test.js` stays green.
- **Model layer:** `tests/integration/test_annotations_integration.py` (incl.
  `test_sense_level_annotation_persistence`) stays green — it already proves the round-trip.
- **New e2e round-trip** `tests/e2e/test_sense_annotations_e2e.py` (model on
  `test_entry_annotations_e2e.py`): add sense annotation via real UI → `submitForm()` → reload via
  `/api/xml/entries/{id}` → assert `<sense>…<annotation name="…" value="…"/></sense>` and exactly
  one annotation control in the sense.
- **Audit:** `python scripts/audit_serialization.py` — count unchanged (1 documented fallback).
- **Sanity:** `tests/e2e/test_all_lift_elements_rendered.py` stays green.

## 5. Verification commands

```bash
npx jest tests/unit/alpine-adapter.test.js
python scripts/audit_serialization.py
.venv/bin/python -m pytest tests/e2e/test_sense_annotations_e2e.py \
    tests/e2e/test_entry_annotations_e2e.py tests/e2e/test_examples_e2e.py \
    tests/e2e/test_all_lift_elements_rendered.py tests/e2e/test_form_submission_e2e.py \
    -q --tb=line -p no:logging -o log_cli=false
```
Done when: sense annotations add/remove in the UI, round-trip to `<sense><annotation>` in saved
XML, entry annotations still work, and no regressions. If a FUNCTIONAL test fails (annotation not
persisting, or duplicate control), STOP and report — don't mask.

## 6. Out of scope (note, don't do)

- Entry annotations (already Alpine). 
- Form-level annotations (LIFT allows `<annotation>` inside `<form>`) — rare; not in the current
  form UI. Leave for a future pass; don't add speculative UI.
- The final `form-serializer.js` / merge-harness decommission (separate deferred task, spec §16.3).
