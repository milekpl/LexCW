# Workset Curation Specification v1.0

> **Purpose**: Define a lightweight, pragmatic workset system for lexicographic curation workflow.
> **Principles**: DRY (Don't Repeat Yourself), KISS (Keep It Simple Stupid), minimal database changes.

## 1. Overview

The Workset Curation System enables lexicographers to:
1. Create worksets from saved queries or search criteria
2. Navigate entries sequentially (back/forth)
3. Mark entries as "done" or "needs review"
4. Save favorite entries to a dedicated list for later work
5. Track progress across worksets

## 2. Data Model Extensions

### 2.1 WorksetEntry Status Enum
```python
class EntryStatus:
    PENDING = "pending"      # Default, not yet reviewed
    DONE = "done"            # Reviewed and completed
    NEEDS_REVIEW = "review"  # Flagged for later attention
```

### 2.2 Extended `workset_entries` Table Schema
```sql
-- Existing columns preserved
workset_id     INTEGER REFERENCES worksets(id) ON DELETE CASCADE
entry_id       VARCHAR(255) NOT NULL

-- NEW COLUMNS
status         VARCHAR(20) DEFAULT 'pending'
position       INTEGER      -- For ordered navigation
is_favorite    BOOLEAN DEFAULT FALSE
notes          TEXT         -- Optional curator notes
modified_at    TIMESTAMP    -- Last status change
```

### 2.3 Favorites Table (Separate, Persistent)
```sql
CREATE TABLE favorites (
    id           SERIAL PRIMARY KEY,
    entry_id     VARCHAR(255) NOT NULL,
    workset_id   INTEGER,                 -- Optional: which workset it came from
    reason       TEXT,                     -- Why favorited (optional)
    created_at   TIMESTAMP DEFAULT NOW()
);
```

## 3. API Endpoints

### 3.1 Workset Entry Operations

#### Get workset with entry list and status
```
GET /api/worksets/{id}/entries?status=all&limit=50&offset=0
Response: {
    "workset": { "id": 1, "name": "...", "total_entries": 150 },
    "entries": [
        {
            "entry_id": "uuid-1",
            "lexical_unit": {"en": "bank"},
            "status": "pending",
            "is_favorite": false,
            "position": 0
        },
        ...
    ],
    "progress": { "done": 45, "pending": 100, "review": 5 }
}
```

#### Update entry status in workset
```
PATCH /api/worksets/{workset_id}/entries/{entry_id}/status
Body: { "status": "done" | "review" | "pending", "notes": "..." }
Response: { "success": true, "status": "done" }
```

#### Toggle favorite for entry
```
POST /api/worksets/{workset_id}/entries/{entry_id}/favorite
Body: { "is_favorite": true | false }
Response: { "success": true, "is_favorite": true }
```

### 3.2 Navigation Endpoints

#### Get current position entry
```
GET /api/worksets/{workset_id}/navigation/current
Response: {
    "entry": { /* full entry data */ },
    "status": "pending",
    "is_favorite": false,
    "position": 45,
    "total": 150,
    "prev_entry_id": "uuid-44",
    "next_entry_id": "uuid-46"
}
```

#### Navigate to position
```
POST /api/worksets/{workset_id}/navigation/position
Body: { "position": 45 }  -- 0-indexed
Response: { /* current entry with nav context */ }
```

#### Navigate relative
```
POST /api/worksets/{workset_id}/navigation/{direction}
-- direction: "next" | "prev" | "first" | "last"
Response: { /* current entry with nav context */ }

Examples:
POST /api/worksets/1/navigation/next  -- Go to next
POST /api/worksets/1/navigation/prev  -- Go to previous
POST /api/worksets/1/navigation/first -- Go to first
POST /api/worksets/1/navigation/last  -- Go to last
```

### 3.3 Favorites Endpoints

#### Get all favorites
```
GET /api/favorites
Response: {
    "favorites": [
        { "entry_id": "uuid-1", "lexical_unit": {...}, "workset_name": "Verbs-QC", "created_at": "..." }
    ],
    "total": 25
}
```

#### Add to favorites (standalone)
```
POST /api/favorites
Body: { "entry_id": "uuid-1", "reason": "Needs IPA review" }
Response: { "success": true, "favorite_id": 123 }
```

#### Remove from favorites
```
DELETE /api/favorites/{favorite_id}
Response: { "success": true }
```

### 3.4 Workset Creation from Search (Existing + Enhancement)

```
POST /api/worksets/from-search
Body: {
    "name": "Entries needing IPA review",
    "search_criteria": { /* existing search format */ },
    "status_filter": "pending"  -- Optional: only include pending entries
}
Response: { "workset_id": 1, "entry_count": 75 }
```

## 4. UI Components

### 4.1 Workset Entry Viewer (New Template)

**Route**: `/workbench/worksets/{id}/curate`

**Layout**:
```
+----------------------------------------------------------+
|  Workset: "Verbs for Review"  [45/150]  ████░░░░░ 30%   |
+----------------------------------------------------------+
|  [< Prev]  Entry 45 of 150  [Next >]                     |
+----------------------------------------------------------+
|  [★ Favorited]  [✓ Mark Done]  [⚠ Needs Review]         |
+----------------------------------------------------------+
|                                                          |
|  +----------------------------------------------+        |
|  |         FULL ENTRY DISPLAY AREA              |        |
|  |                                              |        |
|  |  bank₁ noun                                  |        |
|  |    financial institution                     |        |
|  |                                              |        |
|  |    [Edit in Modal]                           |        |
|  +----------------------------------------------+        |
|                                                          |
|  [Jump to: ___] [Go] | [Progress View] | [Settings]     |
+----------------------------------------------------------+
```

**Keyboard Shortcuts**:
- `←` / `→` - Previous/Next entry
- `d` - Mark as done
- `r` - Mark as needs review
- `f` - Toggle favorite
- `1-9` - Jump to position

### 4.2 Workset List View (Enhance Existing)

**Route**: `/workbench/worksets`

**Features**:
- List all worksets with progress bars
- Quick stats: total, done, pending, flagged
- "Curate" button to enter curation mode
- Delete/Clone workset options

### 4.3 Favorites Panel (Widget)

**Location**: Sidebar or dedicated page `/workbench/favorites`

**Features**:
- List all favorited entries
- Quick navigation to favorites
- Add notes to favorites
- Export favorites as workset

## 5. Implementation Plan

### Phase 1: Database & API Foundation
1. Add columns to `workset_entries` table
2. Create `favorites` table
3. Extend `WorksetService` with new methods
4. Add navigation endpoints

### Phase 2: Curation UI
1. Create `/workbench/worksets/{id}/curate` template
2. Implement entry viewer with navigation
3. Add status toggle buttons
4. Implement keyboard shortcuts

### Phase 3: Favorites System
1. Build favorites API
2. Create favorites panel/sidebar
3. Add "add to favorites" button on entries
4. Enable favorites-to-workset conversion

### Phase 4: Polish
1. Progress visualization
2. Bulk status operations
3. Workset cloning
4. Export workset progress

## 6. Compatibility Notes

### Reuse Existing Components:
- **Search/Query Builder**: Already exists, use for workset creation
- **Entry Display**: Reuse existing entry form in read-only mode
- **API Patterns**: Follow existing `worksets.py` conventions
- **CSS**: Use existing Bootstrap framework

### Database Migrations:
```sql
-- Migration script required
ALTER TABLE workset_entries ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE workset_entries ADD COLUMN position INTEGER;
ALTER TABLE workset_entries ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE;
ALTER TABLE workset_entries ADD COLUMN notes TEXT;
ALTER TABLE workset_entries ADD COLUMN modified_at TIMESTAMP;

CREATE TABLE favorites (
    id SERIAL PRIMARY KEY,
    entry_id VARCHAR(255) NOT NULL,
    workset_id INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 7. Example Workflow

### Scenario: Reviewing verbs needing IPA
1. User searches: ` grammatical_info contains "verb" AND pronunciation IS_EMPTY`
2. Saves as workset: "Verbs without IPA"
3. Opens workset curation view
4. Navigates through entries (→ key)
5. For each entry:
   - Adds IPA pronunciation
   - Presses `d` to mark done
6. At end, sees progress: 150/150 done
7. Exports completed workset stats

## 8. Future Extensions (Out of Scope v1.0)

- Multi-user worksets with assignment
- Workset comments/annotations
- Workset versioning
- Bulk import/export of worksets
- Workset sharing between users