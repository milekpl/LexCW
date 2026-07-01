# Entry Edit History & Change Analytics — Feature Specification

**Status:** Draft | **Author:** Reasonix Code, 2026-06-28
**Goal:** Give editors visibility into *what changed, when, and by whom* — both
per-entry (a timeline of individual revisions) and across the dictionary (aggregate
stats for a given timespan: what kinds of changes were made, by whom, how often).

---

## 1. Design decisions (made upfront to constrain scope)

### 1.1 Storage: PostgreSQL, not BaseX

BaseX is an XML-native database and *could* store revision snapshots as separate
XML documents inside a `revisions/` collection.  But:

- The current save path already uses PostgreSQL for user/auth/project settings.
  Adding a `revisions` table there is low-friction.
- Diff computation on structured JSON (the serialized Alpine state) is simpler and
  faster than XML diff, especially for field-level attribution.
- Aggregate queries (stats dashboard) are trivially SQL.  XQuery aggregation is
  possible but less familiar and harder to maintain.

**Decision:** a single `entry_revisions` table in PostgreSQL storing the
serializer-ready JSON snapshot + a computed `change_report` (field-level diff) at
save time.  The JSON is the canonical state; the change report is a cache for fast
display.  Full XML is NOT stored — it occupies 5–10× the space of the JSON (LIFT
is verbose), and the serializer can always re-generate it from the snapshot if
needed for a "restore this revision" feature (future).

### 1.2 Granularity: field-level, not character-level

Tracking individual keystrokes is impractical (too much data, auto-save floods it)
and not useful for editors.  Every **explicit save** (user clicks Save, or a
committed form submission) produces ONE revision.  If the user opens the form and
closes without saving, no revision is created.

The diff between two consecutive JSON snapshots is computed **field by field**
using a recursive key comparison.  The result is a structured change report:

| Field path | Kind | Before (summary) | After (summary) |
|---|---|---|---|
| `lexical_unit.en` | modified | "run" | "run (verb)" |
| `senses[0].gloss.en` | modified | "move quickly" | "move swiftly on foot" |
| `senses[1]` | added | — | {definition: "operate a machine"} |
| `senses[2].examples[0]` | removed | {sentence: "he runs daily"} | — |

Character-level diff within a text field is out of scope for v1; the change report
shows the full before/after value for modified fields.  A future v2 could add a
per-field inline diff (unified-diff-style).

### 1.3 Scope: entries only, not senses or ranges

Senses and examples are part of the entry JSON — they are covered.  Ranges,
project settings, and corpus data are NOT covered by this feature.  Ranges have
their own CRUD history (if needed, a separate project).

### 1.4 Retention: indefinite, but purge-old-revisions is a future admin feature

No auto-deletion in v1.  A future admin panel could add "delete revisions older
than N days" and "delete revisions for entries that no longer exist."

---

## 2. Data model (PostgreSQL)

### 2.1 `entry_revisions` table

```sql
CREATE TABLE entry_revisions (
    id              SERIAL PRIMARY KEY,
    entry_id        TEXT NOT NULL,          -- LIFT XML entry id (e.g. "abc-123")
    revision_number INTEGER NOT NULL,       -- monotonically increasing per entry (1,2,3…)
    timestamp_utc   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id         TEXT,                   -- future: FK to users table; NULL for pre-auth
    snapshot        JSONB NOT NULL,         -- full Alpine-to-serializer JSON at save time
    change_report   JSONB NOT NULL,         -- structured diff vs previous revision
                                            --   [{field_path, kind, before, after}, …]
    created_by      TEXT,                   -- username / editor identity (denormalized)
    CONSTRAINT uq_entry_rev UNIQUE (entry_id, revision_number)
);

CREATE INDEX idx_entry_revisions_entry ON entry_revisions(entry_id, revision_number);
CREATE INDEX idx_entry_revisions_ts    ON entry_revisions(timestamp_utc);
```

