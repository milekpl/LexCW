# Alpine.js Entry Form Refactor Specification

**Status:** Revised after review | **Reviewer:** Claude Opus 4.8

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

### 5.2 Serialization to XML

`$data` is a **reactive Proxy**, not a plain object. `JSON.stringify($data)` may include
Alpine internals, and passing it to the Web Worker (`form-serializer-worker.js`, reached
via `serializeFormToJSONSafe`) will throw a DataCloneError or drop data. Extract a plain
object first:

```javascript
x-on:submit.prevent="
  const plain = structuredClone(Alpine.raw($data));   // detach from the Proxy
  const input = alpineStateToSerializerInput(plain);  // §5.0 adapter
  const xml = await window.xmlSerializer.serializeEntry(input);
  // ... existing submit/post path, CSRF, progress bar, etc.
"
```

The serializer's **XML-generation** logic is unchanged; the **adapter** (§5.0) is the new
code. During migration, sections not yet on Alpine still serialize via `form-serializer.js`;
the submit handler must merge both sources into one serializer input (see §7).

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
