# Corpus PostgreSQL to Lucene Migration Plan

> **DEPRECATED:** The PostgreSQL-based `CorpusMigrator` has been removed from the codebase (see changelog). Corpus data and corpus-related endpoints now use Lucene services; this document is retained for historical context and planning reference.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate all corpus-related PostgreSQL queries to use Lucene, removing dependency on `parallel_corpus` table. Keep PostgreSQL only for worksets and project settings.

**Architecture:**
- Use existing Lucene corpus service (port 8082) for concordance, frequency, and stats queries
- Remove all `current_app.pg_pool` calls for corpus operations
- Replace with Lucene `CorpusClient` calls
- Keep PostgreSQL for worksets (complex relational queries) and project settings (SQLAlchemy)

**Tech Stack:**
- Python Flask app
- Lucene corpus service (`FlexTools.scripts.corpus_client.CorpusClient`)
- PostgreSQL (worksets, project_settings only)
- psycopg2 for remaining DB operations

**Context from analysis:**
- `parallel_corpus` table has 74,740,856 rows (unused, will be replaced by Lucene)
- `word_sketches`, `subtlex_norms`, `frequency_analysis` tables exist in code but never created in DB
- Worksets table has 293 rows, workset_entries has 3,318 rows (keep in PostgreSQL)
- Lucene API: `/concordance`, `/count`, `/compare`, `/health` endpoints available

---

## Migration Tasks

### Task 1: Remove parallel_corpus table usage from corpus_migrator.py

**Files:**
- Modify: `app/database/corpus_migrator.py`
- Test: `tests/unit/test_corpus_migrator.py`

**Step 1: Write the failing test**

```python
def test_concordance_uses_lucene_not_postgres():
    """Concordance queries should use Lucene, not PostgreSQL."""
    from app.database.corpus_migrator import CorpusMigrator

    migrator = CorpusMigrator()
    # Verify no pg_pool attribute exists for corpus operations
    assert not hasattr(migrator, 'pg_pool') or migrator.pg_pool is None

    # Verify Lucene client is used
    assert hasattr(migrator, 'lucene_client')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_corpus_migrator.py::test_concordance_uses_lucene_not_postgres -v`
Expected: FAIL with "AttributeError: 'CorpusMigrator' has no attribute 'lucene_client'"

**Step 3: Write minimal implementation**

```python
class CorpusMigrator:
    def __init__(self):
        from FlexTools.scripts.corpus_client import CorpusClient
        self.lucene_client = CorpusClient(
            base_url=current_app.config.get('LUCENE_CORPUS_URL', 'http://localhost:8082')
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_corpus_migrator.py::test_concordance_uses_lucene_not_postgres -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_corpus_migrator.py app/database/corpus_migrator.py
git commit -m "feat(corpus): add Lucene client to CorpusMigrator"
```

---

### Task 2: Migrate concordance endpoint to use Lucene

**Files:**
- Modify: `app/routes/corpus_routes.py`
- Test: `tests/integration/test_corpus_concordance.py`

**Step 1: Write the failing test**

```python
def test_corpus_concordance_uses_lucene(migrated_app_client):
    """GET /corpus/concordance should call Lucene, not PostgreSQL."""
    response = migrated_app_client.get('/corpus/concordance?q=house&limit=10')
    assert response.status_code == 200
    data = response.get_json()
    assert 'hits' in data or 'results' in data
    # Should not contain postgres-related fields
    assert 'parallel_corpus' not in str(data)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_corpus_concordance.py::test_corpus_concordance_uses_lucene -v`
Expected: FAIL - endpoint still uses PostgreSQL

**Step 3: Write minimal implementation**

```python
@bp.route('/concordance', methods=['GET'])
def concordance():
    """Get KWIC concordance from Lucene corpus index."""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 50, type=int)

    total, hits = app.corpus_migrator.lucene_client.concordance(query, limit=limit)

    return jsonify({
        'query': query,
        'total': total,
        'hits': [{'left': h.left, 'match': h.match, 'right': h.right} for h in hits]
    })
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_corpus_concordance.py::test_corpus_concordance_uses_lucene -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/routes/corpus_routes.py tests/integration/test_corpus_concordance.py
git commit -m "feat(corpus): migrate concordance endpoint to Lucene"
```

