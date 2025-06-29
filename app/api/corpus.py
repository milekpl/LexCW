"""
API endpoints for corpus management operations.
"""

import json
import logging
import os
from flask import Blueprint, jsonify, request
from app.database.postgresql_connector import PostgreSQLConfig
from app.database.corpus_migrator import CorpusMigrator
from app.services.cache_service import CacheService
from datetime import datetime

corpus_bp = Blueprint('corpus_api', __name__, url_prefix='/api/corpus')
logger = logging.getLogger(__name__)


@corpus_bp.route('/stats', methods=['GET'])
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
        
        migrator = CorpusMigrator(config)
        stats = migrator.get_corpus_stats()
        
        # Format stats for JSON response
        response_stats = {
            'total_records': stats.get('total_records', 0),
            'avg_source_length': float(stats.get('avg_source_length', 0)) if stats.get('avg_source_length') else 0,
            'avg_target_length': float(stats.get('avg_target_length', 0)) if stats.get('avg_target_length') else 0,
        }
        
        # Update cache with fresh data
        cache = CacheService()
        if cache.is_available():
            # Format last_updated for cache
            last_record = stats.get('last_record')
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
            logger.info("Updated cache with fresh corpus stats")
        
        return jsonify({
            'success': True,
            'stats': response_stats
        })
        
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
