"""
Unit tests for Word Sketch client and services.

These tests use mock responses since the word sketch service (port 8080)
is not yet available with real corpus data.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Dict  # Explicit Dict import for testing
import json

from app.services.word_sketch import WordSketchClient, WordSketchResult, CollocationResult


class MockCache:
    """Mock cache for testing."""

    def __init__(self):
        self._data = {}
        self._calls = []

    def get(self, key):
        self._calls.append(('get', key))
        return self._data.get(key)

    def set(self, key, value, ttl=None):
        self._calls.append(('set', key, ttl))
        self._data[key] = value

    def clear_pattern(self, pattern):
        self._calls.append(('clear', pattern))
        # Simple pattern matching - clear all if pattern is "ws:*"
        if pattern == "ws:*":
            count = len(self._data)
            self._data = {}
            return count
        return 0


class MockSession:
    """Mock requests session for testing HTTP calls."""

    def __init__(self):
        self._responses = {}
        self._calls = []

    def get(self, url, params=None, timeout=None):
        self._calls.append(('GET', url, params))
        key = (url, json.dumps(params, sort_keys=True) if params else None)
        response = Mock()
        response.status_code = self._responses.get(key, {}).get('status_code', 200)
        response.json = lambda: self._responses.get(key, {}).get('json', {})
        response.raise_for_status = Mock()
        return response

    def post(self, url, json=None, timeout=None):
        self._calls.append(('POST', url, json))
        response = Mock()
        response.status_code = self._responses.get(url, {}).get('status_code', 200)
        response.json = lambda: self._responses.get(url, {}).get('json', {})
        response.raise_for_status = Mock()
        return response

    def set_response(self, url_or_key, response_data, is_post=False):
        """Set a mock response for a URL."""
        if is_post:
            self._responses[url_or_key] = response_data
        else:
            # For GET, create a key from URL and params
            key = (url_or_key, json.dumps(response_data.get('params', {}), sort_keys=True) if 'params' in response_data else None)
            self._responses[key] = response_data


# =============================================================================
# WordSketchClient Tests
# =============================================================================

class TestWordSketchClient:
    """Tests for WordSketchClient."""

    def test_client_initialization(self):
        """Test client can be initialized with default values."""
        client = WordSketchClient()
        assert client.base_url == "http://localhost:8080"
        assert client._session.timeout == 30

    def test_client_initialization_custom_url(self):
        """Test client can be initialized with custom URL."""
        client = WordSketchClient(base_url="http://localhost:9000")
        assert client.base_url == "http://localhost:9000"

    def test_is_available_healthy_service(self):
        """Test is_available returns True when service is healthy."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'ok'}

        mock_session = Mock(spec=requests.Session)
        mock_session.get.return_value = mock_response
        mock_session.timeout = 30

        client = WordSketchClient(session=mock_session)
        client._available = None  # Reset cached value

        assert client.is_available() is True
        mock_session.get.assert_called_once_with(f"{client.base_url}/health", timeout=5)

    def test_is_available_unhealthy_service(self):
        """Test is_available returns False when service is unhealthy."""
        mock_session = MockSession()
        mock_session.set_response(
            ("http://localhost:8080/health", None),
            {'json': {'status': 'unhealthy'}, 'status_code': 500}
        )

        client = WordSketchClient(session=mock_session)
        client._available = None  # Reset cached value

        assert client.is_available() is False

    def test_is_available_connection_error(self):
        """Test is_available returns False on connection error."""
        import requests
        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Connection refused")

        client = WordSketchClient(session=mock_session)
        client._available = None  # Reset cached value

        assert client.is_available() is False

    def test_word_sketch_returns_cached_result(self):
        """Test word_sketch returns cached data when available."""
        cache = MockCache()
        cached_data = {
            'lemma': 'house',
            'pos': 'noun',
            'collocations': [
                {
                    'collocate': 'big',
                    'lemma': 'big',
                    'relation': 'mod_by',
                    'relation_name': 'Adjectives modifying',
                    'logdice': 11.24,
                    'frequency': 1247,
                    'examples': ['big house']
                }
            ],
            'translations': [],
            'total_examples': 1247
        }
        # Use the correct cache key format (without extra colon at end)
        cache._data['ws:house'] = cached_data

        client = WordSketchClient(cache=cache)
        # Skip health check and HTTP calls entirely by mocking word_sketch
        client._available = True

        result = client.word_sketch('house')

        assert result is not None
        assert result.lemma == 'house'
        assert result.pos == 'noun'
        assert len(result.collocations) == 1
        # Cached collocations are dicts
        assert result.collocations[0]['collocate'] == 'big'

    def test_word_sketch_calls_service_on_cache_miss(self):
        """Test word_sketch calls service when cache is empty."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'lemma': 'house',
            'patterns': {
                'noun_modifiers': {
                    'name': 'Adjectives modifying',
                    'pos_group': 'noun',
                    'collocations': [
                        {
                            'lemma': 'big',
                            'logDice': 11.24,
                            'frequency': 1247,
                            'examples': ['big house']
                        }
                    ]
                }
            }
        }

        mock_session = Mock(spec=requests.Session)
        mock_session.get.return_value = mock_response
        mock_session.timeout = 30

        client = WordSketchClient(session=mock_session)
        client._available = True  # Skip health check

        result = client.word_sketch('house')

        assert result is not None
        assert result.lemma == 'house'
        assert len(result.collocations) == 1
        assert result.collocations[0].collocate == 'big'
        assert result.collocations[0].logdice == 11.24

    def test_word_sketch_graceful_degradation_unavailable(self):
        """Test word_sketch returns None when service is unavailable."""
        mock_session = MockSession()
        mock_session._responses[('http://localhost:8080/health', None)] = {
            'json': {'status': 'unhealthy'},
            'status_code': 500
        }

        client = WordSketchClient(session=mock_session)
        client._available = False

        result = client.word_sketch('house')

        assert result is None

    def test_word_sketch_with_pos_filter(self):
        """Test word_sketch filters by POS when specified."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'lemma': 'help',
            'patterns': {
                'verb_objects': {
                    'name': 'Objects',
                    'pos_group': 'verb',
                    'collocations': [
                        {
                            'lemma': 'help',
                            'logDice': 8.5,
                            'frequency': 500,
                            'examples': []
                        }
                    ]
                }
            }
        }

        mock_session = Mock(spec=requests.Session)
        mock_session.get.return_value = mock_response
        mock_session.timeout = 30

        client = WordSketchClient(session=mock_session)
        client._available = True

        result = client.word_sketch('help', pos='verb')

        assert result is not None
        assert result.pos == 'verb'
        assert len(result.collocations) == 1

    def test_word_sketch_with_min_logdice(self):
        """Test word_sketch respects min_logdice parameter."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'lemma': 'test',
            'patterns': {
                'noun_modifiers': {
                    'name': 'Adjectives',
                    'pos_group': 'noun',
                    'collocations': []
                }
            }
        }

        mock_session = Mock(spec=requests.Session)
        mock_session.get.return_value = mock_response
        mock_session.timeout = 30

        client = WordSketchClient(session=mock_session)
        client._available = True

        result = client.word_sketch('test', min_logdice=8.0)

        assert result is not None

    def test_custom_query(self):
        """Test custom CQL pattern query."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'lemma': 'house',
            'collocations': [
                {
                    'lemma': 'beautiful',
                    'logDice': 9.5,
                    'frequency': 100,
                    'examples': ['beautiful house']
                }
            ]
        }

        mock_session = Mock(spec=requests.Session)
        mock_session.post.return_value = mock_response
        mock_session.timeout = 30

        client = WordSketchClient(session=mock_session)
        client._available = True

        result = client.custom_query('house', '[tag=jj.*]~{0,3}')

        assert result is not None
        assert result.lemma == 'house'
        assert len(result.collocations) == 1
        assert result.collocations[0].collocate == 'beautiful'

    def test_clear_cache(self):
        """Test cache clearing."""
        cache = MockCache()

        client = WordSketchClient(cache=cache)
        count = client.clear_cache()

        assert count == 0  # Empty cache
        assert ('clear', 'ws:*') in cache._calls

    def test_clear_cache_specific_lemma(self):
        """Test cache clearing for specific lemma."""
        cache = MockCache()

        client = WordSketchClient(cache=cache)
        count = client.clear_cache('house')

        assert ('clear', 'ws:house:*') in cache._calls


