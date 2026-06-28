# Plan — §16.3 Phase B: decommission `form-serializer.js` + the merge harness's legacy half

**Status:** Ready to execute, with ONE hard prerequisite (custom_fields).
**Author:** verification pass (Claude Opus 4.8), 2026-06-28.
**Goal:** Remove the legacy `name=`-attribute DOM serializer (`form-serializer.js`) and the merge
harness's "serialize legacy DOM → merge Alpine over it" half, so the entry form has a **single
source of truth** (Alpine state → adapter → `serializeEntry`). This is the capstone of the Alpine
migration: every editable entry element is already Alpine-owned (Stages 1–6 + entryMeta Parts A/B).

---

## 0. What was verified (evidence, not assumption)

Honouring the migration's standing rule (*prove the shape end-to-end; passthrough ≠ persistence*):

1. **Only ONE editable entry-data `name=` field remains that Alpine does not own: `custom_fields`.**
   Full sweep of `entry_form.html` + `entry_form_partials/*` for `name=` (excluding `filename=`
   false positives and comment text). Real editable entry-data fields left:
   | `name=` | File | Disposition |
   |---|---|---|
   | `custom_fields[{type}][{lang}]` | `_custom_fields.html:33` | **THE BLOCKER** — see §1 |
   | `homograph_number` | `_basic_info.html:61` | readonly, server-assigned → not serialized, leave |
   | `id` | `entry_form.html:112` | hidden entry id; Alpine state already carries `id` → covered |
   | `csrf-token` | `entry_form.html:483,585` | not entry data; POST header mechanism → leave |
   | `senses[SENSE_INDEX]...reversals[...]` | `entry_form.html:265–320` | inert `<template id="reversal-template">` clone scaffolding (placeholders); see §2 |
   | `variant-direction` | `_variant_modal.html:20,26` | transient modal radio; no JS reads it by name; not entry data; see §2 |

   POS, morph_type, citation, status, lexical-unit, senses (+nested), pronunciations, notes,
   etymologies, annotations, relations, variant relations, direct variants are **all Alpine-owned**
   (registered sections in `entry_form.html:387–398`).

2. **`custom_fields` is already silently dropped on every edit-save** (a pre-existing bug, same
   class as citation/status were). Two independent proofs:
   - `lift-xml-serializer.js` `serializeEntry` has **no `custom_fields` handler** — `grep custom_field`
     in that file returns nothing; the only `<field>` elements it emits are pronunciation
     cv-pattern/tone (lines 912/925).
   - `xml_entry_service.update_entry` (line 470) is **delete + insert of the posted XML** (line 519
     comment: *"delete+insert is safer"*) — no server-side merge/preserve of the existing entry.
   ∴ The custom-field textareas are captured by FormSerializer into `legacyData.custom_fields`,
   carried through the merge (not an alpineSection, so kept), handed to `serializeEntry`, which
   **ignores them** → the posted XML has no custom fields → delete+insert wipes them.
   **This means removing FormSerializer does NOT regress custom fields — they are already lost at the
   serializer step, not the capture step.** But a correct decommission should FIX them, not inherit
   the bug silently. (Step 0 of execution must confirm this empirically before relying on it.)

3. **`form-serializer.js` live consumers** (non-test):
   | Call site | Role | After decommission |
   |---|---|---|
   | `merge-harness.js:40` (`serializeFormToJSONSafe`, async `mergeSync`) | capture legacy DOM | remove legacy capture |
   | `merge-harness.js:184` (`serializeFormToJSON`, `buildSerializerInput`) | capture legacy DOM | remove legacy capture |
   | `entry-form.js:1005` (`serializeFormToJSONSafe`) | **main save path** STAGE 1 | rewrite to Alpine-only |
   | `entry-form.js:179` (`serializeFormToJSON`) | xml-preview **fallback** (MergeHarness primary) | drop fallback |
   | `live-preview.js:210` (`serializeFormToJSON`) | live-preview **fallback** | drop fallback |
   `form-state-manager.js` does **not** use `form-serializer.js`; its own `serializeFormToJSON()`
   (line 64, the audit's 1 remaining suspect at line 113) is a **dead `else` branch** — it already
   uses `MergeHarness.buildSerializerInput` whenever MergeHarness is present (always, on this form).

---

## 1. Prerequisite (Phase B0) — fix `custom_fields` FIRST

Removing FormSerializer makes the existing custom-field loss permanent-by-design, so fix it as part
of this work. **Port custom_fields to Alpine**, mirroring the citation/status (entryMeta Part B) port:

1. **Empirically confirm the loss (gate).** Seed an entry with a `<field type="...">` custom field
   (via `xml_entry_service.create_entry` or a fixture), load `/entries/{id}/edit`, save unchanged,
   reload `/api/xml/entries/{id}` → assert the custom field is **gone** (proves the precondition).
   Keep this as a regression test that will flip to "present" after the fix.
2. **Serializer:** add `createCustomFields(doc, customFields)` to `lift-xml-serializer.js` emitting
   LIFT `<field type="...">` with multitext `<form lang><text>` children (mirror `createCitation`),
   and call it from `serializeEntry` when `formData.custom_fields` is a non-empty dict. Confirm shape
   against `lift_parser._parse_custom_fields` / the model's `custom_fields` ({type: {lang: text}}).
3. **Component:** `app/static/js/alpine/entry-custom-fields.js` — `Alpine.data('entryCustomFields', …)`
   seeded from `normalizeEntry`'s `customFields`. The UI is **edit-only of existing fields** (no
   "add field" affordance today) — simplest faithful port: an `x-for` over the existing
   `{type → {lang → text}}` with `x-model` on each textarea. Expose a `serialized` getter.
