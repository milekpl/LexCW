"""
Redis caching service for performance optimization.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, List, ClassVar

import redis


class CacheService:
    """Redis-based caching service with graceful fallback."""
    
    # Class-level cache of the instance to avoid repeated Redis connection attempts
    _instance: Optional['CacheService'] = None
    _connection_attempted: ClassVar[bool] = False
    
    def __new__(cls) -> 'CacheService':
        """Singleton pattern to avoid repeated Redis connection attempts."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection with fallback."""
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self._initialized = True
        
        # Only attempt connection once per application lifecycle
        if not CacheService._connection_attempted:
            CacheService._connection_attempted = True
            self._connect()
    
    def _connect(self) -> None:
        """Establish Redis connection."""
        try:
            # Redis 8.0 compatible configuration with more reasonable timeouts
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                password=os.getenv('REDIS_PASSWORD'),
                decode_responses=False,  # We'll handle JSON encoding manually
                socket_connect_timeout=5,  # Increased timeout for better reliability
                socket_timeout=5,
                # Remove deprecated retry_on_timeout parameter for Redis 8.0 compatibility
                retry_on_error=[redis.ConnectionError, redis.TimeoutError]
            )
            
            # Test connection with timeout
            self.redis_client.ping()
            self.logger.info("Redis cache service connected successfully")
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self.logger.warning(f"Redis unavailable, caching disabled: {e}")
            self.redis_client = None
        except Exception as e:
            self.logger.error(f"Unexpected Redis error: {e}")
            self.redis_client = None

    def is_available(self) -> bool:
        """Return True if Redis is connected and available."""
        return self.redis_client is not None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set a value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            return bool(self.redis_client.setex(key, ttl, serialized_value))
        except Exception as e:
            self.logger.error(f"Cache set error for key '{key}': {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/error
        """
        if not self.redis_client:
            return None
        
        try:
            cached_value = self.redis_client.get(key)
            if cached_value:
                return json.loads(cached_value.decode('utf-8'))
            return None
        except Exception as e:
            self.logger.error(f"Cache get error for key '{key}': {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            self.logger.error(f"Cache delete error for key '{key}': {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., 'entries:*')
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            self.logger.error(f"Cache clear pattern error for '{pattern}': {e}")
            return 0
    
    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """
        Increment a counter in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            ttl: Optional TTL for new keys
            
        Returns:
            New value or None on error
        """
        if not self.redis_client:
            return None
        
        try:
            pipeline = self.redis_client.pipeline()
            pipeline.incr(key, amount)
            if ttl:
                pipeline.expire(key, ttl)
            results = pipeline.execute()
            return results[0]
        except Exception as e:
            self.logger.error(f"Cache increment error for key '{key}': {e}")
            return None
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            self.logger.error(f"Cache exists error for key '{key}': {e}")
            return False
    
    def clear(self) -> int:
        """
        Clear all cached data.
        
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0
        
        try:
            # Use pattern '*' to clear all keys
            return self.clear_pattern('*')
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
            return 0
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.redis_client:
            return {'status': 'disabled', 'connected': False}
        
        try:
            info = self.redis_client.info()
            return {
                'status': 'active',
                'connected': True,
                'used_memory': info.get('used_memory_human', 'Unknown'),
                'total_keys': info.get('db0', {}).get('keys', 0) if 'db0' in info else 0,
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': (
                    info.get('keyspace_hits', 0) / 
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100
                )
            }
        except Exception as e:
            self.logger.error(f"Cache stats error: {e}")
            return {'status': 'error', 'connected': False, 'error': str(e)}


# Global cache service instance
cache_service = CacheService()


def cache_key(prefix: str, *args: Any) -> str:
    """
    Generate standardized cache key.
    
    Args:
        prefix: Key prefix
        *args: Additional key components
        
    Returns:
        Formatted cache key
    """
    key_parts = [str(arg) for arg in args if arg is not None]
    return f"{prefix}:{':'.join(key_parts)}"


def cached_result(key_prefix: str, ttl: int = 3600):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function args
            cache_key_value = cache_key(
                key_prefix, 
                func.__name__, 
                *args,
                *[f"{k}={v}" for k, v in sorted(kwargs.items())]
            )
            
            # Try to get from cache
            cached_value = cache_service.get(cache_key_value)
            if cached_value is not None:
                return cached_value
            
            # Calculate and cache result
            result = func(*args, **kwargs)
            cache_service.set(cache_key_value, result, ttl)
            return result
        
        return wrapper
    return decorator