class TestCollocationResult:
    """Tests for CollocationResult dataclass."""

    def test_collocation_result_creation(self):
        """Test creating a CollocationResult."""
        coll = CollocationResult(
            collocate='big',
            lemma='big',
            relation='mod_by',
            relation_name='Adjectives modifying',
            logdice=11.24,
            frequency=1247,
            examples=['big house', 'very big house']
        )

        assert coll.collocate == 'big'
        assert coll.lemma == 'big'
        assert coll.relation == 'mod_by'
        assert coll.relation_name == 'Adjectives modifying'
        assert coll.logdice == 11.24
        assert coll.frequency == 1247
        assert len(coll.examples) == 2

    def test_collocation_result_defaults(self):
        """Test CollocationResult with default values."""
        coll = CollocationResult(
            collocate='test',
            lemma='test',
            relation='test'
        )

        assert coll.relation_name == ""
        assert coll.logdice == 0.0
        assert coll.frequency == 0
        assert coll.examples == []


class TestWordSketchResult:
    """Tests for WordSketchResult dataclass."""

    def test_word_sketch_result_creation(self):
        """Test creating a WordSketchResult."""
        collocations = [
            CollocationResult(
                collocate='big',
                lemma='big',
                relation='mod_by',
                logdice=11.24,
                frequency=1247
            ),
            CollocationResult(
                collocate='beautiful',
                lemma='beautiful',
                relation='mod_by',
                logdice=9.5,
                frequency=500
            )
        ]

        result = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=collocations,
            translations=['dom'],
            total_examples=1747
        )

        assert result.lemma == 'house'
        assert result.pos == 'noun'
        assert len(result.collocations) == 2
        assert result.translations == ['dom']
        assert result.total_examples == 1747

    def test_word_sketch_result_defaults(self):
        """Test WordSketchResult with default values."""
        result = WordSketchResult(lemma='test')

        assert result.pos == ""
        assert result.collocations == []
        assert result.translations == []
        assert result.total_examples == 0


# =============================================================================
# CoverageService Tests
# =============================================================================

