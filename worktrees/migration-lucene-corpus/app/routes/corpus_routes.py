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

# PostgreSQL-based `CorpusMigrator` removed. Prefer Lucene corpus service
# available as `current_app.lucene_corpus_client`. Legacy migration endpoints
# are deprecated and will return 410 (Gone) when the Lucene service is not
# available or the operation is not supported.
from ..database.postgresql_connector import PostgreSQLConfig


# Create blueprint
corpus_bp = Blueprint('corpus', __name__, url_prefix='/api/corpus')


def _get_postgres_config() -> PostgreSQLConfig:
    """Get PostgreSQL configuration from environment."""
    return PostgreSQLConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'dictionary_analytics'),  # Use analytics database for corpus data
        username=os.getenv('POSTGRES_USER', 'dict_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
    )


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
    """Upload and migrate corpus file (TMX, CSV, or SQLite)."""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not _allowed_file(file.filename):
            return jsonify({'error': 'File type not supported. Use TMX, CSV, or SQLite DB files.'}), 400
        
        # Get options
        source_lang = request.form.get('source_lang', 'en')
        target_lang = request.form.get('target_lang', 'pl')
        drop_existing = request.form.get('drop_existing', 'false').lower() == 'true'
        
        # Secure filename and save temporarily
        filename = secure_filename(file.filename or 'corpus')
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{filename}') as temp_file:
            file.save(temp_file.name)
            temp_path = Path(temp_file.name)
        
        try:
            # Deprecated: Postgres-based migration removed. Prefer Lucene ingestion
            current_app.logger.warning("Deprecated endpoint called: /api/corpus/upload. PostgreSQL-based migration has been removed.")
            return jsonify({
                'error': 'Deprecated: PostgreSQL-based corpus migration removed. Use Lucene ingestion tools or offline migration utilities.'
            }), 410
        
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
    
    except Exception as e:
        current_app.logger.error(f"Corpus migration failed: {e}")
        return jsonify({'error': f'Migration failed: {str(e)}'}), 500


@corpus_bp.route('/stats', methods=['GET'])
def get_corpus_stats():
    """Get current corpus statistics - bypasses cache for fresh data."""
    import json
    from datetime import datetime
    from ..services.cache_service import CacheService
    
    try:
        # Prefer Lucene corpus service when available
        lucene_client = getattr(current_app, 'lucene_corpus_client', None)
        if lucene_client:
            lucene_stats = lucene_client.stats()
            formatted_stats = {
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
                    'total_records': formatted_stats['total_records'],
                    'avg_source_length': f"{formatted_stats['avg_source_length']:.2f}",
                    'avg_target_length': f"{formatted_stats['avg_target_length']:.2f}",
                    'last_updated': last_updated
                }
                cache.set('corpus_stats', json.dumps(cache_data), ttl=1800)
                current_app.logger.info("Updated cache with fresh corpus stats (lucene)")
            return jsonify({
                'success': True,
                'stats': formatted_stats
            })
        else:
            return jsonify({'error': 'Lucene corpus service not available. PostgreSQL-based corpus support removed.'}), 410
    
    except Exception as e:
        current_app.logger.error(f"Failed to get corpus stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {
                'total_records': 0,
                'avg_source_length': 0,
                'avg_target_length': 0
            }
        }), 500


