"""
Test for corpus management caching functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.views import corpus_management
from datetime import datetime


def test_corpus_management_uses_cache():
    """Test that corpus management uses caching for stats."""
    with patch('app.views.CorpusMigrator') as mock_migrator_class, \
         patch('app.views.PostgreSQLConfig'), \
         patch('app.views.CacheService') as mock_cache_service_class, \
         patch('app.views.render_template') as mock_render:
        
        # Mock cache service
        mock_cache = MagicMock()
        mock_cache_service_class.return_value = mock_cache
        mock_cache.is_available.return_value = True
        
        # Test cache hit - should not call migrator
        mock_cache.get.return_value = '{"total_records": 100, "avg_source_length": 50.0, "avg_target_length": 55.0, "last_record": null}'
        mock_render.return_value = 'rendered_template'
        
        result = corpus_management()
        
        # Verify cache was checked
        mock_cache.get.assert_called_once_with('corpus_stats')
        
        # Verify migrator was not called (cache hit)
        mock_migrator_class.assert_not_called()
        
        # Verify template was rendered with cached data
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        corpus_stats = kwargs['corpus_stats']
        assert corpus_stats['total_records'] == 100


def test_corpus_management_cache_miss():
    """Test that corpus management fetches fresh data on cache miss."""
    with patch('app.views.CorpusMigrator') as mock_migrator_class, \
         patch('app.views.PostgreSQLConfig'), \
         patch('app.views.CacheService') as mock_cache_service_class, \
         patch('app.views.render_template') as mock_render:
        
        # Mock cache service
        mock_cache = MagicMock()
        mock_cache_service_class.return_value = mock_cache
        mock_cache.is_available.return_value = True
        mock_cache.get.return_value = None  # Cache miss
        
        # Mock migrator
        mock_migrator = MagicMock()
        mock_migrator_class.return_value = mock_migrator
        mock_migrator.get_corpus_stats.return_value = {
            'total_records': 74723856,
            'avg_source_length': 67.23,
            'avg_target_length': 68.58,
            'last_record': datetime(2025, 6, 29, 10, 28, 45)
        }
        
        mock_render.return_value = 'rendered_template'
        
        result = corpus_management()
        
        # Verify cache was checked
        mock_cache.get.assert_called_once_with('corpus_stats')
        
        # Verify migrator was called (cache miss)
        mock_migrator_class.assert_called_once()
        mock_migrator.get_corpus_stats.assert_called_once()
        
        # Verify data was cached
        mock_cache.set.assert_called_once()
        args, kwargs = mock_cache.set.call_args
        assert args[0] == 'corpus_stats'  # cache key
        assert kwargs['ttl'] == 1800  # TTL (30 minutes)


if __name__ == '__main__':
    test_corpus_management_uses_cache()
    test_corpus_management_cache_miss()
    print("Tests passed!")