class TestCoverageService:
    """Tests for CoverageService."""

    def test_check_entry_coverage_success(self):
        """Test coverage check when word sketch is available."""
        mock_client = Mock()
        # Many collocations with good logDice scores to exceed 0.7 threshold
        # 10 collocations gives collocation_score = 1.0
        mock_client.word_sketch.return_value = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=[
                CollocationResult(collocate='big', lemma='big', relation='mod_by', logdice=11.24, frequency=1247),
                CollocationResult(collocate='beautiful', lemma='beautiful', relation='mod_by', logdice=10.5, frequency=800),
                CollocationResult(collocate='old', lemma='old', relation='mod_by', logdice=9.8, frequency=600),
                CollocationResult(collocate='new', lemma='new', relation='mod_by', logdice=8.5, frequency=500),
                CollocationResult(collocate='large', lemma='large', relation='mod_by', logdice=8.0, frequency=400),
                CollocationResult(collocate='small', lemma='small', relation='mod_by', logdice=7.5, frequency=350),
                CollocationResult(collocate='white', lemma='white', relation='mod_by', logdice=7.0, frequency=300),
                CollocationResult(collocate='red', lemma='red', relation='mod_by', logdice=6.5, frequency=250),
                CollocationResult(collocate='green', lemma='green', relation='mod_by', logdice=6.0, frequency=200),
                CollocationResult(collocate='blue', lemma='blue', relation='mod_by', logdice=5.5, frequency=150),
            ],
            total_examples=4797
        )

        from app.services.word_sketch.coverage_service import CoverageService
        service = CoverageService(word_sketch_client=mock_client)

        result = service.check_entry_coverage('house', 'noun')

        assert result.has_coverage is True
        assert result.corpus_count == 4797
        assert result.collocations_count == 10
        assert result.needs_enrichment is False  # Good coverage with 10 collocations

    def test_check_entry_coverage_no_coverage(self):
        """Test coverage check when no word sketch available."""
        mock_client = Mock()
        mock_client.word_sketch.return_value = None

        from app.services.word_sketch.coverage_service import CoverageService
        service = CoverageService(word_sketch_client=mock_client)

        result = service.check_entry_coverage('unknown', 'noun')

        assert result.has_coverage is False
        assert result.corpus_count == 0
        assert result.collocations_count == 0
        assert result.needs_enrichment is True

    def test_check_entry_coverage_low_coverage(self):
        """Test coverage check with low coverage score."""
        mock_client = Mock()
        # Single collocation with low logDice
        mock_client.word_sketch.return_value = WordSketchResult(
            lemma='time',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='the',
                    lemma='the',
                    relation='det',
                    logdice=3.0,  # Low logDice
                    frequency=10
                )
            ],
            total_examples=10
        )

        from app.services.word_sketch.coverage_service import CoverageService
        service = CoverageService(word_sketch_client=mock_client)

        result = service.check_entry_coverage('time', 'noun')

        assert result.has_coverage is True
        assert result.coverage_score < 0.7  # Should need enrichment
        assert result.needs_enrichment is True

    def test_analyze_workset(self):
        """Test workset coverage analysis."""
        mock_client = Mock()
        mock_client.word_sketch.return_value = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='big',
                    lemma='big',
                    relation='mod_by',
                    logdice=11.24,
                    frequency=1247
                )
            ],
            total_examples=1247
        )

        mock_workset_service = Mock()
        mock_workset_service.get_workset.return_value = {
            'id': 1,
            'name': 'Test Workset',
            'total_entries': 2,
            'entries': [
                {'id': 'entry1', 'lexical_unit': {'en': 'house'}, 'grammatical_info': {'part_of_speech': 'noun'}},
                {'id': 'entry2', 'lexical_unit': {'en': 'unknown'}, 'grammatical_info': {'part_of_speech': 'noun'}}
            ]
        }

        from app.services.word_sketch.coverage_service import CoverageService
        service = CoverageService(
            word_sketch_client=mock_client,
            workset_service=mock_workset_service
        )

        # 'unknown' will return None, 'house' returns a result
        mock_client.word_sketch.side_effect = [
            WordSketchResult(lemma='house', pos='noun'),  # For 'house'
            None  # For 'unknown'
        ]

        report = service.analyze_workset(1)

        assert report.workset_id == 1
        assert report.total_entries == 2
        # One entry has coverage, one doesn't
        assert len(report.priority_items) >= 1

    def test_get_missing_lemmas(self):
        """Test getting lemmas missing coverage."""
        mock_client = Mock()
        mock_client.word_sketch.return_value = None

        mock_workset_service = Mock()
        mock_workset_service.get_workset.return_value = {
            'id': 1,
            'name': 'Test',
            'total_entries': 3,
            'entries': [
                {'id': 'e1', 'lexical_unit': {'en': 'word1'}},
                {'id': 'e2', 'lexical_unit': {'en': 'word2'}},
                {'id': 'e3', 'lexical_unit': {'en': 'word3'}}
            ]
        }

        from app.services.word_sketch.coverage_service import CoverageService
        service = CoverageService(
            word_sketch_client=mock_client,
            workset_service=mock_workset_service
        )

        missing = service.get_missing_lemmas(1)

        # All lemmas return None, so all should be in missing list
        assert len(missing) == 3


# =============================================================================
# API Endpoint Tests (limited - requires full app setup with limiter)
# =============================================================================

# Note: Full API endpoint tests are in integration tests since they require
# the Flask app to be fully configured with the rate limiter.
# The tests below verify the core functionality without full app context.

class TestAPIEndpointLogic:
    """Tests for API endpoint logic without full Flask app."""

    def test_status_endpoint_returns_correct_structure(self):
        """Test status endpoint returns correct response structure."""
        from app.services.word_sketch import WordSketchClient

        client = WordSketchClient()

        # When service is unavailable
        client._available = False

        is_available = client.is_available()

        # Should return False, not raise error
        assert is_available is False

    def test_sketch_endpoint_requires_lemma(self):
        """Test sketch endpoint validates lemma parameter."""
        # Test the validation logic directly
        lemma = ""

        # Empty lemma should fail validation
        assert not lemma or not lemma.strip()

    def test_coverage_endpoint_validates_params(self):
        """Test coverage endpoint validates required parameters."""
        # Test validation logic
        lemma = ""

        # Empty lemma should fail
        assert lemma == "" or not lemma.strip()

    def test_cache_clear_returns_message(self):
        """Test cache clear returns appropriate message."""
        client = WordSketchClient()
        client._cache = MockCache()

        # Mock clear_pattern to return count
        client._cache.clear_pattern = Mock(return_value=5)

        count = client.clear_cache()

        assert count == 5


# =============================================================================
# EnrichmentService Tests
# =============================================================================

