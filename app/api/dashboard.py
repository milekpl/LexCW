"""
API endpoints for dashboard statistics and system information.
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, current_app
from flasgger import swag_from

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService

# Create blueprint
dashboard_bp = Blueprint('dashboard_api', __name__, url_prefix='/dashboard')
logger = logging.getLogger(__name__)

# Unified cache key for dashboard stats
DASHBOARD_CACHE_KEY = 'dashboard_stats_v2'
OLD_CACHE_KEYS = ['dashboard_stats', 'dashboard_stats_api']


@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """
    Get dashboard statistics with caching for performance
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Dashboard statistics
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Whether the request was successful
            data:
              type: object
              properties:
                entry_count:
                  type: integer
                  description: Total number of entries
                sense_count:
                  type: integer
                  description: Total number of senses
                example_count:
                  type: integer
                  description: Total number of examples
                system_status:
                  type: object
                  properties:
                    baseX_connected:
                      type: boolean
                      description: BaseX database connection status
                    cache_available:
                      type: boolean
                      description: Redis cache availability
                    uptime:
                      type: string
                      description: System uptime
                recent_activity:
                  type: array
                  description: Recent activity log
                timestamp:
                  type: string
                  description: Data timestamp
            cached:
              type: boolean
              description: Whether the data was retrieved from cache
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Request success status (false)
            error:
              type: string
              description: Error message
    """
    try:
        # Try to get cached data first (new key, then old keys for migration)
        cache = CacheService()
        cache_key = DASHBOARD_CACHE_KEY
        if cache.is_available():
            cached_data = cache.get(cache_key)
            # Try old keys for cache migration
            if not cached_data:
                for old_key in OLD_CACHE_KEYS:
                    cached_data = cache.get(old_key)
                    if cached_data:
                        # Migrate to new key
                        cache.set(cache_key, cached_data, ttl=300)
                        logger.info("Migrated dashboard cache from '%s' to '%s'", old_key, cache_key)
                        break
            if cached_data:
                logger.info("Returning cached dashboard stats from API")
                return jsonify({
                    'success': True,
                    'data': cached_data,
                    'cached': True
                })
        
        # Get fresh data from database
        dict_service = current_app.injector.get(DictionaryService)
        
        # Get entry count
        entry_count = dict_service.count_entries()
        
        # Get sense and example counts
        sense_count, example_count = dict_service.count_senses_and_examples()
        
        # Get recent activity
        recent_activity = dict_service.get_recent_activity(limit=5)
        
        # Get system status
        system_status = dict_service.get_system_status()
        
        # Prepare response data
        stats_data = {
            'stats': {
                'entries': entry_count,
                'senses': sense_count,
                'examples': example_count
            },
            'system_status': system_status,
            'recent_activity': recent_activity,
            'last_updated': datetime.now().isoformat()
        }
        
        # Cache the data for 5 minutes (300 seconds) - shorter than view cache
        if cache.is_available():
            cache.set(cache_key, stats_data, ttl=300)
            logger.info("Cached dashboard stats via API for 5 minutes")
        
        return jsonify({
            'success': True,
            'data': stats_data,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats via API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/clear-cache', methods=['POST'])
@swag_from({
    'tags': ['Dashboard'],
    'summary': 'Clear dashboard cache',
    'description': 'Clear the dashboard statistics cache to force fresh data retrieval on next request.',
    'responses': {
        200: {
            'description': 'Cache cleared successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Dashboard cache cleared successfully'}
                }
            }
        },
        500: {
            'description': 'Error clearing cache',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': 'Cache service error'}
                }
            }
        }
    }
})
def clear_dashboard_cache():
    """
    Clear the dashboard statistics cache.
    """
    try:
        cache = CacheService()
        if cache.is_available():
            # Delete new key and all old keys for complete cache invalidation
            cache.delete(DASHBOARD_CACHE_KEY)
            for old_key in OLD_CACHE_KEYS:
                cache.delete(old_key)
            logger.info("Dashboard stats cache cleared")
            return jsonify({
                'success': True,
                'message': 'Dashboard cache cleared successfully'
            })
        else:
            # Cache service not available, but this is not an error in test environments
            logger.info("Cache service not available, skipping dashboard cache clear")
            return jsonify({
                'success': True,
                'message': 'Cache service not available, no cache to clear'
            })
            
    except Exception as e:
        logger.error(f"Error clearing dashboard cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
