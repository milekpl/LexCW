# Spec: Duplicate Detection

**Based on**: `specification.md §3.4.1`, `specs/advanced_search/tasks.md §2.1`  
**Status**: Draft

---

## 1. Goal

Detect potential duplicate entries in the dictionary so editors can review, merge, or dismiss them. Duplicates waste curation effort and confuse downstream consumers (exports, word sketches, corpus queries).

---

## 2. What Counts as a Duplicate

Four detection modes, from strict to fuzzy:

| Mode | Match Criteria | Example |
|------|---------------|---------|
| **Exact ID** | `entry/@id` matches an existing entry | Same GUID re-imported |
| **Exact headword** | `lexical-unit/form/text` identical after normalisation **AND POS matches or one side lacks POS** | "well (n)" vs "well (n)", "well (n)" vs "well (no POS)" |
| **Near headword** | Levenshtein distance ≤ threshold (default 2) on normalised headword + citation form **AND POS constraint per above** | "colour" vs "color" (both "n") |
| **Fuzzy sense overlap** | Same headword AND ≥1 sense with identical definition/gloss text **AND POS constraint per above** | Two entries for "bank (n)" both listing "financial institution" |

Detection runs against a **configurable field set**: lexical_unit, citation_form, definition, gloss, pronunciation. Each field can be weighted or toggled.

---

## 3. Architecture

### 3.1 Service Layer — `DictionaryService.get_duplicate_candidates()`

New method. Does NOT run at search time — only when the duplicate detection tool is opened.

```
Input:
  - thresholds: Dict[str, float]  (optional overrides)
  - fields: List[str]              (optional field subset)
  - mode: str                      ("all" | "exact" | "near" | "fuzzy")
  - pos: str | None                (optional POS filter — e.g. "n" only matches entries with that POS; entries without POS match everything)

Output:
  - groups: List[DuplicateGroup]
    where DuplicateGroup = {
      id: str,
      confidence: float,           # 0.0–1.0
      mode: str,                   # which mode triggered
      entries: List[{
        entry_id: str,
        headword: str,
        citation_form: str,
        senses_count: int,
        pos: str,
        match_fields: List[str],   # which fields matched
      }],
      merge_suggestion: str,       # "keep_newer" | "keep_complete" | "manual"
    }
  - total_candidates: int
```

### 3.2 Detection Algorithms

#### 3.2.0 Headword Normalisation (applied before all string comparisons)

Before any comparison, headwords pass through a **normalisation pipeline** that generates one or more normalized variants, ensuring that entries differing only in grammatical notation, punctuation, or compound style are flagged.

**Normalisation steps**:

1. **Parenthetical Expansion**: If the headword contains parentheses, generate **two string variants**:
   - **Stripped variant**: Remove parentheses and the text inside them (e.g., `a little (bit)` $\rightarrow$ `a little`). Regex: `\s*\([^)]*\)\s*`.
   - **Retained variant**: Remove the parentheses but keep the text inside them, replacing parentheses with spaces and collapsing extra whitespace (e.g., `a little (bit)` $\rightarrow$ `a little bit`).
   If no parentheses exist, the single original string is the only variant.
   
2. **Strip placeholders**: For each variant, remove any of the following tokens (case-insensitive, whole-word match) from the string, along with any adjoining pipe `|` characters and whitespace:
   - Default set: `sth`, `sb`, `sth/sb`, `sb/sth` (lexicographic shorthand for "something" and "somebody").

3. **Strip articles**: Remove leading `a `, `an `, `the ` (case-insensitive).

4. **Collapse whitespace**: Trim and reduce internal whitespace runs to a single space.

5. **Lowercase**: Fold all characters to lower case.

6. **Compound Normalisation (Optional Variant)**: For compound duplicate detection, generate an additional variant by stripping all hyphens and spaces completely (e.g., `log-in` $\rightarrow$ `login`, `log in` $\rightarrow$ `login`). If two entries share this compound-normalised form, they are flagged as compound duplicates.

**Project-level customisation:**

The placeholder list and article list are stored in `project_settings`:

```sql
ALTER TABLE project_settings
  ADD COLUMN duplicate_placeholders TEXT DEFAULT 'sth,sb,sth/sb,sb/sth',
  ADD COLUMN duplicate_articles TEXT DEFAULT 'a,an,the';
```

Admins can edit these in the Settings page to add language-specific placeholders.

**Examples of Normalised Sets:**