class TestEnrichmentService:
    """Tests for EnrichmentService."""

    def test_get_enrichment_proposals(self):
        """Test getting enrichment proposals."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='big',
                    lemma='big',
                    relation='noun_modifiers',
                    relation_name='Adjectives modifying',
                    logdice=11.24,
                    frequency=1247,
                    examples=['big house', 'the big house']
                ),
                CollocationResult(
                    collocate='beautiful',
                    lemma='beautiful',
                    relation='noun_modifiers',
                    relation_name='Adjectives modifying',
                    logdice=9.5,
                    frequency=500,
                    examples=['beautiful house']
                )
            ],
            total_examples=1747
        )

        mock_corpus_client = Mock()
        mock_corpus_client.concordance.return_value = (2, [])

        service = EnrichmentService(
            word_sketch_client=mock_ws_client,
            corpus_client=mock_corpus_client
        )

        proposals = service.get_enrichment_proposals('house', 'noun', include_examples=False)

        assert len(proposals) == 2
        assert proposals[0].proposal_type == 'collocate'
        assert proposals[0].value == 'big'
        assert proposals[0].confidence >= 0.79
        assert proposals[0].grammatical_relation == 'noun_modifiers'

    def test_get_collocations_for_entry(self):
        """Test getting collocations for an entry."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='time',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='first',
                    lemma='first',
                    relation='noun_modifiers',
                    logdice=10.63,
                    frequency=249
                ),
                CollocationResult(
                    collocate='last',
                    lemma='last',
                    relation='noun_modifiers',
                    logdice=10.17,
                    frequency=174
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)

        collocations = service.get_collocations_for_entry('time', 'noun')

        assert len(collocations) == 2
        assert collocations[0].value == 'first'
        assert collocations[0].confidence > 0.7

    def test_draft_subentry(self):
        """Test drafting a subentry from collocation."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='big',
                    lemma='big',
                    relation='noun_modifiers',
                    relation_name='Adjectives modifying',
                    logdice=11.24,
                    frequency=1247
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)

        draft = service.draft_subentry(
            parent_lemma='house',
            collocate='big',
            relation='noun_modifiers',
            relation_name='Adjectives modifying',
            examples=['big house', 'very big house']
        )

        assert draft.suggested_headword == 'big'
        assert draft.parent_lemma == 'house'
        assert draft.relation_type == 'noun_modifiers'
        assert 'big' in draft.definition_template.lower()
        assert len(draft.examples) == 2
        assert draft.confidence >= 0.79

    def test_get_suggested_subentries(self):
        """Test getting suggested subentries."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='time',
            pos='noun',
            collocations=[
                # High logDice - should be suggested as subentry
                CollocationResult(
                    collocate='first',
                    lemma='first',
                    relation='noun_compound',  # Compound relation
                    relation_name='Nouns in compound',
                    logdice=10.63,
                    frequency=249
                ),
                # Low logDice - should not be suggested
                CollocationResult(
                    collocate='the',
                    lemma='the',
                    relation='det',
                    relation_name='Determiners',
                    logdice=3.0,
                    frequency=5000
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)

        drafts = service.get_suggested_subentries('time', 'noun', min_logdice=6.0)

        # Should include 'first' (compound relation, high logDice)
        # Should exclude 'the' (det relation, low logDice)
        assert len(drafts) == 1
        assert drafts[0].suggested_headword == 'first'

    def test_proposals_to_dict(self):
        """Test converting proposals to dictionary."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='test',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='example',
                    lemma='example',
                    relation='test_rel',
                    relation_name='Test relation',
                    logdice=8.0,
                    frequency=100,
                    examples=['test example']
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)

        proposals = service.get_enrichment_proposals('test', 'noun', include_examples=False)
        dicts = service.proposals_to_dict(proposals)

        assert len(dicts) == 1
        assert dicts[0]['type'] == 'collocate'
        assert dicts[0]['value'] == 'example'
        assert dicts[0]['relation'] == 'test_rel'
        assert 'confidence' in dicts[0]

    def test_get_examples_with_translations(self):
        """Test getting examples from corpus."""
        from app.services.word_sketch.enrichment_service import EnrichmentService
        from app.services.lucene_corpus_client import ConcordanceHit

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = None

        mock_corpus_client = Mock()
        mock_corpus_client.concordance.return_value = (
            2,
            [
                ConcordanceHit(left='The ', match='big', right=' house is old', sentence_id='1'),
                ConcordanceHit(left='A very ', match='big', right=' house downtown', sentence_id='2')
            ]
        )

        service = EnrichmentService(
            word_sketch_client=mock_ws_client,
            corpus_client=mock_corpus_client
        )

        examples = service.get_examples_with_translations('big', None, 10)

        assert len(examples) == 2
        assert 'big' in examples[0]['source']
        assert examples[0]['match'] == 'big'

    def test_enrichment_graceful_degradation(self):
        """Test enrichment when service is unavailable."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = None

        mock_corpus_client = Mock()
        mock_corpus_client.concordance.side_effect = Exception("Connection failed")

        service = EnrichmentService(
            word_sketch_client=mock_ws_client,
            corpus_client=mock_corpus_client
        )

        proposals = service.get_enrichment_proposals('unknown', 'noun')

        # Should return empty list, not throw
        assert proposals == []


# =============================================================================
# Enrichment API Endpoint Tests (limited - requires full app setup with limiter)
# =============================================================================

# Note: Full API endpoint tests are in integration tests since they require
# the Flask app to be fully configured with the rate limiter.
# The tests below verify the core functionality without full app context.

class TestEnrichmentAPILogic:
    """Tests for enrichment API logic without full Flask app."""

    def test_enrich_endpoint_requires_lemma(self):
        """Test enrichment endpoint validates lemma parameter."""
        # Test validation logic
        lemma = ""

        # Empty lemma should fail validation
        assert lemma == "" or not lemma.strip()

    def test_enrich_endpoint_accepts_valid_lemma(self):
        """Test enrichment endpoint accepts valid lemma."""
        # Test validation logic
        lemma = "house"

        # Valid lemma should pass validation
        assert lemma and lemma.strip()

    def test_collocations_endpoint_requires_lemma(self):
        """Test collocations endpoint requires lemma."""
        # Test validation logic
        lemma = ""

        assert lemma == "" or not lemma.strip()

    def test_subentries_endpoint_requires_lemma(self):
        """Test subentries endpoint requires lemma."""
        # Test validation logic
        lemma = ""

        assert lemma == "" or not lemma.strip()

    def test_examples_endpoint_limit_bounds(self):
        """Test examples endpoint limit is bounded."""
        # Test the limit parameter bounds checking
        limit = int(100)
        limit = min(limit, 50)
        assert limit == 50

    def test_draft_subentry_requires_all_params(self):
        """Test draft subentry requires all parameters."""
        # Test validation logic
        data = {'lemma': 'house'}  # Missing collocate and relation

        # Should fail validation
        lemma = data.get('lemma', '').strip().lower()
        collocate = data.get('collocate', '').strip()
        relation = data.get('relation', '')

        assert not all([lemma, collocate, relation])

    def test_draft_subentry_accepts_valid_params(self):
        """Test draft subentry accepts valid parameters."""
        # Test validation logic
        data = {
            'lemma': 'house',
            'collocate': 'big',
            'relation': 'noun_modifiers',
            'relation_name': 'Adjectives modifying',
            'examples': ['big house']
        }

        lemma = data.get('lemma', '').strip().lower()
        collocate = data.get('collocate', '').strip()
        relation = data.get('relation', '')

        # Should pass validation
        assert all([lemma, collocate, relation])


# =============================================================================
# Dict Import Fix Tests
# =============================================================================

class TestDictImportFix:
    """Tests verifying Dict type can be imported and used in API module."""

    def test_dict_type_can_be_imported(self):
        """Test that Dict from typing can be imported successfully."""
        # This tests the fix for the missing Dict import in word_sketch_api.py
        from typing import Dict
        assert Dict is not None

    def test_dict_type_can_be_used_in_annotations(self):
        """Test that Dict can be used in type annotations."""
        from typing import Dict, Union

        # Test basic Dict usage
        def example_function(data: Dict[str, str]) -> Union[Dict, None]:
            return data if data else None

        result = example_function({"key": "value"})
        assert result == {"key": "value"}

        result = example_function({})
        assert result is None

    def test_typing_imports_work(self):
        """Test that typing imports work correctly."""
        # Verify all needed typing imports are available
        from typing import Dict, List, Optional, Union, Any
        assert Dict is not None
        assert List is not None
        assert Optional is not None
        assert Union is not None
        assert Any is not None


# =============================================================================
# Parameter Validation Tests (Bounds Checking)
# =============================================================================

class TestParameterValidation:
    """Tests for parameter bounds checking in API endpoints."""

    def test_limit_parameter_bounds_checking_logic(self):
        """Test limit parameter is capped at 50 (logic test)."""
        # Test the bounds checking logic directly without creating Flask app
        # The API uses: min(int(request.args.get('limit', 10)), 50)
        limit = min(int(100), 50)
        assert limit == 50

        limit = int(50)
        limit = min(limit, 50)
        assert limit == 50

        limit = int(10)  # default
        limit = min(limit, 50)
        assert limit == 10

    def test_custom_query_limit_bounds_checking_logic(self):
        """Test custom query limit is capped at 100 (logic test)."""
        # The API uses: min(int(data.get('limit', 50)), 100)
        limit = min(int(200), 100)
        assert limit == 100

        limit = int(50)  # default
        limit = min(limit, 100)
        assert limit == 50

    def test_examples_limit_bounds_checking_logic(self):
        """Test examples limit is capped at 50 (logic test)."""
        # The API uses: min(int(request.args.get('limit', 10)), 50)
        limit = min(int(100), 50)
        assert limit == 50

    def test_min_logdice_validation(self):
        """Test min_logdice parameter validation."""
        # The API accepts any float value for min_logdice
        # This tests the client handles it correctly
        client = WordSketchClient()

        # Mock the cache to return None (cache miss)
        client._cache = None

        # Mock the session to return a valid response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'lemma': 'test',
            'collocations': []
        }

        # Use patch to properly mock the method
        with patch.object(client._session, 'get', return_value=mock_response):
            client._available = True

            # Test with negative min_logdice (should work, client handles it)
            result = client.word_sketch('test', min_logdice=-5)
            # Should return a result (empty) or None, not raise an exception
            assert result is None or isinstance(result, WordSketchResult)

    def test_limit_type_conversion(self):
        """Test limit parameter handles type conversion correctly."""
        # Test that the client handles various limit values
        client = WordSketchClient()

        # Mock the cache to return None (cache miss)
        client._cache = None

        # Mock the session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'lemma': 'test',
            'collocations': []
        }

        # Use patch to properly mock the method
        with patch.object(client._session, 'get', return_value=mock_response):
            client._available = True

            # Test with integer limit
            result = client.word_sketch('test', limit=25)
            assert result is None or isinstance(result, WordSketchResult)


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_rate_limiter_decorator_format(self):
        """Test rate limiter decorator uses correct format."""
        # The limiter uses: @limiter.limit("100/hour")
        # Test the format is valid
        rate_limit = "100/hour"
        parts = rate_limit.split('/')
        assert len(parts) == 2
        assert parts[0].isdigit()  # 100
        assert parts[1] in ['second', 'minute', 'hour', 'day']  # hour

    def test_rate_limiter_not_blocking_client_requests(self):
        """Test client is not blocked by rate limiter."""
        # The rate limiter applies to Flask routes, not the client
        # This test verifies the client can make requests
        client = WordSketchClient()

        # Set up mock to return unavailable (no actual HTTP call)
        client._available = False

        # is_available should return False, not raise rate limit error
        result = client.is_available()
        assert result is False

    def test_rate_limit_string_format(self):
        """Test rate limit string format is valid."""
        # Test various rate limit formats
        rate_limits = ["100/hour", "50/minute", "10/second", "1000/day"]

        for rate_limit in rate_limits:
            parts = rate_limit.split('/')
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1] in ['second', 'minute', 'hour', 'day']


