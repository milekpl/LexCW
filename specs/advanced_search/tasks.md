# Implementation Plan: Advanced Search

This document outlines the implementation tasks for the Advanced Search feature, based on the requirements in `specification.md`.

1.  [x] **Advanced Search Features**
    *   This epic covers the implementation of advanced search features.

    1.1. [x] **Add Faceted Search Navigation**
        *   Add faceted search navigation to allow users to filter search results by different criteria.
        *   **Requirements**: `7.3`, `18.2`
        *   **Status**: ✅ Done — sidebar with grammatical-info facets, click to filter, remove filter.

    1.2. [x] **Create Semantic Similarity Search**
        *   Create a semantic similarity search that allows users to find entries that are semantically similar to a given query.
        *   **Requirements**: `3.2.2`, `8.1.2`, `18.2`
        *   **Status**: ✅ Done — `EmbeddingService` with Qdrant vector backend, GPU CUDA acceleration, multiple transformer models (`jinaai/jina-embeddings-v3`, `paraphrase-multilingual-mpnet-base-v2`, `all-MiniLM-L6-v2`), `/api/embeddings/search`, background rebuild job with live decimal progress and Stop Indexing control.

    1.3. [x] **Add Search Result Export Capabilities**
        *   Add the ability to export search results to different formats, such as CSV and JSON.
        *   **Requirements**: `3.2.2`, `18.2`
        *   **Status**: ✅ Done — CSV and JSON download buttons in search results.

2.  [ ] **Analysis Tools**
    *   This epic covers the implementation of analysis tools.

    2.1. [x] **Build Duplicate Detection Algorithms**
        *   Build algorithms for detecting duplicate entries.
        *   **Requirements**: `3.4.1`, `18.2`
        *   **Status**: ✅ Done — Exact/Near headword Levenshtein duplicate detection, Qdrant semantic duplicate detection via cosine similarity (`EmbeddingService.find_semantic_duplicates`), and orphaned phrase Subentry Discovery scan mode (`discover_subentries`).

    2.2. [x] **Implement Statistical Analysis Dashboard**
        *   Implement a dashboard for displaying statistical analysis of the dictionary data.
        *   **Requirements**: `3.4.2`, `18.2`
        *   **Status**: ✅ Done — `app/api/dashboard.py` `/stats` endpoint & `dashboard.html` displaying headword composition charts, PoS distribution, and sense statistics.

    2.3. [x] **Add Data Completeness Assessment**
        *   Add a tool for assessing the completeness of the dictionary data.
        *   **Requirements**: `3.4.2`, `18.2`
        *   **Status**: ✅ Done — `app/api/dashboard.py` `/quality` metrics endpoint calculating completeness scores for missing definitions, missing glosses, missing pronunciations, and incomplete entries.

    2.4. [x] **Create Anomaly Detection System**
        *   Create a system for detecting anomalies in the dictionary data.
        *   **Requirements**: `3.4.2`, `12.2`, `18.2`
        *   **Status**: ✅ Done — `POSCoherenceService` (`app/services/pos_coherence_service.py`) with `/api/dashboard/anomalies` endpoint for POS/definition anomalies. `IPAAnomalyService` (`app/services/ipa_anomaly_service.py`) with validation rule R4.3.1. Dual-model G2P anomaly detector in `scripts/ipa_training/g2p/anomaly_detector.py`. Unit tests for both IPA anomaly service and validation rule.

3.  [x] **UI Testing with Playwright**
    *   This epic covers the implementation of a comprehensive UI testing suite for the advanced search page using Playwright.

    3.1. [x] **Write Comprehensive Tests for the Advanced Search Page**
        *   Write a comprehensive suite of tests for the advanced search page, covering all features, including:
            *   Faceted search.
            *   Semantic similarity search.
            *   Exporting search results.
        *   **Status**: ✅ 14 E2E tests and 12 unit tests covering faceted search, search-within-results, export, save/load.
