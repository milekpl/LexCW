# Service Unification: Autosave, Operation History & Backup Coordination

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate redundancy between autosave (simulated), operation history, and backup scheduler by creating a unified event-driven coordination layer. Autosave becomes functional, backups become incremental, and operation history integrates with both.

**Architecture:**
1. Create `EventBus` service (signal/slot pattern with topics)
2. Wire autosave API to actually persist entries via DictionaryService
3. Connect EventBus to OperationHistoryService (record on entry changes)
4. Connect EventBus to BackupScheduler (incremental decisions)
5. Delete dead autosave files
6. Remove unused backup_manager/backup_scheduler params from DictionaryService

**Tech Stack:**
- Python: Vanilla signal/slot implementation (no new deps)
- Existing: APScheduler, Flask, DictionaryService
- Tests: pytest with existing fixtures

---

## Plan

### Phase 1: Event Bus Foundation

#### Task 1: Create EventBus service

**Files:**
- Create: `app/services/event_bus.py`
- Test: `tests/unit/test_event_bus.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_event_bus.py
import pytest
from app.services.event_bus import EventBus

def test_event_bus_emit_and_receive():
    bus = EventBus()
    received = []

    def handler(data):
        received.append(data)

    bus.on('entry_updated', handler)
    bus.emit('entry_updated', {'id': 'test-entry', 'action': 'update'})

    assert len(received) == 1
    assert received[0]['id'] == 'test-entry'

def test_event_bus_unsubscribe():
    bus = EventBus()
    call_count = [0]

    def handler(data):
        call_count[0] += 1

    bus.on('entry_updated', handler)
    bus.off('entry_updated', handler)
    bus.emit('entry_updated', {'id': 'test'})

    assert call_count[0] == 0

def test_event_bus_multiple_handlers():
    bus = EventBus()
    calls = []

    bus.on('entry_updated', lambda d: calls.append('a'))
    bus.on('entry_updated', lambda d: calls.append('b'))

    bus.emit('entry_updated', {})

    assert len(calls) == 2
    assert 'a' in calls
    assert 'b' in calls
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_event_bus.py -v
# Expected: ERROR - import error (file doesn't exist)
```

**Step 3: Write minimal implementation**

```python
# app/services/event_bus.py
"""
Simple event bus with signal/slot pattern for service coordination.
"""
from typing import Dict, List, Callable, Any

class EventBus:
    """
    Lightweight event bus for inter-service communication.

    Provides signal/slot pattern with topic support. Services can:
    - Subscribe to events via `on(event, callback)`
    - Unsubscribe via `off(event, callback)`
    - Emit events via `emit(event, data)`
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to an event."""
        if event not in self._subscribers:
            self._subscribers[event] = []
        if callback not in self._subscribers[event]:
            self._subscribers[event].append(callback)

    def off(self, event: str, callback: Callable[[Any], None]) -> None:
        """Unsubscribe from an event."""
        if event in self._subscribers:
            self._subscribers[event] = [c for c in self._subscribers[event] if c != callback]

    def emit(self, event: str, data: Any) -> None:
        """Emit an event to all subscribers."""
        for callback in self._subscribers.get(event, []):
            callback(data)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_event_bus.py -v
# Expected: PASS (3 tests)
```

**Step 5: Commit**

```bash
git add app/services/event_bus.py tests/unit/test_event_bus.py
git commit -m "feat: add EventBus service for inter-service coordination"
```

---

#### Task 2: Register EventBus in dependency injection

**Files:**
- Modify: `app/__init__.py` (find DI setup section)

**Step 1: Read current DI configuration**

```bash
grep -n "injector\|Singleton\|Factory" app/__init__.py | head -30
```

**Step 2: Add EventBus registration**

Add after other service registrations (exact line TBD after reading):

```python
# EventBus for service coordination
injector.binder.bind(EventBus, scope=Singleton)
```

**Step 3: Verify no test failures**

```bash
python -m pytest tests/unit/ -v --tb=short -q 2>&1 | tail -20
```

**Step 4: Commit**

```bash
git add app/__init__.py
git commit -m "feat: register EventBus in dependency injection"
```

---

### Phase 2: Wire Autosave to DictionaryService

#### Task 3: Modify autosave to actually persist entries

**Files:**
- Modify: `app/api/entry_autosave_working.py`
- Test: `tests/unit/test_autosave.py`

**Step 1: Read current autosave implementation**

```bash
cat app/api/entry_autosave_working.py
```

**Step 2: Write failing test**