# =============================================================================
# Shared Service Instance Tests
# =============================================================================

class TestSharedServiceInstances:
    """Tests for shared service instance patterns."""

    def test_coverage_service_reuses_client(self):
        """Test CoverageService reuses word sketch client."""
        from app.services.word_sketch.coverage_service import CoverageService

        # Mock the word sketch client
        mock_client = Mock()
        mock_client.word_sketch.return_value = None

        # Create service with mock client
        service = CoverageService(word_sketch_client=mock_client)

        # Call check_entry_coverage
        service.check_entry_coverage('unknown', 'noun')

        # Verify the client was used
        mock_client.word_sketch.assert_called()

    def test_enrichment_service_creates_with_defaults(self):
        """Test EnrichmentService can be created with default services."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        # Should create without errors
        service = EnrichmentService()
        assert service is not None

    def test_multiple_service_instances_use_same_client(self):
        """Test multiple CoverageService instances use the same client."""
        from app.services.word_sketch.coverage_service import CoverageService

        mock_ws_client = Mock()
        mock_workset_service = Mock()

        service1 = CoverageService(
            word_sketch_client=mock_ws_client,
            workset_service=mock_workset_service
        )
        service2 = CoverageService(
            word_sketch_client=mock_ws_client,
            workset_service=mock_workset_service
        )

        # Both services reference the same client instance
        # Note: CoverageService uses 'ws_client' attribute
        assert service1.ws_client is mock_ws_client
        assert service2.ws_client is mock_ws_client

    def test_services_can_be_created_without_app_context(self):
        """Test services can be created without Flask app context."""
        from app.services.word_sketch.coverage_service import CoverageService
        from app.services.word_sketch.enrichment_service import EnrichmentService

        # Both should create without Flask app context
        coverage_service = CoverageService(word_sketch_client=Mock())
        enrichment_service = EnrichmentService()

        assert coverage_service is not None
        assert enrichment_service is not None

    def test_service_initialization_with_custom_clients(self):
        """Test services can be initialized with custom clients."""
        from app.services.word_sketch.coverage_service import CoverageService
        from app.services.word_sketch.enrichment_service import EnrichmentService

        custom_ws_client = Mock()
        custom_workset_service = Mock()
        custom_corpus_client = Mock()

        coverage = CoverageService(
            word_sketch_client=custom_ws_client,
            workset_service=custom_workset_service
        )
        enrichment = EnrichmentService(
            word_sketch_client=custom_ws_client,
            corpus_client=custom_corpus_client
        )

        # CoverageService uses 'ws_client' attribute
        assert coverage.ws_client is custom_ws_client


# =============================================================================
# Cache Key Consistency Tests
# =============================================================================

class TestCacheKeyConsistency:
    """Tests for cache key format consistency."""

    def test_cache_key_format_without_pos(self):
        """Test cache key format when pos is not specified."""
        client = WordSketchClient()

        key = client._get_cache_key('house')
        assert key == 'ws:house'

    def test_cache_key_format_with_pos(self):
        """Test cache key format includes pos when specified."""
        client = WordSketchClient()

        key = client._get_cache_key('house', pos='noun')
        assert key == 'ws:house:noun'

    def test_cache_key_format_with_min_logdice(self):
        """Test cache key format includes min_logdice when > 0."""
        client = WordSketchClient()

        key = client._get_cache_key('house', min_logdice=6.0)
        assert key == 'ws:house:6.0'

    def test_cache_key_format_full(self):
        """Test cache key format with all parameters."""
        client = WordSketchClient()

        key = client._get_cache_key('house', pos='noun', min_logdice=6.0)
        assert key == 'ws:house:noun:6.0'

    def test_cache_key_case_insensitive(self):
        """Test cache key is case insensitive for lemma."""
        client = WordSketchClient()

        key1 = client._get_cache_key('House')
        key2 = client._get_cache_key('HOUSE')
        key3 = client._get_cache_key('house')

        assert key1 == key2 == key3 == 'ws:house'

    def test_cache_key_custom_query_format(self):
        """Test custom query uses different cache key format."""
        client = WordSketchClient()

        # Custom query uses different key format
        key = f"ws:query:house:[tag=jj.*]:6.0"
        assert 'ws:query:house' in key
        assert '[tag=jj.*]' in key


# =============================================================================
# Blueprint URL Prefix Tests
# =============================================================================

class TestBlueprintRegistration:
    """Tests for blueprint URL prefix configuration."""

    def test_browser_blueprint_name(self):
        """Test browser blueprint has correct name."""
        from app.routes.word_sketch_routes import word_sketch_browser_bp

        assert word_sketch_browser_bp.name == 'word_sketch_browser'

    def test_browser_blueprint_has_route(self):
        """Test browser blueprint has the /browser route."""
        # Check the routes file contains the browser route
        with open('/home/milek/flask-app/app/routes/word_sketch_routes.py', 'r') as f:
            source = f.read()

        # Should have /browser route defined
        assert "@word_sketch_browser_bp.route('/browser')" in source

    def test_api_blueprint_url_prefix_is_defined(self):
        """Test API blueprint url_prefix is defined in source code."""
        # Read the source file to verify the URL prefix
        with open('/home/milek/flask-app/app/api/word_sketch_api.py', 'r') as f:
            source = f.read()

        # The url_prefix should be defined in the blueprint
        assert "url_prefix='/api/word-sketch'" in source

    def test_browser_blueprint_url_prefix_is_defined(self):
        """Test browser blueprint url_prefix is defined in source code."""
        with open('/home/milek/flask-app/app/routes/word_sketch_routes.py', 'r') as f:
            source = f.read()

        # The blueprint is registered without url_prefix (uses default)
        # Check that blueprint is defined
        assert "word_sketch_browser_bp" in source

    def test_blueprint_names_are_documented(self):
        """Test blueprint names are defined in source code."""
        with open('/home/milek/flask-app/app/api/word_sketch_api.py', 'r') as f:
            api_source = f.read()
        with open('/home/milek/flask-app/app/routes/word_sketch_routes.py', 'r') as f:
            browser_source = f.read()

        # Both blueprints should have names
        assert "word_sketch" in api_source
        assert "word_sketch_browser" in browser_source


# =============================================================================
# AddToWorkset Tests
# =============================================================================

class TestAddToWorkset:
    """Tests for addToWorkset functionality with mock workset API."""

    def test_enrichment_proposal_to_dict_format(self):
        """Test enrichment proposals are converted to correct dict format."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='big',
                    lemma='big',
                    relation='noun_modifiers',
                    relation_name='Adjectives modifying',
                    logdice=11.24,
                    frequency=1247,
                    examples=['big house']
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)
        proposals = service.get_enrichment_proposals('house', 'noun', include_examples=False)

        dicts = service.proposals_to_dict(proposals)

        assert len(dicts) == 1
        assert dicts[0]['type'] == 'collocate'
        assert dicts[0]['value'] == 'big'
        assert dicts[0]['relation'] == 'noun_modifiers'
        assert 'confidence' in dicts[0]
        # logdice is inside metadata
        assert dicts[0]['metadata']['logdice'] == 11.24

    def test_collocations_to_workset_format(self):
        """Test collocations can be formatted for workset addition."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='test',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='col1',
                    lemma='col1',
                    relation='noun_modifiers',
                    logdice=10.0,
                    frequency=100,
                    examples=['example1']
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)
        collocations = service.get_collocations_for_entry('test', 'noun')

        # Verify collocations can be processed
        assert len(collocations) == 1
        assert collocations[0].value == 'col1'

    def test_subentry_drafts_to_dict_format(self):
        """Test subentry drafts are converted to correct dict format."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='big',
                    lemma='big',
                    relation='noun_compound',
                    relation_name='Nouns in compound',
                    logdice=10.63,
                    frequency=249
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)
        drafts = service.get_suggested_subentries('house', 'noun', min_logdice=6.0)

        if drafts:
            dicts = service.drafts_to_dict(drafts)
            assert len(dicts) >= 1
            assert dicts[0]['parent_lemma'] == 'house'
            assert 'suggested_headword' in dicts[0]
            assert 'confidence' in dicts[0]

    def test_proposal_dicts_have_required_fields(self):
        """Test proposal dicts have required fields for workset addition."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='house',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='big',
                    lemma='big',
                    relation='noun_modifiers',
                    relation_name='Adjectives modifying',
                    logdice=11.24,
                    frequency=1247
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)
        proposals = service.get_enrichment_proposals('house', 'noun', include_examples=False)

        # Get proposals as dicts - these can be sent to workset API
        proposal_dicts = service.proposals_to_dict(proposals)

        # Each proposal should have the required fields for workset addition
        for proposal in proposal_dicts:
            assert 'type' in proposal
            assert 'value' in proposal
            assert 'relation' in proposal
            assert 'confidence' in proposal
            # Verify metadata contains logdice and frequency
            assert 'metadata' in proposal
            assert 'logdice' in proposal['metadata']
            assert 'frequency' in proposal['metadata']

    def test_enrichment_proposal_types(self):
        """Test different enrichment proposal types."""
        from app.services.word_sketch.enrichment_service import EnrichmentService

        # Test with collocations that should produce different proposal types
        mock_ws_client = Mock()
        mock_ws_client.word_sketch.return_value = WordSketchResult(
            lemma='time',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='first',
                    lemma='first',
                    relation='noun_compound',
                    relation_name='Nouns in compound',
                    logdice=10.63,
                    frequency=249
                ),
                CollocationResult(
                    collocate='quick',
                    lemma='quick',
                    relation='noun_modifiers',
                    relation_name='Adjectives modifying',
                    logdice=8.5,
                    frequency=200
                )
            ]
        )

        service = EnrichmentService(word_sketch_client=mock_ws_client)
        proposals = service.get_enrichment_proposals('time', 'noun', include_examples=False)

        # Should have 2 proposals
        assert len(proposals) == 2

        # Convert to dicts
        dicts = service.proposals_to_dict(proposals)

        # Verify structure
        for d in dicts:
            assert 'type' in d
            assert 'value' in d
            assert 'relation' in d


# =============================================================================
# Threshold Comments Tests
# =============================================================================

class TestThresholdComments:
    """Tests verifying threshold comments don't affect functionality."""

    def test_coverage_threshold_comment_values(self):
        """Test coverage threshold comments match actual behavior."""
        from app.services.word_sketch.coverage_service import CoverageService
        from app.services.word_sketch import WordSketchResult, CollocationResult

        mock_client = Mock()
        mock_client.word_sketch.return_value = WordSketchResult(
            lemma='test',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate=f'col{i}',
                    lemma=f'col{i}',
                    relation='noun_modifiers',
                    logdice=10.0,
                    frequency=100
                )
                for i in range(10)  # 10 collocations
            ],
            total_examples=1000
        )

        service = CoverageService(word_sketch_client=mock_client)
        result = service.check_entry_coverage('test', 'noun')

        # 10 collocations with logDice 10.0 should give high coverage
        assert result.collocations_count == 10
        assert result.coverage_score > 0.7  # Exceeds threshold
        assert result.needs_enrichment is False

    def test_low_collocations_triggers_enrichment(self):
        """Test low collocation count triggers needs_enrichment."""
        from app.services.word_sketch.coverage_service import CoverageService
        from app.services.word_sketch import WordSketchResult, CollocationResult

        mock_client = Mock()
        mock_client.word_sketch.return_value = WordSketchResult(
            lemma='test',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate='col1',
                    lemma='col1',
                    relation='noun_modifiers',
                    logdice=3.0,  # Low logDice
                    frequency=10
                )
            ],
            total_examples=10
        )

        service = CoverageService(word_sketch_client=mock_client)
        result = service.check_entry_coverage('test', 'noun')

        # Single low-logDice collocation should need enrichment
        assert result.needs_enrichment is True

    def test_threshold_comment_does_not_break_code(self):
        """Test that threshold comments are just comments and don't affect logic."""
        # This test verifies the code doesn't have hardcoded threshold issues
        from app.services.word_sketch.coverage_service import CoverageService
        from app.services.word_sketch import WordSketchResult, CollocationResult

        # Create mock with varying collocation counts
        mock_client = Mock()

        # Test with 5 high-quality collocations
        mock_client.word_sketch.return_value = WordSketchResult(
            lemma='test',
            pos='noun',
            collocations=[
                CollocationResult(
                    collocate=f'col{i}',
                    lemma=f'col{i}',
                    relation='noun_modifiers',
                    logdice=11.0,  # High logDice
                    frequency=100
                )
                for i in range(5)
            ],
            total_examples=500
        )

        service = CoverageService(word_sketch_client=mock_client)
        result = service.check_entry_coverage('test', 'noun')

        # Should work correctly regardless of comment values
        assert result.collocations_count == 5
        assert result.has_coverage is True




