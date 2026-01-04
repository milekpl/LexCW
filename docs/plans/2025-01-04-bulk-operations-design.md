# Bulk Operations System Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Comprehensive bulk operations system for lexicographic curation with full CRUD, search-replace, and cross-entry relational operations.

**Architecture:** Workset-centric design with two-pass execution. Pass 1: Query entries and collect related entries for cross-entry operations. Pass 2: Apply operations atomically. Pipeline chaining for complex multi-step workflows. All type/value validation uses LIFT ranges.

**Tech Stack:** Flask Blueprint API, workset_service.py foundations, LIFT ranges for validation, Bootstrap 5 modals for UI.

---

## 1. Architecture Overview

The bulk operations system follows a workset-centric design:

**Core Pattern - Two-Pass Execution:**
- **Pass 1 (Query):** Evaluate conditions against entries, collect related entries for cross-entry operations. Returns matching entry IDs.
- **Pass 2 (Execute):** Apply operations atomically to each entry, using related entries collected in pass 1.

**Workset Integration:**
- Selection in UI creates temporary workset
- Saved queries become persistent worksets
- Condition builder can load from existing worksets

**Pipeline Architecture:**
```python
class PipelineExecutor:
    def execute(condition: QueryFilter, operations: List[BulkOperation]) -> ExecutionResult:
        # Pass 1: Collect entries and their related entries
        entries = query_service.find_entries(condition)
        related_cache = collect_related_entries(entries)

        # Pass 2: Apply operations with related data
        results = []
        for entry in entries:
            result = apply_operations(entry, operations, related_cache)
            results.append(result)
```

---

## 2. Condition Syntax

Conditions determine which entries match using a JSON-based condition language.

### 2.1 Field Conditions

```json
{ "field": "lexical_unit.en", "op": "equals", "value": "run" }
{ "field": "senses.0.definition.en", "op": "is_empty" }
{ "field": "grammatical_info.trait", "op": "contains", "value": "verb" }
```

Operators: `equals`, `not_equals`, `contains`, `starts_with`, `ends_with`, `regex`, `is_empty`, `is_not_empty`, `gt`, `lt`, `in`.

### 2.2 Relational Conditions

```json
{
  "related": { "type": "synonym" },
  "condition": { "field": "lexical_unit.en", "op": "is_not_empty" }
}
```

Matches entries with a synonym relation to an entry with non-empty headword. Use `target_in_field` for FTFlags-style lookups.

### 2.3 Compound Conditions

```json
{
  "and": [
    { "field": "lexical_unit.en", "op": "is_empty" },
    { "related": { "type": "synonym", "target_in_field": "ftflags" },
      "condition": { "field": "lexical_unit.en", "op": "contains", "value": "important" } }
  ]
}
```

---

## 3. Action Types

### 3.1 Set/Clear Actions

```json
{ "action": "set", "field": "grammatical_info.trait", "value": "noun" }
{ "action": "clear", "field": "senses.0.definition.en" }
{ "action": "append", "field": "traits", "value": "borrowed" }
{ "action": "prepend", "field": "lexical_unit.en", "value": "[" }
{ "action": "append", "field": "lexical_unit.en", "value": "]" }
```

### 3.2 Relation Actions

```json
{ "action": "add_relation", "type": "synonym", "target_entry_id": "${related.id}" }
{ "action": "remove_relation", "type": "synonym", "target_entry_id": "${related.id}" }
{ "action": "replace_relation", "type": "synonym", "old_target": "${old}", "new_target": "${new}" }
```

### 3.3 Cross-Entry Copy

```json
{
  "action": "copy_from_related",
  "from_field": "senses.0.definition.en",
  "to_field": "senses.0.definition.en",
  "relation_type": "synonym"
}
```

FTFlags pattern:
```json
{
  "action": "copy_from_related",
  "from_field": "lexical_unit.en",
  "to_field": "examples.0.text",
  "target_in_field": "ftflags"
}
```

### 3.4 Pipeline Actions

```json
{ "action": "pipeline", "steps": [
  { "action": "set", "field": "grammatical_info.trait", "value": "verb" },
  { "action": "add_relation", "type": "see_also", "target_entry_id": "${parent.id}" }
]}
```

---

## 4. API Endpoints

### 4.1 Ranges Endpoint

```
GET /api/ranges
```

Returns valid types for dropdown validation:
```json
{
  "relation_types": ["synonym", "antonym", "hypernym", "hyponym", "see_also", ...],
  "trait_types": ["verb", "noun", "adjective", ...],
  "part_of_speech": ["noun", "verb", "adjective", "adverb", ...]
}
```

### 4.2 Query Endpoint

```
POST /bulk/query
{
  "condition": { "field": "grammatical_info.trait", "op": "equals", "value": "verb" },
  "ranges": { "allowed_traits": ["noun", "verb", "adjective"] },
  "limit": 100,
  "offset": 0
}
```

### 4.3 Execute Endpoint

```
POST /bulk/execute
{
  "entry_ids": ["id1", "id2"],
  "operations": [
    { "action": "set", "field": "grammatical_info.trait", "value": "noun",
      "ranges": { "allowed_values": ["noun", "verb", "adjective"] } }
  ],
  "dry_run": false
}
```

### 4.4 Pipeline Endpoint

```
POST /bulk/pipeline
{
  "ranges": {
    "relation_types": ["synonym", "antonym", "see_also", ...],
    "trait_types": ["verb", "noun", "adjective"]
  },
  "condition": { ... },
  "operations": [
    { "action": "add_relation", "type": "synonym", "target_entry_id": "${related.id}",
      "ranges": { "allowed_types": ["synonym", "antonym", ...] } }
  ]
}
```

### 4.5 Preview Endpoint

```
POST /bulk/preview
Same body as execute, dry_run defaults to true.
Returns: { "changes": [ { "entry_id": "id1", "field": "lexical_unit.en", "old_value": "x", "new_value": "y" }, ... ] }
```

---

## 5. UI Components

### 5.1 Condition Builder Panel

Visual query construction with relation type dropdowns populated from LIFT ranges.

### 5.2 Operation Pipeline Panel

Chain actions with field/type dropdowns validated against ranges.

### 5.3 Results Panel

Preview changes before execution with diff display.

---

## 6. Implementation Tasks

### Backend
1. Create `app/services/bulk_query_service.py` - Query building and execution
2. Create `app/services/bulk_action_service.py` - Action application logic
3. Extend `app/api/bulk_operations.py` - Add query, execute, pipeline, preview endpoints
4. Add `/api/ranges` endpoint if not exists (check existing)

### Frontend
5. Create `app/static/js/bulk-editor.js` - Complete rewrite with condition builder
6. Create `app/static/js/bulk-query-builder.js` - Visual condition construction
7. Create `app/static/js/bulk-operation-pipeline.js` - Pipeline UI
8. Update `app/templates/entries.html` - Add bulk editor panel sections

### Testing
9. Add unit tests for condition parsing
10. Add integration tests for pipeline execution
11. Add e2e tests for UI workflows

---

## 7. Reference Files

- `app/services/workset_service.py` - WorksetQuery, QueryFilter, BulkOperation foundations
- `app/models/entry.py` - Entry fields, Relation class
- `app/parsers/lift_parser.py` - LIFT ranges access
- `app/api/bulk_operations.py` - Existing minimal API (replace/extend)
- `app/static/js/bulk-editor.js` - Current placeholder (rewrite)
