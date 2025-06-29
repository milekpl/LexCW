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

from ..database.corpus_migrator import CorpusMigrator, MigrationStats
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
            # Initialize migrator
            postgres_config = _get_postgres_config()
            migrator = CorpusMigrator(postgres_config)
            
            # Drop existing database if requested
            if drop_existing:
                migrator.drop_database()
            
            # Detect format and migrate
            file_ext = temp_path.suffix.lower()
            if filename.endswith('.db'):
                file_ext = '.db'
            
            if file_ext == '.db':
                stats = migrator.migrate_sqlite_corpus(temp_path, cleanup_temp=True)
            elif file_ext == '.tmx':
                stats = migrator.migrate_tmx_corpus(temp_path, source_lang, target_lang, cleanup_temp=True)
            elif file_ext == '.csv':
                migrator.create_database_if_not_exists()
                migrator.create_schema()
                migrator.import_csv_to_postgres(temp_path)
                migrator.create_indexes()
                stats = migrator.stats
            else:
                return jsonify({'error': 'Unsupported file format'}), 400
            
            return jsonify({
                'success': True,
                'message': 'Corpus migrated successfully',
                'stats': _format_migration_stats(stats)
            })
        
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
        postgres_config = _get_postgres_config()
        migrator = CorpusMigrator(postgres_config)
        stats = migrator.get_corpus_stats()
        
        # Format stats for frontend compatibility
        formatted_stats = {
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
                'total_records': formatted_stats['total_records'],
                'avg_source_length': f"{formatted_stats['avg_source_length']:.2f}",
                'avg_target_length': f"{formatted_stats['avg_target_length']:.2f}",
                'last_updated': last_updated
            }
            cache.set('corpus_stats', json.dumps(cache_data), ttl=1800)
            current_app.logger.info("Updated cache with fresh corpus stats")
        
        return jsonify({
            'success': True,
            'stats': formatted_stats
        })
    
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


@corpus_bp.route('/cleanup', methods=['POST'])
def cleanup_corpus():
    """Clean up corpus database - drop and recreate."""
    try:
        postgres_config = _get_postgres_config()
        migrator = CorpusMigrator(postgres_config)
        
        # Drop database
        migrator.drop_database()
        
        # Recreate database and schema
        migrator.create_database_if_not_exists()
        migrator.create_schema()
        
        return jsonify({
            'success': True,
            'message': 'Corpus database cleaned up successfully'
        })
    
    except Exception as e:
        current_app.logger.error(f"Corpus cleanup failed: {e}")
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500


@corpus_bp.route('/deduplicate', methods=['POST'])
def deduplicate_corpus():
    """Remove duplicate entries from corpus."""
    try:
        postgres_config = _get_postgres_config()
        migrator = CorpusMigrator(postgres_config)
        
        duplicates_removed = migrator.deduplicate_corpus()
        
        return jsonify({
            'success': True,
            'message': f'Removed {duplicates_removed} duplicate entries',
            'duplicates_removed': duplicates_removed
        })
    
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
            # Convert to CSV
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w+') as csv_file:
                csv_path = Path(csv_file.name)
            
            postgres_config = _get_postgres_config()
            migrator = CorpusMigrator(postgres_config)
            records_converted = migrator.convert_tmx_to_csv(tmx_path, csv_path, source_lang, target_lang)
            
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