```python
# tests/unit/test_autosave.py
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

def test_autosave_persists_entry(monkeypatch):
    """Autosave should call DictionaryService.update_entry()"""
    from app.api.entry_autosave_working import autosave_entry

    mock_dictionary_service = Mock()
    mock_dictionary_service.update_entry.return_value = {'id': 'test', 'version': '1.0'}

    with patch('app.api.entry_autosave_working.get_dictionary_service', return_value=mock_dictionary_service):
        with patch('app.api.entry_autosave_working.get_event_bus') as mock_bus:
            mock_bus.return_value = Mock()

            result = autosave_entry(
                entry_data={'id': 'test', 'lexical_unit': {'en': 'test'}},
                version='1.0'
            )

            mock_dictionary_service.update_entry.assert_called_once()
            assert result['success'] == True
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/unit/test_autosave.py -v
# Expected: FAIL - function signature different or not implemented
```

**Step 4: Write implementation**

```python
# In app/api/entry_autosave_working.py, replace autosave_entry function:

@autosave_bp.route('/api/entry/autosave', methods=['POST'])
def autosave_entry():
    """Auto-save entry data with validation and persistence."""
    from flask import current_app
    from app.services.event_bus import EventBus

    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': 'No JSON data provided'
            }), 400

        entry_data = data.get('entryData')
        client_version = data.get('version', 'unknown')
        timestamp = data.get('timestamp')

        if not entry_data:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': 'Missing entryData'
            }), 400

        # Validate the entry data using centralized validation
        validator = ValidationEngine()
        validation_result = validator.validate_json(entry_data)

        critical_errors = [e for e in validation_result.errors if e.priority == ValidationPriority.CRITICAL]
        if critical_errors:
            return jsonify({
                'success': False,
                'error': 'validation_failed',
                'validation_errors': [...],
                'message': f'Cannot save due to {len(critical_errors)} critical validation errors'
            }), 400

        # Get services from injector
        dictionary_service = current_app.injector.get(DictionaryService)
        event_bus = current_app.injector.get(EventBus)

        # Persist the entry
        entry_id = entry_data.get('id')
        updated_entry = dictionary_service.update_entry(entry_id, entry_data)

        # Emit event for other services
        event_bus.emit('entry_updated', {
            'entry_id': entry_id,
            'source': 'autosave',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        new_version = str(datetime.now(timezone.utc).timestamp())

        response = {
            'success': True,
            'newVersion': new_version,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': 'Entry auto-saved successfully'
        }

        if validation_result.warnings:
            response['warnings'] = [...]

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in autosave: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_autosave.py -v
# Expected: PASS
```

**Step 6: Commit**

```bash
git add app/api/entry_autosave_working.py tests/unit/test_autosave.py
git commit -m "feat: wire autosave to DictionaryService persistence"
```

---

#### Task 4: Delete dead autosave files

**Files:**
- Delete: `app/api/entry_autosave.py`
- Delete: `app/api/entry_autosave_simple.py`
- Verify: Check `app/__init__.py` for any references to deleted files

**Step 1: Check for references**

```bash
grep -r "entry_autosave_simple\|entry_autosave\.py" app/
```

**Step 2: Delete files**

```bash
rm app/api/entry_autosave.py app/api/entry_autosave_simple.py
```

**Step 3: Verify app still starts**

```bash
python -c "from app import create_app; app = create_app(); print('OK')"
```

**Step 4: Commit**

```bash
git rm app/api/entry_autosave.py app/api/entry_autosave_simple.py
git commit -m "chore: remove dead autosave implementations"
```

---

### Phase 3: Connect OperationHistoryService to EventBus

#### Task 5: Wire OperationHistoryService to listen for entry updates

**Files:**
- Modify: `app/services/operation_history_service.py`
- Test: `tests/unit/test_operation_history_service.py`

**Step 1: Write failing test**

```python
# tests/unit/test_operation_history_service.py
def test_listens_to_entry_updated_event(monkeypatch):
    """OperationHistoryService should record operations when entry_updated is emitted."""
    from app.services.operation_history_service import OperationHistoryService

    mock_event_bus = Mock()
    service = OperationHistoryService(event_bus=mock_event_bus)

    # Verify on() was called
    mock_event_bus.on.assert_called_with('entry_updated', service._on_entry_updated)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_operation_history_service.py::test_listens_to_entry_updated_event -v
# Expected: FAIL - event_bus param doesn't exist
```

**Step 3: Read OperationHistoryService constructor**

```bash
head -30 app/services/operation_history_service.py
```

**Step 4: Modify constructor to accept EventBus**

