# Plan — Port the last legacy entry scalars to Alpine (`entryMeta`)

**Status:** ✅ DONE — Part A (POS + morph_type) and Part B (citation + status) both ported to
`entryMeta` and round-trip-tested. The only `name=` left in `_basic_info.html` is the readonly
homograph. Serializer support for citation/status shipped first (the data-loss fix), then the
inputs were moved onto Alpine `x-model` (name-free). Tests: `tests/unit/alpine-adapter.test.js`
(entryMeta citation/status path + serializer), `tests/e2e/test_citation_status_e2e.py`
(citation save, citation edit-reload, status save). Audit unchanged (1 documented fallback).
| **Author:** verification pass (Claude Opus 4.8)
**Goal:** Move the last 4 editable entry-level scalar fields off the legacy `name=` / form-serializer
path into Alpine, so the form is fully single-source-of-truth and `form-serializer.js` + the merge
harness can finally be removed. **Do NOT remove form-serializer in this task** — that's the follow-up
(§16.3 Phase B); this task only closes the scalar gap and is its prerequisite.

## 0. Current state — VERIFIED, with one trap

The remaining non-Alpine editable fields live in `_basic_info.html` (`name=` inputs, serialized by
`form-serializer.js` through the merge harness):

| Field | Input | Client serializer (`lift-xml-serializer.js`) | Adapter (`alpine-to-serializer.js`) | normalizeEntry |
|-------|-------|----------------------------------------------|-------------------------------------|----------------|
| `grammatical_info.part_of_speech` (entry POS) | `#part-of-speech`, range `grammatical-info` | **emits** (line 78 → `createGrammaticalInfo`) | **emits** (`state.grammaticalInfo` → `grammatical_info`, line ~222) | **has** `grammaticalInfo` (line 345) |
| `morph_type` | `#morph-type`, range `morph-type` | **emits** (line 79/128 → `createTrait('morph-type')`) | **emits** (`state.morphType` → `morph_type`, line ~223) | **has** `morphType` (line 346) |
| `citation_form` | `#citation-form`, text | **does NOT emit** any `<citation>` | not handled | not carried |
| `status` | `#status`, range `status` | **does NOT emit** any status trait | not handled | not carried |
| `homograph_number` | `#homograph-number`, **readonly** | (auto-assigned server-side) | n/a | n/a |

**THE TRAP (verify before assuming):** `grammatical_info` + `morph_type` are fully serializer/adapter-ready —
porting them is just "add a component + remove `name=`." But **`citation_form` and `status` are not emitted
by the client serializer at all.** That strongly implies they are **already silently dropped on save in the
CURRENT form** (the posted XML never contains them). Porting them to Alpine will NOT fix that — it needs
serializer support too. So treat this as TWO parts. Do **not** claim citation/status "round-trip" without a
test proving it (see §3) — that exact assumption-without-a-round-trip-test has caused real silent-loss bugs in
this migration (pronunciation, etymology, sense annotations).

## 1. Lessons that this migration keeps re-learning (honour them)

1. **Sync to the current tree first.** Stale bases have re-broken deleted script tags 3×. Confirm your base
   has the §16.2 entry components, `MergeHarness.buildSerializerInput`, `scripts/audit_serialization.py`, the
   sense-annotation restore, and the deleted clone templates absent.
2. **Verify the shape end-to-end — passthrough/assumption is not proof.** A field "rendering" or being in
   state ≠ it reaching the saved XML.
3. **Round-trip persistence test is the gate**: set the field via the REAL Alpine UI → `submitForm()` →
   reload via `/api/xml/entries/{id}` → assert it's in the saved XML. One per field.
4. **Run `python scripts/audit_serialization.py`** after — it must stay at its current count (1 documented
   fallback). Adding a new Alpine section must not introduce a new legacy serialize sink.

## 2. Part A — port `grammatical_info` (entry POS) + `morph_type` (READY, do first)

These have full serializer + adapter support; only a component + UI + wiring is missing.

1. **New component** `app/static/js/alpine/entry-meta.js` — `Alpine.data('entryMeta', (rawEntry) => {...})`:
   - State from `normalizeEntry(rawEntry)`: `grammaticalInfo`, `morphType` (both already produced — line
     345/346). Also `citation`, `status` for Part B (see §3) — but gate their *serialization* on §3.
   - Range-backed selects use the **§11.2 pattern**: load `grammatical-info` and `morph-type` ranges into
     reactive `rangeData`, render `<option>`s via `x-for`, key on `:key="opt.key"` (NEVER `opt.value`), bind
     with `x-model`. Reuse the `sense-tree.js` `loadRanges`/`_whenRangesLoader`/`flattenRangeValues` approach
     (extract to a shared helper if cheap, or copy the proven code).