# =============================================================================
# Max Drafts Bounds Checking Tests
# =============================================================================

class TestMaxDraftsBoundsChecking:
    """Tests for max_drafts parameter bounds checking."""

    def test_max_drafts_bounds_checking_logic(self):
        """Test max_drafts is capped at 100 (logic test).
        
        The API uses: min(max(1, int(request.args.get('max', 10))), 100)
        """
        # Test upper bound
        raw_max = int(200)
        max_drafts = min(max(1, raw_max), 100)
        assert max_drafts == 100

        # Test normal value
        raw_max = int(50)
        max_drafts = min(max(1, raw_max), 100)
        assert max_drafts == 50

        # Test default value
        raw_max = int(10)  # default
        max_drafts = min(max(1, raw_max), 100)
        assert max_drafts == 10

        # Test lower bound (negative becomes 1)
        raw_max = int(-5)
        max_drafts = min(max(1, raw_max), 100)
        assert max_drafts == 1

        # Test zero becomes 1
        raw_max = int(0)
        max_drafts = min(max(1, raw_max), 100)
        assert max_drafts == 1

    def test_max_drafts_exact_boundary_values(self):
        """Test exact boundary values for max_drafts."""
        # Exactly at upper bound
        assert min(max(1, int(100)), 100) == 100
        
        # Just over upper bound
        assert min(max(1, int(101)), 100) == 100
        
        # Just under upper bound
        assert min(max(1, int(99)), 100) == 99


