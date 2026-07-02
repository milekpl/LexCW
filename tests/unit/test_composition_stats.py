"""
Unit tests for the data composition statistics API endpoint.
"""

import pytest
import json
from unittest.mock import MagicMock, patch


class TestCompositionStatsEndpoint:
    """Tests for GET /api/dashboard/composition"""

    def test_composition_returns_all_sections(self, client):
        """Response should contain pos_distribution, field_coverage, senses_per_entry, examples_per_sense."""
        resp = client.get('/api/dashboard/composition')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'pos_distribution' in data['data']
        assert 'field_coverage' in data['data']
        assert 'senses_per_entry' in data['data']
        assert 'examples_per_sense' in data['data']
        assert 'total_entries' in data['data']

    def test_composition_pos_distribution_format(self, client):
        """POS distribution should be a dict mapping POS strings to counts."""
        resp = client.get('/api/dashboard/composition')
        data = resp.get_json()
        pos = data['data']['pos_distribution']
        assert isinstance(pos, dict)
        for key, val in pos.items():
            assert isinstance(key, str)
            assert isinstance(val, int)

    def test_composition_field_coverage_format(self, client):
        """Each field should have count and pct."""
        resp = client.get('/api/dashboard/composition')
        data = resp.get_json()
        fc = data['data']['field_coverage']
        expected_fields = {'headword', 'citation_form', 'sense', 'definition',
                           'gloss', 'example', 'pronunciation', 'note'}
        assert set(fc.keys()) == expected_fields
        for field, info in fc.items():
            assert 'count' in info
            assert 'pct' in info
            assert isinstance(info['count'], int)
            assert isinstance(info['pct'], (int, float))
            assert 0 <= info['pct'] <= 100

    def test_composition_senses_histogram_format(self, client):
        """Senses-per-entry histogram should have 6 buckets (0,1,2,3,4,5+)."""
        resp = client.get('/api/dashboard/composition')
        data = resp.get_json()
        hist = data['data']['senses_per_entry']
        assert len(hist) == 6
        expected_buckets = ['0', '1', '2', '3', '4', '5+']
        buckets = [item['bucket'] for item in hist]
        assert buckets == expected_buckets
        for item in hist:
            assert isinstance(item['count'], int)
            assert item['count'] >= 0

    def test_composition_examples_histogram_format(self, client):
        """Examples-per-sense histogram should have 4 buckets (0,1,2,3+)."""
        resp = client.get('/api/dashboard/composition')
        data = resp.get_json()
        hist = data['data']['examples_per_sense']
        assert len(hist) == 4
        expected_buckets = ['0', '1', '2', '3+']
        buckets = [item['bucket'] for item in hist]
        assert buckets == expected_buckets
        for item in hist:
            assert isinstance(item['count'], int)

    def test_composition_total_entries_matches_field_coverage(self, client):
        """total_entries should match headword coverage count."""
        resp = client.get('/api/dashboard/composition')
        data = resp.get_json()
        total = data['data']['total_entries']
        headword_count = data['data']['field_coverage']['headword']['count']
        assert total == headword_count


class TestCompositionStatsError:
    """Tests for error handling in composition stats."""

    def test_composition_handles_service_error(self, client):
        """Should return 500 on service error."""
        with patch('app.api.dashboard.DictionaryService') as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_composition_stats.side_effect = Exception("DB error")
            resp = client.get('/api/dashboard/composition')
            assert resp.status_code == 500
            data = resp.get_json()
            assert data['success'] is False
