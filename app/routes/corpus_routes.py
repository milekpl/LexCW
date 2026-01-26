"""
Flask routes for corpus management - TMX/CSV upload and migration via web interface.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from flasgger import swag_from



# Create blueprint
corpus_bp = Blueprint('corpus', __name__, url_prefix='/api/corpus')




def _allowed_file(filename: str) -> bool:
    """Check if uploaded file has allowed extension."""
    allowed_extensions = {'tmx', 'csv', 'db'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def _format_migration_stats(stats: MigrationStats) -> Dict[str, Any]:
    """Format migration statistics for JSON response."""
    return {
        'records_processed': stats.records_processed,
        'records_exported': stats.records_exported,
        'records_imported': stats.records_imported,
        'errors_count': stats.errors_count,
        'duration': stats.duration,
        'records_per_second': stats.records_per_second
    }


@corpus_bp.route('/upload', methods=['POST'])
def upload_corpus():
    """Upload and migrate corpus file (TMX, CSV, or SQLite).

    DEPRECATED: Corpus upload and PostgreSQL-based migration endpoints have been removed.
    Use the Lucene corpus service and offline utilities for importing and converting corpora.
    """
    return jsonify({'success': False, 'error': 'Corpus upload and migration endpoints are deprecated. Use Lucene services or offline tools.'}), 410


@corpus_bp.route('/stats', methods=['GET'])
def get_corpus_stats():
    """Get current corpus statistics from Lucene - bypasses cache for fresh data."""
    import json
    from datetime import datetime
    from ..services.cache_service import CacheService

    try:
        # Get stats from Lucene corpus client
        stats = current_app.lucene_corpus_client.stats()

        total_records = stats.get('total_documents', stats.get('total_records', 0))
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
            current_app.logger.info("Updated cache with fresh corpus stats from Lucene")

        return jsonify({
            'success': True,
            'total_records': total_records,
            'last_updated': last_updated,
            'source': 'lucene'
        })

    except Exception as e:
        current_app.logger.error(f"Failed to get corpus stats from Lucene: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_records': 0,
            'last_updated': None,
            'source': 'lucene'
        }), 500


@corpus_bp.route('/stats/ui', methods=['GET'])
def get_corpus_stats_ui():
    """
    Get corpus statistics and connection status for UI display with caching.
    Returns simplified stats: total_records and last_updated only.
    ---
    tags:
      - Corpus
    responses:
      200:
        description: Corpus statistics and connection status
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Request success status
            lucene_status:
              type: object
              properties:
                connected:
                  type: boolean
                  description: Lucene service connection status
                error:
                  type: string
                  description: Error message if connection failed
            corpus_stats:
              type: object
              properties:
                total_records:
                  type: integer
                  description: Total number of corpus records
                last_updated:
                  type: string
                  description: Last update timestamp
            cached:
              type: boolean
              description: Whether data was retrieved from cache
    """
    import json
    from datetime import datetime
    from ..services.cache_service import CacheService

    lucene_status = {'connected': False, 'error': None}
    corpus_stats = {
        'total_records': 0,
        'last_updated': 'N/A'
    }

    # Try to get cached corpus stats first
    cache = CacheService()
    # Skip cache during tests to avoid stale statistics
    use_cache = cache.is_available() and not current_app.testing
    if use_cache:
        cached_stats = cache.get('corpus_stats')
        if cached_stats:
            try:
                stats_data = json.loads(cached_stats)
                lucene_status['connected'] = True

                # Use cached data
                corpus_stats.update(stats_data)

                current_app.logger.info("Using cached corpus stats for UI")
                return jsonify({
                    'success': True,
                    'lucene_status': lucene_status,
                    'corpus_stats': corpus_stats,
                    'cached': True
                })
            except (json.JSONDecodeError, KeyError) as e:
                current_app.logger.warning(f"Invalid cached corpus stats: {e}")

    # If no cache or cache miss, fetch fresh data from Lucene
    try:
        stats = current_app.lucene_corpus_client.stats()

        # Check if Lucene returned valid data
        if stats.get('status') == 'unhealthy':
            raise Exception(stats.get('error', 'Lucene service unhealthy'))

        lucene_status['connected'] = True

        # Format stats for template
        total_records = stats.get('total_documents', stats.get('total_records', 0))
        corpus_stats['total_records'] = total_records
        corpus_stats['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Cache the stats for 30 minutes (1800 seconds)
        if use_cache:
            cache.set('corpus_stats', json.dumps(corpus_stats), ttl=1800)
            current_app.logger.info("Cached fresh corpus stats from Lucene for 30 minutes")

    except Exception as e:
        current_app.logger.warning(f"Could not fetch corpus statistics from Lucene: {e}")
        lucene_status['connected'] = False
        lucene_status['error'] = str(e)

    return jsonify({
        'success': True,
        'lucene_status': lucene_status,
        'corpus_stats': corpus_stats,
        'cached': False
    })


@corpus_bp.route('/cleanup', methods=['POST'])
def cleanup_corpus():
    """Clear all documents from the Lucene index via /clear endpoint."""
    try:
        data = current_app.lucene_corpus_client.clear()

        return jsonify({
            'success': True,
            'message': f"Cleared {data.get('documentsDeleted', 0)} documents from index",
            'documents_deleted': data.get('documentsDeleted', 0)
        })

    except Exception as e:
        current_app.logger.error(f"Clear failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@corpus_bp.route('/deduplicate', methods=['POST'])
def deduplicate_corpus():
    """Optimize Lucene index via /optimize endpoint.

    Note: True deduplication requires index rebuild. This endpoint
    optimizes the index which may help with duplicate handling.
    """
    try:
        data = current_app.lucene_corpus_client.optimize()

        return jsonify({
            'success': True,
            'message': data.get('message', 'Index optimized'),
            'segments_merged': data.get('segmentsMerged', 0),
            'documents_remaining': data.get('docs', 0)
        })

    except Exception as e:
        current_app.logger.error(f"Optimization failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@corpus_bp.route('/convert/tmx-to-csv', methods=['POST'])
def convert_tmx_to_csv():
    """Convert TMX file to CSV format and return download."""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No TMX file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.tmx'):
            return jsonify({'error': 'File must be a TMX file'}), 400
        
        # Get options
        source_lang = request.form.get('source_lang', 'en')
        target_lang = request.form.get('target_lang', 'pl')
        
        # Save TMX file temporarily
        tmx_filename = secure_filename(file.filename or 'corpus.tmx')
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{tmx_filename}') as tmx_file:
            file.save(tmx_file.name)
            tmx_path = Path(tmx_file.name)
        
        # DEPRECATED: TMX-to-CSV conversion endpoint removed. Use local tools for TMX conversion.
        return jsonify({'success': False, 'error': 'TMX to CSV conversion via web endpoint is deprecated. Use local/offline conversion utilities.'}), 410
        
    
    except Exception as e:
        current_app.logger.error(f"TMX to CSV conversion failed: {e}")
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500


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
        from app.services.cache_service import CacheService
        cache = CacheService()
        if cache.is_available():
            cache.delete('corpus_stats')
            current_app.logger.info("Corpus stats cache cleared")
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
        current_app.logger.error(f"Error clearing corpus cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