**`snapshot`** is the output of `alpineStateToSerializerInput(alpineState)` — a
JSON object with `lexical_unit`, `senses`, `pronunciations`, `etymologies`,
`variants`, `relations`, `variant_relations`, `annotations`, `notes`,
`custom_fields`, `citation`, `status`, `grammatical_info`, `morph_type`,
`date_created`, `date_modified`, `id`, `guid`.  This shape is already the
contract used by `serializeEntry` → `create_entry`/`update_entry`, so every
save site naturally produces it.

**`change_report`** is computed by a new pure function
`computeChangeReport(previousSnapshot, currentSnapshot)` (see §3).  It is
NULL for revision 1 (first save — no previous snapshot to compare against).

### 2.2 Why not store the diff only?

Storing the full snapshot (≈2–50 KiB of JSON per revision, depending on entry
size) is cheap with JSONB.  A typical dictionary of 10 000 entries averaging 2
revisions each costs ≈ 200–500 MiB — negligible for a dedicated server.  The full
snapshot enables:

- **Restore** a previous revision in a future "rollback" feature.
- **Recompute** diffs if the diff algorithm changes (the snapshot is always the
  ground truth).
- **Audit** exactly what was persisted, independent of the diff logic.

### 2.3 Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| Store XML in BaseX | 5–10× space; XML diff is harder; aggregate SQL queries impossible |
| Store only change_report, not full snapshot | Cannot recompute diffs or restore |
| Store per-key auto-save deltas | Too noisy; editors want "committed" saves |
| Use Git-like object storage | Overengineered for a dictionary; JSONB handles it |
| Store the Alpine reactive state (arrays-of-objects) | Adapter transform is lossy; serializer JSON is the canonical save contract |

---

## 3. Change-report computation (Python, server-side)

### 3.1 Algorithm

```python
def compute_change_report(prev: dict | None, curr: dict) -> list[dict]:
    """Return a list of {field_path, kind, before, after} objects."""
    if prev is None:
        return []  # first revision — no diff
    return _diff_dicts(prev, curr, path="")
```

`_diff_dicts` recursively walks two dicts/arrays and emits a change for every key:

- **Dicts:** iterate union of keys.  If a key is in both, recurse.  If only in
  `curr`, emit `kind="added"`.  If only in `prev`, emit `kind="removed"`.
- **Lists of objects with stable `id`:** match by `id`; recurse into matched
  pairs.  Unmatched `curr` items are `added`; unmatched `prev` items are
  `removed`.  **Stable-id matching is opt-in per field** (see §3.2).
- **Lists of primitives:** emit the whole before/after list if they differ
  (no granular per-element add/remove — string lists are short).
- **Scalars:** compare.  If different, emit `kind="modified"` with `before` and
  `after` values.
- **Depth limit:** 6 levels.  Beyond that, treat the subtree as a scalar.

### 3.2 Stable-id field map

The following fields in the serializer JSON contain objects with stable `id` keys
that should be matched for per-element diffs:

| JSON path | Match key |
|---|---|
| `senses` | `id` |
| `senses[*].subsenses` | `id` |
| `senses[*].examples` | `id` |
| `senses[*].examples[*].translations` | `lang` (not a generated id — language code is the stable key) |
| `senses[*].relations` | `ref` (ref+type are the compound identity) |
| `senses[*].reversals` | `type` |
| `pronunciations` | `type` (not id — writing-system code) |
| `etymologies` | composite of `type` + `source` |
| `variants` | `ref` |
| `relations` | `ref` + `type` |
| `annotations` | `name` + `who` |
| `notes` | dict key (the note type) |

These match keys are stored in a static `REVISION_ID_FIELDS` map so the diff
function is data-driven, not hardcoded.

### 3.3 Summary strings

For display purposes (e.g., "Modified gloss in Sense 1"), each change entry also
receives a human-readable `summary`:

