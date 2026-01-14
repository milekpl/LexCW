# Bulk Edit Implementation - Quick Reference

## File Structure

### New Files to Create
```
app/
├── services/
│   ├── bulk_operations_service.py          # Core bulk operations
│   └── sequential_operation_service.py     # Sequential operations
├── api/
│   ├── bulk_operations.py                  # Bulk API endpoints
│   └── sequential_operations.py            # Sequential API endpoints
└── static/
    ├── js/
    │   ├── bulk-editor.js                  # Tabular editor UI
    │   └── sequential-builder.js           # Sequential builder UI
```

### Modified Files
```
app/
├── api/
│   └── __init__.py                         # Register new blueprints
├── templates/
│   └── entries.html                       # Add bulk UI elements
└── static/
    └── js/
        └── entries.js                      # Add bulk selection handlers
```

## Implementation Checklist

### Phase 1: Enhanced Tabular Editor

#### Step 1: Service Layer
- [ ] Create `app/services/bulk_operations_service.py`
- [ ] Implement `BulkOperationsService` class
- [ ] Add `convert_traits()` method
- [ ] Add `update_pos_bulk()` method
- [ ] Add factory function `get_bulk_operations_service()`

#### Step 2: API Endpoints
- [ ] Create `app/api/bulk_operations.py`
- [ ] Add `convert_traits()` endpoint
- [ ] Add `update_pos_bulk()` endpoint
- [ ] Register blueprint in `app/api/__init__.py`

#### Step 3: Frontend JavaScript
- [ ] Create `app/static/js/bulk-editor.js`
- [ ] Implement `BulkEditor` class
- [ ] Add selection handlers
- [ ] Add operation modals
- [ ] Add execution logic

#### Step 4: Template Integration
- [ ] Modify `app/templates/entries.html`
- [ ] Add bulk select column
- [ ] Add bulk action panel
- [ ] Include bulk-editor.js

#### Step 5: Tests
- [ ] Unit tests for `BulkOperationsService`
- [ ] Integration tests for API endpoints
- [ ] Performance tests for 1000+ entries

### Phase 2: Sequential Operation Builder

#### Step 1: Service Layer
- [ ] Create `app/services/sequential_operation_service.py`
- [ ] Implement `SequentialOperationService` class
- [ ] Add `execute_sequence()` method
- [ ] Add `preview_sequence()` method

#### Step 2: API Endpoints
- [ ] Create `app/api/sequential_operations.py`
- [ ] Add `preview()` endpoint
- [ ] Add `execute()` endpoint
- [ ] Register blueprint

#### Step 3: Frontend JavaScript
- [ ] Create `app/static/js/sequential-builder.js`
- [ ] Implement `SequentialOperationBuilder` class
- [ ] Add operation adding UI
- [ ] Add preview functionality
- [ ] Add execution logic

#### Step 4: Integration
- [ ] Connect to bulk editor selection
- [ ] Add toggle button to entries page
- [ ] Integrate with operation history

#### Step 5: Tests
- [ ] Unit tests for sequential service
- [ ] Integration tests for sequence execution
- [ ] UI tests for builder interface

### Phase 3: Performance & Polish

#### Step 1: Optimization
- [ ] Add batch processing (100 entries at a time)
- [ ] Implement progress tracking
- [ ] Add client-side caching
- [ ] Optimize database queries

#### Step 2: Monitoring
- [ ] Add analytics logging
- [ ] Track performance metrics
- [ ] Monitor error rates

#### Step 3: Documentation
- [ ] Update API docs with flasgger
- [ ] Add user guide section
- [ ] Create migration examples

## Code Patterns to Follow

### Service Pattern
```python
class BulkOperationsService:
    def __init__(self, dictionary_service, workset_service, history_service):
        self.dictionary = dictionary_service
        self.workset = workset_service
        self.history = history_service
    
    def convert_traits(self, entry_ids, from_trait, to_trait):
        # Reuse existing entry update logic
        results = []
        for entry_id in entry_ids:
            entry = self.dictionary.get_entry(entry_id)
            modified = entry.convert_trait(from_trait, to_trait)
            updated = self.dictionary.update_entry(entry_id, modified)
            self.history.record_operation(...)
            results.append({'id': entry_id, 'status': 'success'})
        return {'results': results}
```

### API Pattern
```python
@bulk_bp.route('/traits/convert', methods=['POST'])
@swag_from({...})
@require_auth
def convert_traits():
    data = request.get_json()
    service = get_bulk_operations_service()
    result = service.convert_traits(
        data['entry_ids'],
        data['from_trait'],
        data['to_trait']
    )
    return jsonify(result)
```

### Frontend Pattern
```javascript
class BulkEditor {
    constructor() {
        this.selectedEntries = new Set();
        this.validationUI = new ValidationUI();
        this.init();
    }
    
    init() {
        this.setupSelectionHandlers();
        this.setupOperationHandlers();
    }
    
    setupSelectionHandlers() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('bulk-select-checkbox')) {
                // Handle selection
            }
        });
    }
}
```

