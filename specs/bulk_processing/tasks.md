# Implementation Plan: Bulk Processing

This document outlines the implementation tasks for the Bulk Processing feature, based on the requirements in `specification.md`.

1.  [ ] **Bulk Processing Framework**
    *   This epic covers the design and implementation of a framework for performing bulk operations on entries.

    1.1. [ ] **Design Bulk Operation Architecture**
        *   Design a flexible and scalable architecture for performing bulk operations on entries.
        *   The UI will use a table metaphor (spreadsheet-like view on a database) with sortable and filtrable (through search and maybe otherwise) columns, hidden/shown, reordered.
        *   **Requirements**: `3.2`, `8.1.1`, `18.2`

    1.2. [ ] **Implement Atomic Transaction Support**
        *   Implement support for atomic transactions to ensure data consistency during bulk operations.
        *   **Requirements**: `3.2.1`, `5.4.2`, `18.2`

    1.3. [ ] **Add Progress Tracking for Long Operations**
        *   Implement progress tracking for long-running bulk operations to provide feedback to the user.
        *   **Requirements**: `3.2.1`, `8.1.1`, `18.2`

    1.4. [ ] **Create Rollback and Recovery Mechanisms**
        *   Implement mechanisms for rolling back and recovering from failed bulk operations.
        *   **Requirements**: `3.2.1`, `5.4.3`, `18.2`


## Decision: remove Postgres-backed FastCorpusProcessor (2026-01-17)

- Summary: The `FastCorpusProcessor` and its PostgreSQL-backed integration tests were removed because corpus processing is implemented without Postgres (Lucene-based pipeline). Keeping the old Postgres-centric implementation caused test/coverage noise and confusion.
- Files affected: `app/services/fast_corpus_processor.py`, `app/models/corpus_batch.py`, `tests/integration/test_fast_corpus_processing.py`, `.env.example` (removed `CORPUS_BATCH_SIZE`).
- Rationale: no production code depends on the Postgres implementation; the feature is covered by the Lucene-based implementation and CI should not carry dead, skipped integration suites.
- Follow-up: create an issue/PR to delete demo scripts and docs that reference the removed implementation if any remain.