```python
_summaries = {
    "lexical_unit": lambda c: "Changed headword",
    "senses[*].gloss": lambda c: f"Changed gloss in {_sense_label(c)}",
    "senses[*].definition": lambda c: f"Changed definition in {_sense_label(c)}",
    "senses[*].subsenses[*].gloss": lambda c: f"Changed subsense gloss",
    "senses": lambda c: _counted(c, "sense"),
    "senses[*].examples": lambda c: _counted(c, "example"),
    ...
}
```

Where `_counted` produces "Added 1 example", "Removed 2 senses", etc. for
add/remove of list items.

---

## 4. Integration points (where revision data is created)

### 4.1 Save path

`entry-form.js` already produces the serializer-ready JSON from Alpine state (via
`MergeHarness.buildSerializerInput`).  The existing save flow is:

```
Alpine state → extractAlpineState() → alpineStateToSerializerInput() →
JSON → POST /api/xml/entries → serializeEntry → create_entry / update_entry
```

The hook is **after** `alpineStateToSerializerInput` and **before** the POST.
On the client, after `buildSerializerInput()`, the JSON is included in the POST
payload.  The server already receives the full snapshot — we just need to store it.

### 4.2 Server-side: `EntryRevisionService`

A new Python service (`app/services/entry_revision_service.py`) that:

1. **`save_revision(entry_id, snapshot_json, user_id=None)`**  
   - Fetch the previous snapshot (highest `revision_number` for this `entry_id`).
   - Compute `change_report` via `compute_change_report(prev, snapshot_json)`.
   - `INSERT INTO entry_revisions (...)`.
   - Return the new `revision_number`.

2. Called from the existing `save_entry` / `update_entry` flow in
   `xml_entry_service.py` (or a Flask `@after_request` hook for the XML entry
   endpoint).

### 4.3 Concurrency

Two editors saving the same entry at nearly the same time produce two revisions
with consecutive numbers.  `INSERT … (entry_id, revision_number)` with a
`SELECT MAX(revision_number) + 1 FOR UPDATE` row-lock + `ON CONFLICT` retry
handles this.  The first write wins; the second retries with a new number.
Since saves are infrequent (seconds apart at worst), optimistic locking is fine.

---

## 5. API endpoints

### 5.1 Per-entry revision history

```
GET /api/entries/{entry_id}/revisions
```

Returns a paginated list of revisions for one entry, newest first:

```json
{
  "entry_id": "abc-123",
  "revisions": [
    {
      "revision_number": 5,
      "timestamp_utc": "2026-06-28T14:00:00Z",
      "created_by": "editor@example.com",
      "change_count": 3,
      "summary_lines": [
        "Changed gloss in Sense 1",
        "Added 1 example to Sense 1",
        "Modified lexical_unit"
      ]
    },
    ...
  ],
  "total": 12
}
```

Query parameter `?page=1&per_page=20` for pagination.

Only `change_count` and `summary_lines` are returned in the list view — the full
`change_report` with before/after values is behind a detail endpoint (below) to
keep the list payload small.

### 5.2 Single revision detail

```
GET /api/entries/{entry_id}/revisions/{revision_number}
```

Returns the full `change_report` with before/after values, plus the `snapshot`
JSON (for a future restore button).  The before/after values are **truncated**
for long text fields (over 200 chars) to avoid payload bloat; a `truncated: true`
flag + a separate `GET …/field?path=senses[0].definition.en` endpoint returns the
full value if needed.

### 5.3 Stats / aggregate endpoint

```
GET /api/revisions/stats?from=2026-06-01&to=2026-06-28
```

Parameters:
- `from`, `to` (ISO dates, required) — timespan
- `user_id` (optional) — filter by user
- `entry_id` (optional) — filter by entry
- `granularity` (optional) — `"day"` (default) or `"week"`

Returns:

