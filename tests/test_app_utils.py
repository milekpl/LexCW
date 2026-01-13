"""
Test utilities for managing Flask app state during testing.

This module provides utilities that can be called from test fixtures (like conftest.py)
to reset Flask app state without requiring direct access to the app context.
"""

import os
import sys
from typing import Optional

# Global reference to the last created Flask app for test utilities
_test_app_ref: Optional['Flask'] = None


def set_test_app(app):
    """Set the current test app reference for test utilities.

    This is called by flask_test_server fixture to enable test utilities
    to access the app context.
    """
    global _test_app_ref
    _test_app_ref = app


def get_test_app():
    """Get the current test app reference."""
    return _test_app_ref


def invalidate_all_caches():
    """Invalidate all Flask caches after database restore.

    This should be called after restoring the database from a snapshot
    to ensure get_ranges() returns fresh data instead of stale cache,
    and entries list shows correct data.

    Usage:
        from tests.test_app_utils import invalidate_all_caches
        invalidate_all_caches()
    """
    app = get_test_app()
    if app is None:
        # Try to create a minimal app context
        from app import create_app
        app = create_app('testing')
        with app.app_context():
            _invalidate_cache_inner()
        return

    with app.app_context():
        _invalidate_cache_inner()


def _invalidate_cache_inner():
    """Internal function to invalidate caches within app context."""
    from app.services.dictionary_service import DictionaryService
    from app.services.cache_service import CacheService

    try:
        # Get the database name from environment or app config
        db_name = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')

        # Clear ALL Redis cache patterns that could cause test pollution
        cache = CacheService()
        if cache.is_available():
            patterns_to_clear = [
                'entries:*',        # Entries list cache
                'entry:*',          # Individual entry cache
                'dashboard_stats*', # Dashboard statistics cache
                'ranges:*',         # Ranges cache
            ]
            total_cleared = 0
            for pattern in patterns_to_clear:
                cleared = cache.clear_pattern(pattern)
                total_cleared += cleared
            if total_cleared > 0:
                print(f"Cleared {total_cleared} Redis cache keys for database: {db_name}")

        # Also invalidate DictionaryService ranges cache (in-memory)
        from flask import current_app
        if hasattr(current_app, 'injector'):
            dictionary_service = current_app.injector.get(DictionaryService)
            dictionary_service.invalidate_ranges_cache()
            print(f"Ranges cache invalidated for database: {db_name}")
    except Exception as e:
        print(f"Warning: Failed to invalidate caches: {e}")


# Keep old function name for backwards compatibility
def invalidate_ranges_cache():
    """Deprecated: Use invalidate_all_caches() instead."""
    invalidate_all_caches()


def reset_test_app():
    """Reset the test app reference. Call this in fixture teardown."""
    global _test_app_ref
    _test_app_ref = None