## Testing Commands

### Run Tests
```bash
# Unit tests
python -m pytest tests/unit/test_bulk_operations_service.py -v

# Integration tests
python -m pytest tests/integration/test_bulk_operations_integration.py -v

# Performance tests
python -m pytest tests/integration/test_bulk_performance.py -v -m performance

# All tests
python -m pytest tests/unit/test_bulk* tests/integration/test_bulk* -v
```

### Coverage
```bash
python -m pytest --cov=app.services.bulk_operations_service --cov-report=html
```

## Common Issues & Solutions

### Issue: "Bulk operations not appearing"
**Solution**: Check that `bulk-editor.js` is loaded and `BulkEditor` is initialized on entries page

### Issue: "Selection not working"
**Solution**: Verify event delegation is set up correctly and checkboxes have `data-entry-id` attribute

### Issue: "API returns 404"
**Solution**: Ensure blueprints are registered in `app/api/__init__.py`

### Issue: "Performance slow with 1000+ entries"
**Solution**: Implement batch processing in service layer

## Quick Start Commands

### 1. Create Service Files
```bash
touch app/services/bulk_operations_service.py
touch app/services/sequential_operation_service.py
```

### 2. Create API Files
```bash
touch app/api/bulk_operations.py
touch app/api/sequential_operations.py
```

### 3. Create Frontend Files
```bash
touch app/static/js/bulk-editor.js
touch app/static/js/sequential-builder.js
```

### 4. Run Initial Tests
```bash
# Create empty test files
touch tests/unit/test_bulk_operations_service.py
touch tests/integration/test_bulk_operations_integration.py

# Run to verify structure
python -m pytest tests/unit/test_bulk_operations_service.py -v
```

## Key Files to Reference

### Existing Services
- `app/services/dictionary_service.py` - Entry operations
- `app/services/workset_service.py` - Entry collections
- `app/services/operation_history_service.py` - Undo/redo

### Existing APIs
- `app/api/entries.py` - Entry endpoints
- `app/api/worksets.py` - Workset endpoints

### Existing Frontend
- `app/static/js/entries.js` - Entry list UI
- `app/static/js/validation-ui.js` - Validation display
- `app/static/js/entry-form.js` - Form patterns

### Existing Templates
- `app/templates/entries.html` - Entry list page
- `app/templates/base.html` - Base template

## Development Workflow

### 1. Start Development
```bash
# Activate virtual environment
source .venv/bin/activate

# Start Flask app
python run.py

# In another terminal, run tests
python -m pytest tests/unit/test_bulk* -v --tb=short
```

### 2. Test-Driven Development
```python
# 1. Write failing test
def test_bulk_trait_conversion():
    # Test will fail initially
    pass

# 2. Implement minimal code to pass
class BulkOperationsService:
    def convert_traits(self, entry_ids, from_trait, to_trait):
        return {'results': []}

# 3. Run test to verify
# 4. Add more tests and refine implementation
```

### 3. Integration Testing
```bash
# Test API endpoints
python -m pytest tests/integration/test_bulk_operations_integration.py -v

# Test performance
python -m pytest tests/integration/test_bulk_performance.py -v -m performance
```

### 4. Final Verification
```bash
# Run all bulk-related tests
python -m pytest tests/unit/test_bulk* tests/integration/test_bulk* -v

# Check coverage
python -m pytest --cov=app.services.bulk_operations_service --cov-report=term-missing
```

## Success Criteria

### Phase 1 Complete When:
- [ ] Bulk trait conversion works for 10+ entries
- [ ] Bulk POS update works for 10+ entries
- [ ] Selection UI works correctly
- [ ] API endpoints return proper responses
- [ ] Unit tests pass (>90% coverage)
- [ ] Integration tests pass
- [ ] Performance <5s for 1000 entries

### Phase 2 Complete When:
- [ ] Sequential builder UI works
- [ ] Preview functionality works
- [ ] Sequence execution works
- [ ] Integration with operation history
- [ ] All tests pass

### Phase 3 Complete When:
- [ ] Performance optimized
- [ ] Documentation complete
- [ ] User guide updated
- [ ] All tests pass
- [ ] Code review approved

## Support Resources

### Existing Code to Study
- `app/services/merge_split_service.py` - Complex operations
- `app/static/js/entry-form.js` - Form patterns
- `app/static/js/validation-ui.js` - UI patterns

### Test Examples
- `tests/unit/test_dictionary_service.py` - Service tests
- `tests/integration/test_entries_api.py` - API tests

### Documentation
- `specification.md` - Project requirements
- `API_DOCUMENTATION.md` - API patterns
- `AGENTS.md` - Development guidelines

---

**Remember**: The key to success is following existing patterns and reusing existing code. Don't reinvent the wheel - extend what's already working!