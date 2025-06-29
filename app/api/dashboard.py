"""
API endpoints for dashboard statistics and system information.
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify
from flasgger import swag_from

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app import injector

# Create blueprint
dashboard_bp = Blueprint('dashboard_api', __name__, url_prefix='/dashboard')
logger = logging.getLogger(__name__)


@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """
    Get dashboard statistics with caching for performance
    ---
    tags:
      - dashboard
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
        # Try to get cached data first
        cache = CacheService()
        cache_key = 'dashboard_stats_api'
        if cache.is_available():
            cached_data = cache.get(cache_key)
            if cached_data:
                try:
                    cached_stats = json.loads(cached_data)
                    logger.info("Returning cached dashboard stats from API")
                    return jsonify({
                        'success': True,
                        'data': cached_stats,
                        'cached': True
                    })
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Invalid cached dashboard API data: {e}")
        
        # Get fresh data from database
        dict_service = injector.get(DictionaryService)
        
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
            cache.set(cache_key, json.dumps(stats_data, default=str), ttl=300)
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
def clear_dashboard_cache():
    """
    Clear the dashboard statistics cache.
    """
    try:
        cache = CacheService()
        if cache.is_available():
            cache.delete('dashboard_stats')
            cache.delete('dashboard_stats_api')
            logger.info("Dashboard stats cache cleared")
            return jsonify({
                'success': True,
                'message': 'Dashboard cache cleared successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Cache service not available'
            }), 500
            
    except Exception as e:
        logger.error(f"Error clearing dashboard cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
