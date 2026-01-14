# Bulk Edit Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement bulk edit interface for atomic operations (trait conversion, POS tagging) using existing infrastructure (Bootstrap 5, Vanilla JS, Flask).

**Architecture:**
- Service layer: `BulkOperationsService` using DictionaryService and OperationHistoryService
- API endpoints: Flask blueprints for bulk operations
- Frontend: Vanilla JS extending existing entry selection patterns

**Tech Stack:**
- Backend: Flask + existing services (DictionaryService, WorksetService, OperationHistoryService)
- Frontend: Bootstrap 5 + Vanilla JavaScript (existing patterns)
- Storage: BaseX (LIFT XML) + PostgreSQL (Worksets)

---

## Plan

### Phase 1: Entry Model Extensions

#### Task 1: Add convert_trait method to Entry model

**Files:**
- Modify: `app/models/entry.py`
- Test: `tests/unit/test_entry.py`

**Step 1: Write failing test**

```python
# tests/unit/test_entry.py
def test_convert_trait():
    """Entry should support trait conversion."""
    entry = Entry(
        id='test-1',
        lexical_unit={'en': 'test'},
        traits={'part-of-speech': 'verb', 'transitivity': 'transitive'}
    )

    # Convert verb to phrasal-verb
    entry.convert_trait('part-of-speech', 'verb', 'phrasal-verb')

    assert entry.traits['part-of-speech'] == 'phrasal-verb'
    assert entry.traits['transitivity'] == 'transitive'  # Unchanged
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_entry.py::test_convert_trait -v
# Expected: FAIL - method doesn't exist
```

**Step 3: Add method to Entry class**

```python
# In app/models/entry.py, add to Entry class:
def convert_trait(self, trait_type: str, old_value: str, new_value: str) -> None:
    """
    Convert a trait value from old_value to new_value.

    Args:
        trait_type: The key of the trait to convert (e.g., 'part-of-speech')
        old_value: Current value that should be replaced
        new_value: New value to set

    Raises:
        ValueError: If trait_type doesn't exist or old_value doesn't match
    """
    if self.traits.get(trait_type) != old_value:
        raise ValueError(f"Trait '{trait_type}' does not have value '{old_value}'")

    self.traits[trait_type] = new_value
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_entry.py::test_convert_trait -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add app/models/entry.py tests/unit/test_entry.py
git commit -m "feat: add convert_trait method to Entry model"
```

---

#### Task 2: Add update_grammatical_info method to Entry model

**Files:**
- Modify: `app/models/entry.py`
- Test: `tests/unit/test_entry.py`

**Step 1: Write failing test**

```python
# tests/unit/test_entry.py
def test_update_grammatical_info():
    """Entry should support updating grammatical info."""
    entry = Entry(
        id='test-1',
        lexical_unit={'en': 'test'},
        grammatical_info='noun'
    )

    entry.update_grammatical_info('verb')

    assert entry.grammatical_info == 'verb'
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_entry.py::test_update_grammatical_info -v
# Expected: FAIL - method doesn't exist
```

**Step 3: Add method to Entry class**

```python
# In app/models/entry.py, add to Entry class:
def update_grammatical_info(self, grammatical_info: str) -> None:
    """
    Update the grammatical information for this entry.

    Args:
        grammatical_info: New grammatical info string (e.g., 'noun', 'verb')
    """
    self.grammatical_info = grammatical_info
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_entry.py::test_update_grammatical_info -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add app/models/entry.py tests/unit/test_entry.py
git commit -m "feat: add update_grammatical_info method to Entry model"
```

---

### Phase 2: BulkOperationsService

#### Task 3: Create BulkOperationsService

**Files:**
- Create: `app/services/bulk_operations_service.py`
- Test: `tests/unit/test_bulk_operations_service.py`

**Step 1: Write failing test**