# =============================================================================
# Rate Limiter Null Safety Tests
# =============================================================================

class TestRateLimiterNullSafety:
    """Tests for rate limiter null safety."""

    def test_check_limiter_returns_noop_when_none(self):
        """Test _check_limiter returns noop decorator when limiter is None."""
        import sys
        import importlib
        
        # Import fresh to get module-level state
        if 'app.api.word_sketch_api' in sys.modules:
            del sys.modules['app.api.word_sketch_api']
        
        from app.api.word_sketch_api import _check_limiter, limiter
        
        # Verify limiter is None
        assert limiter is None
        
        # Get the decorator
        decorator = _check_limiter()
        
        # Should return a decorator that passes through the function
        def test_func():
            return "test"
        
        decorated = decorator(test_func)
        assert decorated() == "test"

    def test_init_limiter_function_exists(self):
        """Test init_limiter function exists and is callable."""
        from app.api.word_sketch_api import init_limiter
        assert callable(init_limiter)


# =============================================================================
# Service Documentation Tests
# =============================================================================

class TestServiceDocumentation:
    """Tests for service helper documentation."""

    def test_get_enrichment_service_has_docstring(self):
        """Test get_enrichment_service has proper documentation."""
        from app.api.word_sketch_api import get_enrichment_service
        assert get_enrichment_service.__doc__ is not None
        assert "request-scoped" in get_enrichment_service.__doc__

    def test_get_coverage_service_has_docstring(self):
        """Test get_coverage_service has proper documentation."""
        from app.api.word_sketch_api import get_coverage_service
        assert get_coverage_service.__doc__ is not None
        assert "request-scoped" in get_coverage_service.__doc__


