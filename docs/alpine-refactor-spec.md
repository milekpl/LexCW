# Alpine.js Entry Form Refactor Specification

**Status:** Stage 1 complete & verified | **Reviewer:** Claude Opus 4.8

## 0a. CURRENT STATUS & NEXT TASK (executing agent: read this first)

**Stage 1 (the sense tree) is implemented and verified against live BaseX+Flask.**
The sense tree round-trips correctly: examples E2E 7/7, broad sense suite ~39 green,
unit adapter 31/31. Do **not** redo Stage 1. Your job is **§11 (Stage 1.5): the
range-backed sense selects**, which are the only remaining failures (8 tests).

**What already works — do not touch / do not regress:**
- `app/static/js/alpine/{sense-tree,normalize-entry,alpine-to-serializer,merge-harness,lexical-unit,pronunciation,notes}.js`
- `app/templates/entry_form_partials/_senses.html` — senses are `x-for`, **no `name=` attributes**.
  Do not re-add `name=`/`:name=` to sense fields (that is the bug class we removed).
- Submit/live-preview extract Alpine state via `MergeHarness.extractAlpineState()` (see §5.2 —
  the old `structuredClone(Alpine.raw($data))` advice was WRONG and has been corrected).
- Only `senses` is a registered Alpine section (`entry_form.html`). **Do not** register
  `lexical_unit`/`pronunciations`/`notes` — they still use `name=`/legacy and the adapter
  is not yet keyed for them (that is Stage 2, not your task).
- Field names in Alpine state: `sense.glossForms`, `sense.definitionForms`,
  `sense.examples[].{sentence,sentenceLang,translations[]}`, `sense.subsenses`,
  `sense.grammaticalInfo` (string), `sense.domainType`/`semanticDomains`/`usageType` (arrays),
  `sense.relations[].{type,ref}`. The §10.3 sketch used `glosses`/`definition`; the **real**
  names are the ones in this list (from `normalize-entry.js`). Trust the code, not §10.3.

**Your task is §11.** Verification commands are in §11.5. Keep changes inside
`sense-tree.js` and `_senses.html` (+ locating one POS-propagation call site). Stop when
§11.5 is green.

## 0. Review verdict (read first)

**Adopt — but only with the corrections in this revision.** The diagnosis in §2 is
accurate and Alpine is a defensible no-build choice. However, the original draft rested
on one false premise and under-modeled the integration surface. Three findings, verified
against the code, change the plan materially:

1. **"The serializer reads Alpine state directly, no change needed" is false.** Four
   different data shapes exist today (see §5.0). The executor must pin a single contract
   and adapt at one boundary — this is now mandatory work, not a no-op.
2. **Serialization runs in a Web Worker** (`form-serializer-worker.js`;
   `serializeFormToJSONSafe` is async). Alpine `$data` is a reactive Proxy and is **not**
   structured-cloneable. `JSON.stringify($data)` is unsafe — use `Alpine.raw()` + deep
   clone (see §5.2).
3. **Undo/redo, auto-save, and live-preview are coupled to the DOM.**
   `entry-form-undo-redo.js` replaces regions via `innerHTML`, which silently destroys
   Alpine bindings in the replaced subtree. This is the highest-risk interaction and was
   absent from the draft (see §7).