```python
# tests/unit/test_bulk_operations_service.py
import pytest
from unittest.mock import Mock
from app.services.bulk_operations_service import BulkOperationsService

def test_convert_traits():
    """BulkOperationsService should convert traits across entries."""
    mock_dict = Mock()
    mock_dict.get_entry.return_value = Mock(
        traits={'part-of-speech': 'verb'},
        lexical_unit={'en': 'test'}
    )
    mock_dict.update_entry.return_value = Mock(
        traits={'part-of-speech': 'phrasal-verb'},
        lexical_unit={'en': 'test'}
    )

    mock_history = Mock()
    mock_workset = Mock()

    service = BulkOperationsService(
        dictionary_service=mock_dict,
        workset_service=mock_workset,
        history_service=mock_history
    )

    result = service.convert_traits(['entry-1', 'entry-2'], 'verb', 'phrasal-verb')

    assert result['total'] == 2
    assert all(r['status'] == 'success' for r in result['results'])
    mock_history.record_operation.assert_called()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_bulk_operations_service.py -v
# Expected: FAIL - module doesn't exist
```

**Step 3: Create BulkOperationsService**

```python
# app/services/bulk_operations_service.py
"""
Service for atomic bulk operations on dictionary entries.
"""
import logging
from typing import List, Dict, Any, Optional
from app.services.dictionary_service import DictionaryService
from app.services.workset_service import WorksetService
from app.services.operation_history_service import OperationHistoryService

logger = logging.getLogger(__name__)

class BulkOperationsService:
    """Service for atomic bulk operations using existing infrastructure"""

    def __init__(self,
                 dictionary_service: DictionaryService,
                 workset_service: WorksetService,
                 history_service: Optional[OperationHistoryService] = None):
        self.dictionary = dictionary_service
        self.workset = workset_service
        self.history = history_service

    def convert_traits(self, entry_ids: List[str], from_trait: str, to_trait: str) -> Dict[str, Any]:
        """
        Convert a trait value across multiple entries atomically.

        Args:
            entry_ids: List of entry IDs to modify
            from_trait: Trait key to convert (e.g., 'part-of-speech')
            to_trait: New trait value

        Returns:
            Dict with 'results' list and 'total' count
        """
        results = []

        for entry_id in entry_ids:
            try:
                entry = self.dictionary.get_entry(entry_id)
                if entry:
                    # Apply trait conversion
                    entry.convert_trait(from_trait, entry.traits.get(from_trait), to_trait)
                    updated = self.dictionary.update_entry(entry)
                    results.append({
                        'id': entry_id,
                        'status': 'success',
                        'data': {'traits': updated.traits}
                    })

                    # Record operation for undo/redo
                    if self.history:
                        self.history.record_operation(
                            operation_type='bulk_trait_conversion',
                            data={
                                'entry_id': entry_id,
                                'trait': from_trait,
                                'old_value': entry.traits.get(from_trait),
                                'new_value': to_trait
                            },
                            entry_id=entry_id
                        )
                else:
                    results.append({'id': entry_id, 'status': 'error', 'error': 'Entry not found'})
            except Exception as e:
                logger.error(f"Error converting trait for entry {entry_id}: {e}")
                results.append({'id': entry_id, 'status': 'error', 'error': str(e)})

        return {'results': results, 'total': len(results)}

    def update_pos_bulk(self, entry_ids: List[str], pos_tag: str) -> Dict[str, Any]:
        """
        Update part-of-speech tag across multiple entries.

        Args:
            entry_ids: List of entry IDs to modify
            pos_tag: New POS tag (e.g., 'noun', 'verb')

        Returns:
            Dict with 'results' list and 'total' count
        """
        results = []

        for entry_id in entry_ids:
            try:
                entry = self.dictionary.get_entry(entry_id)
                if entry:
                    old_pos = entry.grammatical_info
                    entry.update_grammatical_info(pos_tag)
                    updated = self.dictionary.update_entry(entry)
                    results.append({
                        'id': entry_id,
                        'status': 'success',
                        'data': {'grammatical_info': updated.grammatical_info}
                    })

                    # Record operation for undo/redo
                    if self.history:
                        self.history.record_operation(
                            operation_type='bulk_pos_update',
                            data={
                                'entry_id': entry_id,
                                'old_value': old_pos,
                                'new_value': pos_tag
                            },
                            entry_id=entry_id
                        )
                else:
                    results.append({'id': entry_id, 'status': 'error', 'error': 'Entry not found'})
            except Exception as e:
                logger.error(f"Error updating POS for entry {entry_id}: {e}")
                results.append({'id': entry_id, 'status': 'error', 'error': str(e)})

        return {'results': results, 'total': len(results)}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_bulk_operations_service.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add app/services/bulk_operations_service.py tests/unit/test_bulk_operations_service.py
git commit -m "feat: add BulkOperationsService for atomic bulk operations"
```