4. **normalize-entry.js:** add `customFields: safeObject(raw.custom_fields)` (preserve the
   `{type:{lang:text}}` shape; no array transform needed since keys are types, not langs).
5. **Adapter:** in `alpineStateToSerializerInput`, emit `result.custom_fields` from
   `state.entryCustomFields` (or fold into entryMeta if cheaper — but a separate component keeps
   `_custom_fields.html` self-contained).
6. **Wire-up:** `merge-harness.js` sectionReader `{selector:'[x-data^="entryCustomFields"]',
   dataKey:'serialized', stateKey:'entryCustomFields'}`; `registerAlpineSection('custom_fields')`;
   load the new JS module; convert `_custom_fields.html` textareas to `x-model`, **remove `name=`**.
7. **Round-trip test** (`tests/e2e/test_custom_fields_e2e.py`): edit an existing custom field via the
   Alpine UI → save → reload → assert the new value is in the saved XML; and that an untouched custom
   field survives a save. This is the gate that custom fields now persist.

Output of B0: **no editable `name=` entry-data field remains** anywhere in the form, and FormSerializer
captures nothing that Alpine state doesn't already hold.

> If B0 is judged too large to bundle, ship it as its own task and STOP — do not remove FormSerializer
> while `custom_fields` still depends on `name=` capture, or the loss becomes irreversible-by-design.

---

## 2. Phase B1 — neutralise the dead stragglers

These don't block serialization (senses are an alpineSection; the modal radio is transient), but
remove them so the post-decommission form has no orphan `name=` inputs:

- **`#reversal-template` + legacy `addReversal()` (`entry-form.js` ~line 1551–1560+):** reversals are
  Alpine-owned (`sense-tree.js` `addReversal`/`reversals`; `test_reversal_illustration_e2e.py`).
  Verify no live button/handler calls the legacy `addReversal` and no `.reversals-container` legacy
  markup is rendered; then delete the legacy function + the `<template id="reversal-template">` block
  (`entry_form.html:248–~330`). (Its `senses[SENSE_INDEX]...` `name=` fields are inert inside a
  `<template>` and are stripped as `senses` during merge regardless — pure dead weight.)
- **`variant-direction` radios (`_variant_modal.html`):** confirm the variant-add modal applies its
  result through the Alpine variant-relations/direct-variants components (not via FormSerializer
  capture). No `name=` dependency on FormSerializer; no change needed beyond confirming. If the modal
  handler reads `document.querySelector('input[name=variant-direction]:checked')` that keeps working
  (DOM read, not FormSerializer) — leave the `name=` or switch to an `id`/`x-model` for cleanliness.

---

## 3. Phase B2 — cut FormSerializer out of the live code paths

Order matters: rewire callers BEFORE deleting the file.

1. **`merge-harness.js`:** drop the legacy-capture half.
   - `buildSerializerInput(form)`: replace the `FormSerializer.serializeFormToJSON` + strip + merge
     with `var merged = alpineStateToSerializerInput(extractAlpineState())`. Preserve the id fallback
     by reading the hidden `#entry-id`/`id` input directly (`merged.id ||= form.querySelector('[name="id"]').value`).
   - Remove `mergeSync`'s and the async path's `FormSerializer` branches (or delete `mergeSync` if
     `buildSerializerInput` is the only remaining caller — check `live-preview.js`, auto-save).
   - `_deepMerge`/`alpineSections`/`registerAlpineSection` become vestigial once there is no legacy
     half to override — they can stay as no-ops initially, then be removed in B3 cleanup. **Keep
     `extractAlpineState` + `sectionReaders`** — those are the Alpine read layer and remain essential.