**Chosen strategy (2026-06-26): solid, not minimal-but-fragile.** The migration is
organized so Alpine **owns whole subtrees end-to-end**, never grafting reactive fragments
onto imperatively-cloned HTML. The keystone is **Stage 1: the entire sense tree as one
Alpine component** (senses + nested gloss/definition/example/translation/subsense) — because
nesting is the only place legacy cloning and Alpine actually collide. Independent top-level
sections (lexical-unit, pronunciation, etymology, reversals, notes) follow as self-contained
islands. The legacy↔Alpine merge harness is **temporary scaffolding, deleted in Stage 3**,
not a permanent layer. See the rewritten §4. (The earlier "gloss section alone, behind an
`initTree` seam" plan is explicitly rejected as fragile — see §10.)

## 1. Motivation

The dictionary entry form (`editor`) is the most complex UI surface in the
application. It is built with server-rendered Jinja templates, hand-written
JavaScript DOM manipulation, and a multi-step form-to-JSON-to-XML serialization
pipeline.

After fixing 20+ bugs in the form JavaScript over several sessions, a
recurring pattern is clear: the current architecture is the root cause, not
the fixes.

This document proposes replacing the entry form's client-side rendering with
Alpine.js — a 14 KB declarative framework that eliminates the fragile patterns
we keep patching.

## 2. Current architecture (what's broken)

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Jinja template  │     │  JS DOM cloning  │     │  Form serializer  │
│  (server render) │────▶│  (client render) │────▶│  (name→JSON path) │
│  language code   │     │  .replace(/INDEX/g, idx)  │                   │
│  in name attr    │     │  template literals│     │                   │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                                                            │
                                           ┌────────────────┘
                                           ▼
                                  ┌───────────────────┐
                                  │  entry-form.js     │
                                  │  gloss normalizer  │────────▶ loses .lang value
                                  │  (lang key→flat)   │
                                  └───────────────────┘
                                           │
                                           ▼
                                  ┌───────────────────┐
                                  │  lift-xml-serializer│
                                  │  createDefinition  │────────▶ reads dict key,
                                  │  createExample     │          ignores data.lang
                                  └───────────────────┘
```

### 2.1 Identified bug classes

| Class | Root cause | Examples fixed |
|-------|-----------|---------------|
| Language code in field name | `name="senses[0].definition.en.text"` | `createDefinition` fix, `multilingual_form_processor` fix |
| Hardcoded `en` in serializers | `{ en: text }` for sentences/translations | `lift-xml-serializer.js:657, 694` |
| String-template DOM cloning | `.replace(/INDEX/g, idx)` across 6 sites | `addExample` language-select init |
| Async init races | Constructor calls `async init()` without `await` | `EtymologyFormsManager`, `DirectVariantsManager` |
| Event delegation over class names | 50+ `if (e.target.closest('.X'))` branches | `addLanguageField` silent exit for empty glosses |
| Non-atomic state | DOM names ≠ JS arrays ≠ XML output | Gloss normalization at `entry-form.js:1578` |

### 2.2 What the current approach does well

- No build step — plain JS + Jinja works immediately
- E2E tests cover the form extensively
- LIFT XML serialization is a mature, tested module
- Works with existing Flask backend without API changes

## 3. Proposed architecture (Alpine.js)

```
┌──────────────────────────────────────────────────────┐
│                 Alpine reactive data model            │
│  entry = {                                           │
│    lexical_unit: { en: "headword" },                  │
│    senses: [{                                        │
│      definition: { pl: "definicja", en: "..." },      │
│      gloss: { en: "equivalent" },                     │
│      examples: [{ form: "text", translations: {...} }]│
│    }],                                               │
│    ...                                               │
│  }                                                   │
│                                                      │
│  This IS the serialized form. No DOM field-name       │
│  decoding needed. The XML serializer reads this       │
│  directly.                                            │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│              Alpine HTML template                     │
│                                                      │
│  <div x-data="{ ... }" x-init="initFromEditData()">  │
│    <template x-for="(sense, si) in senses">           │
│      <template x-for="(text, lang) in sense.definition">│
│        <select x-model="lang">                        │
│        <textarea x-model="text">                      │
│                                                      │
│  No string cloning. No INDEX replacement.            │
│  Language code is a dict key in the data model.      │
│  Adding a language: glosses.push({pl: ''}).          │
│  No DOM cloning, no field-name rewriting.            │
└──────────────────────────────────────────────────────┘
```

### 3.1 What it eliminates

| Current pattern | Alpine replacement |
|-----------------|-------------------|
| `.replace(/INDEX/g, idx)` | `x-for="(sense, si) in senses"` |
| `addLanguageField()` cloning + field-name rewrite | `definitions[newLang] = ''` (push to dict) |
| `event.target.closest('.add-definition-language-btn')` | `x-on:click="definitions[newLangCode] = ''"` |
| `form-serializer.js` name→JSON decode | Alpine state, *adapted at one boundary* to the serializer's existing input contract (§5.0) |
| Language code in name attribute | Language code as data-model dict key |
| Async init races *within a section* | `x-init` is deterministic per component (but see §7 for cross-script ordering, which Alpine does **not** fix) |
| Three+ copies of form state | Single Alpine reactive state *for migrated sections* |

### 3.2 Dependencies

- **Alpine.js** (14 KB) — **pin an exact version** (e.g. `alpinejs@3.14.x`) and use SRI;
  do not load `@latest` from CDN (SortableJS is already loaded as `@latest` — fix that too).
- **Existing LIFT XML serializer** — its *XML-generation* logic is unchanged. Its *input
  contract* is real and must be matched by an explicit adapter (§5.0). It is **not** a no-op.
- **Existing E2E tests** — same Playwright suite. Most assert on DOM and survive, but the
  ones that read serialized state, and the auto-save/undo/preview interactions, need
  attention (see §6, §7). No server changes required for the migrated form itself.

### 3.3 What stays the same

- Flask backend, BaseX, LIFT parser
- Jinja server-side rendering for navigation, sidebar, metadata
- Server-side validation engine
- E2E test infrastructure (Playwright)

## 4. Migration plan — own whole subtrees, never bridge a seam

> **Strategy (decided 2026-06-26): solid deliverable, not a minimal-but-fragile one.**
> The fragility in earlier drafts came from the **legacy↔Alpine seam** — the `initTree`
> bridge into cloned senses, and the period where `innerHTML`/`FormData`/Select2 fight Alpine
> for the same DOM. We design that seam *out*. The unit of work is a **complete subtree that
> Alpine owns end-to-end**, never a fragment grafted onto imperatively-cloned HTML. The merge
> harness is **temporary scaffolding that gets deleted** (Stage 4), not a permanent layer.

**The keystone insight:** the only place legacy cloning and Alpine reactivity actually
collide is **nesting** — gloss/definition/example/translation live *inside* a sense that is
cloned by `.replace(/INDEX/g, idx)`. So gloss cannot be migrated alone. The smallest *solid*
unit is the **entire sense tree** (Stage 1). Once Alpine owns senses via `x-for`, there is no
clone, so there is no seam and no `initTree` bridge for that tree.

Each stage is one reviewable, independently revertable change. The §7.1 go/no-go gate and the
full round-trip acceptance bar (§4.4) apply to every stage.

### 4.0 Stage 0 — Foundation (scaffolding; no user-visible change)

Build the machinery every later stage depends on. Nothing in the form behaves differently yet.

- **Pin Alpine** (e.g. `alpinejs@3.14.x`) + SortableJS with SRI; control load order so Alpine
  initializes *after* its dependencies (R5). Do not rely on `defer` ordering alone.
- **`#entry-data` JSON block** — server embeds `entry.to_dict() | tojson` (§5.1).
- **`normalizeEntry(raw)`** — pure, null-safe; coerces the server dict into the Alpine state
  shape (arrays-of-objects with stable ids). Unit-tested against real `to_dict()` fixtures.
- **`alpineStateToSerializerInput(state)`** — the §5.0 adapter; the single home of shape
  knowledge. Unit-tested.
- **Merge harness (temporary)** — one function feeding submit, auto-save, and live-preview
  that merges *legacy-DOM-serialized* sections + *Alpine-serialized* sections into one
  serializer input (§8 item 1). It shrinks every stage and is deleted in Stage 4.
- **Golden test** `test_alpine_adapter_matches_legacy` — for any not-yet-migrated section the
  merged output must byte-match today's `form-serializer.js` output for the same state.

**Exit:** all of the above unit-tested; full E2E suite still green (form unchanged).

### 4.1 Stage 1 — The sense tree (the keystone)

Alpine takes **full ownership** of the senses list and everything nested in it, as **one
component tree**: senses → definition, gloss, examples → translations, subsenses (recursively),
sense-level notes/relations. No `<template id="sense-template">` clone source remains; senses
are `<template x-for="(sense, si) in senses" :key="sense.id">` and every nested multilingual
list is a nested `x-for` (the §10 pattern, applied throughout — gloss is just one nested list
among several).

Eliminate (delete, not disable):
- `multilingual-sense-fields.js` entirely (`addLanguageField`, all `.add-*-language-btn` /
  `.remove-*-language-btn` delegation for gloss **and** definition).
- `entry-form.js` sense/example/subsense cloning: `addExample()` (`:1892-1926`), subsense
  and relation `innerHTML` builders, `reindexSenses()`, the gloss→glosses conversion pass
  (`:1542-1593` — moves into the §5.0 adapter).
- `<template id="sense-template">`, `#example-template`, `#subsense-template` and the
  duplicated rendered partials they shadowed.

Add:
- `senseTree(seed)` Alpine component (§10.3 generalized to the full tree).
- Recursive subsense rendering (Alpine handles recursion via a named `<template x-for>` that
  references the same row markup; document the recursion approach explicitly).
- Sense reordering folded in **now**, not deferred: SortableJS `onEnd` → `splice` the Alpine
  array; Alpine re-renders. Never let both own order simultaneously (R7). `reindexSenses()` is
  deleted — indices are reactive.

**Risk:** This is the largest single stage and the highest-value one. Mitigated by: it is
*one coherent tree* with *one* data model, fully Alpine-owned, so there is no seam *within*
it; the merge harness keeps the rest of the form working; it is revertable as one change.
**Validation:** `test_add_gloss_language_button_works`, `test_definition_language_selector_exists`,
`test_example_sentence_has_language_selector`, `test_translation_has_language_selector`,
`test_generated_xml_contains_correct_languages`, `test_field_lang_overrides_dict_key`,
plus the full round-trip test (§4.4) for a multi-sense, multi-example entry.

### 4.2 Stage 2 — Independent top-level sections (sequenced)

These do **not** nest inside the sense tree, so each is a self-contained Alpine island,
migrated and shipped one at a time. Each deletes its legacy cloning + delegation and joins
the Alpine half of the merge harness. Order by ascending risk:

1. **Lexical-unit languages** (headword forms) — `entry-form.js:641-693`. Low risk; same
   array-of-objects pattern as gloss.
2. **Pronunciation** (IPA / CV-pattern / tone) — `pronunciation-forms.js:226-258` + 6
   delegation blocks. **IPA validation must be preserved**: keep `ipa-validation.js`, wire it
   to the Alpine field via input/blur, not via the deleted cloning path.
   Validation: `test_valid_ipa_accepted`, `test_invalid_ipa_characters_show_error`,
   `test_ipa_double_stress_error`.
3. **Reversals, notes, annotations** — same array-of-objects pattern; one island each.
4. **Etymology** (last — riskiest) — `etymology-forms.js` entirely; removes the async
   `constructor→init()` race and the duplicate `_populateTypeDropdown`. Etymology uses
   **Select2/ranges-backed dropdowns**, so the R6 pattern (bind via `change` event, render
   options from Alpine, never `x-model` a Select2-managed `<select>`) must be **proven on a
   throwaway spike first** (§8 item 8). Validation: `test_etymology_type_dropdown_populated`,
   `test_etymology_type_selection_works`.

### 4.3 Stage 3 — Decommission the scaffolding

Once every section is Alpine-owned, the merge harness has no legacy half left to merge.

- Delete the merge harness; submit/auto-save/live-preview read Alpine state directly via
  `structuredClone(Alpine.raw($data))` → `alpineStateToSerializerInput` (§5.2).
- Delete `form-serializer.js`, `form-serializer-worker.js` *if* serialization no longer needs
  the worker (re-measure: a single `structuredClone` + adapter call may be fast enough on the
  main thread; keep the worker only if profiling says so).
- Delete the now-dead sections of `entry-form.js`, all string-template cloning, and all
  class-name event delegation for migrated sections.

### 4.4 Definition of done (the "solid" bar — applies to every stage)

A stage is done only when, in addition to §7.1:
- **Full round-trip fidelity:** load an entry → edit in every migrated control → serialize →
  save to BaseX → reload → state and rendered DOM match. No field silently dropped, no
  language code lost, no `null`/empty-collection crash. This is an explicit E2E test, not a
  manual check.
- **No orphaned legacy code** for the migrated section (delete, don't comment out).
- The merge harness golden test (§4.0) still passes for everything not yet migrated.

## 5. Data model: server → Alpine → XML

### 5.0 The data-shape contract (MANDATORY — read before any code)

There is no single shape today. Four coexist, and the draft conflated them:

| Layer | File / line | Shape (gloss example) |
|-------|-------------|-----------------------|
| Form serializer output | `form-serializer.js` | `gloss` (singular): `{en: {text: "...", lang: "en"}}` |
| XML serializer input | `lift-xml-serializer.js:283-289, 837-842` | accepts **both** `definition` and `definitions`; reads `defData.text \|\| defData.value`; honors `defData.lang` over the dict key |
| Submit conversion pass | `entry-form.js:1542-1593` | rewrites `gloss`→`glosses`, `{text}`→flat string, for the API |
| Model / API | `entry.to_dict()` | `glosses` (plural), flat: `{en: "..."}` |

**Decision (resolves checklist Q3):** Do **not** invent a fifth shape. The Alpine state's
**internal** shape may be whatever is ergonomic for `x-for` (nested `{text, lang}` objects
are fine and make the language-override case explicit). But the **submit boundary** must
emit *exactly* the structure `serializeEntry()` already consumes. Write one pure function:

```javascript
// alpine-to-serializer.js — the single adapter. Pure, unit-tested in isolation.
function alpineStateToSerializerInput(state) { /* state -> shape serializeEntry() expects */ }
```

This function is the **only** place shape-knowledge lives. The `gloss`→`glosses`
flattening currently inlined at `entry-form.js:1542-1593` moves here (or stays in the
serializer path — pick one, document it). Until *all* sections are migrated, the legacy
`form-serializer.js` path and this adapter must produce byte-identical serializer input
for the *same form state* — assert this in a test (§6, `test_alpine_adapter_matches_legacy`).

### 5.1 Initialization from server data

On page load, Alpine needs the entry data. Instead of parsing DOM field names,
the server will embed a JSON script block:

```html
<script id="entry-data" type="application/json">
  {{ entry.to_dict() | tojson | safe }}
</script>
```

Alpine `x-init` reads this and initializes the reactive state:

```javascript
x-init="const raw = JSON.parse(document.getElementById('entry-data').textContent);
        senses = raw.senses.map(s => ({...s}));
        ..."
```

### 5.2 Serialization to XML (CORRECTED — the original advice here was wrong)

> **Two facts the original draft got wrong, discovered during Stage 1. Heed them or you
> will silently lose all sense data again:**
>
> 1. **`structuredClone(Alpine.raw($data))` throws.** Alpine component objects contain
>    **methods** (`addSense`, `addRow`, …); `structuredClone` rejects functions, the throw is
>    swallowed by the surrounding `try/catch`, and the component is silently skipped.
> 2. **Alpine v3 `$data` is a merge-proxy whose keys are NOT enumerable.** `Object.keys($data)`
>    and `for…in` return `[]`, even though `$data.senses` reads fine. So you cannot "iterate
>    the component's keys" — you must read each known key **by name**.

The working extraction lives in `merge-harness.js` as `MergeHarness.extractAlpineState()`.
It reads each registered section's reactive key by name and JSON-clones it (detaches the
proxy *and* drops methods in one step):

```javascript
// merge-harness.js — the real, working pattern. Add a sectionReaders entry per migrated section.
sectionReaders: [
  { selector: '[x-data^="senseTree"]', dataKey: 'senses', stateKey: 'senses' }
],
extractAlpineState() {
  const state = {};
  this.sectionReaders.forEach(r => {
    const el = document.querySelector(r.selector);
    if (!el) return;
    const data = window.Alpine.$data(el);              // merge-proxy: read BY NAME
    if (data && data[r.dataKey] !== undefined) {
      state[r.stateKey] = JSON.parse(JSON.stringify(data[r.dataKey])); // detach + drop fns
    }
  });
  return state;
}
```

Submit (`entry-form.js`) and live-preview (`live-preview.js`) both call
`MergeHarness.extractAlpineState()`, pass the result through `mergeSync` (legacy DOM +
adapter, overriding **only** registered sections — never the adapter's empty skeleton), then
`serializeEntry`. The serializer's XML-generation is unchanged. **When you migrate a new
section, add one `sectionReaders` entry and one `registerAlpineSection(...)` call — that is
the whole wiring.**

## 6. E2E test strategy

Most existing tests pass because they assert against the DOM content visible
to Playwright, not against internal JS structures. They will continue to pass
as long as the DOM renders correctly.

Tests that may need adaptation:

| Test | Why |
|------|-----|
| `test_add_gloss_language_button_works` | Checks that `.gloss-forms .language-form` count increases after click |
| `test_definition_language_selector_exists` | Checks `select.language-select` presence |
| `test_example_sentence_has_language_selector` | Checks selector exists |
| `test_translation_has_language_selector` | Checks selector exists |
| `test_generated_xml_contains_correct_languages` | Reads `document.querySelector` values — needs to read Alpine state instead or keep DOM structure |
| `test_etymology_type_dropdown_populated` | Timeout issues with async init — Alpine should fix this |
| IPA validation tests | Input selectors unchanged; just need `.ipa-input` to exist |

New tests to add:

| Test | What it validates |
|------|------------------|
| `test_alpine_state_matches_dom` | After modifying form, Alpine state JSON equals expected values |
| `test_serialized_xml_from_alpine_state` | XML serializer produces correct LIFT from Alpine state |
| `test_add_language_updates_alpine_state` | Clicking Add Language pushes to the Alpine data array |
| `test_alpine_adapter_matches_legacy` | **(unit)** §5.0 adapter and legacy `form-serializer.js` produce byte-identical serializer input for the same form state — the migration's safety net |
| `test_field_lang_overrides_dict_key` | When the selected language ≠ dict key, emitted XML uses the selected language (guards the original bug class) |
| `test_live_preview_reflects_alpine_change` | Editing an Alpine-owned field updates the live preview (R2) |
| `test_autosave_roundtrips_alpine_section` | Auto-save captures and restores an Alpine-owned section (R2) |
| `test_undo_redo_preserves_alpine_bindings` | After undo/redo re-renders a migrated region, its Alpine bindings still work (R1) |

## 7. Risks and mitigations (revised — verified against code)

Ordered by severity. The first three are the ones that will actually break this migration.

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | **Undo/redo destroys Alpine bindings.** `entry-form-undo-redo.js` is server-backed and re-renders regions via `innerHTML` (`:92,114`). Injected nodes are inert — Alpine does not bind them. | **High** | After any innerHTML replacement of a migrated region, call `Alpine.initTree(node)` on it. **Per phase**, run an undo/redo cycle against the migrated section as an explicit acceptance test. If a section is migrated but undo/redo still rewrites its HTML, the section is **not done**. |
| R2 | **Live-preview & auto-save go blind on Alpine sections.** `live-preview.js` (`:190-229`) and `auto-save-manager.js` read the form via `FormData`/`querySelector`/`form-serializer.js`. Migrated sections have no `name=`-bearing inputs to read. | **High** | Route both through the **same merge step** as submit (§5.2): legacy DOM serialize + Alpine adapter → merged serializer input. Build this in Stage 0 (temporary scaffolding, deleted in Stage 3). Verify live-preview updates when an Alpine field changes. |
| R3 | **Data-shape drift across the four shapes (§5.0).** "No change to serializer" is false. | **High** | Single adapter (§5.0), unit-tested. Golden test: legacy path and Alpine path produce byte-identical serializer input for the same state (`test_alpine_adapter_matches_legacy`). |
| R4 | **`$data` Proxy not serializable** to the Web Worker. | Medium | `structuredClone(Alpine.raw($data))` before serialize/post (§5.2). |
| R5 | **Cross-script init ordering.** Alpine does **not** fix this (contra the draft). `select2`, `ranges-loader`, `form-event-bus`, `form-component`, `form-state-manager` all init on load; `x-init` order relative to deferred scripts is not guaranteed. | Medium | For ranges/select2 inside Alpine, `await rangesLoader.loadRange()` inside `x-init` and bind the result to reactive state; do not assume a global is ready at `x-init` time — guard it. Initialize Alpine **after** the libraries it depends on (control load order explicitly; don't rely on `defer` ordering alone). |
| R6 | **Select2 + Alpine double-control of the same `<select>`.** Select2 mutates the DOM and detaches the native element from `x-model`. | Medium | Don't put `x-model` on a Select2-managed `<select>`. Bind via Select2's `change` event → write to Alpine state; render options from Alpine. Or defer Select2-backed dropdowns (etymology, ranges) to their own phase and keep them legacy until then. |
| R7 | **SortableJS reorders DOM behind Alpine's back.** | Medium | Fold reordering into the sense component in **Stage 1**: on Sortable's `onEnd`, `splice` the Alpine `senses` array and let Alpine re-render — never let both manage order simultaneously. (Or use Alpine's official `sort` plugin.) `reindexSenses()` is deleted. |
| R8 | **`x-for` re-render drops focus / loses uncommitted input** when the keyed array mutates (e.g. add-language re-renders the list). | Low/Med | Always provide a stable `:key`. Never key on array index for editable lists; key on a stable id. Verify typing in field N survives adding field N+1. |
| R9 | **E2E flakiness during the mixed period.** | Low | Run full suite after each phase. Do not blanket-skip; for any test touching a half-migrated interaction, fix or quarantine with a dated `# TODO(alpine-phaseN)` and re-enable at phase end. |

### 7.1 Go / no-go gate per stage

A phase is complete only when **all** hold: (a) its validation test(s) pass; (b) full E2E
suite is green or only quarantined-with-reason; (c) live-preview reflects changes in the
migrated section; (d) auto-save round-trips the section; (e) undo/redo over the section
preserves Alpine bindings; (f) the adapter golden test passes. Miss any → not done.

## 8. Critical guidance for the executing agent

Only the things that will cause silent data loss or wasted rework if ignored.

1. **Build the merge harness in Stage 0 as temporary scaffolding; delete it in Stage 3.**
   Submit, auto-save, and live-preview must all serialize through one function that merges
   legacy-DOM state + Alpine state into the serializer's input contract. Every stage moves
   one subtree from the "legacy" half to the "Alpine" half of that merge. Without it, every
   section you migrate goes invisible to preview/auto-save the moment you remove its `name=`
   inputs. It is scaffolding, not architecture — once all sections are Alpine-owned it has
   nothing left to merge and is removed.

2. **The adapter (§5.0) is the only place data-shape lives.** Write it first, unit-test it
   against real `entry.to_dict()` fixtures from BaseX, and assert byte-identical serializer
   input vs. the legacy path. Do not scatter `gloss`/`glosses` knowledge across templates.

3. **Never let two systems own the same DOM.** Select2 ↔ `x-model`, SortableJS ↔ `x-for`,
   undo/redo `innerHTML` ↔ Alpine bindings — each is a corruption source. Pick one owner per
   element; for innerHTML-injected regions, re-run `Alpine.initTree`.

4. **Extract before serialize:** `structuredClone(Alpine.raw($data))`. Never stringify or
   post the raw Proxy.

5. **Preserve the `.lang` override semantics.** The serializer honors `defData.lang` over
   the dict key (`lift-xml-serializer.js:837`). The whole point of this refactor is correct
   per-field language codes — your Alpine model must carry `lang` per value and your adapter
   must pass it through. Add a test that the emitted XML uses the selected language, not the
   dict key, when they differ (this is the original bug class — guard against regressing it).

6. **Pin versions + SRI** for Alpine and SortableJS. No `@latest` from CDN in a data-entry
   tool.

7. **Keep phases atomically revertable.** One section per commit/PR, behind the merge
   harness, so a bad phase reverts without touching others. Run the §7.1 gate before moving on.

8. **Don't migrate etymology (Stage 2, last) or any Select2/ranges-backed dropdown until the
   Select2↔Alpine pattern (R6) is proven on a throwaway spike.** It is the riskiest binding;
   prove it in isolation before committing the etymology rewrite.

## 9. Decision checklist — resolved

1. **Phased approach (gloss → definition → example → rest)?** Yes — retained, with the
   §7.1 go/no-go gate added per stage, but **restructured** (§4): the sense tree migrates as
   one coherent unit (Stage 1) rather than gloss-then-definition-then-example, because nesting
   makes those inseparable. Independent top-level sections still sequence one at a time (Stage 2).
2. **Alpine vs. HTMX/Svelte/Vue?** Alpine is acceptable for the no-build constraint. HTMX
   is the wrong tool (it's for server-driven partials, not client-side reactive arrays).
   Svelte/Vue would be cleaner but reintroduce a build step the team explicitly avoids.
3. **Adapt serializer to read Alpine state, or write an interim adapter?** **Write the
   adapter** (§5.0). The serializer's XML-generation stays untouched; the adapter owns all
   shape knowledge. "No change needed" was incorrect — the adapter is mandatory.
4. **E2E changes acceptable?** Yes, plus the new tests in §6 (adapter golden test,
   lang-override, preview/auto-save/undo interactions) are **required**, not optional.
5. **Mixing Alpine + legacy JS during migration acceptable?** Yes *only behind the merge
   harness* (§8, item 1), which is **temporary scaffolding deleted in Stage 3**. Without it,
   mixing causes silent data loss in preview/auto-save. With it, the mixed period is safe and
   each stage is atomically revertable.

## 10. Stage 1 pattern: the sense-tree component (2026-06-26)

The first prototype (Alpine 3.13.0) tried to migrate the gloss section alone and failed with:
*"the `@click` 'Add Language' expression doesn't trigger DOM updates."* That failure is what
drove the §4 strategy decision: gloss can't be migrated alone because it nests inside a
cloned sense. The diagnosis below corrects the prototype's findings and gives the pattern for
the **whole sense tree** (Stage 1). **Read this before starting Stage 1.**

### 10.1 Root cause — the real one

The gloss `@click`/`x-for` were placed inside `<template id="sense-template">`, which is
stamped out by the **legacy** `.replace(/INDEX/g, idx)` cloning machinery — not by Alpine.

- A `<template>`'s `.content` is an **inert DocumentFragment**: directives inside never run.
  When legacy JS clones and injects it, Alpine auto-inits the inserted node *only if it
  carries its own `x-data` root*. A bare `@click`/`x-for` with no enclosing initialized
  scope stays dead. **That is why the click did nothing — the handler was never bound to a
  reactive scope.** Nothing to do with the spread operator.

This is risk **R3 / "never let two systems own the same DOM"** (§7) landing exactly where
predicted: legacy `INDEX` cloning and Alpine `x-for` were nested, both trying to manage the
same list. You cannot migrate *just* the gloss button while the surrounding sense is still
produced by imperative cloning.

### 10.2 Two prototype conclusions were Alpine anti-patterns — do NOT carry them forward

| Prototype conclusion | Verdict | Reality |
|----------------------|---------|---------|
| "Spread `gloss = {...gloss, [k]:v}` doesn't trigger re-render; must mutate in place." | **False** | Alpine 3 uses Vue-3 proxy reactivity. It tracks **both** reassigning a top-level `x-data` key **and** adding a new key to a reactive object. Both forms work — *if the expression runs in Alpine's scope.* |
| "Reach into `_x_dataStack[0]` / hand-wrap with `Alpine.reactive()`." | **Anti-pattern — the actual culprit** | Mutating via `_x_dataStack[0]` touches the raw target and bypasses the effect scheduler — *that* is why re-render didn't fire. **Never touch `_x_dataStack` or manually `Alpine.reactive()` in-component state.** Let `@click="..."` run in Alpine's evaluation context; reactivity is automatic. (`_x_dataStack` is not a test API either — read state via `Alpine.$data(el)` or assert on the DOM.) |

### 10.3 The pattern: multilingual lists as nested `x-for`

Per the chosen strategy (§4), Alpine owns the **whole sense tree** as one component. Gloss is
therefore **not** a standalone island with its own `x-data` root — it is one nested `x-for`
among several (definition, gloss, examples → translations, subsenses) inside the `senseTree`
component. The same per-list mechanics below apply to every multilingual list, whether nested
in the sense tree (Stage 1) or used as a self-contained island for an independent top-level
section (Stage 2, e.g. pronunciation, lexical-unit).

**Two rules that make every list robust:**
1. **Model each collection as an array of objects with a stable id, not a lang-keyed dict.**
   A dict keyed by language code breaks the instant the user *changes* a language (key change
   = delete+add = lost focus and identity → risk R8) and cannot hold a half-typed duplicate.
   The Alpine docs require a **stable unique `:key`** for add/remove/reorder. Convert
   array → dict only in the §5.0 adapter, at the serialize boundary.
2. **Mutate via component methods in Alpine's scope** (`this.glosses.push(...)`), never via
   `_x_dataStack` or hand-rolled `Alpine.reactive()` (§10.2).

```html
<!-- senses live in ONE component; no #sense-template clone source anywhere. -->
<div x-data="senseTree(JSON.parse(document.getElementById('entry-data').textContent))">
  <template x-for="(sense, si) in senses" :key="sense.id">
    <div class="sense-item">

      <!-- one multilingual list = one nested x-for. gloss shown; definition/example identical. -->
      <div class="gloss-forms">
        <template x-for="g in sense.glosses" :key="g.id">
          <div class="language-form">
            <!-- plain <select>: x-model is fine. For Select2-backed selects use the R6 pattern. -->
            <select class="language-select" x-model="g.lang">
              <template x-for="opt in languageOptions" :key="opt.code">
                <option :value="opt.code" x-text="opt.label"></option>
              </template>
            </select>
            <input type="text" class="gloss-text" x-model="g.text"
                   :placeholder="`Enter gloss in ${g.lang}`">
            <button type="button" x-show="sense.glosses.length > 1"
                    @click.prevent="removeRow(sense.glosses, g.id)">×</button>
          </div>
        </template>
        <button type="button" @click.prevent="addRow(sense.glosses)">Add Language</button>
      </div>

      <!-- definition, examples (with nested translations), subsenses: same pattern -->

    </div>
  </template>
  <button type="button" @click.prevent="addSense()">Add Sense</button>
</div>
```

```javascript
// senseTree.js — registered via Alpine.data('senseTree', ...). ONE component owns the tree.
function senseTree(rawEntry) {
  const e = normalizeEntry(rawEntry);     // pure, null-safe; → arrays-of-objects with ids
  return {
    senses: e.senses,
    languageOptions: window.PROJECT_LANGUAGES,        // [{code, label}]
    // generic helpers reused by every multilingual list in the tree:
    addRow(list) {
      const used = new Set(list.map(r => r.lang));
      const next = (this.languageOptions.find(o => !used.has(o.code)) || {}).code || '';
      list.push({ id: crypto.randomUUID(), lang: next, text: '' });
    },
    removeRow(list, id) {
      const i = list.findIndex(r => r.id === id);
      if (i !== -1) list.splice(i, 1);    // splice keeps the SAME reactive array (R8)
    },
    addSense() {
      this.senses.push({ id: crypto.randomUUID(), glosses: [], definition: [], examples: [], subsenses: [] });
    },
  };
}
```

`normalizeEntry` (Stage 0, §4.0) is the single null-safe boundary that turns the server's
`to_dict()` shape into this state — never `x-model` against `null`, no null-guards scattered
through the template. This kills the bug class the refactor exists for: **add/remove never
clones a `<template>`** — it mutates a reactive array and `x-for` renders the row.

### 10.4 `Alpine.initTree` — only for `innerHTML` re-renders (undo/redo), not for senses

Under the chosen strategy the sense tree is rendered by `x-for`, so **there is no clone and
no seam for senses** — `initTree` is *not* needed there. The bridge survives for exactly one
case: code that replaces a migrated region's markup via `innerHTML` (R1 — `entry-form-undo-redo.js`
rebuilds regions this way). Injected nodes are inert until initialized:

```javascript
// after any innerHTML replacement of an Alpine-owned region:
mutateDom(() => { container.innerHTML = serverHtml; Alpine.initTree(container); });
```

Alpine's own `x-if` uses this exact pattern. Until undo/redo is reworked to drive Alpine state
instead of replacing HTML, every undo/redo touching a migrated region must re-run `initTree`,
and a per-stage test must prove bindings survive an undo/redo cycle (§7.1e).

### 10.5 Corrected next steps (supersedes the prototype's list)

These now describe **Stage 1 (the sense tree)**, not a gloss island:

1. Build the `senseTree` component (§10.3) covering definition, gloss, examples →
   translations, and recursive subsenses. **Delete** `multilingual-sense-fields.js`, the
   sense/example/subsense cloning in `entry-form.js`, `reindexSenses()`, and the gloss→glosses
   pass (`:1542-1593`, which moves into the §5.0 adapter). Remove `<template id="sense-template">`,
   `#example-template`, `#subsense-template`.
2. Model every collection as `[{id, lang, text}]` (or richer for examples); convert to the
   serializer's shape only in the §5.0 adapter.
3. Normalize the server seed once in `normalizeEntry` (Stage 0). Never `x-model` against `null`.
4. Do **not** use `_x_dataStack` or manual `Alpine.reactive()`. Let `@click`/methods run in scope.
5. Fold sense reordering into the component now: SortableJS `onEnd` → `splice` the `senses`
   array (R7). Delete `reindexSenses()`.
6. Tests: assert via `Alpine.$data(el)` or the DOM. Run the Stage-1 validation set and the
   full **round-trip** test (§4.4) for a multi-sense, multi-example entry, plus the §7.1 gate.

## 11. Stage 1.5 — Range-backed sense selects (THE TASK — precise work order)

Stage 1 left the **range-backed `<select>`s inside the sense tree** half-migrated. They are
the only failing tests (8): grammatical-info/POS, domain-type, semantic-domain, usage-type,
relation-type. Fix them with the R6 pattern done uniformly. **Scope: `sense-tree.js` and
`_senses.html` only**, plus one POS-propagation call site. ~1 hour of work.

### 11.1 Why they fail (root cause)

Two inconsistent strategies coexist, both wrong:
- **Single-selects** (grammatical-info, relation-type) are filled **imperatively** by
  `rangesLoader.populateSelect` (which also attaches **Select2**), bound with `@change`, and
  have **no value restore** → saved value never displays, and Select2 fights Alpine (R6).
- **Multi-selects** (domain/semantic/usage) render options via `x-for` from `rangeData` but
  bind with a manual `@change` + `<option :selected>` instead of `x-model` → selection is not
  reliably written back to state → **saves empty `[]`** (the 5 semantic-domain failures).
- `rangeData` is filled by `_loadRanges` using **`setTimeout` polling** (the async-race
  anti-pattern, R5) and re-run on every `addSense`.

### 11.2 The one pattern (apply to every range select)

**Options come from `rangeData` via `x-for`; selection is bound with `x-model`; nothing is
populated imperatively; no Select2.** These are plain native `<select>`s — `x-model` on a
`multiple` select binds an **array** natively, and on a single select binds a **string**. The
getters already exist (`grammaticalInfoOptions`, `domainTypeOptions`, `semanticDomainOptions`,
`usageTypeOptions`, `relationTypeOptions` — each returns `rangeData[id]`).

> **CRITICAL — `:key` on range options must be UNIQUE (verification bug, 2026-06-27).**
> Never use `:key="opt.value"` for range-option `x-for`. A hierarchical range flattens to
> entries whose `value` repeats (e.g. the same POS value appears under several parents), and
> **Alpine `x-for` silently refuses to render a list with duplicate `:key` — it drops the
> entire list** (the select shows only its placeholder). This is invisible with small/flat test
> ranges (which is why it shipped); it only bites on real hierarchical data. semantic-domain
> escaped only because DDP4 ids (`1`, `1.1`, …) are coincidentally unique. Fix: `flattenRangeValues`
> assigns a unique `key` per option (`.map((o,i)=>{o.key=i;return o;})` — index keys are safe
> because the list is replaced wholesale and `<option>`s hold no input state), and every range
> `x-for` uses `:key="opt.key"`. Language-option lists keyed on `opt.code` are fine (codes are
> unique). When adding any new range-backed `x-for`, key it on `opt.key`, never `opt.value`.

### 11.3 `sense-tree.js` — exact changes

**(a) Replace `init()` + `_loadRanges()` with an async loader (delete the polling and ALL
`populateSelect`/`populateSingles`/Select2 code):**

```javascript
init() {
  if (this.senses.length === 0) this.addSense();
  this.loadRanges();      // async; x-for fills options when rangeData arrives
  this.setupSortable();
},

async loadRanges() {
  const loader = await this._whenRangesLoader();   // wait for the global script (R5 guard)
  if (!loader) return;
  const ids = ['grammatical-info','domain-type','semantic-domain-ddp4','usage-type','lexical-relation'];
  await Promise.all(ids.map(async (id) => {
    try {
      const data = await loader.loadRange(id);
      if (data && data.values) this.rangeData[id] = flattenRangeValues(data.values);
    } catch (e) { console.warn('[senseTree] range load failed', id, e); }
  }));
},

// Bounded one-shot wait for the rangesLoader global (NOT per-render polling — this is the
// allowed R5 "guard a global is ready" case, runs once at init).
_whenRangesLoader() {
  return new Promise((resolve) => {
    if (window.rangesLoader && window.rangesLoader.loadRange) return resolve(window.rangesLoader);
    let n = 0;
    const t = setInterval(() => {
      if (window.rangesLoader && window.rangesLoader.loadRange) { clearInterval(t); resolve(window.rangesLoader); }
      else if (++n > 50) { clearInterval(t); resolve(null); }   // ~5s cap
    }, 100);
  });
},

setupSortable() {
  const container = this.$el.querySelector('#senses-container');
  if (container && typeof Sortable !== 'undefined') {
    Sortable.create(container, { handle: '.drag-handle', animation: 150,
      onEnd: (evt) => this.reorderSenses(evt.oldIndex, evt.newIndex) });
  }
},
```

**(b) Delete** the `setTimeout(function () { self._loadRanges(); }, 200);` line in `addSense`.
Options are reactive; new senses get them automatically.

**(c) Add the POS-propagation method (§11.4):**

```javascript
applyEntryPos(value) {                 // called by entry-level POS change
  if (!value) return;
  this.senses.forEach((s) => { s.grammaticalInfo = value; });
},
```

### 11.4 `_senses.html` — exact per-select changes

For **every** range select, remove `@change=...` and `<option :selected=...>` and bind
`x-model`. Keep the existing `class=` (tests select by it). Patterns:

```html
<!-- grammatical-info (single) -->
<select class="form-select sense-grammatical-info-select" x-model="sense.grammaticalInfo">
  <option value="">Select part of speech</option>
  <template x-for="opt in grammaticalInfoOptions" :key="opt.value">
    <option :value="opt.value" x-text="opt.label"></option>
  </template>
</select>

<!-- domain-type / semantic-domain / usage-type (multiple): x-model binds an ARRAY -->
<select class="form-select sense-domain-type-select" multiple x-model="sense.domainType">
  <template x-for="opt in domainTypeOptions" :key="opt.value">
    <option :value="opt.value" x-text="opt.label"></option>
  </template>
</select>
<!-- …semantic-domain → x-model="sense.semanticDomains", options semanticDomainOptions -->
<!-- …usage-type      → x-model="sense.usageType",      options usageTypeOptions -->

<!-- relation type (single, inside x-for="rel") -->
<select class="form-select form-select-sm sense-relation-type-select" x-model="rel.type">
  <option value="">Select type</option>
  <template x-for="opt in relationTypeOptions" :key="opt.value">
    <option :value="opt.value" x-text="opt.label"></option>
  </template>
</select>

<!-- subsense grammatical-info → x-model="sub.grammaticalInfo", options grammaticalInfoOptions -->
```

**POS propagation wiring:** grep for the entry-level POS→sense propagation
(`grep -rn "propagat\|part_of_speech\|grammatical_info" app/static/js/*.js`). It currently
writes to sense POS `<select>`s in the DOM and throws `Cannot set properties of null`.
Replace those DOM writes with a single call:

```javascript
const el = document.querySelector('[x-data^="senseTree"]');
if (el && window.Alpine) window.Alpine.$data(el).applyEntryPos(value);
```

Read `tests/e2e/test_pos_ui.py::test_entry_pos_propagation_with_existing_sense_pos` first —
if it expects existing sense POS to be **preserved** (not overwritten), guard `applyEntryPos`
to only set senses whose `grammaticalInfo` is empty.

### 11.5 Verification (run these; all must pass)

```bash
npx jest tests/unit/alpine-adapter.test.js          # 31/31 (must stay green)
.venv/bin/python -m pytest tests/e2e/test_semantic_domains_e2e.py \
    tests/e2e/test_pos_ui.py tests/e2e/test_pos_field_behavior.py \
    tests/e2e/test_examples_e2e.py -q --tb=short -p no:logging -o log_cli=false
```

Expected: semantic-domains 5/5, pos_ui 2 propagation tests, examples 7/7 still green. The one
remaining known failure outside your scope —
`test_entry_relations_playwright.py::test_entry_complex_components_and_variants_persist...`
(`div.relations-section` strict-mode matches 2) — is a **test selector** fix (scope it to the
entry-level section or `.first`), not a code defect; fix only if quick.

### 11.6 Do NOT

- Do **not** re-add `name=`/`:name=` to any sense field.
- Do **not** call `populateSelect` or init Select2 on sense selects (that is what broke them).
- Do **not** register `lexical_unit`/`pronunciations`/`notes` as Alpine sections (Stage 2).
- Do **not** use `_x_dataStack` or `Alpine.reactive()` on component state (§10.2).
- Do **not** touch the serializer, adapter, or `normalize-entry.js` field names.

> **NOTE (post-Stage-1.5):** §11.6's "do not register lexical_unit/pronunciations/notes"
> applied to Stages 1/1.5. **Stage 2 (§12) is exactly the task of registering them.** Follow
> §12, not that line, once you are doing Stage 2.

## 12. Stage 2 — Wire the three simple top-level sections (THE TASK)

Scope (decided 2026-06-26): migrate **lexical-unit, notes, pronunciation** from the legacy
`name=` path to Alpine-owned. **Etymology stays legacy** (separate spiked sub-stage later —
do not touch `_etymology.html` / `etymology-forms.js`). Reversals/annotations are out of scope.

**Why this is mostly mechanical:** all three components already exist
(`alpine/{lexical-unit,pronunciation,notes}.js`) and the adapter already emits their sections
(`alpine-to-serializer.js`). The only gap is that they still serialize via `name=`/legacy
instead of through Alpine. The `sectionReaders` mechanism from §5.2 bridges the
component-key→adapter-key mismatch (`dataKey` ≠ `stateKey`) with no component renaming.

### 12.1 The per-section recipe (apply to each of the three)

Do these **one section per commit**, lowest risk first: **lexical-unit → notes →
pronunciation**. After each, run §12.5 before starting the next.

1. **Verify the adapter output** for the section against the serializer's `create*` function
   (see §12.2/§12.4 — pronunciation has a real bug to fix first). Fix in
   `alpine-to-serializer.js` only.
2. **Add one `sectionReaders` entry** in `merge-harness.js` (the `dataKey`→`stateKey` map):
   ```javascript
   sectionReaders: [
     { selector: '[x-data^="senseTree"]',     dataKey: 'senses', stateKey: 'senses' },          // Stage 1
     { selector: '[x-data^="lexicalUnit"]',   dataKey: 'forms',  stateKey: 'lexicalUnitForms' }, // 12.2
     { selector: '[x-data^="notes"]',         dataKey: 'items',  stateKey: 'notes' },             // 12.3
     { selector: '[x-data^="pronunciation"]', dataKey: 'items',  stateKey: 'pronunciations' }     // 12.4
   ],
   ```
3. **Register the serializer-input key** in `entry_form.html` (the key the serializer reads —
   see per-section notes; this is the `stateKey`'s adapter output key, not the component key):
   ```javascript
   window.MergeHarness.registerAlpineSection('lexical_unit');   // 12.2
   window.MergeHarness.registerAlpineSection('notes');          // 12.3
   window.MergeHarness.registerAlpineSection('pronunciations'); // 12.4
   ```
4. **Remove every `name=`/`:name=`** from the section's partial (and any hidden input that only
   carried a name). This is what makes the section Alpine-owned; the legacy path stops seeing it.
5. **Migrate that section's E2E selectors** from `name*="…"` to stable classes (add classes to
   the partial where missing), exactly as Stage 1 did. Keep changes scoped to the section.
6. **Verify** (§12.5). The section is done only when its tests + the full Stage-1 regression set
   stay green (no cross-section breakage from a mis-registered key).

> The seeding rule differs by section: **lexical-unit is required** → its `init()` already
> seeds one empty row (keep it). **Pronunciation and notes are optional** → do **not** seed;
> a new entry legitimately has zero. Adapter emits `[]` and the serializer omits the element.

### 12.2 Lexical-unit (do first — lowest risk)

- Component `lexicalUnit` exposes `forms`; adapter reads `state.lexicalUnitForms` → emits
  `lexical_unit` **and** `lexicalUnit`. Serializer reads `formData.lexicalUnit || lexical_unit`
  (`lift-xml-serializer.js:77`), so registering **`lexical_unit`** is sufficient.
- Partial: `entry_form_partials/_basic_info.html` (7 `:name=`). Remove them. The headword input
  already has class `.lexical-unit-text`; the lang select `.language-select`. Keep those.
- Adapter already correct (`formsToFlatDict`). No adapter change needed.
- Tests: the headword is exercised by `test_form_submission_e2e.py`, `test_entry_roundtrip_e2e.py`,
  `test_language_codes.py`, and indirectly everywhere via `input.lexical-unit-text` (already
  class-based from Stage 1). Migrate any `name*="lexical_unit"` selectors to `.lexical-unit-text`.

### 12.3 Notes

- Component `notes` exposes `items`; adapter reads `state.notes` and emits
  `[{type, <lang>:text}]` (`alpine-to-serializer.js:223`). **Verify** this matches what the
  serializer's note path consumes (`createNote`/the `formData.notes` loop at
  `lift-xml-serializer.js:71`, keyed by note **type**). If the serializer expects a
  `{type: {lang:text}}` dict rather than an array, adjust the adapter — this is the one place
  to confirm before removing names.
- Partial: `entry_form_partials/_notes.html` (2 `:name=`, keyed `notes.<type>.…`). Remove them;
  add classes (e.g. `.note-type-select`, `.note-text`) and migrate `name*="notes"` selectors.
- No seeding.

### 12.4 Pronunciation (do last of the three — has a real bug + IPA validation)

- **Adapter bug — fix first.** `alpine-to-serializer.js:199` hardcodes
  `out.forms = { en: p.value }`. The serializer's `createPronunciation` emits
  `<form lang="…">` from `pronData.forms` (`lift-xml-serializer.js:105-108`), so IPA currently
  serializes as `lang="en"`. Fix to the pronunciation's **writing system**:
  ```javascript
  if (p.value) { out.forms = {}; out.forms[p.type || 'seh-fonipa'] = p.value; }
  ```
  Confirm the expected IPA writing system against `test_ipa_validation.py` and the LIFT parser
  (it is `seh-fonipa` in this project unless project settings say otherwise).
- **IPA validation must keep working.** `pronunciation.js` has `validateIpa(el)`; ensure the
  template still calls it on input/blur after name removal (it binds via event, not `name`).
- Component `pronunciation` exposes `items`; adapter reads `state.pronunciations`; register
  `pronunciations`.
- Partial: `entry_form_partials/_pronunciations.html` (6 `:name=`, incl. a hidden `type` input
  and `cv_pattern`/`tone` per-lang names). Remove them; the IPA input needs a stable class
  (e.g. `.ipa-input` if the tests use it — check `test_ipa_validation.py`). Migrate selectors.
- No seeding.

### 12.4a VERIFICATION DEFECT (found 2026-06-26) — pronunciation IPA value lost

Stage-2 pronunciation shipped broken: **typed IPA values are silently dropped on save.** The
adapter writing-system fix was correct, but a still-live legacy manager fights Alpine for the
same DOM (the §8.3 "two systems own one DOM" rule, the pronunciation analogue of the
`#sense-template` deleted in Stage 1).

**Root cause (verified):** `pronunciation-forms.js` is still loaded (`entry_form.html:1066`) and
its `PronunciationFormsManager` runs on load. It (a) binds `#add-pronunciation-btn` (so one
click adds a legacy clone *and* an Alpine item), (b) runs `renderExistingPronunciations()` which
does `#pronunciation-container.innerHTML = ''`, and (c) clones `<template id="pronunciation-template">`
(`entry_form.html:376`). Result: a **second, non-reactive `.ipa-input`**; the user fills it,
the value never reaches Alpine `item.value`, and `mergeSync` discards it. Proof: typing into
`.ipa-input` gives `{domValue:"ˈtɛst", stateValue:""}` and saved XML `<pronunciation/>`.

**Fix (do this):**
- `pronunciation-forms.js` also owns **audio upload/generate** (`.upload-audio-btn` /
  `.generate-audio-btn` are still in the Alpine partial), so do **not** just delete it. Instead:
  - Stop the legacy manager from touching pronunciation rows: do **not** bind
    `#add-pronunciation-btn`, do **not** run `renderExistingPronunciations()` /
    `addPronunciation()` / template cloning. Keep only the audio handlers.
  - Best: move the audio handlers into the Alpine `pronunciation.js` (component methods bound
    via `@click`), then remove `pronunciation-forms.js` and the `<script>` tag entirely.
- Delete `<template id="pronunciation-template">` (`entry_form.html:376`).
- **Add a real persistence test** (the missing coverage that let this through): type an IPA
  value into `input.ipa-input`, submit, reload via API, assert the value is present **and**
  serialized under `lang="seh-fonipa"` (NOT `lang="en"`, NOT empty `<pronunciation/>`). Assert
  `document.querySelectorAll('input.ipa-input').length === 1` after adding one pronunciation.

**Also (Stage-1 cleanup debt, lower priority):** `#sense-template`, `#example-template`,
`#subsense-template` (`entry_form.html`) and `multilingual-sense-fields.js` (`:1092`) are still
present. Currently inert (senses work), but the spec said delete them. Remove once confirmed no
legacy code references them.

### 12.5 Verification (run after EACH section; all must stay green)

```bash
npx jest tests/unit/alpine-adapter.test.js          # 31/31
# the section under test:
.venv/bin/python -m pytest tests/e2e/test_pronunciation_forms_playwright.py \
    tests/e2e/test_ipa_validation.py -q --tb=short -p no:logging -o log_cli=false   # (pronunciation)
# full Stage-1 regression — proves no cross-section break from key registration:
.venv/bin/python -m pytest tests/e2e/test_examples_e2e.py tests/e2e/test_gloss_field_e2e.py \
    tests/e2e/test_multisense_entry_e2e.py tests/e2e/test_sense_deletion.py \
    tests/e2e/test_entry_roundtrip_e2e.py tests/e2e/test_form_submission_e2e.py \
    tests/e2e/test_semantic_domains_e2e.py tests/e2e/test_language_codes.py \
    -q --tb=line -p no:logging -o log_cli=false
```

**The cross-section regression is the key gate.** A mis-registered key (e.g. registering
`pronunciation` instead of `pronunciations`, or forgetting the `sectionReaders` entry) makes
the adapter's empty skeleton clobber the section → silent data loss. The round-trip tests catch
it; do not skip them.

### 12.6 Do NOT (Stage 2)

- Do **not** touch etymology (`_etymology.html`, `etymology-forms.js`) — separate sub-stage.
- Do **not** register a section without its matching `sectionReaders` entry (clobber risk).
- Do **not** seed empty rows for pronunciation/notes (they are optional).
- Do **not** re-add `name=` or introduce `populateSelect`/Select2 (Stage-1.5 lessons hold).
- Do **not** change `normalize-entry.js` field names or the senses path.

## 13. Stage 3 — Etymology (the last section; build a new component)

Etymology is the riskiest and the only one with **no existing Alpine component**. It is
currently 100% legacy: `_etymology.html` is an empty shell (`#etymology-container`), and
`EtymologyFormsManager` (`etymology-forms.js`, ~441 lines) builds the whole UI via `innerHTML`
template literals with `name=` attributes, populates the type dropdown with
`rangesLoader.populateSelect` (→ Select2), and has the classic `constructor → async init()`
race. You will **build a new Alpine `etymology` component** and **delete the legacy manager
entirely** (unlike pronunciation, etymology-forms.js owns nothing else — no audio — so it goes
completely, including its `<script>` tag).

**Two lessons from Stages 1.5/2 that this section makes or breaks on:**
- The legacy manager owns `#etymology-container` and binds `#add-etymology-btn`. **Deleting its
  `name=` is not enough** — you must remove the manager and its script, or it will
  `innerHTML`-clobber the Alpine DOM and inject duplicate non-reactive inputs (exactly the
  pronunciation bug, §12.4a). Prove it with an "exactly one of each element" assertion.
- The type dropdown does **not** need Select2. Use the Stage-1.5 pattern: plain
  `<select x-model="etym.type">` + `<template x-for>` options from reactive `rangeData`. This
  dissolves the R6 Select2 risk that made etymology "riskiest" in the original plan.

### 13.1 The data-shape trap (do this first — the adapter currently loses all etymology data)

`alpine-to-serializer.js:219` is `result.etymologies = state.etymologies` — a **raw
passthrough**. The serializer's `createEtymology` (`lift-xml-serializer.js:971`) expects:
```
{ type: "<string>", source: "<string>", form: {lang: text}, gloss: {lang: text} }
```
But `normalizeEtymology` (`normalize-entry.js:228`) produces
`{ type, sourceLanguage, targetLanguage, glossForms:[{id,lang,text}], form:"<string>", protoform, comment }`.
Neither matches. So **two things are mandatory**:

1. **Fix `normalizeEtymology`** to model multilingual fields as arrays with ids (etymology
   `form` and `gloss` are per-language — the legacy `name="etymologies[i][form][lang]"` proves
   it):
   ```javascript
   formForms: dictToForms(raw.form),      // was: form: safeString(raw.form)  ← wrong, drops langs
   glossForms: dictToForms(raw.glosses || raw.gloss),
   source: safeString(raw.source || raw.source_language || raw.sourceLanguage || ''),
   type: safeString(raw.type || ''),
   // keep protoform, comment as strings
   ```
   Verify what the `source` attribute should hold against an existing imported entry (it is the
   LIFT `<etymology source="…">` — typically the source language); preserve whatever the legacy
   `etymologies[i][source]` field captured.
2. **Add `adaptEtymology` to the adapter** (mirrors `adaptSense`), and replace the passthrough:
   ```javascript
   function adaptEtymology(e) {
     var out = { type: e.type || '', source: e.source || '' };
     out.form  = {}; (e.formForms  || []).forEach(function (f) { if (f.lang && f.text) out.form[f.lang]  = f.text; });
     out.gloss = {}; (e.glossForms || []).forEach(function (g) { if (g.lang && g.text) out.gloss[g.lang] = g.text; });
     if (e.protoform) out.protoform = e.protoform;
     if (e.comment)   out.comment   = e.comment;
     return out;
   }
   // ...
   result.etymologies = (state.etymologies || []).map(adaptEtymology);
   ```
   Add adapter unit tests (round-trip: normalize → adapt → `createEtymology` emits
   `<etymology type=… source=…>` with `<form lang>`/`<gloss lang>`). This is the §13 golden test.

### 13.2 Build the Alpine `etymology` component

`alpine/etymology.js` — same shape as `pronunciation.js`/`notes.js`:
- `Alpine.data('etymology', (rawEntry) => { ... })`, reads `normalizeEntry(rawEntry).etymologies`
  into `items`.
- `rangeData['etymology']` + getter `etymologyTypeOptions`, loaded async via the **same
  `loadRanges()` / `_whenRangesLoader()` pattern as `sense-tree.js`** (avoids the constructor race).
- `addItem()` (push a blank etymology: `{id, type:'', source:'', formForms:[], glossForms:[], protoform:'', comment:''}`),
  `removeItem(id)`, and `addRow(list)`/`removeRow(list,id)` for the multilingual form/gloss lists.
- **Do not seed** — etymology is optional (a new entry has none).

### 13.3 Convert `_etymology.html` to an Alpine partial

- Put `x-data="etymology(window.__entryData || {})"` on the section; keep `#add-etymology-btn`
  but wire `@click.prevent="addItem()"`.
- `<template x-for="(etym, ei) in items" :key="etym.id">` renders `.etymology-form-item`s.
- Type: `<select class="etymology-type-select" x-model="etym.type"><template x-for="opt in etymologyTypeOptions" :key="opt.value"><option :value="opt.value" x-text="opt.label"></option></template></select>`.
- form / gloss: nested `<template x-for>` over `etym.formForms` / `etym.glossForms` with
  `x-model` on lang select + text input (the §10.3 pattern). Give them stable classes.
- **No `name=` anywhere.**

### 13.4 Delete the legacy manager + wire the harness

- Delete `app/static/js/etymology-forms.js` **and** its `<script>` tag in `entry_form.html`.
  Grep for any other reference (`EtymologyFormsManager`, `etymology-forms`) and remove.
- `merge-harness.js`: add `{ selector:'[x-data^="etymology"]', dataKey:'items', stateKey:'etymologies' }`.
- `entry_form.html`: `registerAlpineSection('etymologies')`.
- Load `alpine/etymology.js` with the other Alpine modules (before Alpine, like the rest).

### 13.5 Tests

- Migrate `test_etymology.py` selectors: `.etymology-type-select` stays (class kept); it is now
  a plain `<select x-model>`, so `select_option(label='borrowed')` still works (Stage-1.5 proved
  it). Drop any `name=`-based selectors.
- **Add the mandatory round-trip test** (the §12.4a lesson — this is what catches silent loss):
  add an etymology, select a type, type a gloss in one language → `submitForm()` → reload XML via
  API → assert `<etymology type="…" source="…">` with the gloss under `<gloss lang="…">`. Assert
  `document.querySelectorAll('.etymology-form-item').length === 1` and
  `.etymology-type-select` count === 1 (proves the legacy manager is truly gone — no duplicates).

### 13.6 Verification

```bash
npx jest tests/unit/alpine-adapter.test.js          # incl. new adaptEtymology round-trip
.venv/bin/python -m pytest tests/e2e/test_etymology.py -q --tb=short -p no:logging -o log_cli=false
# full regression (no cross-section break):
.venv/bin/python -m pytest tests/e2e/test_examples_e2e.py tests/e2e/test_ipa_validation.py \
    tests/e2e/test_semantic_domains_e2e.py tests/e2e/test_form_submission_e2e.py \
    tests/e2e/test_entry_roundtrip_e2e.py -q --tb=line -p no:logging -o log_cli=false
```

### 13.7 Do NOT

- Do **not** keep `etymology-forms.js` "just for now" — a live legacy manager that owns the
  container is the §12.4a bug. Delete it; move any still-needed behavior into the component.
- Do **not** use `populateSelect`/Select2 for the type dropdown — `x-model` + `x-for` only.
- Do **not** leave the adapter passthrough — without `adaptEtymology`, every etymology saves
  with the wrong/empty shape and the round-trip test will fail (as designed).

### 13.8 After etymology — see §14 (Stage 4 cleanup)

## 14. Stage 4 — Cleanup / partial decommission (THE TASK)

> **Status (2026-06-27): partially done + two findings.**
> Done: `multilingual-sense-fields.js` deleted (it was NOT dead — it self-instantiated on
> DOMContentLoaded and its `document` delegation shadow-fired on the Alpine add-language
> buttons; deletion removed an active double-binding). The four dead clone templates
> (`#sense-/#example-/#subsense-/#pronunciation-template`) deleted; `#reversal-template` kept.
> The §14.4 sanity test added (`tests/e2e/test_all_lift_elements_rendered.py`).
>
> **Finding 1 — systemic delegation conflict (do during porting):** `entry-form.js` still
> registers a `document`-click delegation whose branches (`.remove-sense-btn`, `.move-sense-up/
> down`, `.add-example-btn`, `.remove-example-btn`, `.add-subsense-btn`, `.remove-subsense-btn`,
> `.add-nested-subsense-btn`, `.add-exemplar-language-btn`, `.add-sense-relation-btn`) **share
> class names with Alpine sense-tree buttons** and shadow-fire. Most no-op on missing legacy
> data-attrs, but `.remove-subsense-btn` runs a stray `confirm()` + DOM removal. These retire
> when the remaining legacy sense code is removed during porting (Stage 5) — remove the
> Alpine-owned branches, keep the genuinely-legacy ones (reversal, annotation) until those are
> migrated.
>
> **Finding 2 — illustration regression:** the Alpine `_senses.html` **dropped the illustration
> editing UI** that legacy `_senses_fixed.html` had. `senseTree` carries `illustrations` in
> state but renders no field for it (the §14.4 sanity test flags this; it is currently in that
> test's EXCLUDED set as a tracked gap). Re-add an illustration sub-component when porting.

**Important correction:** the migration is **not** complete. Five sections are Alpine-owned
(senses, lexical-unit, pronunciation, notes, etymology — all in `sectionReaders`), but
**variants, relations, reversals, annotations, and custom-fields are still legacy** (no
`x-data`). Therefore the merge harness, `form-serializer.js`, and the legacy managers for those
sections **must stay**. Stage 4 only removes the **dead artifacts of the five migrated
sections**. Full merge-harness/`form-serializer` deletion is a later stage, after the remaining
sections are migrated.

### 14.1 Delete (each behind a full regression run)

- **`multilingual-sense-fields.js`** + its `<script>` tag (`entry_form.html:1093`). This is not
  just dead — it is an **active conflict** (the §12.4a class). It delegates `click` on
  `.add-definition-language-btn` / `.add-gloss-language-btn` / `.add-note-language-btn` — the
  **same classes the Alpine "Add Language" buttons use** — so each click currently runs both
  Alpine's `addRow` *and* the legacy clone path. After deleting it, verify clicking "Add
  Language" on a definition/gloss adds **exactly one** row (`.language-form` count increases by 1,
  not 2).
- **Legacy clone templates** in `entry_form.html` for migrated sections only:
  `#sense-template` (:426), `#example-template` (:702), `#subsense-template` (:768),
  `#pronunciation-template` (:376). **Keep `#reversal-template` (:892)** — reversals are still
  legacy. Grep each id first to confirm no live JS references it.
- Any now-dead helpers in `entry-form.js` left over from sense/pronunciation cloning
  (e.g. no-op'd `addPronunciation`, `reindexSenses`, subsense innerHTML builders). Delete the
  function bodies and their call sites; do **not** touch the submit/merge orchestration.

### 14.2 Keep (do NOT delete — still in use)

`form-serializer.js`, the merge harness, `entry-form.js`, `pronunciation-forms.js` (now
audio-only — keep the audio handlers), `variant-forms.js`, `relations.js`,
`sense-variant-relations.js`, and `#reversal-template`. These serve the not-yet-migrated
sections through the legacy half of the merge harness.

### 14.3 Verification

After **each** deletion:
```bash
npx jest tests/unit/alpine-adapter.test.js
.venv/bin/python -m pytest tests/e2e/test_range_duplicate_keys.py tests/e2e/test_examples_e2e.py \
    tests/e2e/test_gloss_field_e2e.py tests/e2e/test_multisense_entry_e2e.py \
    tests/e2e/test_pronunciation_forms_playwright.py tests/e2e/test_ipa_validation.py \
    tests/e2e/test_etymology.py tests/e2e/test_form_submission_e2e.py \
    -q --tb=line -p no:logging -o log_cli=false
```
Plus the per-section round-trip probe pattern from §12.4a/§13 (no duplicate elements; data
persists). A deletion that removes a still-referenced template/manager will surface as a
round-trip failure or a JS console error — watch for both.

### 14.4 Sanity test — every LIFT element renders a form field (NEW, required)

Add `tests/e2e/test_all_lift_elements_rendered.py`. The migration moved many fields between
templates/components; nothing currently proves a field wasn't silently dropped. Drive it from
the **registry as source of truth** (`app/data/lift_elements.json` / `LiftElementRegistry`,
28 elements) so it can't drift:

1. Load the registry's `elements`; filter to the **editable leaf elements** (exclude structural
   ones — `entry` root, `trait`, `field`, and anything `category: 'extensibility'`/`'root'`).
   Maintain the inclusion list in the test, derived from the registry, with a comment per
   exclusion so future LIFT elements are consciously triaged.
2. Open `/entries/add`, ensure one sense exists.
3. For each included element assert a rendering exists via a **registry-declared selector map**
   (`lexical-unit → input.lexical-unit-text`, `gloss → .gloss-text`, `definition → .definition-text`,
   `example → .example-item / .example-sentence-text`, `translation → .example-translation-text`,
   `pronunciation → .ipa-input` (after add), `etymology → .etymology-form-item` (after add),
   `note → .note-text` (after add), `grammatical-info → .sense-grammatical-info-select`,
   `semantic-domain → .sense-semantic-domain-select`, `variant`, `relation`, `reversal`,
   `citation`, etc.). Each assertion failure must name the missing element.
4. **Guard test:** assert the included-element count equals the registry's editable-element count,
   so adding a new LIFT element to the registry forces adding it to the map (the test fails until
   someone maps it). This is what makes it a true "all elements" sanity check rather than a
   hand-maintained subset.

## 15. Stage 5 (secondary, after cleanup) — Ranges data-quality & display

Two ranges defects found during verification (2026-06-27). Both are at the ranges layer, separate
from the Alpine form work; do this **after** Stage 4.

### 15.1 Duplicate range-elements — detect, flag, offer cleanup  *(IMPLEMENTED 2026-06-27)*

**Done:** `app/services/ranges_dedup.py` (pure `dedupe_exact_duplicates` / `find_id_conflicts` /
`summarize_duplicates`, unit-tested in `tests/unit/test_ranges_dedup.py`). The ranges API
(`ranges_editor.py` `get_range`/`list_ranges`) **auto-removes exact duplicates** (same id AND
guid) from served data — lossless, and defence-in-depth for the §11.2 render bug. A
`GET /<range_id>/duplicates` endpoint reports `exact_duplicate_count` + `id_conflicts` (same id,
different guid) annotated with `referenced`/`usage_count`. The ranges editor shows a banner:
exact dups as an info note (auto-excluded), id/guid conflicts as a warning with usage guidance
("used by N entries — merge, don't delete" vs "unused — safe to delete a copy"). Integration:
`tests/e2e/test_ranges_duplicates_api.py`.

**Remaining follow-up (not yet built):** an actual one-click *action* in the editor to delete an
unused conflicting copy (by guid, not by id — `delete_range_element` deletes by id and is
ambiguous for conflicts) and a merge flow for referenced conflicts. Conflicts are currently
flagged for manual handling only.

Original plan (for reference):

Real FieldWorks exports contain **duplicate `<range-element>`s with identical `id` *and* identical
`guid`** (a FieldWorks bug; the lexicographer never sees them). They are invisible in the editor
today and cause real damage (they were the trigger for the §11.2 duplicate-`:key` render bug).

- **Detect**: in the ranges editor / ranges service, flag any range containing two elements with
  the same `id` (and separately mark same-`id`+same-`guid`, the FieldWorks defect). Surface a
  per-range warning in the editor UI.
- **Offer cleanup**: for each duplicate, run a **usage scan** across entries (which `value`s are
  actually referenced by any sense/etymology/etc.) and offer one-click deletion of duplicates that
  are **unreferenced**. Referenced duplicates need a merge/reassign flow, not blind deletion —
  do not auto-delete those.
- Note: the §11.2 `:key="opt.key"` fix makes the **UI tolerate** duplicates; this step removes the
  bad data at the source. Complementary, not redundant.

### 15.2 Inconsistent range label language (root-caused)

Bilingual ranges (e.g. "Academic Types" / `domain-type`) display **mixed languages** in the
dropdowns — some options English, some Polish. Root cause (verified against real data):
`pickLabel` (`sense-tree.js`, duplicated in `etymology.js`) resolves a label as
`projectSourceLang → 'en' → firstKey`. With `data-source-language="en"`, a value that has an
English label shows English, but a value with **only** a `pl` label (e.g. `antyk: {pl:"antyk"}`)
falls through to its first key and shows **Polish** — so the language varies per option depending
on which labels each value happens to have. It is not "ignoring lang"; it is an inconsistent
fallback chain, and the **legacy `populateSelect`** (`ranges-loader.js`) has its own label logic,
so entry-level and sense-level selects can disagree too.

**Fix:**
- Pick **one** display language consistently. Recommended: a project **ranges-display-language**
  setting (default = source language); fall back to `value`/`id` when that language is missing —
  **never** to a different language. (Showing the id `antyk` is better than silently switching the
  whole option to Polish mid-list.)
- Apply the *same* resolution in **both** `pickLabel` (sense-tree.js + etymology.js — extract a
  shared helper) **and** the legacy `populateSelect` label path, so all dropdowns agree.
- Test: seed a bilingual range where one value lacks the chosen language; assert every rendered
  option is in the chosen language (or shows the id), never a mix.

## 16. Stage 6 — Port the remaining sections + final decommission (THE TASK)

Goal: move the last legacy sections to Alpine so the **merge harness, `form-serializer.js`, and
the legacy `document`-click delegation can be deleted entirely** — single source of truth.

**Big simplification — read first.** The data model is already done for all of these:
`normalize-entry.js` normalizes `variants`, `relations`, `variantRelations`, `annotations`
(entry level) and `relations`, `variantRelations`, `annotations`, `reversals`, `illustrations`
(sense level); the adapter already emits the **sense-level** ones via `adaptSense` (they ride
the existing `senses` sectionReader). So:

- **Sense-level sections (reversals, illustrations, + any sense annotations/variant-relations UI):**
  no new component, no new `sectionReader`, no `registerAlpineSection`. Just **add UI to the
  `senseTree` template + component** and verify the adapter shape. They serialize through senses.
- **Entry-level sections (variants, variant-relations, entry relations, entry annotations,
  components, subentries):** each is a new self-contained Alpine island = the §12 recipe
  (component + `sectionReader` + `registerAlpineSection` + remove `name=` + verify adapter +
  delete legacy + tests).

### 16.0 The three lessons that this stage lives or dies on (from Stages 2/3/4)

1. **Verify the adapter shape — passthrough is NOT correct** (the etymology trap). The adapter
   currently does `result.variants = state.variants` etc. — raw passthrough. For each section,
   check what the serializer's `create*` consumes (`createVariant` :906, `createRelation` :947,
   `createAnnotation` :220-region) vs what `normalizeX` produces, and add an `adaptX` if they
   differ. Add a golden **unit** test (round-trip normalize→adapt→`serializeEntry`) per section.
2. **Delete the legacy manager AND its `document`-delegation branch — removing `name=` is not
   enough** (the pronunciation §12.4a / multilingual / subsense lessons). A live legacy manager
   that binds shared buttons/containers `innerHTML`-clobbers Alpine and injects duplicate
   non-reactive inputs. After each section: assert **exactly one** of each control and run the
   round-trip probe.
3. **Add a round-trip persistence test per section** (the pronunciation lesson): add an item via
   the real UI → `submitForm()` → reload via API → assert the value is in the saved LIFT XML, and
   assert no duplicate DOM elements. This is the test that actually catches silent loss.

### 16.1 Sense-level: fold reversals + illustrations into `senseTree` (do first)

No wiring changes — senses are already Alpine-owned. Edit `sense-tree.js` + `_senses.html`.

- **Illustrations (the §14 regression — re-add the dropped UI).** `senseTree` already keeps
  `sense.illustrations`. Add `addIllustration(sense)` / `removeIllustration(sense, id)` /
  `addRow` for multilingual labels, and an `x-for` block in `_senses.html` modelled on the legacy
  `_senses_fixed.html` illustration markup (href/upload, preview, multilingual `label`s). The
  audio/file-upload endpoints are server-side and unchanged — wire the upload button via an
  Alpine `@click` calling the existing endpoint, not the deleted legacy cloner. Verify
  `adaptSense` emits `illustrations` in the shape `createIllustration`/the serializer expects.
  Move `illustration` from EXCLUDED back to **MAPPED** in `test_all_lift_elements_rendered.py`
  and add a round-trip test (the user's data has none, but it must round-trip when present).
- **Reversals.** `sense.reversals` exists in state. Add `addReversal`/`removeReversal` + an
  `x-for` block; delete the legacy `#reversal-template` and the `entry-form.js` `.add-reversal-btn`
  / `.remove-reversal-btn` delegation + `addReversal`/`reindexReversals` functions. Verify the
  adapter/`createReversal` shape. Move `reversal` from EXCLUDED to MAPPED in the §14.4 test.
- While here, confirm **sense-level annotations / variant-relations** have edit UI (state exists;
  UI may not). Add `x-for` blocks if missing, or document them EXCLUDED with a reason.

### 16.2 Entry-level islands (each = the §12 recipe), low risk → high

For each: build `alpine/<name>.js` (`Alpine.data(...)`, reads `normalizeEntry(...)` slice into
`items`, `addItem`/`removeItem` [+ `addRow` for multilingual]); add a `sectionReaders` entry
(`{ selector:'[x-data^="<name>"]', dataKey:'items', stateKey:'<adapterKey>' }`); convert the
partial to `x-data` + `x-for`, remove all `name=`; `registerAlpineSection('<adapterKey>')`;
verify/ fix the adapter shape; delete the legacy manager + its `<script>` tag + its delegation
branch; migrate that section's tests; round-trip test.

1. **Annotations** — `_*` entry annotations (`.annotations-section-entry`); legacy delegation
   `.add-annotation-btn`/`.remove-annotation-btn` (+ `.remove-annotation-language-btn`). stateKey
   `annotations`. Simplest; do first.
2. **Entry relations** — `_relations.html` (`.relations-section`, `#add-relation-btn`),
   `relations.js`. stateKey `relations`. **Reuse the sense-relations pattern already in
   `senseTree`** (type select via `x-model`+`x-for` from `rangeData['lexical-relation']`, ref
   input). Mind the §11.2 `:key="opt.key"` rule for the type dropdown.
3. **Variants + variant-relations** — `_variants.html` (`.variants-section`, `#add-variant-btn`,
   `variant-forms.js`) and `_direct_variants.html` (`.direct-variants-section`,
   `sense-variant-relations.js`). stateKeys `variants` / `variant_relations`. Variant type uses a
   ranges dropdown → same `:key="opt.key"` rule. Riskier (two managers, Select2-ish) — spike the
   dropdown first.
4. **Components / subentries** — `_components.html`, `_subentries.html`. Port **only if they have
   real edit UI**; if display-only, document EXCLUDED. **Custom fields (`_custom_fields.html`)
   are display-only (`{% if entry.custom_fields %}`, no add control) — do NOT port; leave as-is.**

### 16.3 Final decommission (only after §16.1–16.2 are all green)

> **Status (2026-06-27): Phase A + delegation cleanup DONE; form-serializer/merge-harness removal DEFERRED.**
> Done: deleted dead managers (`relations.js`, `variant-forms.js`, `direct-variants.js`) + the
> dead `addAnnotation` cluster + dead manager-inits in `entry-form-init.js`; deleted
> `_senses_fixed.html`; and **removed the entire conflicting `sensesContainer` click-delegation
> block** (`entry-form.js`, was lines 723–1077) — every branch was Alpine-owned, so the §14
> Finding-1 conflicts (incl. the stray `remove-subsense` `confirm()`) are gone. Verified: 32
> sense e2e passed. The legacy `addExample`/`addSubsense`/`addReversal`/`reindexSenses` functions
> it called are now fully unreferenced — delete in the final pass.
>
> **DEFERRED — `form-serializer.js` + merge-harness removal (do as a dedicated, fresh pass):**
> Not safe to rush. Two concrete risks: (1) **silent data loss** — `_custom_fields.html` carries
> `name=` attributes, so re-saving an entry that HAS custom fields currently preserves them via
> form-serializer; removing it without explicitly capturing custom fields drops them. (2) The
> `_basic_info` scalars (id, citation_form, status, morph_type, grammatical_info.part_of_speech,
> homograph_number) are still serialized by form-serializer's `name`-path parsing — that must be
> replicated (capture-at-submit) first. Required before deletion: a round-trip test that creates
> an entry WITH custom fields + all scalars, saves, reloads, and asserts none are dropped — then
> swap form-serializer for direct scalar+custom-field capture, then delete it and the merge
> harness's legacy half. This is the only remaining item; everything else is Alpine-owned.



When `extractAlpineState` supplies **every** data section and no `name=`-bearing inputs remain:

- Delete the **legacy `document`-click delegation block** in `entry-form.js` (the §14 Finding-1
  branches) and the now-dead `addSubsense`/`addExample`/`addReversal`/`reindex*` functions.
  Keep only genuinely non-section handlers.
- Delete `form-serializer.js` + `form-serializer-worker.js` (re-measure: a single
  `structuredClone`+adapter on the main thread is likely fast enough — keep the worker only if
  profiling says so), `variant-forms.js`, `relations.js`, `sense-variant-relations.js`,
  `pronunciation-forms.js` *only after* moving its audio handlers into `pronunciation.js`.
- Delete the **merge harness** legacy half: submit/live-preview read Alpine state directly via
  `MergeHarness.extractAlpineState()` → adapter → `serializeEntry`; drop the `legacyData` merge.
  (Keep `extractAlpineState` + the adapter — rename out of "merge harness" once it's the only path.)
- Delete `#reversal-template` and any remaining clone templates.

### 16.4 Verification (per section + final)

```bash
npx jest tests/unit/alpine-adapter.test.js          # + new adaptX golden tests
.venv/bin/python -m pytest tests/e2e/test_all_lift_elements_rendered.py \
    tests/e2e/test_range_duplicate_keys.py tests/e2e/test_ranges_duplicates_api.py \
    tests/e2e/test_examples_e2e.py tests/e2e/test_etymology.py \
    tests/e2e/test_form_submission_e2e.py tests/e2e/test_entry_roundtrip_e2e.py \
    -q --tb=line -p no:logging -o log_cli=false
```
Per section, also: the section's own E2E (migrated to class selectors) + a round-trip probe
(real UI → save → reload → assert XML + exactly-one-of-each control). **The §14.4 sanity test is
the completion gate** — every element must end in MAPPED (illustration + reversal moved back from
EXCLUDED) except the documented display-only ones. When it's all green with the merge harness and
`form-serializer.js` deleted, the migration is done.

### 16.5 Do NOT

- Do **not** trust adapter passthrough — verify each `adaptX` against the serializer (lesson 1).
- Do **not** leave a legacy manager loaded "just for now" — delete it with its delegation (lesson 2).
- Do **not** key any range/option `x-for` on `opt.value` — use `opt.key` (§11.2).
- Do **not** delete the merge harness / `form-serializer.js` until *every* section is Alpine-owned
  and the §14.4 sanity test has no non-display-only EXCLUDED elements.
