"""
API endpoints for corpus management operations.
"""

import json
import logging
from flask import Blueprint, jsonify, current_app
from flasgger import swag_from
from app.services.cache_service import CacheService
from datetime import datetime

corpus_bp = Blueprint('corpus_api', __name__, url_prefix='/corpus')
logger = logging.getLogger(__name__)


@corpus_bp.route('/stats', methods=['GET'])
@swag_from({
    'tags': ['Corpus'],
    'summary': 'Get corpus statistics',
    'description': 'Retrieve corpus statistics from Lucene index.',
    'responses': {
        200: {
            'description': 'Corpus statistics retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'total_records': {'type': 'integer', 'example': 74740856, 'description': 'Total number of corpus documents'},
                    'last_updated': {'type': 'string', 'example': '2024-01-15 10:30:00', 'description': 'Last update timestamp'},
                    'source': {'type': 'string', 'example': 'lucene'}
                }
            }
        },
        500: {
            'description': 'Error retrieving corpus statistics',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': 'Lucene service unavailable'},
                    'total_records': {'type': 'integer', 'example': 0},
                    'last_updated': {'type': 'string', 'example': None}
                }
            }
        }
    }
})
def get_corpus_stats():
    """
    Get corpus statistics from Lucene index.
    Returns document count and last update timestamp.
    """
    try:
        # Get stats from Lucene corpus client
        lucene_stats = current_app.lucene_corpus_client.stats()

        total_records = lucene_stats.get('total_documents', 0)
        last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update cache with fresh data
        cache = CacheService()
        if cache.is_available():
            cache_data = {
                'total_records': total_records,
                'last_updated': last_updated,
                'source': 'lucene'
            }
            cache.set('corpus_stats', json.dumps(cache_data), ttl=1800)
            logger.info("Updated cache with fresh corpus stats from Lucene")

        return jsonify({
            'success': True,
            'total_records': total_records,
            'last_updated': last_updated,
            'source': 'lucene'
        })

    except Exception as e:
        logger.error(f"Error fetching corpus stats from Lucene: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_records': 0,
            'last_updated': None,
            'source': 'lucene'
        }), 500


@corpus_bp.route('/clear-cache', methods=['POST'])
@swag_from({
    'tags': ['Corpus'],
    'summary': 'Clear corpus cache',
    'description': 'Clear the corpus statistics cache to force fresh data retrieval on next request.',
    'responses': {
        200: {
            'description': 'Cache cleared successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Cache cleared successfully'}
                }
            }
        },
        500: {
            'description': 'Error clearing cache',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': 'Cache service not available'}
                }
            }
        }
    }
})
def clear_corpus_cache():
    """
    Clear the corpus statistics cache.
    """
    try:
        cache = CacheService()
        if cache.is_available():
            cache.delete('corpus_stats')
            logger.info("Corpus stats cache cleared")
            return jsonify({
                'success': True,
                'message': 'Cache cleared successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Cache service not available'
            }), 500
            
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