| Raw headword | Normalised Variant Set | Rationale |
|-------------|-------------------------|-----------|
| `sth/sb` | `{""}` (empty — excluded) | Placeholder-only entries are excluded from detection |
| `sth to do` | `{"to do"}` | Leading placeholder stripped |
| `tell sb sth` | `{"tell"}` | Both placeholders stripped |
| `cat (animal)` | `{"cat"}` | Parenthetical stripped |
| `a little (bit)` | `{"a little", "a little bit"}` | Parenthetical expansion: produces both stripped and retained forms |
| `log-in` | `{"log-in", "login"}` | Standard normalization keeps hyphen, compound variant strips it |
| `log in` | `{"log in", "login"}` | Standard normalization keeps space, compound variant strips it |
| `give sth to sb` | `{"give to"}` | Placeholders stripped, "to" retained |


#### 3.2.1 XQuery — Exact headword duplicates (fast path)

Run this first — it's the most common case and the cheapest:

```xquery
let $entries := collection('DB')//entry
let $headwords := $entries/lexical-unit/form/text/string() ! lower-case(.)
let $dupes := $headwords[index-of($headwords, .)[2]]
return $dupes
```

Implementation detail: use `functx:non-distinct-values()` from the installed FunctX library.

**POS constraint**: When `pos` is specified, filter candidate pairs to only those where both entries share the given POS (or at least one has no POS — no-POS entries match everything). POS comparison is done in Python after the XQuery fetch, since it requires comparing pairs.

#### 3.2.2 Python — Near-headword (Levenshtein)

For entries not caught by exact matching, run Levenshtein distance in Python (XQuery has no Levenshtein built-in):

1. Fetch all headword + ID pairs from BaseX (one query, ~O(n)), applying normalisation in Python after fetch
2. Build a sorted index of normalised headwords
3. Sliding window comparison: for each word, compare against neighbours within edit-distance threshold
4. Filter out already-exact-matched pairs
5. Return candidate pairs

Reference implementation pattern: `ipa_service.py:280` already has `levenshtein_distance()`. Use `Levenshtein` PyPI package if available, else the inline implementation.

#### 3.2.3 Python — Fuzzy sense overlap

1. Fetch entries where headword matches exactly (already known from 3.2.1) or near-match (from 3.2.2).
2. For each candidate pair, compare sense definitions/glosses using:
   - Token overlap (Jaccard similarity) on definition text.
   - Threshold: ≥0.7 Jaccard on any one sense pair.
3. Score boosts confidence (confidence $\ge 0.9$ if Jaccard similarity $\ge 0.7$).

#### 3.2.4 Corpus Frequency Integration (Tiebreaking & Canonical Forms)

To make smart merge suggestions (i.e. which form to keep as the canonical target), we integrate the Lucene corpus index.
1. When presenting duplicate candidates (e.g. `login` vs `log in` vs `log-in`), query the Lucene corpus index API (`/api/corpus/count` or existing client count function) for the occurrence frequency of each headword form in the corpus.
2. The candidate with the highest corpus frequency is flagged as the recommended canonical target (`merge_suggestion` is set to `"keep_most_frequent"`, pointing to this form).
3. If corpus service is unavailable, fall back to `"keep_complete"` (the entry with the most populated fields / senses).

#### 3.2.5 Cross-Field Duplication: Examples vs. Subentries

To find redundant example sentences that duplicate separate dictionary subentries (or vice versa):
1. **Scope**: Compare all lexical entries whose primary morph type is "phrase" (subentries) against all example sentences listed under any sense of any entry.
2. **Match Metric**: Compare entry headword against example text using:
   - Length similarity: length difference $\le 4$ characters.
   - Jaro-Winkler similarity: similarity ratio $\ge 0.95$.
3. **Action**: Flag these in the Data Quality Dashboard under a "Redundant Examples" section. Editors can choose to convert the example sentence to a cross-reference link to the subentry, or dismiss/delete the redundant example.

#### 3.2.6 Structural/Schema Validation Rules (Intra-entry Hygiene)

To prevent duplication before entries are created, add the following validations to the XML schema and the save-time validator (`validation_rules_v2.json`):
1. **Redundant Variants/Allomorphs**: Alternate forms (`allomorph`) or entry variants (`variant`) cannot be identical to the main headword form (case-insensitive).
2. **Duplicate Alternate Forms**: An entry cannot have duplicate `allomorph` entries with the exact same form.
3. **Duplicate Variant References**: An entry cannot list the same target entry as a variant multiple times.
4. **Gloss Redundancy**: A sense gloss must be surrounded by parentheses. If the text of the gloss (excluding parentheses) is completely contained within the sense's definition, flag a warning: "Redundant gloss duplicates definition text".

### 3.3 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/dashboard/duplicates` | Run detection, return groups |
| `POST` | `/api/dashboard/duplicates/<group_id>/dismiss` | Mark group as reviewed, not a duplicate |
| `POST` | `/api/dashboard/duplicates/<group_id>/merge` | Merge entries in group (delegates to existing merge service) |