---

### Task 3: Migrate frequency count endpoint to Lucene

**Files:**
- Modify: `app/routes/corpus_routes.py`
- Test: `tests/integration/test_corpus_frequency.py`

**Step 1: Write the failing test**

```python
def test_corpus_count_uses_lucene(migrated_app_client):
    """GET /corpus/count should use Lucene."""
    response = migrated_app_client.get('/corpus/count?q=house')
    assert response.status_code == 200
    data = response.get_json()
    assert 'count' in data
    assert isinstance(data['count'], int)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_corpus_frequency.py::test_corpus_count_uses_lucene -v`
Expected: FAIL - endpoint uses PostgreSQL

**Step 3: Write minimal implementation**

```python
@bp.route('/count', methods=['GET'])
def count():
    """Get term frequency from Lucene corpus index."""
    query = request.args.get('q', '')
    count = app.corpus_migrator.lucene_client.count(query)
    return jsonify({'query': query, 'count': count})
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_corpus_frequency.py::test_corpus_count_uses_lucene -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/routes/corpus_routes.py tests/integration/test_corpus_frequency.py
git commit -m "feat(corpus): migrate count endpoint to Lucene"
```

---

### Task 4: Remove PostgreSQL corpus queries from postgresql_connector.py

**Files:**
- Modify: `app/database/postgresql_connector.py`
- Test: `tests/unit/test_postgresql_connector.py`

**Step 1: Write the failing test**

```python
def test_no_corpus_queries_in_connector():
    """Connector should not have corpus-related query methods."""
    from app.database.postgresql_connector import PostgreSQLConnector

    # These methods should not exist or should raise NotImplementedError
    connector = PostgreSQLConnector()

    # Check corpus-related methods are removed or disabled
    with pytest.raises(AttributeError):
        connector.get_concordance("test")

    with pytest.raises(AttributeError):
        connector.get_parallel_corpus_stats()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_postgresql_connector.py::test_no_corpus_queries_in_connector -v`
Expected: FAIL - methods still exist

**Step 3: Write minimal implementation**

```python
class PostgreSQLConnector:
    # ... existing workset/project_settings methods remain ...

    # REMOVE or comment out these methods:
    # def get_concordance(self, query, limit=100):
    #     raise NotImplementedError("Use Lucene corpus client instead")

    # def get_parallel_corpus_stats(self):
    #     raise NotImplementedError("Use Lucene /health endpoint instead")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_postgresql_connector.py::test_no_corpus_queries_in_connector -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/database/postgresql_connector.py tests/unit/test_postgresql_connector.py
git commit -m "refactor(corpus): remove PostgreSQL corpus queries from connector"
```

---

### Task 5: Update word_sketch_service to use Lucene

**Files:**
- Modify: `app/services/word_sketch_service.py`
- Test: `tests/integration/test_word_sketch_lucene.py`

**Step 1: Write the failing test**

```python
def test_word_sketch_uses_lucene_not_postgres(migrated_app_client):
    """Word sketch queries should use Lucene, not PostgreSQL."""
    response = migrated_app_client.get('/word-sketch/house')
    assert response.status_code == 200
    data = response.get_json()
    assert 'collocations' in data
    # Verify Lucene was called (mock would show this)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_word_sketch_lucene.py::test_word_sketch_uses_lucene_not_postgres -v`
Expected: FAIL - service still uses PostgreSQL

**Step 3: Write minimal implementation**

```python
class WordSketchService:
    def __init__(self):
        from FlexTools.scripts.word_sketch_client import WordSketchClient
        self.lucene_client = WordSketchClient(
            base_url=current_app.config.get('LUCENE_WORD_SKETCH_URL', 'http://localhost:8083')
        )

    def get_word_sketch(self, lemma, pos_filter=None, min_logdice=5.0):
        """Get grammatical collocations from Lucene word-sketch index."""
        return self.lucene_client.word_sketch(lemma, pos_filter, min_logdice)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_word_sketch_lucene.py::test_word_sketch_uses_lucene_not_postgres -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/word_sketch_service.py tests/integration/test_word_sketch_lucene.py
git commit -m "feat(word-sketch): migrate to Lucene client"
```