@corpus_bp.route('/stats/ui', methods=['GET'])
def get_corpus_stats_ui():
    """
    Get corpus statistics and connection status for UI display with caching.
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
            postgres_status:
              type: object
              properties:
                connected:
                  type: boolean
                  description: PostgreSQL connection status
                error:
                  type: string
                  description: Error message if connection failed
            corpus_stats:
              type: object
              properties:
                total_records:
                  type: integer
                  description: Total number of corpus records
                avg_source_length:
                  type: string
                  description: Average source text length (formatted)
                avg_target_length:
                  type: string
                  description: Average target text length (formatted)
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
    
    postgres_status = {'connected': False, 'error': None}
    corpus_stats = {
        'total_records': 0,
        'avg_source_length': '0.00',
        'avg_target_length': '0.00',
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
                postgres_status['connected'] = True
                
                # Use cached data
                corpus_stats.update(stats_data)
                
                current_app.logger.info("Using cached corpus stats for UI")
                return jsonify({
                    'success': True,
                    'postgres_status': postgres_status,
                    'corpus_stats': corpus_stats,
                    'cached': True
                })
            except (json.JSONDecodeError, KeyError) as e:
                current_app.logger.warning(f"Invalid cached corpus stats: {e}")
    
    # If no cache or cache miss, fetch fresh data (prefer Lucene)
    try:
        lucene_client = getattr(current_app, 'lucene_corpus_client', None)
        if lucene_client:
            try:
                stats = lucene_client.stats()
                postgres_status['connected'] = True

                corpus_stats['total_records'] = stats.get('total_documents', stats.get('total_records', 0))
                corpus_stats['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Cache the stats for 30 minutes (1800 seconds)
                if use_cache:
                    cache.set('corpus_stats', json.dumps(corpus_stats), ttl=1800)
                    current_app.logger.info("Cached fresh corpus stats for 30 minutes")

            except Exception as e:
                current_app.logger.warning(f"Could not fetch corpus statistics from Lucene: {e}")
                postgres_status['connected'] = False
                postgres_status['error'] = f"Could not fetch stats: {e}"
        else:
            postgres_status['connected'] = False
            postgres_status['error'] = 'Lucene corpus service not configured'

    except Exception as e:
        current_app.logger.error(f"Lucene connection error: {e}")
        postgres_status['error'] = str(e)
    
    return jsonify({
        'success': True,
        'postgres_status': postgres_status,
        'corpus_stats': corpus_stats,
        'cached': False
    })


@corpus_bp.route('/cleanup', methods=['POST'])
def cleanup_corpus():
    """Clean up corpus database - drop and recreate."""
    try:
        lucene_client = getattr(current_app, 'lucene_corpus_client', None)
        if lucene_client:
            result = lucene_client.clear()
            return jsonify({
                'success': True,
                'message': f"Cleared corpus index: {result}"
            })
        else:
            return jsonify({'error': 'Lucene corpus service not available. Cleanup operation not supported.'}), 410
    
    except Exception as e:
        current_app.logger.error(f"Corpus cleanup failed: {e}")
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500


@corpus_bp.route('/deduplicate', methods=['POST'])
def deduplicate_corpus():
    """Remove duplicate entries from corpus."""
    try:
        lucene_client = getattr(current_app, 'lucene_corpus_client', None)
        if lucene_client:
            result = lucene_client.optimize()
            # Return whatever the lucene client reports
            return jsonify({
                'success': True,
                'message': 'Optimization completed',
                **(result or {})
            })
        else:
            return jsonify({'error': 'Lucene corpus service not available. Deduplication not supported.'}), 410
    
    except Exception as e:
        current_app.logger.error(f"Corpus deduplication failed: {e}")
        return jsonify({'error': f'Deduplication failed: {str(e)}'}), 500


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
        
        try:
            # Convert to CSV (local implementation; no Postgres dependency)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w+', encoding='utf-8') as csv_file:
                csv_path = Path(csv_file.name)

            import csv as _csv
            import xml.etree.ElementTree as ET

            records_converted = 0
            tree = ET.parse(tmx_path)
            root = tree.getroot()

            with open(csv_path, 'w', newline='', encoding='utf-8') as out_csv:
                writer = _csv.writer(out_csv, quoting=_csv.QUOTE_ALL)
                writer.writerow(['source_text', 'target_text'])

                for tu in root.findall('.//tu'):
                    source_text = ''
                    target_text = ''
                    for tuv in tu.findall('tuv'):
                        lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang') or tuv.get('lang')
                        seg = tuv.find('seg')
                        if seg is None or seg.text is None:
                            continue
                        text = ' '.join(seg.text.split())
                        if lang == source_lang:
                            source_text = text
                        if lang == target_lang:
                            target_text = text
                    if source_text and target_text:
                        writer.writerow([source_text, target_text])
                        records_converted += 1

            # Read CSV content
            with open(csv_path, 'r', encoding='utf-8') as f:
                csv_content = f.read()

            return jsonify({
                'success': True,
                'message': f'Converted {records_converted} records',
                'records_converted': records_converted,
                'csv_content': csv_content,
                'filename': tmx_filename.replace('.tmx', '.csv')
            })
        
        finally:
            # Clean up temporary files
            if tmx_path.exists():
                tmx_path.unlink()
            if csv_path.exists():
                csv_path.unlink()
    
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