Query params for `GET /api/dashboard/duplicates`:

- `mode` — `"all"` (default), `"exact"`, `"near"`, `"fuzzy"`
- `pos` — optional POS filter, e.g. `"n"` (only pairs where both entries have this POS; no-POS entries match everything)
- `threshold` — Levenshtein distance (default 2)
- `min_confidence` — minimum confidence to return (default 0.5)

### 3.4 UI

Add a **"Duplicate Detection" tab** to the existing Data Quality Dashboard (`/data-quality`). Pattern:

1. **Summary bar**: "Found 47 potential duplicates in 23 groups"
2. **Filter row**: Mode toggle pills (All / Exact / Near / Fuzzy), POS dropdown (all / noun / verb / adjective / adverb / … populated from existing POS metadata), threshold slider
3. **Group list**: Each group renders as a card with:
   - Confidence badge (color-coded: green ≥0.9, yellow ≥0.7, red <0.7)
   - Mode badge (Exact / Near / Fuzzy)
   - Entry table (2–3 rows) showing headword, citation form, POS, senses count, matched fields
   - Action buttons: **Merge** (calls existing merge/split service), **Dismiss** (hides from future results)
4. **Merge dialog**: When "Merge" is clicked, delegate to the existing Merge UI — the merge/split service already handles `conflict_resolution = {"duplicate_senses": "rename"}` etc.

### 3.5 Storage

Dismissed groups are persisted in PostgreSQL (project-level, JSON column for dismissed group IDs):

```sql
CREATE TABLE IF NOT EXISTS dismissed_duplicates (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES project_settings(id),
    group_id TEXT NOT NULL,
    dismissed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, group_id)
);
```

---

## 4. Implementation Plan

### Phase 1 — Backend core (3–4 days)
1. Implement `get_duplicate_candidates()` in `DictionaryService`:
   - XQuery exact-headword pass
   - Python Levenshtein pass (reuse/factor `ipa_service.levenshtein_distance`)
   - Python fuzzy-sense pass
2. Add `GET /api/dashboard/duplicates` endpoint in `dashboard.py`
3. Add dismiss POST endpoint + PostgreSQL table
4. Wire merge POST to existing `merge_split_service`

### Phase 2 — Frontend (2–3 days)
1. Add "Duplicate Detection" section to `data_quality_dashboard.html`
2. JS in `quality-dashboard.js`: fetch groups, render cards, handle dismiss/merge actions
3. Merge dialog — reuse existing merge UI workflow

### Phase 3 — Tests (2 days)
1. Unit tests for detection algorithms (mocked BaseX)
2. API endpoint tests (mock the service layer)
3. E2E test for the full flow: load dashboard → see groups → dismiss → confirm removal

---

## 5. Acceptance Criteria

1. Dashboard at `/data-quality` shows a "Duplicates" section with group count
2. Clicking "Run Detection" scans the database and shows groups within 10s for 200k-entry DB
3. Each group shows the matched entries with headword, POS, senses count
4. "Exact headword" mode finds entries where headwords match case-insensitively
5. "Near headword" (default threshold 2) finds "colour/color", "theatre/theater" etc.
6. "tell sb sth" and "tell" are detected as duplicates (placeholders stripped)
7. "cat (animal)" and "cat" are detected as exact duplicates (parenthetical stripped)
8. "a cat" and "cat" are detected as exact duplicates (articles stripped)
9. "explain (sth) (to sb)" normalises to "explain" (parentheticals + placeholders stripped)
10. "well (n)" and "well (adv)" are not flagged as duplicates when POS filter is "n"
11. "well (n)" and "well" (no POS) are flagged as duplicates regardless of POS filter (no-POS = wildcard)
12. "sth/sb" (placeholder-only) is excluded from detection entirely
13. Custom placeholders from project settings are respected (e.g. French "qqch/qqn")
12. "Fuzzy sense" boosts confidence when sense definitions overlap
13. Confidence badge is color-coded
14. "Dismiss" hides the group (persisted to PG, survives page reload)
15. "Merge" opens the existing merge dialog for the group's entries
16. Threshold slider re-runs detection with new threshold
17. All detection runs complete within 10s for a 200k-entry dictionary

---

## 6. Open Questions

1. Should duplicate detection auto-run on dashboard load, or require a manual "Run" button? (Prefer manual — it's expensive)
2. How to handle entries with identical headwords but different POS (e.g., "run" as Noun vs Verb)? (Treat as distinct unless fuzzy sense mode confirms overlap)
3. Dismiss table: keep in PG or store as a per-project JSON setting? (PG table — cleaner schema, easy to query, survives DB resets)
4. Should pronunciation similarity be a detection mode? (Deferred — IPA dedup is already handled by `ipa_service.py` separately)