---

### Task 6: Update Flask app initialization to remove corpus PG pool

**Files:**
- Modify: `app/__init__.py`
- Test: `tests/unit/test_app_init.py`

**Step 1: Write the failing test**

```python
def test_no_corpus_pg_pool_in_app():
    """App should not initialize pg_pool for corpus operations."""
    from app import create_app

    app = create_app()
    # pg_pool should only be used for worksets/settings, not corpus
    assert not hasattr(app, 'pg_pool') or app.pg_pool is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_app_init.py::test_no_corpus_pg_pool_in_app -v`
Expected: FAIL - pg_pool still initialized

**Step 3: Write minimal implementation**

```python
def create_app():
    app = Flask(__name__)

    # Remove corpus pg_pool initialization
    # Keep only for worksets if needed:
    # app.pg_pool = None  # or remove entirely

    # Initialize Lucene corpus client instead
    from FlexTools.scripts.corpus_client import CorpusClient
    app.corpus_client = CorpusClient(
        base_url=app.config.get('LUCENE_CORPUS_URL', 'http://localhost:8082')
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_app_init.py::test_no_corpus_pg_pool_in_app -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/__init__.py tests/unit/test_app_init.py
git commit -m "refactor(app): remove corpus pg_pool, add Lucene client"
```

---

### Task 7: Remove parallel_corpus table and related migrations

**Files:**
- Delete: `migrations/remove_parallel_corpus.sql` (create new)
- Modify: `app/database/workset_db.py` (ensure worksets still work)
- Test: `tests/integration/test_worksets_still_work.py`

**Step 1: Write the failing test**

```python
def test_worksets_still_work_after_corpus_removal(migrated_app_client):
    """Worksets should still function without parallel_corpus table."""
    # Create workset
    response = migrated_app_client.post('/api/worksets', json={'name': 'test'})
    assert response.status_code == 201

    # Add entry
    workset_id = response.get_json()['id']
    response = migrated_app_client.post(f'/api/worksets/{workset_id}/entries',
                                        json={'entry_id': 'test-123'})
    assert response.status_code == 201

    # Verify workset still accessible
    response = migrated_app_client.get(f'/api/worksets/{workset_id}')
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_worksets_still_work.py::test_worksets_still_work_after_corpus_removal -v`
Expected: PASS (worksets already independent)

**Step 3: Write migration script**

```sql
-- migrations/drop_parallel_corpus.sql
-- Run after verifying worksets don't depend on parallel_corpus

DROP TABLE IF EXISTS parallel_corpus;
DROP TABLE IF EXISTS parallel_corpus_sample;

-- Verify worksets table still exists
SELECT * FROM worksets LIMIT 1;
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_worksets_still_work.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/drop_parallel_corpus.sql
git commit -m "refactor(db): drop unused parallel_corpus tables"
```

---

### Task 8: Remove unused analytics table definitions

**Files:**
- Modify: `app/database/postgresql_connector.py`
- Test: `tests/unit/test_no_unused_table_definitions.py`

**Step 1: Write the failing test**

```python
def test_no_unused_analytics_table_definitions():
    """Analytics tables (word_sketches, subtlex_norms, etc.) should be removed."""
    from app.database.postgresql_connector import PostgreSQLConnector

    connector = PostgreSQLConnector()
    # These methods should not create unused tables
    with pytest.raises(AttributeError):
        connector.create_word_sketch_tables()

    with pytest.raises(AttributeError):
        connector._create_subtlex_norms_table()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_postgresql_connector.py::test_no_unused_analytics_table_definitions -v`
Expected: FAIL - methods still exist

**Step 3: Write minimal implementation**

```python
class PostgreSQLConnector:
    # REMOVE: create_word_sketch_tables() method
    # REMOVE: _create_subtlex_norms_table() method
    # REMOVE: _create_frequency_analysis_table() method
    # REMOVE: _create_corpus_sentences_table() method
    # REMOVE: _create_linguistic_cache_table() method
    # REMOVE: _create_processing_batches_table() method
    # REMOVE: create_performance_indexes() (word-sketch related parts)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_postgresql_connector.py::test_no_unused_analytics_table_definitions -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/database/postgresql_connector.py
git commit -m "refactor(db): remove unused analytics table definitions"
```