```json
{
  "timespan": {"from": "2026-06-01", "to": "2026-06-28"},
  "total_revisions": 342,
  "unique_entries_touched": 87,
  "unique_users": 3,
  "by_field": {
    "lexical_unit": {"modified": 45},
    "senses.gloss": {"modified": 120},
    "senses.definition": {"modified": 98},
    "senses.examples": {"added": 34, "removed": 12, "modified": 67},
    "senses": {"added": 23, "removed": 5},
    "pronunciations": {"added": 15, "modified": 8, "removed": 2},
    "relations": {"added": 41, "removed": 9},
    "annotations": {"added": 56, "modified": 18, "removed": 3},
    "...": {}
  },
  "timeline": [
    {"date": "2026-06-01", "count": 12},
    {"date": "2026-06-02", "count": 8},
    ...
  ],
  "top_edited_entries": [
    {"entry_id": "abc-123", "headword": "run", "revisions": 15},
    ...
  ],
  "top_editors": [
    {"user_id": "editor@example.com", "revisions": 200},
    ...
  ]
}
```

The `by_field` map uses dotted-field-path keys (e.g., `senses.gloss`) aggregated
from the `change_report` JSONB using a single SQL query:

```sql
SELECT
  change_entry->>'field_path' AS field_path,
  change_entry->>'kind' AS kind,
  COUNT(*) AS cnt
FROM entry_revisions,
     jsonb_array_elements(change_report) AS change_entry
WHERE timestamp_utc BETWEEN :from AND :to
GROUP BY 1, 2
ORDER BY cnt DESC;
```

### 5.4 Compare two revisions (future v2)

```
GET /api/entries/{entry_id}/revisions/compare?left=3&right=5
```

Returns a side-by-side diff between any two revisions.  Out of scope for v1 but
the snapshot model makes this trivial to add later.

---

## 6. UI — entry-level revision timeline

### 6.1 Placement

A collapsible "Revision History" section on the entry edit page, below the
existing "Dictionary Preview" card and above "Show/Hide XML Preview".  Collapsed
by default.  When expanded, loads revisions via the API.

### 6.2 Visual design (rough wireframe)

```
┌─ Revision History (last 12 changes) ────────────────────────[collapse]─┐
│                                                                        │
│  #5  Jun 28 14:00  by editor@example.com                              │
│      • Changed gloss in Sense 1     "move quickly" → "move swiftly …" │
│      • Added 1 example to Sense 1   ◀ click to expand                 │
│      • Modified lexical_unit        "run" → "run (verb)"              │
│                                                                        │
│  #4  Jun 27 09:30  by editor@example.com                              │
│      • Added 1 sense                "Sense 2"                         │
│      • Removed annotation           "review-status: pending"          │
│                                                                        │
│  #3  Jun 26 16:15  by assistant@example.com                           │
│      • Changed definition in Sense 1                                   │
│      • Added 1 relation             synonym → "sprint"                │
│                                                                        │
│  :                                                                     │
│                                                                        │
│                                    [Load more]                         │
└────────────────────────────────────────────────────────────────────────┘
```

Each change line is colour-coded: green for added, red for removed, amber for
modified.  Long "after" values are truncated with a "… more" toggle.

### 6.3 REST interaction

- The component fetches `GET /api/entries/{id}/revisions?page=1&per_page=20` on
  expand.
- "Load more" fetches the next page.
- Clicking a revision number or summary line fetches the detail
  `GET …/revisions/{n}` and expands an inline detail panel showing the full
  before/after values for each field change.

### 6.4 Technologies

Plain fetch + vanilla JS (or Alpine.js since the project already uses it).
No React/Vue/Svelte dependency.  A simple Alpine component
`Alpine.data('revisionHistory')` that loads and renders the timeline.

---

## 7. UI — change analytics dashboard

### 7.1 Placement

A new page at `/dashboard/analytics` (linked from the navigation under "Tools"
or "Workbench") — or a tab on the existing Data Quality Dashboard.

### 7.2 Components

