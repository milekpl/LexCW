"""
Test suite for Redis caching implementation.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
import redis

from app.services.cache_service import CacheService


class TestCacheService:
    """Test caching service functionality."""
    
    def test_cache_service_initialization(self):
        """Test that cache service initializes properly."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.return_value.ping.return_value = True
            
            cache_service = CacheService()
            assert cache_service.redis_client is not None
    
    def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_client.get.return_value = b'{"test": "data"}'
            
            cache_service = CacheService()
            
            # Test set
            cache_service.set('test_key', {'test': 'data'}, 300)
            mock_client.setex.assert_called_once()
            
            # Test get
            result = cache_service.get('test_key')
            assert result == {'test': 'data'}
    
    def test_cache_delete(self):
        """Test cache deletion."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.delete.return_value = 1
            
            cache_service = CacheService()
            
            result = cache_service.delete('test_key')
            assert result is True
            mock_client.delete.assert_called_once_with('test_key')
    
    def test_cache_clear_pattern(self):
        """Test clearing cache keys by pattern."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.keys.return_value = [b'entries:*:1', b'entries:*:2']
            mock_client.delete.return_value = 2
            
            cache_service = CacheService()
            
            result = cache_service.clear_pattern('entries:*')
            assert result == 2
            mock_client.keys.assert_called_once_with('entries:*')
    
    def test_cache_fallback_when_redis_unavailable(self):
        """Test that service works without Redis."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.side_effect = redis.ConnectionError("Redis unavailable")
            
            cache_service = CacheService()
            
            # Should not raise error
            cache_service.set('test', {'data': 'test'})
            result = cache_service.get('test')
            assert result is None