---

### Task 9: Update environment configuration

**Files:**
- Modify: `.env.example`
- Create: `.env` (if needed)
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
def test_lucene_urls_in_config():
    """Environment should have Lucene URLs configured."""
    from app import create_app

    app = create_app()
    assert app.config.get('LUCENE_CORPUS_URL') is not None
    assert '8082' in app.config.get('LUCENE_CORPUS_URL', '')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py::test_lucene_urls_in_config -v`
Expected: FAIL - config not set

**Step 3: Write minimal implementation**

Add to `.env.example`:
```bash
# Lucene Corpus Service (replaces parallel_corpus table)
LUCENE_CORPUS_URL=http://localhost:8082

# Lucene Word Sketch Service (replaces word_sketches table)
LUCENE_WORD_SKETCH_URL=http://localhost:8083
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py::test_lucene_urls_in_config -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .env.example
git commit -m "config: add Lucene service URLs"
```

---

### Task 10: Run full integration test suite

**Files:**
- Test: `tests/integration/test_corpus_lucene_migration.py`

**Step 1: Write comprehensive integration test**

```python
def test_full_corpus_migration(migrated_app_client):
    """Verify all corpus operations use Lucene."""
    # Concordance
    resp = migrated_app_client.get('/corpus/concordance?q=house&limit=5')
    assert resp.status_code == 200
    assert 'hits' in resp.get_json()

    # Count
    resp = migrated_app_client.get('/corpus/count?q=house')
    assert resp.status_code == 200
    assert resp.get_json()['count'] >= 0

    # Stats
    resp = migrated_app_client.get('/corpus/stats')
    assert resp.status_code == 200

    # Word sketch
    resp = migrated_app_client.get('/word-sketch/house')
    assert resp.status_code == 200
    assert 'collocations' in resp.get_json()

    # Worksets still work
    resp = migrated_app_client.post('/api/worksets', json={'name': 'test'})
    assert resp.status_code == 201
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_corpus_lucene_migration.py::test_full_corpus_migration -v`
Expected: FAIL (some endpoints not migrated yet)

**Step 3: Fix any remaining issues**

Address failures from previous task tests.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_corpus_lucene_migration.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/integration/test_corpus_lucene_migration.py
git commit -m "test: add full corpus migration integration test"
```

---

## Summary

| Task | Files Modified | Key Change |
|------|----------------|------------|
| 1 | corpus_migrator.py | Add Lucene client |
| 2 | corpus_routes.py | Concordance → Lucene |
| 3 | corpus_routes.py | Count → Lucene |
| 4 | postgresql_connector.py | Remove corpus queries |
| 5 | word_sketch_service.py | Word sketch → Lucene |
| 6 | app/__init__.py | Remove corpus pg_pool |
| 7 | migrations/*.sql | Drop parallel_corpus tables |
| 8 | postgresql_connector.py | Remove analytics definitions |
| 9 | .env.example | Add Lucene config |
| 10 | tests/*.py | Full integration test |

## Post-Migration PostgreSQL Tables

After migration, PostgreSQL will only contain:

| Schema | Table | Purpose |
|--------|-------|---------|
| public | worksets | User collections (keep) |
| public | workset_entries | Workset entries (keep) |
| public | project_settings | App config (keep) |
| public | users | Auth (keep) |
| public | display_profiles | Display settings (keep) |

**Removed:**
- `parallel_corpus` (replaced by Lucene)
- `parallel_corpus_sample` (unused)
- `word_sketches` (never created, word-sketch index in Lucene)
- `subtlex_norms` (never created, compute from Lucene)
- `frequency_analysis` (never created)
- `corpus_sentences` (never created)
- `linguistic_cache` (never created)
- `processing_batches` (never created)
- `sketch_grammars` (never created)

---

## Execution Notes

- **Reference:** See `docs/word-sketch-lucene-migration.md` for word-sketch architecture
- **Reference:** See `docs/corpus-lucene-api.md` for Lucene API documentation
- **Key dependency:** `FlexTools.scripts.corpus_client.CorpusClient`
- **Testing:** Mock Lucene service for unit tests, use real service for integration tests