1. **Date range picker** (from / to).  Defaults: last 7 days.
2. **Summary cards** row: total revisions, unique entries touched, unique editors.
3. **Timeline chart** — bar chart showing revisions per day/week.  Built with
   Chart.js (already in the project's static deps?  If not, a simple HTML table
   or CSS bar chart is fine for v1).
4. **By-field breakdown** — table with field path, added/modified/removed counts,
   sorted by total changes descending.
5. **Top edited entries** — table with headword, revision count, last-edited date.
   Click navigates to that entry's edit page.
6. **Top editors** — table with user name, revision count, last-active date.

### 7.3 User filtering

Every stat component links to a filtered view: clicking an editor name navigates
to `?user_id=…`, adding that filter to all queries until cleared.

---

## 8. Implementation plan (6 steps, ~2–3 days of work)

### Step 1 — Database migration + `EntryRevisionService`
- Create `entry_revisions` table (Alembic migration).
- Implement `EntryRevisionService.save_revision()` with snapshot storage.
- Implement `compute_change_report()` + stable-id field map.
- Unit tests for the diff algorithm (golden fixtures: add sense, modify gloss,
  remove example, etc.).

### Step 2 — Hook into save path
- Wire `save_revision()` into `xml_entry_service.update_entry()` (and
  `create_entry()` for the initial revision 1).
- The existing save path already receives the serializer JSON; pass it directly.
- Concurency test: two parallel saves for the same entry.

### Step 3 — API endpoints
- `GET /api/entries/{entry_id}/revisions` (paginated list)
- `GET /api/entries/{entry_id}/revisions/{n}` (detail)
- `GET /api/revisions/stats` (aggregate)
- Integration tests for each.

### Step 4 — Revision timeline UI
- Alpine component `revisionHistory` on the edit page.
- Fetch, render, colour-code, load-more.
- Detail inline expansion.

### Step 5 — Analytics dashboard
- New route `/dashboard/analytics`.
- Date picker, summary cards, timeline chart, by-field table, top entries/editors.
- Filtering by user.

### Step 6 — Polish + edge cases
- Handle very large entries (100+ senses → change_report may be large; paginate
  the detail view?).
- Handle deleted entries (revisions remain but the entry no longer exists — show
  "entry deleted" badge).
- Handle first-time saves (revision 1 has `change_report: null` — display
  "Initial version").
- Keyboard shortcut to toggle revision panel.

---

## 9. Out of scope (explicitly deferred)

- **Restore/revert** a previous revision — needs a "restore this version" button
  + confirmation modal.  The snapshot storage makes this a small addition later.
- **Side-by-side diff view** — `GET …/revisions/compare`.
- **Per-field inline diff** (character-level) — truncate to before/after in v1.
- **Branch/merge** — no branching model; linear revision history per entry.
- **Sense-level history** — senses are nested inside the entry snapshot.  If
  "Sense 3" is removed and a new "Sense 3" is added later, they are unrelated
  (the `id` differs).  The change report captures this correctly at the entry
  level.
- **Email notifications** — "entry X was changed by Y" triggers.
- **Approval workflows** — change must be reviewed before publishing.  The
  revision history is a foundation for this but the workflow itself is separate.
- **Auto-save revisions** — every auto-save event would flood the table with
  partial edits.  Only deliberate form submissions produce revisions.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| JSON snapshots too large (100+ KB for huge entries) | JSONB compresses well; test with a 50-sense entry before shipping |
| Diff computation slow for complex entries | When `change_report` is NULL (no meaningful diff) for entries with >100 fields, skip diff and store a summary count only; compute on read if needed |
| Database migration on a live server locks the table | `CREATE TABLE IF NOT EXISTS` is instantaneous; no migration of existing data needed |
| Revision numbers drift under concurrent saves | `FOR UPDATE` + retry loop; test with parallel saves |
| `DELETE entry` removes the record but revisions persist | OK — revisions show "entry no longer exists" without a link; future admin cleanup can purge orphaned revisions |
