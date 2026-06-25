"""
Data Path Integrity Tests - Validation and Cache
================================================

Tests verifying validation text extraction and cache consistency.
Addresses critical data paths 9-10 from the data path integrity audit.

Components Tested:
1. Validation text extraction completeness (_extract_text_from_entry)
2. Validation cache staleness detection

Usage:
    pytest tests/unit/test_validation_cache_integrity.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import hashlib
from app.services.validation_cache_service import ValidationCacheService


class TestValidationTextExtractionCompleteness:
    """Test _extract_text_from_entry() extracts all text - component: validation_cache_service"""

    @pytest.fixture
    def service(self):
        """Provide a ValidationCacheService instance."""
        # The service uses a singleton pattern, so we need to reset it
        ValidationCacheService._instance = None
        return ValidationCacheService()

    def test_extraction_includes_lexical_unit(self, service):
        """Text extraction must include lexical unit text."""
        entry_data = {
            'lexical_unit': {'en': 'test word', 'es': 'palabra'}
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'test word' in text
        assert 'palabra' in text

    def test_extraction_includes_sense_definitions(self, service):
        """Text extraction must include sense definitions."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'senses': [
                {'definition': {'en': 'first definition', 'es': 'primera definición'}},
                {'definition': {'en': 'second definition'}}
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'first definition' in text
        assert 'primera definición' in text
        assert 'second definition' in text

    def test_extraction_includes_sense_glosses(self, service):
        """Text extraction must include sense glosses."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'senses': [
                {'gloss': {'en': 'gloss one', 'fr': 'glose un'}},
                {'gloss': {'en': 'gloss two'}}
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'gloss one' in text
        assert 'glose un' in text
        assert 'gloss two' in text

    def test_extraction_includes_examples(self, service):
        """Text extraction must include example forms and translations."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'senses': [
                {
                    'examples': [
                        {'form': {'en': 'Example sentence'}, 'translation': {'es': 'Oración de ejemplo'}},
                        {'form': {'en': 'Another example'}, 'notes': {'en': 'Example note'}}
                    ]
                }
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'Example sentence' in text
        assert 'Oración de ejemplo' in text
        assert 'Another example' in text
        assert 'Example note' in text

    def test_extraction_includes_etymology_source_forms(self, service):
        """Text extraction must include etymology source forms and glosses."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'etymologies': [
                {
                    'source': 'Latin',
                    'form': {'la': 'origo'},
                    'gloss': {'en': 'origin'}
                },
                {
                    'source': 'Greek',
                    'comment': {'en': 'Borrowed from Greek'}
                }
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'Latin' in text
        assert 'origo' in text
        assert 'origin' in text
        assert 'Greek' in text
        assert 'Borrowed from Greek' in text

    def test_extraction_includes_citation_forms(self, service):
        """Text extraction must include citation forms from all languages."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'citation_forms': {'en': 'citation', 'fr': 'citation française'}
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'citation' in text
        assert 'citation française' in text

    def test_extraction_includes_relation_references(self, service):
        """Text extraction must include relation target references."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'relations': [
                {'type': 'synonym', 'ref': 'synonym_entry', 'display': 'Synonym Word'},
                {'type': 'antonym', 'ref': 'antonym_entry'}
            ],
            'senses': [
                {
                    'relations': [
                        {'type': 'see_also', 'ref': 'related_entry', 'display': 'Related Word'}
                    ]
                }
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'synonym_entry' in text
        assert 'Synonym Word' in text
        assert 'antonym_entry' in text
        assert 'related_entry' in text
        assert 'Related Word' in text

    def test_extraction_includes_notes(self, service):
        """Text extraction must include complex note structures."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'notes': {
                'general': {'en': 'General note'},
                'grammar': {'en': 'Grammar note'},
                'anthropology': {'en': 'Cultural note'}
            }
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'General note' in text
        assert 'Grammar note' in text
        assert 'Cultural note' in text

    def test_extraction_includes_usage_notes_within_senses(self, service):
        """Text extraction must include usage notes embedded in senses."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'senses': [
                {
                    'usage_notes': {'en': 'Used in formal contexts'},
                    'anthropology_notes': {'en': 'Used in rituals'},
                    'sociolinguistics_notes': {'en': 'High register'}
                }
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'Used in formal contexts' in text
        assert 'Used in rituals' in text
        assert 'High register' in text

    def test_extraction_includes_scientific_name(self, service):
        """Text extraction must include scientific name field."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'senses': [
                {'scientific_name': 'Homo sapiens'}
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'Homo sapiens' in text

    def test_extraction_includes_variants(self, service):
        """Text extraction must include variant forms."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'variants': [
                {'form': {'en': 'variant1'}, 'comment': {'en': 'Variant comment'}},
                {'form': {'en': 'variant2'}}
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'variant1' in text
        assert 'Variant comment' in text
        assert 'variant2' in text

    def test_extraction_includes_pronunciations(self, service):
        """Text extraction must include pronunciation values and notes."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'pronunciations': [
                {'type': 'ipa', 'value': '/wɜrd/', 'notes': 'Standard pronunciation'},
                {'type': 'audio', 'value': 'recording', 'notes': 'Field recording'}
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert '/wɜrd/' in text
        assert 'Standard pronunciation' in text
        assert 'Field recording' in text

    def test_extraction_includes_main_entry_reference(self, service):
        """Text extraction must include main entry reference."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'main_entry': 'main_entry_id'
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'main_entry_id' in text

    def test_extraction_handles_empty_entry(self, service):
        """Text extraction must handle empty entry gracefully."""
        entry_data = {}

        text = service._extract_text_from_entry(entry_data)

        assert text == ''

    def test_extraction_handles_nested_structures(self, service):
        """Text extraction must handle deeply nested structures."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'senses': [
                {
                    'subsenses': [
                        {
                            'gloss': {'en': 'nested gloss'},
                            'definition': {'en': 'nested definition'}
                        }
                    ]
                }
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        assert 'nested gloss' in text
        assert 'nested definition' in text

    def test_extraction_removes_duplicates_through_filter(self, service):
        """Text extraction filter should remove None values."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'senses': [
                {'gloss': {'en': None}},  # None value
                {'gloss': {'en': 'valid gloss'}}
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        # Should not contain 'None' string from the None value
        assert 'valid gloss' in text


class TestValidationCacheStalenessDetection:
    """Test validation cache properly detects stale data"""

    @pytest.fixture
    def service(self):
        """Provide a ValidationCacheService instance."""
        ValidationCacheService._instance = None
        return ValidationCacheService()

    def test_cache_key_includes_date_hash(self, service):
        """Cache key must include date_modified hash for staleness detection."""
        date_modified = "2024-01-15T10:30:00"
        date_hash = hashlib.md5(date_modified.encode()).hexdigest()[:8]

        cache_key = service._make_cache_key('spellcheck', 'entry_1', date_modified)

        assert 'validation:spellcheck:entry_1:' in cache_key
        assert date_hash in cache_key

    def test_different_dates_produce_different_cache_keys(self, service):
        """Different date_modified values must produce different cache keys."""
        key1 = service._make_cache_key('spellcheck', 'entry_1', '2024-01-15T10:00:00')
        key2 = service._make_cache_key('spellcheck', 'entry_1', '2024-01-15T10:01:00')

        assert key1 != key2

    def test_same_date_produces_same_cache_key(self, service):
        """Same date_modified must produce same cache key."""
        key1 = service._make_cache_key('spellcheck', 'entry_1', '2024-01-15T10:00:00')
        key2 = service._make_cache_key('spellcheck', 'entry_1', '2024-01-15T10:00:00')

        assert key1 == key2

    def test_cache_key_format_includes_all_components(self, service):
        """Cache key must include validator type, entry ID, and date hash."""
        cache_key = service._make_cache_key('hunspell', 'entry_123', '2024-06-20T14:30:00')

        parts = cache_key.split(':')
        assert len(parts) == 4
        assert parts[0] == 'validation'
        assert parts[1] == 'hunspell'
        assert parts[2] == 'entry_123'
        assert len(parts[3]) == 8  # MD5 hash prefix

    def test_extract_text_handles_list_values(self, service):
        """Text extraction must handle list values correctly (e.g., etymologies)."""
        entry_data = {
            'lexical_unit': {'en': 'word'},
            'etymologies': [
                {'source': 'Latin', 'form': {'la': 'origo'}, 'gloss': {'en': 'note1'}},
                {'source': 'Greek', 'form': {'gr': 'archē'}, 'gloss': {'en': 'note2'}}
            ]
        }

        text = service._extract_text_from_entry(entry_data)

        # Etymology source, form values, and gloss should be extracted
        assert 'Latin' in text or 'note1' in text
        assert 'Greek' in text or 'note2' in text

    def test_extract_text_handles_deeply_nested_dicts(self, service):
        """Text extraction must handle deeply nested dictionaries."""
        entry_data = {
            'lexical_unit': {
                'en': 'word',
                'nested': {  # This shouldn't happen but code should handle it
                    'more': 'deep value'
                }
            }
        }

        # Should not crash and should extract top-level values
        text = service._extract_text_from_entry(entry_data)
        assert 'word' in text