```python
def __init__(self, history_file_path: str = 'instance/operation_history.json',
             max_history: int = 100, event_bus: Optional['EventBus'] = None):
    # Existing init code...
    self.event_bus = event_bus
    if event_bus:
        event_bus.on('entry_updated', self._on_entry_updated)
```

**Step 5: Add event handler method**

```python
def _on_entry_updated(self, data: Dict[str, Any]):
    """Handle entry_updated events from EventBus."""
    # Record the autosave as an update operation
    self.record_operation(
        operation_type='autosave',
        data=data,
        entry_id=data.get('entry_id'),
        user_id='autosave',  # System user for autosaves
        db_name=None
    )
```

**Step 6: Run test to verify it passes**

```bash
pytest tests/unit/test_operation_history_service.py::test_listens_to_entry_updated_event -v
# Expected: PASS
```

**Step 7: Commit**

```bash
git add app/services/operation_history_service.py
git commit -m "feat: wire OperationHistoryService to EventBus for autosave tracking"
```

---

### Phase 4: Connect BackupScheduler to EventBus

#### Task 6: Make BackupScheduler increment-aware

**Files:**
- Modify: `app/services/backup_scheduler.py`
- Test: `tests/unit/test_backup_scheduler.py`

**Step 1: Write failing test**

```python
def test_skips_backup_when_no_changes(monkeypatch):
    """Backup should not run if _dirty flag is False."""
    from app.services.backup_scheduler import BackupScheduler

    mock_backup_manager = Mock()
    scheduler = BackupScheduler(backup_manager=mock_backup_manager)

    # No dirty flag set - should skip
    scheduler._dirty = False
    scheduler._execute_scheduled_backup()

    mock_backup_manager.backup.assert_not_called()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_backup_scheduler.py::test_skips_backup_when_no_changes -v
# Expected: FAIL - _dirty attribute not handled
```

**Step 3: Modify _execute_scheduled_backup to check dirty flag**

```python
def _execute_scheduled_backup(self, scheduled_backup: ScheduledBackup):
    """Execute a scheduled backup job, skipping if no changes."""
    # Check if any changes occurred since last backup
    if not getattr(self, '_dirty', True):  # Default to True for first run
        self.logger.info(f"No changes since last backup for {scheduled_backup.db_name}, skipping")
        return

    try:
        # Reset dirty flag
        self._dirty = False

        # Existing backup logic...
        result = self.backup_manager.backup(scheduled_backup.db_name, backup_path)

        if result['success']:
            scheduled_backup.last_run = datetime.now()
            scheduled_backup.last_status = 'success'
            self.logger.info(f"Backup completed for {scheduled_backup.db_name}")
        else:
            scheduled_backup.last_status = 'failed'

    except Exception as e:
        scheduled_backup.last_status = 'failed'
        self.logger.error(f"Backup failed: {str(e)}")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_backup_scheduler.py::test_skips_backup_when_no_changes -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add app/services/backup_scheduler.py
git commit -m "feat: add dirty flag check to skip unnecessary backups"
```

---

#### Task 7: Wire BackupScheduler to EventBus

**Files:**
- Modify: `app/services/backup_scheduler.py`
- Test: `tests/unit/test_backup_scheduler.py`

**Step 1: Write failing test**

```python
def test_sets_dirty_on_entry_updated(monkeypatch):
    """BackupScheduler should set _dirty=True when entry_updated is emitted."""
    from app.services.backup_scheduler import BackupScheduler

    mock_event_bus = Mock()
    mock_backup_manager = Mock()
    scheduler = BackupScheduler(backup_manager=mock_backup_manager, event_bus=mock_event_bus)

    # Trigger the event handler
    handler = mock_event_bus.on.call_args_list[0][0][1]  # Get the callback
    handler({'entry_id': 'test'})

    assert scheduler._dirty == True
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_backup_scheduler.py::test_sets_dirty_on_entry_updated -v
# Expected: FAIL - event_bus param not handled
```

**Step 3: Modify BackupScheduler constructor**

```python
def __init__(self, backup_manager: BaseXBackupManager,
             event_bus: Optional['EventBus'] = None):
    # Existing init...
    self._dirty = True  # First run always does backup

    if event_bus:
        event_bus.on('entry_updated', self._on_entry_updated)

def _on_entry_updated(self, data: Dict[str, Any]):
    """Handle entry_updated events - mark backup as needed."""
    self._dirty = True
    self.logger.debug(f"Entry {data.get('entry_id')} updated, backup needed")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_backup_scheduler.py::test_sets_dirty_on_entry_updated -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add app/services/backup_scheduler.py
git commit -m "feat: wire BackupScheduler to EventBus for incremental backup"
```

---

### Phase 5: Cleanup DictionaryService

