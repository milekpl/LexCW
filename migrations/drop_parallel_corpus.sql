-- Migration: Drop parallel_corpus and related unused tables
-- Date: 2026-01-15
-- Purpose: Remove PostgreSQL corpus tables that have been replaced by Lucene

-- Run this script in the dictionary_analytics database

-- Check if we're in the right database
SELECT current_database();

-- Drop unused corpus/analytics tables
-- These tables were defined in code but never populated or are now obsolete

DROP TABLE IF EXISTS parallel_corpus CASCADE;
DROP TABLE IF EXISTS parallel_corpus_sample CASCADE;

-- Word sketch tables (never created in production)
DROP TABLE IF EXISTS word_sketches CASCADE;
DROP TABLE IF EXISTS sketch_grammars CASCADE;
DROP TABLE IF EXISTS subtlex_norms CASCADE;
DROP TABLE IF EXISTS frequency_analysis CASCADE;
DROP TABLE IF EXISTS corpus_sentences CASCADE;
DROP TABLE IF EXISTS linguistic_cache CASCADE;
DROP TABLE IF EXISTS processing_batches CASCADE;

-- Verify worksets table still exists
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('worksets', 'workset_entries');

-- Verify project settings tables still exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'project_%';