---

### Phase 3: API Endpoints

#### Task 4: Create bulk operations API blueprint

**Files:**
- Create: `app/api/bulk_operations.py`
- Modify: `app/api/__init__.py` (register blueprint)
- Test: `tests/unit/test_bulk_operations_api.py`

**Step 1: Write failing test**

```python
# tests/unit/test_bulk_operations_api.py
import pytest
from unittest.mock import Mock, patch
from flask import Flask

def test_convert_traits_endpoint(monkeypatch):
    """Bulk API should handle trait conversion requests."""
    from app.api.bulk_operations import bulk_bp

    app = Flask(__name__)
    app.register_blueprint(bulk_bp)

    mock_service = Mock()
    mock_service.convert_traits.return_value = {
        'results': [{'id': 'entry-1', 'status': 'success'}],
        'total': 1
    }

    with patch('app.api.bulk_operations.get_bulk_operations_service', return_value=mock_service):
        with app.test_client() as client:
            response = client.post('/bulk/traits/convert',
                json={'entry_ids': ['entry-1'], 'from_trait': 'verb', 'to_trait': 'noun'},
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['total'] == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_bulk_operations_api.py -v
# Expected: FAIL - blueprint doesn't exist
```

**Step 3: Create API blueprint**

```python
# app/api/bulk_operations.py
"""
API endpoints for bulk operations on dictionary entries.
"""
from flask import Blueprint, request, jsonify
from app.services.bulk_operations_service import BulkOperationsService

bulk_bp = Blueprint('bulk_operations', __name__, url_prefix='/bulk')

def get_bulk_operations_service() -> BulkOperationsService:
    """Get BulkOperationsService from injector."""
    from flask import current_app
    return current_app.injector.get(BulkOperationsService)

@bulk_bp.route('/traits/convert', methods=['POST'])
def convert_traits():
    """
    Convert traits across multiple entries.

    Request body:
    {
        "entry_ids": ["id1", "id2"],
        "from_trait": "verb",
        "to_trait": "phrasal-verb"
    }

    Response:
    {
        "operation_id": "op-xxx",
        "summary": {"requested": 2, "success": 2, "failed": 0},
        "results": [{"id": "id1", "status": "success"}, ...]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    entry_ids = data.get('entry_ids', [])
    from_trait = data.get('from_trait')
    to_trait = data.get('to_trait')

    if not entry_ids or not from_trait or not to_trait:
        return jsonify({'error': 'Missing required fields'}), 400

    service = get_bulk_operations_service()
    result = service.convert_traits(entry_ids, from_trait, to_trait)

    # Build summary
    summary = {
        'requested': result['total'],
        'success': sum(1 for r in result['results'] if r['status'] == 'success'),
        'failed': sum(1 for r in result['results'] if r['status'] == 'error')
    }

    return jsonify({
        'operation_id': f'op-{request.date.strftime("%Y%m%d")}-{len(result["results"])}',
        'summary': summary,
        'results': result['results']
    })

@bulk_bp.route('/pos/update', methods=['POST'])
def update_pos_bulk():
    """
    Update part-of-speech tags across multiple entries.

    Request body:
    {
        "entry_ids": ["id1", "id2"],
        "pos_tag": "noun"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    entry_ids = data.get('entry_ids', [])
    pos_tag = data.get('pos_tag')

    if not entry_ids or not pos_tag:
        return jsonify({'error': 'Missing required fields'}), 400

    service = get_bulk_operations_service()
    result = service.update_pos_bulk(entry_ids, pos_tag)

    summary = {
        'requested': result['total'],
        'success': sum(1 for r in result['results'] if r['status'] == 'success'),
        'failed': sum(1 for r in result['results'] if r['status'] == 'error')
    }

    return jsonify({
        'operation_id': f'op-{request.date.strftime("%Y%m%d")}-{len(result["results"])}',
        'summary': summary,
        'results': result['results']
    })
```