#### Task 8: Remove unused backup_manager and backup_scheduler params

**Files:**
- Modify: `app/services/dictionary_service.py`
- Test: `tests/unit/test_dictionary_service.py`

**Step 1: Write failing test**

```python
def test_dictionary_service_no_unused_params():
    """DictionaryService should not accept unused backup_manager/backup_scheduler."""
    import inspect
    sig = inspect.signature(DictionaryService.__init__)
    params = list(sig.parameters.keys())

    assert 'backup_manager' not in params, "backup_manager should be removed"
    assert 'backup_scheduler' not in params, "backup_scheduler should be removed"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_dictionary_service.py::test_dictionary_service_no_unused_params -v
# Expected: FAIL - params still exist
```

**Step 3: Remove unused parameters from DictionaryService.__init__**

```python
# Remove from __init__ signature:
def __init__(self, db_connector: Union[BaseXConnector, MockDatabaseConnector],
             history_service: Optional['OperationHistoryService'] = None):
    # Remove:
    # backup_manager: Optional['BaseXBackupManager'] = None,
    # backup_scheduler: Optional['BackupScheduler'] = None

    # Remove attribute assignments:
    # self.backup_manager = backup_manager
    # self.backup_scheduler = backup_scheduler
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_dictionary_service.py::test_dictionary_service_no_unused_params -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add app/services/dictionary_service.py
git commit -m "refactor: remove unused backup params from DictionaryService"
```

---

### Phase 6: Integration Tests

#### Task 9: Write full integration test

**Files:**
- Create: `tests/integration/test_service_unification.py`

**Step 1: Write integration test**

```python
"""
Integration test: Verify EventBus coordinates autosave, history, and backup.
"""
import pytest
from unittest.mock import Mock, patch

def test_autosave_triggers_history_and_marks_backup_dirty():
    """Full flow: autosave → persist → emit event → history records → backup marked dirty"""
    from app.services.event_bus import EventBus
    from app.services.operation_history_service import OperationHistoryService
    from app.services.backup_scheduler import BackupScheduler

    event_bus = EventBus()

    # Create services with shared event bus
    history_service = OperationHistoryService(event_bus=event_bus)
    mock_backup_manager = Mock()
    backup_scheduler = BackupScheduler(backup_manager=mock_backup_manager, event_bus=event_bus)

    # Verify initial state
    assert backup_scheduler._dirty == True  # First run

    # Simulate entry update from autosave
    event_bus.emit('entry_updated', {
        'entry_id': 'entry-123',
        'source': 'autosave',
        'timestamp': '2025-01-04T10:00:00Z'
    })

    # Verify backup is marked dirty
    assert backup_scheduler._dirty == True

    # Verify operation was recorded in history
    history = history_service.get_operation_history()
    autosave_ops = [op for op in history if op.get('type') == 'autosave']
    assert len(autosave_ops) == 1
    assert autosave_ops[0].get('entry_id') == 'entry-123'
```

**Step 2: Run integration test**

```bash
pytest tests/integration/test_service_unification.py -v
# Expected: PASS
```

**Step 3: Commit**

```bash
git add tests/integration/test_service_unification.py
git commit -m "test: add integration test for service unification"
```

---

### Phase 7: Final Verification

#### Task 10: Run full test suite

**Files:**
- All modified files

**Step 1: Run all tests**

```bash
python -m pytest tests/unit/ tests/integration/ -v --tb=short -q 2>&1 | tail -50
```

**Step 2: Verify app starts**

```bash
python -c "from app import create_app; app = create_app(); print('App created successfully')"
```

**Step 3: Final commit**

```bash
git status
git add -A
git commit -m "feat: unify autosave, operation history, and backup coordination"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `app/services/event_bus.py` | Created (new) |
| `app/api/entry_autosave_working.py` | Wired to DictionaryService |
| `app/api/entry_autosave.py` | Deleted (dead code) |
| `app/api/entry_autosave_simple.py` | Deleted (dead code) |
| `app/services/operation_history_service.py` | Added EventBus listener |
| `app/services/backup_scheduler.py` | Added EventBus listener + dirty flag |
| `app/services/dictionary_service.py` | Removed unused params |
| `app/__init__.py` | Registered EventBus in DI |

## Testing Commands

```bash
# Run all tests
pytest tests/unit/ tests/integration/ -v --tb=short

# Run specific test file
pytest tests/unit/test_event_bus.py -v
pytest tests/integration/test_service_unification.py -v

# Verify app loads
python -c "from app import create_app; app = create_app(); print('OK')"
```

---

**Plan complete and saved to `docs/plans/2025-01-04-service-unification.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