2. **`entry-form.js:1005` save path:** replace `STAGE 1` (`serializeFormToJSONSafe` + manual merge) with
   `const formData = window.MergeHarness.buildSerializerInput(form, { includeEmpty:false })` (now
   Alpine-only). Re-validate the `normalizeIndexedArray(formData.senses)` /
   `applySenseRelationsFromDom` follow-ups (lines 1031–1032): senses come from Alpine already
   normalized — confirm these are no-ops or remove them. (`normalize-indexed-array.js` is **also** used
   by `sense-relations-utils.js`, so it is NOT deleted here — only its entry-form save-path call is
   re-evaluated.)
3. **`entry-form.js:179` (xml-preview) & `live-preview.js:210`:** delete the
   `: window.FormSerializer.serializeFormToJSON(...)` fallback arms; `MergeHarness.buildSerializerInput`
   is the sole path.
4. **`form-state-manager.js`:** remove the dead `else` branches (lines 55, 113) and the now-unused
   hand-rolled `serializeFormToJSON`/`getSenses`/`getCustomFields`/… helpers. This clears the audit's
   last suspect (line 113) and drops a second, independent legacy serializer. (Pure cleanup; the
   MergeHarness branch already drives change-detection.)

---

## 4. Phase B3 — delete files, scripts, tests

After B2 leaves zero live references:

- Delete `app/static/js/form-serializer.js`, `app/static/js/form-serializer-browser-test.js`,
  `app/static/js/form-serializer.test.js`.
- Remove `<script ... form-serializer.js>` from `entry_form.html:419` (and the browser-test include if
  present).
- Remove the vestigial `_deepMerge`/`alpineSections`/`registerAlpineSection` machinery from
  `merge-harness.js` and the `registerAlpineSection(...)` calls in `entry_form.html:387–400` (rename
  the harness to reflect it is now just the Alpine extraction+adapter orchestrator, or fold
  `buildSerializerInput` into the adapter module).
- `grep -rn "FormSerializer\|serializeFormToJSON" app/static app/templates` must return only history,
  not live code.
- Update `scripts/audit_serialization.py` expectation: suspects must now be **0** (the live-preview
  fallback and form-state-manager suspect are gone). Adjust the gate's documented baseline.

---

## 5. Gates / verification

```bash
npx jest tests/unit/alpine-adapter.test.js                # adapter+serializer incl. new custom_fields
python scripts/audit_serialization.py                     # expect suspects: 0
.venv/bin/python -m pytest \
  tests/e2e/test_custom_fields_e2e.py \                    # B0 round-trip (the new gate)
  tests/e2e/test_citation_status_e2e.py \
  tests/e2e/test_entry_meta_e2e.py \
  tests/e2e/test_form_submission_e2e.py \
  tests/e2e/test_entry_roundtrip_e2e.py \
  tests/e2e/test_examples_e2e.py \
  tests/e2e/test_sense_annotations_e2e.py \
  tests/e2e/test_reversal_illustration_e2e.py \
  tests/e2e/test_variant_relations_e2e.py \
  tests/e2e/test_direct_variants_e2e.py \
  tests/e2e/test_all_lift_elements_rendered.py \
  -q --tb=line -p no:logging -o log_cli=false
```
Done when: custom fields round-trip (B0 gate green), no live `FormSerializer` reference remains,
audit = 0 suspects, the full e2e entry suite is green, and change-detection (dirty-state warning on
unsaved navigation) still fires for an Alpine-only edit (manual smoke or a small e2e).

---

## 6. Risks & rollback

- **Highest risk: `custom_fields` (B0).** If its shape is mis-modelled the fix can itself drop fields.
  Mitigate with the before/after round-trip gate (§1.7) and a multilingual custom field in the fixture.
- **Save-path rewrite (B2.2)** is the load-bearing change — every save flows through it. Land B0+B1
  first so that when the legacy capture is removed, nothing it captured is still needed. Each phase is
  independently committable; `git revert` of B2/B3 restores the dual path without touching B0's fix.
- **`id` on add page:** the new entry has `id=""`; preserve the existing temp-id fallback
  (`entry-form.js:185`, `updateXmlPreview`) in the Alpine-only `buildSerializerInput`.
- Keep `extractAlpineState` + `sectionReaders` — removing them by mistake would break every Alpine
  read. "Remove the merge harness" means **remove its legacy-merge half only**.
```