**Step 4: Register blueprint in app/api/__init__.py**

```python
# In app/api/__init__.py, add:
from app.api.bulk_operations import bulk_bp
api_bp.register_blueprint(bulk_bp, url_prefix='/bulk')
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_bulk_operations_api.py -v
# Expected: PASS
```

**Step 6: Commit**

```bash
git add app/api/bulk_operations.py tests/unit/test_bulk_operations_api.py
git commit -m "feat: add bulk operations API endpoints"
```

---

### Phase 4: Frontend JavaScript

#### Task 5: Create bulk-editor.js

**Files:**
- Create: `app/static/js/bulk-editor.js`
- Modify: `app/templates/entries.html` (add bulk UI elements)

**Step 1: Write failing test (conceptual - JS testing)**

```javascript
// Verify bulk-editor.js exists and has expected methods
// This is verified by loading the page and checking console
```

**Step 2: Create bulk-editor.js**

```javascript
// app/static/js/bulk-editor.js
/**
 * Bulk Editor - Tabular interface for atomic bulk operations
 * Extends existing entries.js patterns and reuses existing components
 */

class BulkEditor {
    constructor() {
        this.selectedEntries = new Set();
        this.currentOperation = null;
        this.validationUI = new ValidationUI();
        this.init();
    }

    init() {
        this.setupSelectionHandlers();
        this.setupOperationHandlers();
        this.setupBulkActionPanel();
        console.log('[BulkEditor] Initialized');
    }

    setupSelectionHandlers() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('bulk-select-checkbox')) {
                const entryId = e.target.dataset.entryId;
                if (e.target.checked) {
                    this.selectedEntries.add(entryId);
                } else {
                    this.selectedEntries.delete(entryId);
                }
                this.updateSelectionUI();
            }

            if (e.target.id === 'bulk-select-all') {
                this.toggleSelectAll(e.target.checked);
            }
        });
    }

    setupOperationHandlers() {
        const traitBtn = document.getElementById('bulk-convert-traits-btn');
        if (traitBtn) {
            traitBtn.addEventListener('click', () => this.showTraitConversionModal());
        }

        const posBtn = document.getElementById('bulk-update-pos-btn');
        if (posBtn) {
            posBtn.addEventListener('click', () => this.showPOSUpdateModal());
        }
    }

    setupBulkActionPanel() {
        const entriesHeader = document.querySelector('.card-header');
        if (entriesHeader && !document.getElementById('bulk-actions-panel')) {
            const panel = this.createBulkActionPanel();
            entriesHeader.insertAdjacentHTML('beforeend', panel);
        }
    }

    createBulkActionPanel() {
        return `
            <div id="bulk-actions-panel" class="mt-2" style="display: none;">
                <div class="alert alert-info d-flex align-items-center">
                    <span class="me-2"><strong>Bulk Actions:</strong> <span id="selected-count">0</span> entries selected</span>
                    <button class="btn btn-sm btn-primary me-2" id="bulk-convert-traits-btn">Convert Traits</button>
                    <button class="btn btn-sm btn-primary me-2" id="bulk-update-pos-btn">Update POS</button>
                    <button class="btn btn-sm btn-secondary" id="bulk-clear-selection-btn">Clear</button>
                </div>
            </div>
        `;
    }

    updateSelectionUI() {
        const count = this.selectedEntries.size;
        const panel = document.getElementById('bulk-actions-panel');
        const countSpan = document.getElementById('selected-count');

        if (panel) {
            panel.style.display = count > 0 ? 'block' : 'none';
            if (countSpan) countSpan.textContent = count;
        }
    }

    toggleSelectAll(checked) {
        const checkboxes = document.querySelectorAll('.bulk-select-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = checked;
            const entryId = cb.dataset.entryId;
            if (checked) {
                this.selectedEntries.add(entryId);
            } else {
                this.selectedEntries.delete(entryId);
            }
        });
        this.updateSelectionUI();
    }

    showTraitConversionModal() {
        const modalHtml = `
            <div class="modal fade" id="trait-conversion-modal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Convert Traits</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">From Trait Value</label>
                                <input type="text" class="form-control" id="from-trait" placeholder="e.g., verb">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">To Trait Value</label>
                                <input type="text" class="form-control" id="to-trait" placeholder="e.g., phrasal-verb">
                            </div>
                            <div class="alert alert-warning">
                                This will affect <strong>${this.selectedEntries.size}</strong> entries
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="execute-trait-conversion">Execute</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (!document.getElementById('trait-conversion-modal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        const modal = new bootstrap.Modal(document.getElementById('trait-conversion-modal'));
        modal.show();

        document.getElementById('execute-trait-conversion').onclick = () => this.executeTraitConversion();
    }

    async executeTraitConversion() {
        const fromTrait = document.getElementById('from-trait').value;
        const toTrait = document.getElementById('to-trait').value;

        if (!fromTrait || !toTrait) {
            this.validationUI.showError('Please enter both trait values');
            return;
        }

        const entryIds = Array.from(this.selectedEntries);

        try {
            const response = await fetch('/bulk/traits/convert', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    entry_ids: entryIds,
                    from_trait: fromTrait,
                    to_trait: toTrait
                })
            });

            const result = await response.json();

            if (response.ok) {
                const successCount = result.summary.success;
                this.validationUI.showSuccess(`Successfully updated ${successCount} entries`);
                this.clearSelection();

                const modal = bootstrap.Modal.getInstance(document.getElementById('trait-conversion-modal'));
                modal.hide();

                // Refresh entries table if needed
                if (typeof refreshEntriesTable === 'function') {
                    refreshEntriesTable();
                }
            } else {
                this.validationUI.showError('Bulk operation failed');
            }
        } catch (error) {
            this.validationUI.showError('Network error: ' + error.message);
        }
    }

    showPOSUpdateModal() {
        const modalHtml = `
            <div class="modal fade" id="pos-update-modal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Update Part-of-Speech</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">New POS Tag</label>
                                <select class="form-select" id="pos-tag">
                                    <option value="">Select POS...</option>
                                    <option value="noun">Noun</option>
                                    <option value="verb">Verb</option>
                                    <option value="adjective">Adjective</option>
                                    <option value="adverb">Adverb</option>
                                    <option value="preposition">Preposition</option>
                                    <option value="conjunction">Conjunction</option>
                                </select>
                            </div>
                            <div class="alert alert-warning">
                                This will affect <strong>${this.selectedEntries.size}</strong> entries
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="execute-pos-update">Execute</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (!document.getElementById('pos-update-modal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        const modal = new bootstrap.Modal(document.getElementById('pos-update-modal'));
        modal.show();

        document.getElementById('execute-pos-update').onclick = () => this.executePOSUpdate();
    }

    async executePOSUpdate() {
        const posTag = document.getElementById('pos-tag').value;

        if (!posTag) {
            this.validationUI.showError('Please select a POS tag');
            return;
        }

        const entryIds = Array.from(this.selectedEntries);

        try {
            const response = await fetch('/bulk/pos/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    entry_ids: entryIds,
                    pos_tag: posTag
                })
            });

            const result = await response.json();

            if (response.ok) {
                const successCount = result.summary.success;
                this.validationUI.showSuccess(`Successfully updated ${successCount} entries`);
                this.clearSelection();

                const modal = bootstrap.Modal.getInstance(document.getElementById('pos-update-modal'));
                modal.hide();
            } else {
                this.validationUI.showError('Bulk operation failed');
            }
        } catch (error) {
            this.validationUI.showError('Network error: ' + error.message);
        }
    }

    clearSelection() {
        this.selectedEntries.clear();
        this.toggleSelectAll(false);
    }
}

// Initialize on entries page
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('entries-table')) {
        window.bulkEditor = new BulkEditor();
    }
});
```

**Step 3: Add to entries template**

```html
<!-- In app/templates/entries.html, add to extra_js block -->
<script src="{{ url_for('static', filename='js/bulk-editor.js') }}"></script>
```

**Step 4: Test by verifying file exists and loads**

```bash
ls -la app/static/js/bulk-editor.js
```

**Step 5: Commit**

```bash
git add app/static/js/bulk-editor.js
git commit -m "feat: add bulk-editor JavaScript module"
```

---

### Phase 5: Integration Tests

#### Task 6: Write integration tests

**Files:**
- Create: `tests/integration/test_bulk_operations_integration.py`

**Step 1: Write integration test**

```python
# tests/integration/test_bulk_operations_integration.py
import pytest
from flask import url_for

class TestBulkOperationsIntegration:
    def test_bulk_trait_conversion_api(self, client, auth_headers, test_entries):
        """Test bulk trait conversion API endpoint with real entries."""
        entry_ids = [entry.id for entry in test_entries[:5]]

        response = client.post(
            url_for('bulk_operations.convert_traits'),
            json={
                'entry_ids': entry_ids,
                'from_trait': 'verb',
                'to_trait': 'noun'
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'operation_id' in data
        assert 'summary' in data
        assert len(data['results']) == 5

    def test_bulk_pos_update_api(self, client, auth_headers, test_entries):
        """Test bulk POS update API endpoint."""
        entry_ids = [entry.id for entry in test_entries[:3]]

        response = client.post(
            url_for('bulk_operations.update_pos_bulk'),
            json={
                'entry_ids': entry_ids,
                'pos_tag': 'adjective'
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['results']) == 3
        assert data['summary']['requested'] == 3
```

**Step 2: Run integration tests**

```bash
pytest tests/integration/test_bulk_operations_integration.py -v
# Expected: PASS (requires running Flask app with BaseX)
```

**Step 3: Commit**

```bash
git add tests/integration/test_bulk_operations_integration.py
git commit -m "test: add integration tests for bulk operations"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `app/models/entry.py` | Added `convert_trait()` and `update_grammatical_info()` methods |
| `app/services/bulk_operations_service.py` | Created new service for bulk operations |
| `app/api/bulk_operations.py` | Created API blueprint with `/bulk/traits/convert` and `/bulk/pos/update` |
| `app/api/__init__.py` | Registered bulk blueprint |
| `app/static/js/bulk-editor.js` | Created frontend module with selection and modal UI |
| `app/templates/entries.html` | Added bulk-editor.js script include |

## Testing Commands

```bash
# Run all tests
pytest tests/unit/test_bulk_operations_service.py tests/unit/test_bulk_operations_api.py tests/unit/test_entry.py -v

# Run integration tests (requires BaseX)
pytest tests/integration/test_bulk_operations_integration.py -v

# Verify app loads
python -c "from app import create_app; app = create_app(); print('OK')"
```

## Precommit Checklist

Before merging, ensure:
- [ ] Unit tests pass for BulkOperationsService
- [ ] API integration tests pass
- [ ] Entry model methods tested
- [ ] Operation history entries created for undo support
- [ ] Frontend JS loads without errors

---

**Plan complete and saved to `docs/plans/2025-01-04-bulk-edit-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
