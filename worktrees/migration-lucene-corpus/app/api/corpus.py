"""
API endpoints for corpus management operations.
"""

import json
import logging
import os
from flask import Blueprint, jsonify, request, current_app
from flasgger import swag_from
from app.database.postgresql_connector import PostgreSQLConfig
# PostgreSQL-based CorpusMigrator removed; prefer Lucene corpus client on the app
from app.services.cache_service import CacheService
from datetime import datetime

corpus_bp = Blueprint('corpus_api', __name__, url_prefix='/corpus')
logger = logging.getLogger(__name__)


@corpus_bp.route('/stats', methods=['GET'])
@swag_from({
    'tags': ['Corpus'],
    'summary': 'Get corpus statistics',
    'description': 'Retrieve fresh corpus statistics from PostgreSQL database, bypassing cache. Supports both new corpus schema and legacy public schema locations.',
    'responses': {
        200: {
            'description': 'Corpus statistics retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'stats': {
                        'type': 'object',
                        'properties': {
                            'total_records': {'type': 'integer', 'example': 74740856, 'description': 'Total number of parallel corpus records'},
                            'avg_source_length': {'type': 'number', 'example': 67.22, 'description': 'Average character length of source texts'},
                            'avg_target_length': {'type': 'number', 'example': 68.56, 'description': 'Average character length of target texts'}
                        }
                    }
                }
            }
        },
        500: {
            'description': 'Error retrieving corpus statistics',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': 'Database connection failed'},
                    'stats': {
                        'type': 'object',
                        'properties': {
                            'total_records': {'type': 'integer', 'example': 0},
                            'avg_source_length': {'type': 'number', 'example': 0},
                            'avg_target_length': {'type': 'number', 'example': 0}
                        }
                    }
                }
            }
        }
    }
})
def get_corpus_stats():
    """
    Get fresh corpus statistics, bypassing cache.
    Used by the refresh button in corpus management UI.
    """
    try:
        # Create PostgreSQL config from environment
        config = PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
        )
        
        # Prefer Lucene corpus service when available
        lucene_client = getattr(current_app, 'lucene_corpus_client', None)
        if lucene_client:
            lucene_stats = lucene_client.stats()
            response_stats = {
                'total_records': int(lucene_stats.get('total_documents', 0)),
                'avg_source_length': float(lucene_stats.get('avg_source_length', 0.0) or 0.0),
                'avg_target_length': float(lucene_stats.get('avg_target_length', 0.0) or 0.0),
            }

            # Update cache with fresh data
            cache = CacheService()
            if cache.is_available():
                last_record = lucene_stats.get('last_record')
                if isinstance(last_record, datetime):
                    last_updated = last_record.strftime('%Y-%m-%d %H:%M:%S')
                elif last_record:
                    last_updated = str(last_record)
                else:
                    last_updated = 'N/A'

                cache_data = {
                    'total_records': response_stats['total_records'],
                    'avg_source_length': f"{response_stats['avg_source_length']:.2f}",
                    'avg_target_length': f"{response_stats['avg_target_length']:.2f}",
                    'last_updated': last_updated
                }
                cache.set('corpus_stats', json.dumps(cache_data), ttl=1800)
                logger.info("Updated cache with fresh corpus stats (lucene)")

            return jsonify({
                'success': True,
                'stats': response_stats
            })
        else:
            return jsonify({'error': 'Lucene corpus service not available. PostgreSQL-based corpus support removed.'}), 410
        
    except Exception as e:
        logger.error(f"Error fetching corpus stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {
                'total_records': 0,
                'avg_source_length': 0,
                'avg_target_length': 0
            }
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
