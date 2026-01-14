# dictionary_service.py Refactoring Design

**Date:** 2026-01-03
**Author:** Code Analysis
**Status:** Approved

---

## Overview

Refactor `dictionary_service.py` (~3,800 lines) by extracting specialized services while maintaining backward compatibility. The current file handles CRUD, search, import/export, ranges, bidirectional relations, and XML processing in a single monolithic class.

## Goals

1. **Single Responsibility Principle** - Split into focused services
2. **Maintainability** - Reduce cognitive load, eliminate dead code
3. **Testability** - Easier to test specialized components
4. **Backward Compatibility** - Preserve existing API signatures

---

## Architecture

### Current State

```
dictionary_service.py (3,800 lines)
├── Entry CRUD (get_entry, create_entry, update_entry, delete_entry)
├── Search (search_entries, list_entries, count_entries)
├── Import/Export (import_lift_*, export_lift, initialize_database)
├── Ranges (get_ranges, get_lift_ranges, scan_and_create_custom_ranges)
├── Bidirectional Relations (_handle_bidirectional_relations)
└── XML/Namespace Processing (_prepare_entry_xml, _detect_namespace_usage)
```

### Proposed Structure

```
app/services/
├── entry_service.py (~800 lines)          # Entry CRUD operations
├── search_service.py (~500 lines)          # Search & listing
├── bidirectional_service.py (~400 lines)   # Relation management
├── xml_processing_service.py (~300 lines)  # XML & namespace utilities
├── database_utils.py (~200 lines)          # Shared DB helpers
├── dictionary_service.py (~400 lines)      # Facade (backward compatible)
│
# Existing files (enhanced):
├── lift_import_service.py                  # Import logic moved here
├── ranges_service.py                       # Already exists
└── lift_export_service.py                  # Already exists
```

---

## Component Specifications

### 1. database_utils.py

Shared utilities for database operations.

```python
# app/services/database_utils.py

def get_db_name(
    db_connector,
    project_id: Optional[int] = None,
    logger: Optional[logging.Logger] = None
) -> str:
    """Resolve database name, checking project-specific settings if needed.

    Replaces 15+ duplicate patterns throughout the codebase.

    Raises:
        DatabaseError: If no database is configured.
    """

def kill_blocking_sessions(
    connector,
    db_name: str,
    max_retries: int = 5
) -> bool:
    """Kill BaseX sessions blocking database operations.

    Returns:
        True if successful, False otherwise.
    """

def close_database_gracefully(
    connector,
    db_name: str,
    logger: Optional[logging.Logger] = None
) -> None:
    """Safely close database with error suppression."""
```

### 2. entry_service.py

Core entry CRUD operations.

```python
# app/services/entry_service.py

class EntryService:
    """Service for managing dictionary entries."""

    def __init__(
        self,
        db_connector: Union[BaseXConnector, MockDatabaseConnector],
        ranges_service: Optional[RangesService] = None,
        xml_service: Optional['XMLProcessingService'] = None
    ):
        self.db_connector = db_connector
        self.ranges_service = ranges_service
        self.xml_service = xml_service or XMLProcessingService()
        self.logger = logging.getLogger(__name__)
        self.lift_parser = LIFTParser(validate=False)

    def get_entry(
        self,
        entry_id: str,
        project_id: Optional[int] = None
    ) -> Entry:
        """Retrieve single entry by ID.

        Raises:
            NotFoundError: If entry does not exist.
            DatabaseError: If there is a retrieval error.
        """

    def create_entry(
        self,
        entry: Entry,
        project_id: Optional[int] = None,
        draft: bool = False,
        skip_validation: bool = False
    ) -> str:
        """Create new entry.

        Returns:
            ID of the created entry.
        """

    def update_entry(
        self,
        entry: Entry,
        project_id: Optional[int] = None,
        skip_validation: bool = False
    ) -> None:
        """Update existing entry."""

    def delete_entry(
        self,
        entry_id: str,
        project_id: Optional[int] = None
    ) -> bool:
        """Delete entry by ID.

        Returns:
            True if deleted, False if not found.
        """

    def entry_exists(
        self,
        entry_id: str,
        project_id: Optional[int] = None
    ) -> bool:
        """Check if entry exists."""
```

### 3. search_service.py

Search and listing operations.

```python
# app/services/search_service.py

class SearchService:
    """Service for searching and listing dictionary entries."""

    def __init__(
        self,
        db_connector: Union[BaseXConnector, MockDatabaseConnector],
        entry_service: Optional[EntryService] = None
    ):
        self.db_connector = db_connector
        self.entry_service = entry_service
        self.xquery_builder = XQueryBuilder()
        self.logger = logging.getLogger(__name__)

    def search_entries(
        self,
        query: str = "",
        project_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Tuple[List[Entry], int]:
        """Full-text search with pagination.

        Returns:
            Tuple of (entries, total_count).
        """

    def list_entries(
        self,
        project_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
        sort_order: str = "asc",
        filter_text: Optional[str] = None
    ) -> Tuple[List[Entry], int]:
        """List entries with pagination, sorting, and filtering.

        Returns:
            Tuple of (entries, total_count).
        """

    def count_entries(
        self,
        project_id: Optional[int] = None,
        filter_text: Optional[str] = None
    ) -> int:
        """Count total or filtered entries."""

    def _count_entries_with_filter(
        self,
        filter_text: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> int:
        """Internal: count entries matching filter."""
```