2. **`merge-harness.js` sectionReaders** — add ONE reader for the whole entry-meta blob. Because these are
   scalars (not a `senses`-style array), the cleanest is a reader whose `dataKey` is a small getter on the
   component returning `{grammatical_info, morph_type, citation_form, status}` (the adapter then spreads them).
   Decide the exact `stateKey`/`dataKey` and make the adapter read them — keep it consistent with how
   `extractAlpineState` maps things. Simplest correct option: give the component a `serialized` getter and a
   reader `{ selector:'[x-data^="entryMeta"]', dataKey:'serialized', stateKey:'entryMeta' }`, then in
   `alpineStateToSerializerInput` merge `state.entryMeta` keys (`grammatical_info`, `morph_type`, …) into the
   top-level result. (The adapter already sets `grammatical_info`/`morph_type` from `state.grammaticalInfo`/
   `state.morphType`; reconcile so there is ONE source — don't double-emit.)
3. **`entry_form.html`** — `registerAlpineSection(...)` for whatever top-level keys you register
   (`grammatical_info`, `morph_type`; later `citation`/`status` if §3 makes them real), and load
   `entry-meta.js` with the other Alpine modules.
4. **`_basic_info.html`** — convert `#part-of-speech` and `#morph-type` from `render_dynamic_select`
   (name-bearing) to Alpine `<select x-model + x-for>`. **Remove their `name=`.** Keep the labels/tooltips.
   Note the entry POS is "inherited from senses" — preserve any existing inheritance behaviour if it's wired
   (check `updateGrammaticalCategoryInheritance` / the POS-propagation code; don't break it).

## 3. Part B — `citation_form` + `status` (VERIFY FIRST; likely needs serializer work)

**Step 1 — prove the current behaviour with a test, before changing anything.** Write a temporary check:
load `/entries/add`, set citation + status via the *current* legacy inputs, `submitForm()`, reload the XML.
- If citation/status ARE in the saved XML → there's serialization happening somewhere (server-side?); trace
  it, then port the inputs to Alpine mirroring Part A and keep that path working.
- If they are NOT in the saved XML (expected, given `serializeEntry` ignores them) → this is a **pre-existing
  serializer gap**, independent of Alpine. Porting the input to Alpine alone will not make them persist.

**Step 2 (if dropped) — add serializer support, then port:**
- `citation`: LIFT `<citation>` is a multitext (like lexical-unit). Add `createCitation` to
  `lift-xml-serializer.js` (mirror `createLexicalUnit`), emit it from `formData.citation`/`citations`; the
  model+parser already handle `citations` (entry.py:156, lift_parser ./lift:citation). Model citation in
  Alpine as a multilingual form list (`{lang:text}`) or a single text per project convention — check what
  `citations` shape the model expects and match it.
- `status`: determine how status is meant to persist (most likely a `<trait name="status" value="…">` or a
  `<field>`). Add the corresponding emit to the serializer, then port the select.
- Add round-trip tests for each (set via Alpine → save → reload → assert in XML).

**Do NOT silently port citation/status without resolving the serializer gap** — that would reproduce the
"UI captures it, save drops it" bug this project keeps hitting. If the serializer work is larger than
expected, ship Part A, and split Part B into its own task with the serializer fix scoped explicitly.

## 4. `homograph_number` — leave as-is

Readonly, auto-assigned server-side. Not user-editable → no Alpine port needed. If you want it shown in an
Alpine-rendered basic-info block, bind it read-only (`x-text`), but it carries no `name=` data to capture.

## 5. Tests (gates)

- **Round-trip per field** (`tests/e2e/test_entry_meta_e2e.py`, model on `test_entry_annotations_e2e.py`):
  - POS: select an entry POS → save → reload → assert `<grammatical-info value="…">` at entry level.
  - morph_type: select → save → reload → assert `<trait name="morph-type" value="…">`.
  - citation/status: per §3 — assert they persist (only after the serializer supports them).
- **Unit** golden test in `tests/unit/alpine-adapter.test.js`: `entryMeta` state → adapter →
  `serializeEntry` emits the entry-level `grammatical-info` / `morph-type` (and citation/status if done).
- **Audit:** `python scripts/audit_serialization.py` — count unchanged.
- **No regression:** `_basic_info`'s lexical-unit (already Alpine) and the sense-level POS must still work;
  run the broad sense suite + `test_pos_ui.py` (entry→sense POS propagation must not break).

## 6. Verification + what this unblocks

```bash
npx jest tests/unit/alpine-adapter.test.js
python scripts/audit_serialization.py
.venv/bin/python -m pytest tests/e2e/test_entry_meta_e2e.py tests/e2e/test_pos_ui.py \
    tests/e2e/test_examples_e2e.py tests/e2e/test_form_submission_e2e.py \
    tests/e2e/test_all_lift_elements_rendered.py -q --tb=line -p no:logging -o log_cli=false
```
Done (Part A) when entry POS + morph_type are Alpine-owned, `name=`-free, round-trip-tested, and the only
remaining `name=` in `_basic_info.html` is the readonly homograph (and citation/status pending §3).

**Unblocks:** once these are Alpine (and citation/status resolved), `_basic_info` has no editable `name=`
fields, so the merge harness's legacy half + `form-serializer.js` can be removed (§16.3 Phase B) — **but**
that removal still has the separate `_custom_fields` data-loss caveat (re-saving an entry with custom fields
must not drop them); handle that in the decommission task, not here.
