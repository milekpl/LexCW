# Validation Rule Editor Implementation Plan

## Overview
Implementation of a Validation Rule Editor UI for customizing dictionary project validation rules, based on the specification in `VALIDATION_RULE_EDITOR_UI_SPECIFICATION.md`.

## Implementation Order

### Phase 1: Backend Foundation (Database & API)

#### Task 1.1: Database Schema
- Create PostgreSQL table `project_validation_rules`
- Add indexes for project_id and rule_id
- Location: `app/models/validation_models.py`

#### Task 1.2: Validation Rule Model
- Create `ValidationRule` model class
- Define schema for rule structure
- Location: `app/models/validation_models.py`

#### Task 1.3: Storage Service
- Create `ValidationRulesService` for CRUD operations
- Handle file + database synchronization
- Location: `app/services/validation_rules_service.py`

#### Task 1.4: API Endpoints
- `GET /api/projects/{project_id}/validation-rules` - Get rules
- `PUT /api/projects/{project_id}/validation-rules` - Update rules
- `GET /api/validation-rule-templates` - Get templates
- `POST /api/validation-rules/test` - Test rules
- Location: `app/api/validation_rules_api.py`

---

### Phase 2: Validation Engine Integration

#### Task 2.1: Project-Aware Validation Engine
- Modify `validation_engine.py` to accept project_id
- Implement rule caching per project
- Add fallback to default rules

#### Task 2.2: Rule Testing Endpoint
- Implement rule validation against sample data
- Return detailed validation results
- Use existing validation engine logic

#### Task 2.3: Template System
- Define standard templates (Basic, Academic, Bilingual, Research)
- Store templates in `app/data/validation_templates/`
- Load defaults from `validation_rules_v2.json`

---

### Phase 3: Frontend Components

#### Task 3.1: JavaScript State Management
- Create `validation-rules-manager.js` module
- State: rules list, current rule, dirty state, test results
- Location: `app/static/js/validation-rules-manager.js`

#### Task 3.2: Rule List Component
- Display rules in table format
- Add filtering (category, priority)
- Add search functionality
- Location: `app/static/js/validation-rules-list.js`

#### Task 3.3: Rule Editor Component
- Form for editing rule properties
- Dynamic validation parameters based on type
- Real-time JSON preview
- Location: `app/static/js/validation-rule-editor.js`

#### Task 3.4: Rule Preview & Test Component
- JSON preview panel
- Sample data input
- Test validation button
- Location: `app/static/js/validation-rule-preview.js`

---

### Phase 4: UI Integration

#### Task 4.1: Admin Page Template
- Create `validation_rules_admin.html`
- Layout matching specification
- Location: `app/templates/admin/validation_rules_admin.html`

#### Task 4.2: Modal Dialogs
- Add rule modal
- Delete confirmation modal
- Import/Export dialogs
- Location: `app/templates/admin/`

#### Task 4.3: JavaScript Module Integration
- Initialize manager on page load
- Wire up event handlers
- Integrate with existing admin navigation

---

### Phase 5: Import/Export & Templates

#### Task 5.1: Export Functionality
- Export rules as JSON file
- Include metadata (project, version, timestamp)

#### Task 5.2: Import Functionality
- Import rules from JSON
- Validate against schema
- Merge or replace options

#### Task 5.3: Template Management
- Create template files
- Load/save custom templates
- UI for template selection

---

### Phase 6: Security & Polish

#### Task 6.1: Access Control
- Add permission checks (admin only for edit)
- Audit logging for rule changes

#### Task 6.2: Input Validation
- JSONPath sanitization
- Regex pattern validation
- Schema validation before save

#### Task 6.3: User Experience
- Loading states
- Success/error notifications
- Unsaved changes warning
- Keyboard shortcuts

---

## File Changes Summary

### New Files
| File | Purpose |
|------|---------|
| `app/models/validation_models.py` | Database model |
| `app/services/validation_rules_service.py` | CRUD service |
| `app/api/validation_rules_api.py` | REST endpoints |
| `app/static/js/validation-rules-manager.js` | Main state manager |
| `app/static/js/validation-rules-list.js` | Rule list component |
| `app/static/js/validation-rule-editor.js` | Rule editor form |
| `app/static/js/validation-rule-preview.js` | Preview & test |
| `app/templates/admin/validation_rules_admin.html` | Main UI page |
| `app/data/validation_templates/*.json` | Template files |

### Modified Files
| File | Changes |
|------|---------|
| `app/models/__init__.py` | Export new model |
| `app/api/__init__.py` | Register blueprint |
| `app/services/validation_engine.py` | Project-aware validation |
| `app/views.py` | Add route for admin page |
| `requirements.txt` | Add jsonpath-ng if needed |

---

## Database Schema

```sql
CREATE TABLE project_validation_rules (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    rule_id VARCHAR(50) NOT NULL,
    rule_config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_pvr_project ON project_validation_rules(project_id);
CREATE INDEX idx_pvr_rule ON project_validation_rules(rule_id);
```

---

## API Endpoints

### GET /api/projects/{project_id}/validation-rules
**Response:**
```json
{
  "rules": [...],
  "version": "1.0",
  "default_rules_used": false
}
```

### PUT /api/projects/{project_id}/validation-rules
**Request:**
```json
{
  "rules": [...],
  "version": "1.0"
}
```

### POST /api/validation-rules/test
**Request:**
```json
{
  "rule": {...},
  "test_data": {...}
}
```

**Response:**
```json
{
  "valid": true,
  "errors": []
}
```

---

## Implementation Checklist

- [x] Task 1.1: Create database schema
- [x] Task 1.2: Create ValidationRule model
- [x] Task 1.3: Create ValidationRulesService
- [x] Task 1.4: Implement API endpoints
- [x] Task 2.1: Make validation engine project-aware
- [x] Task 2.2: Implement rule testing endpoint
- [x] Task 2.3: Create template system
- [x] Task 3.1: Create validation-rules-manager.js
- [x] Task 3.2: Create validation-rules-list.js
- [x] Task 3.3: Create validation-rule-editor.js
- [x] Task 3.4: Create validation-rule-preview.js
- [x] Task 4.1: Create admin page template
- [x] Task 4.2: Add modal dialogs (built into page template)
- [x] Task 4.3: Wire up JavaScript modules
- [ ] Task 5.1: Implement export functionality
- [ ] Task 5.2: Implement import functionality
- [ ] Task 5.3: Create template management
- [ ] Task 6.1: Add access control
- [ ] Task 6.2: Add input validation
- [ ] Task 6.3: Polish UX

---

## Dependencies

- `jsonpath-ng` - For JSONPath expression validation
- `jsonschema` - For rule schema validation
- Existing: Flask, SQLAlchemy, PostgreSQL

---

## Testing Strategy

1. **Unit Tests**: Model serialization, service methods, API endpoints
2. **Integration Tests**: Full CRUD workflow, rule testing
3. **Frontend Tests**: Component rendering, event handling
4. **E2E Tests**: Complete user workflow in browser

---

## Rollout Plan

1. Deploy backend changes (database migration, API)
2. Add JavaScript modules
3. Add admin page
4. Test with sample project
5. Document new feature
6. Announce to users

---

**Created:** 2025-12-30
**Status:** Ready for implementation