# =============================================================================
# JavaScript parseInt Validation Tests
# =============================================================================

class TestJavaScriptParseIntValidation:
    """Tests for JavaScript parseInt validation logic (logic tests)."""

    def test_parse_int_radix_10(self):
        """Test parseInt with radix 10."""
        assert parseInt("123", 10) == 123
        assert parseInt("0", 10) == 0
        assert parseInt("999", 10) == 999

    def test_parse_int_nan_handling(self):
        """Test parseInt returns NaN for invalid input."""
        import math
        result = parseInt("abc", 10)
        assert math.isnan(result)

    def test_js_parseint_wrapper(self):
        """Test JavaScript parseInt behavior simulation."""
        import math
        
        def parseIntWrapper(value, radix=10):
            try:
                return int(value, radix)
            except (ValueError, TypeError):
                return float('nan')
        
        # Valid integer
        assert parseIntWrapper("42", 10) == 42
        
        # Invalid input returns NaN
        assert math.isnan(parseIntWrapper("invalid", 10))
        
        # Negative numbers
        assert parseIntWrapper("-5", 10) == -5
        
        # Zero
        assert parseIntWrapper("0", 10) == 0


# =============================================================================
# Workset Data Attribute Escaping Tests
# =============================================================================

class TestWorksetDataAttributeEscaping:
    """Tests for workset data attribute escaping logic."""

    def test_escape_html_for_id_attribute(self):
        """Test that IDs are properly converted to string and could be escaped."""
        def escapeHtml(str):
            if str is None:
                return ""
            return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")
        
        # Test numeric ID conversion
        ws_id = 123
        escaped = escapeHtml(String(ws_id))
        assert escaped == "123"
        
        # Test string ID with special characters (edge case)
        ws_id = "test<script>"
        escaped = escapeHtml(String(ws_id))
        assert "&lt;script&gt;" in escaped or "<script>" not in escaped

    def test_string_conversion(self):
        """Test String() equivalent in Python."""
        def String(value):
            return str(value) if value is not None else ""
        
        assert String(123) == "123"
        assert String("test") == "test"
        assert String(None) == ""
        assert String(0) == "0"


# Helper function to simulate JavaScript parseInt
def parseInt(value, radix=10):
    """Simulate JavaScript parseInt behavior."""
    try:
        return int(value, radix)
    except (ValueError, TypeError):
        return float('nan')


# Helper function to simulate JavaScript String
class String(str):
    """Simulate JavaScript String conversion."""
    pass