### 4. bidirectional_service.py

Bidirectional relation management.

```python
# app/services/bidirectional_service.py

class BidirectionalService:
    """Service for managing bidirectional lexical relations."""

    def __init__(
        self,
        entry_service: EntryService,
        db_connector: Union[BaseXConnector, MockDatabaseConnector]
    ):
        self.entry_service = entry_service
        self.db_connector = db_connector
        self.logger = logging.getLogger(__name__)

    def handle_bidirectional_relations(
        self,
        entry: Entry,
        project_id: Optional[int] = None
    ) -> None:
        """Process all bidirectional relations for an entry.

        Creates/updates/deletes reverse relations based on the entry's
        lexical-relation elements. Uses internal flag to prevent
        infinite recursion.
        """

    def create_reverse_relation(
        self,
        target_guid: str,
        relation_type: str,
        entry: Entry,
        project_id: Optional[int] = None
    ) -> None:
        """Create reverse relation on target entry."""

    def remove_reverse_relation(
        self,
        target_guid: str,
        relation_type: str,
        entry: Entry,
        project_id: Optional[int] = None
    ) -> None:
        """Remove reverse relation from target entry."""
```

### 5. xml_processing_service.py

XML and namespace utilities.

```python
# app/services/xml_processing_service.py

class XMLProcessingService:
    """Service for XML processing and namespace handling."""

    def __init__(self):
        self.lift_parser = LIFTParser(validate=False)
        self.namespace_manager = LIFTNamespaceManager()
        self.query_builder = XQueryBuilder()
        self._has_namespace: Optional[bool] = None
        self.logger = logging.getLogger(__name__)

    def prepare_entry_xml(self, entry: Entry) -> str:
        """Generate XML string, stripping namespaces.

        Returns:
            XML string without namespace prefixes.
        """

    def detect_namespace_usage(
        self,
        db_name: str,
        db_connector
    ) -> Dict[str, bool]:
        """Detect if entries use namespaces in database.

        Returns:
            Dict with 'has_namespace' boolean.
        """

    def build_entry_query(
        self,
        entry_id: str,
        db_name: str,
        has_namespace: bool = False
    ) -> str:
        """Build XQuery for retrieving entry by ID."""
```

### 6. lift_import_service.py (Enhanced)

Existing file gets import methods moved from dictionary_service.py.

```python
# app/services/lift_import_service.py (additions)

class LIFTImportService:
    # ... existing methods ...

    def initialize_database(
        self,
        lift_path: str,
        ranges_path: Optional[str] = None
    ) -> None:
        """Initialize DB from LIFT file."""

    def import_lift_replace(
        self,
        lift_path: str,
        ranges_path: Optional[str] = None
    ) -> int:
        """Replace all entries with LIFT content.

        Returns:
            Number of entries imported.
        """

    def import_lift_merge(
        self,
        lift_path: str,
        ranges_path: Optional[str] = None
    ) -> int:
        """Merge LIFT content with existing entries.

        Returns:
            Number of entries imported/updated.
        """

    # Methods consolidated from dictionary_service.py:
    # - _import_lift_with_ranges
    # - _import_lift_replace_with_ranges
    # - _import_lift_merge_with_ranges
    # - _import_lift_merge_continue
```

### 7. dictionary_service.py (Facade)

Facade class maintains backward compatibility.

```python
# app/services/dictionary_service.py

class DictionaryService:
    """Facade orchestrating all dictionary operations.

    Maintains backward compatibility while delegating to specialized services.
    All existing public method signatures are preserved.
    """

    def __init__(
        self,
        db_connector: Union[BaseXConnector, MockDatabaseConnector],
        history_service: Optional['OperationHistoryService'] = None,
        backup_manager: Optional['BaseXBackupManager'] = None,
        backup_scheduler: Optional['BackupScheduler'] = None
    ):
        # Create specialized services
        self._entry_service = EntryService(db_connector)
        self._search_service = SearchService(db_connector, self._entry_service)
        self._bidirectional_service = BidirectionalService(
            self._entry_service, db_connector
        )
        self._xml_service = XMLProcessingService()
        self._lift_import_service = LIFTImportService(db_connector)

        # Preserve existing attributes for compatibility
        self.db_connector = db_connector
        self.history_service = history_service
        self.backup_manager = backup_manager
        self.backup_scheduler = backup_scheduler
        self.logger = logging.getLogger(__name__)

        # Testing mode check (existing logic)
        if not (os.getenv("TESTING") == "true" or "pytest" in sys.modules):
            self._initialize_connection()

    # Delegate to specialized services
    def get_entry(self, entry_id: str, project_id: Optional[int] = None) -> Entry:
        return self._entry_service.get_entry(entry_id, project_id)

    def create_entry(self, entry: Entry, **kwargs) -> str:
        return self._entry_service.create_entry(entry, **kwargs)

    def update_entry(self, entry: Entry, **kwargs) -> None:
        # Handle bidirectional relations
        self._entry_service.update_entry(entry, **kwargs)
        if not kwargs.get('skip_bidirectional', False):
            self._bidirectional_service.handle_bidirectional_relations(entry, kwargs.get('project_id'))

    # ... similar delegation for all other methods ...
```

---

## Code Quality Improvements

### 1. Remove Dead Code

Remove commented-out blocks like lines 2133-2170 that are remnants of refactoring.

### 2. Replace Bare `except:` Clauses

```python
# Before:
except:
    pass  # Database might not be open, that's fine

# After:
except DatabaseError as e:
    self.logger.debug("Database close error (may be expected): %s", e)
except Exception as e:
    self.logger.warning("Unexpected error during disconnect: %s", e)
```

### 3. Replace Print Statements with Logger

```python
# Before:
print(f"Executing query for entry: {entry_id}")

# After:
self.logger.debug("Executing query for entry: %s", entry_id)
```

### 4. Remove Test Hardcoding

The hardcoded `test_pronunciation_entry` logic should be removed from production code.

---

## Test Coverage

### Tests Directly Using DictionaryService

| Test File | Type | Coverage |
|-----------|------|----------|
| `tests/unit/test_dictionary_service_search.py` | Unit | Search, namespace handling |
| `tests/unit/test_dictionary_service_filtering.py` | Unit | List/filter/sort |
| `tests/unit/test_lift_import_fixes.py` | Unit | `find_ranges_file` |
| `tests/unit/test_import_lift_drop_retry.py` | Unit | Import retry logic |
| `tests/integration/test_dictionary_service.py` | Integration | Full CRUD + import/export |
| `tests/integration/test_advanced_crud.py` | Integration | Complex entries, errors |
| `tests/integration/test_entry_update.py` | Integration | Update operations |
| `tests/integration/test_database_drop_integration.py` | Integration | Drop/reinit |
| `tests/integration/test_xml_service_basex.py` | Integration | Full lifecycle |

### Test Fixtures to Update

- `tests/conftest.py`: `dict_service_with_db`, `populated_dict_service`
- `tests/unit/conftest.py`: `mock_dict_service`

### Assumptions to Preserve

1. **Constructor signature:** `DictionaryService(db_connector, history_service=None, backup_manager=None, backup_scheduler=None)`
2. **Testing mode:** `os.getenv("TESTING") == "true"` skips auto-connect
3. **Public API methods:** All existing method signatures unchanged
4. **Return types:** Preserved (e.g., `list_entries` → `Tuple[List[Entry], int]`)
5. **Exception types:** `NotFoundError`, `ValidationError`, `DatabaseError`

---

## Files to Create/Modify

### New Files

1. `app/services/entry_service.py`
2. `app/services/search_service.py`
3. `app/services/bidirectional_service.py`
4. `app/services/xml_processing_service.py`
5. `app/services/database_utils.py`

### Modified Files

1. `app/services/dictionary_service.py` - Convert to facade
2. `app/services/lift_import_service.py` - Add import methods
3. `app/services/__init__.py` - Update exports if needed

### Test Files (Updates Only)

1. `tests/conftest.py` - Update fixtures
2. `tests/unit/conftest.py` - Update fixtures

---

## Estimated Impact

| Metric | Before | After |
|--------|--------|-------|
| dictionary_service.py | 3,800 lines | ~400 lines |
| Total service lines | ~3,800 | ~3,400 (distributed) |
| Methods with duplicate DB logic | 15+ | 0 |
| Bare except clauses | 10+ | 0 |
| Print statements | 6+ | 0 |
| Dead code blocks | 2+ | 0 |

---

## Implementation Order

1. Create `database_utils.py` with shared helpers
2. Create `xml_processing_service.py`
3. Create `entry_service.py`
4. Create `search_service.py`
5. Create `bidirectional_service.py`
6. Enhance `lift_import_service.py` with import methods
7. Convert `dictionary_service.py` to facade
8. Update test fixtures
9. Run all tests to verify compatibility
10. Remove old dead code from dictionary_service.py

---

## Backward Compatibility

The facade pattern ensures:
- All existing method calls continue to work
- Constructor signature unchanged
- Return types preserved
- Exception types preserved
- Tests can migrate incrementally

---

## Related Files

- `app/services/ranges_service.py` - Already exists, integrate as needed
- `app/services/lift_export_service.py` - Already exists
- `app/services/merge_split_service.py` - Already exists
- `app/utils/xquery_builder.py` - Used by search_service
- `app/utils/namespace_manager.py` - Used by xml_processing_service
