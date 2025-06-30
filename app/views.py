"""
Views for the Dictionary Writing System's frontend.
"""

import json
import logging
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app.models.entry import Entry
from app.utils.exceptions import NotFoundError, ValidationError
from app.database.postgresql_connector import PostgreSQLConfig
from app.database.corpus_migrator import CorpusMigrator
from app import injector

# Create blueprint
main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


@main_bp.route('/corpus-management')
def corpus_management():
    """Render corpus management interface with async stats loading."""
    # Return page immediately with loading indicators
    # Stats will be loaded via AJAX
    postgres_status = {'connected': False, 'error': None}
    corpus_stats = {
        'total_records': 0,
        'avg_source_length': '0.00',
        'avg_target_length': '0.00',
        'last_updated': 'Loading...'
    }
    
    return render_template(
        'corpus_management.html', 
        corpus_stats=corpus_stats, 
        postgres_status=postgres_status
    )


@main_bp.route('/')
def index():
    """
    Render the dashboard/home page with cached stats for performance.
    """
    from app.services.cache_service import CacheService
    import json
    
    # Default data for dashboard if DB connection fails
    stats = {
        'entries': 0,
        'senses': 0,
        'examples': 0
    }
    
    system_status = {
        'db_connected': False,
        'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'storage_percent': 0
    }
    
    recent_activity = [
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'action': 'Entry Created',
            'description': 'Added new entry "example"'
        },
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'action': 'Entry Updated',
            'description': 'Updated entry "test"'
        }
    ]
    
    # Try to get cached dashboard data first
    cache = CacheService()
    cache_key = 'dashboard_stats'
    if cache.is_available():
        cached_data = cache.get(cache_key)
        if cached_data:
            try:
                cached_stats = json.loads(cached_data)
                stats = cached_stats.get('stats', stats)
                system_status = cached_stats.get('system_status', system_status)
                recent_activity = cached_stats.get('recent_activity', recent_activity)
                logger.info("Using cached dashboard stats")
                return render_template('index.html', 
                                     stats=stats, 
                                     system_status=system_status, 
                                     recent_activity=recent_activity)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid cached dashboard data: {e}")
    
    # Get actual stats from the database if possible
    try:
        dict_service = injector.get(DictionaryService)
        entry_count = dict_service.count_entries()
        stats['entries'] = entry_count
        
        # Get sense and example counts
        sense_count, example_count = dict_service.count_senses_and_examples()
        stats['senses'] = sense_count
        stats['examples'] = example_count
        
        # Get recent activity
        recent_activity = dict_service.get_recent_activity(limit=5)
        
        # Get system status
        system_status = dict_service.get_system_status()
        logger.info(f"System status retrieved: {system_status}")
        
        # Check system_status type to debug issues
        logger.info(f"system_status type: {type(system_status)}")
        logger.info(f"system_status keys: {system_status.keys() if hasattr(system_status, 'keys') else 'N/A'}")
        logger.info(f"db_connected value: {system_status.get('db_connected', 'ERROR')}")
        logger.info(f"last_backup value: {system_status.get('last_backup', 'ERROR')}")
        logger.info(f"storage_percent value: {system_status.get('storage_percent', 'ERROR')}")
        
        # Cache the dashboard data for 10 minutes (600 seconds)
        if cache.is_available():
            cache_data = {
                'stats': stats,
                'system_status': system_status,
                'recent_activity': recent_activity
            }
            cache.set(cache_key, json.dumps(cache_data, default=str), ttl=600)
            logger.info("Cached dashboard stats for 10 minutes")
            
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}", exc_info=True)
        flash(f"Error loading dashboard data: {str(e)}", "danger")
    
    return render_template('index.html', 
                           stats=stats, 
                           system_status=system_status, 
                           recent_activity=recent_activity)


@main_bp.route('/entries')
def entries():
    """
    Render the entries list page.
    """
    return render_template('entries.html')


@main_bp.route('/entries/<entry_id>')
def view_entry(entry_id):
    """
    Render the entry detail page.
    
    Args:
        entry_id: ID of the entry to view.
    """
    try:
        # Get dictionary service
        dict_service = injector.get(DictionaryService)
        
        # Get entry
        entry = dict_service.get_entry(entry_id)
        
        return render_template('entry_view.html', entry=entry)
    
    except NotFoundError:
        flash(f"Entry with ID {entry_id} not found.", "danger")
        return redirect(url_for('main.entries'))
    
    except Exception as e:
        logger.error(f"Error viewing entry {entry_id}: {e}")
        flash(f"Error loading entry: {str(e)}", "danger")
        return redirect(url_for('main.entries'))


@main_bp.route('/entries/<entry_id>/edit', methods=['GET', 'POST'])
def edit_entry(entry_id):
    """
    Render the entry edit page.
    
    Args:
        entry_id: ID of the entry to edit.
    """
    try:
        # Get dictionary service
        dict_service = injector.get(DictionaryService)
        
        if request.method == 'POST':
            # Handle form submission
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Create entry object
            entry = Entry.from_dict(data)
            entry.id = entry_id
            
            # Update entry
            dict_service.update_entry(entry)
            
            # Return success response
            return jsonify({'id': entry_id, 'message': 'Entry updated successfully'})
        
        # Get entry for display
        entry = dict_service.get_entry(entry_id)
        
        return render_template('entry_form.html', entry=entry)
    
    except NotFoundError:
        flash(f"Entry with ID {entry_id} not found.", "danger")
        return redirect(url_for('main.entries'))
    
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"Error editing entry {entry_id}: {e}")
        flash(f"Error loading entry: {str(e)}", "danger")
        return redirect(url_for('main.entries'))


@main_bp.route('/entries/add', methods=['GET', 'POST'])
def add_entry():
    """
    Render the add entry page.
    """
    try:
        if request.method == 'POST':
            # Handle form submission
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Create entry object
            entry = Entry.from_dict(data)
            
            # Get dictionary service
            dict_service = injector.get(DictionaryService)
            
            # Create entry
            entry_id = dict_service.create_entry(entry)
            
            # Return success response
            return jsonify({'id': entry_id, 'message': 'Entry created successfully'})
        
        # Create an empty entry for the form
        entry = Entry()
        
        return render_template('entry_form.html', entry=entry)
    
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"Error adding entry: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        if request.method == 'POST':
            return jsonify({'error': str(e)}), 500
        
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('main.entries'))


@main_bp.route('/search')
def search():
    """
    Render the search page.
    """
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    entries = []
    total = 0
    
    if query:
        try:
            dict_service = injector.get(DictionaryService)
            offset = (page - 1) * per_page
            entries, total = dict_service.search_entries(
                query=query,
                limit=per_page,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Error searching entries: {e}", exc_info=True)
            flash(f"Error searching entries: {str(e)}", "danger")
    
    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('search.html', 
                           query=query,
                           entries=entries,
                           total=total,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           has_prev=has_prev,
                           has_next=has_next)


@main_bp.route('/import/lift', methods=['GET', 'POST'])
def import_lift():
    """
    Render the LIFT import page.
    """
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'lift_file' not in request.files:
            flash("No file selected", "danger")
            return redirect(request.url)
        
        file = request.files['lift_file']
        
        # Check if file is empty
        if file.filename == '':
            flash("No file selected", "danger")
            return redirect(request.url)
        
        # Check file extension
        if not file.filename.lower().endswith('.lift'):
            flash("Invalid file type. Please upload a .lift file.", "danger")
            return redirect(request.url)
        
        try:
            # Save the file temporarily
            filepath = os.path.join(current_app.instance_path, 'uploads', file.filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            # Get dictionary service
            dict_service = injector.get(DictionaryService)
            
            # Import the LIFT file
            entry_count = dict_service.import_lift(filepath)
            
            flash(f"Successfully imported {entry_count} entries from LIFT file.", "success")
            return redirect(url_for('main.entries'))
            
        except Exception as e:
            logger.error(f"Error importing LIFT file: {e}")
            flash(f"Error importing LIFT file: {str(e)}", "danger")
            return redirect(request.url)
    
    return render_template('import_lift.html')


@main_bp.route('/export/lift')
def export_lift():
    """
    Export the dictionary to a LIFT file.
    """
    try:
        # Get dictionary service
        dict_service = injector.get(DictionaryService)
        
        # Generate the LIFT file
        lift_content = dict_service.export_lift()
        
        # Create a unique filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"dictionary_export_{timestamp}.lift"
        
        # Save the file
        filepath = os.path.join(current_app.instance_path, 'exports', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(lift_content)
        
        # Send the file as a download
        return send_from_directory(
            os.path.join(current_app.instance_path, 'exports'),
            filename,
            as_attachment=True
        )
        
    except Exception as e:
        logger.error(f"Error exporting LIFT file: {e}")
        flash(f"Error exporting LIFT file: {str(e)}", "danger")
        return redirect(url_for('main.index'))


@main_bp.route('/export/kindle')
def export_kindle():
    """
    Export the dictionary for Kindle.
    """
    try:
        # Get dictionary service
        dict_service = injector.get(DictionaryService)
        
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(current_app.instance_path, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate directory name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_name = f"kindle_export_{timestamp}"
        
        # Get Kindle export options from form or use defaults
        title = request.args.get('title', 'Dictionary')
        source_lang = request.args.get('source_lang', 'en')
        target_lang = request.args.get('target_lang', 'pl')
        author = request.args.get('author', 'Dictionary Writing System')
        
        # Get kindlegen path from config if available
        kindlegen_path = current_app.config.get('KINDLEGEN_PATH')
        
        # Export to Kindle format
        output_path = os.path.join(exports_dir, dir_name)
        output_dir = dict_service.export_to_kindle(
            output_path, 
            title=title,
            source_lang=source_lang,
            target_lang=target_lang,
            author=author,
            kindlegen_path=kindlegen_path
        )
        
        # Check if MOBI file was created
        mobi_path = os.path.join(output_dir, 'dictionary.mobi')
        mobi_created = os.path.exists(mobi_path)
        
        flash(f"Dictionary exported to Kindle format in {dir_name}", "success")
        
        # Return the download page for the exported files
        return render_template('export_download.html', 
                              export_type='kindle',
                              directory=dir_name,
                              files={
                                  'opf': 'dictionary.opf',
                                  'html': 'dictionary.html',
                                  'mobi': 'dictionary.mobi' if mobi_created else None
                              })
        
    except Exception as e:
        logger.error(f"Error exporting to Kindle format: {e}")
        flash(f"Error exporting to Kindle format: {str(e)}", "danger")
        return redirect(url_for('main.export_options'))


@main_bp.route('/export/sqlite')
def export_sqlite():
    """
    Export the dictionary to SQLite for mobile apps.
    """
    try:
        # Get dictionary service
        dict_service = injector.get(DictionaryService)
        
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(current_app.instance_path, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"dictionary_export_{timestamp}.db"
        
        # Get SQLite export options from form or use defaults
        source_lang = request.args.get('source_lang', 'en')
        target_lang = request.args.get('target_lang', 'pl')
        
        # Export to SQLite
        output_path = os.path.join(exports_dir, filename)
        dict_service.export_to_sqlite(
            output_path, 
            source_lang=source_lang,
            target_lang=target_lang,
            batch_size=500
        )
        
        flash(f"Dictionary exported to SQLite format as {filename}", "success")
        
        # Return the download page for the exported file
        return render_template('export_download.html', 
                              export_type='sqlite',
                              files={'sqlite': filename})
        
    except Exception as e:
        logger.error(f"Error exporting to SQLite format: {e}")
        flash(f"Error exporting to SQLite format: {str(e)}", "danger")
        return redirect(url_for('main.export_options'))


@main_bp.route('/export')
def export_options():
    """
    Show export options.
    """
    return render_template('export_options.html')


@main_bp.route('/export/download/<path:filename>')
def download_export(filename):
    """
    Download an exported file.
    
    Args:
        filename: Name of the file to download.
    """
    try:
        # Get the directory and filename
        if '/' in filename:
            directory, filename = filename.split('/', 1)
        else:
            directory = None
        
        # Construct the path
        if directory:
            file_path = os.path.join(current_app.instance_path, 'exports', directory, filename)
        else:
            file_path = os.path.join(current_app.instance_path, 'exports', filename)
        
        # Check if file exists
        if not os.path.isfile(file_path):
            flash(f"File not found: {filename}", "danger")
            return redirect(url_for('main.export_options'))
        
        # Determine MIME type based on file extension
        mime_type = 'application/octet-stream'  # Default
        if filename.endswith('.lift'):
            mime_type = 'application/xml'
        elif filename.endswith('.db'):
            mime_type = 'application/x-sqlite3'
        elif filename.endswith('.mobi'):
            mime_type = 'application/x-mobipocket-ebook'
        elif filename.endswith('.opf'):
            mime_type = 'application/oebps-package+xml'
        elif filename.endswith('.html'):
            mime_type = 'text/html'
        
        # Send file
        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            mimetype=mime_type,
            as_attachment=True
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        flash(f"Error downloading file: {str(e)}", "danger")
        return redirect(url_for('main.export_options'))


@main_bp.route('/tools/batch-edit')
def batch_edit():
    """
    Render the batch edit page.
    """
    # To be implemented
    flash("Batch editing is not yet implemented.", "info")
    return redirect(url_for('main.index'))


@main_bp.route('/tools/validation')
def validation():
    """
    Render the validation page.
    """
    # To be implemented
    flash("Validation is not yet implemented.", "info")
    return redirect(url_for('main.index'))


@main_bp.route('/tools/pronunciation')
def pronunciation():
    """
    Render the pronunciation management page.
    """
    # To be implemented
    flash("Pronunciation management is not yet implemented.", "info")
    return redirect(url_for('main.index'))


@main_bp.route('/settings')
def settings():
    """
    Render the settings page.
    """
    # To be implemented
    flash("Settings is not yet implemented.", "info")
    return redirect(url_for('main.index'))


@main_bp.route('/activity-log')
def activity_log():
    """
    Render the activity log page.
    """
    # To be implemented
    flash("Activity log is not yet implemented.", "info")
    return redirect(url_for('main.index'))


@main_bp.route('/audio/<filename>')
def audio_file(filename):
    """
    Serve audio files.
    
    Args:
        filename: Name of the audio file.
    """
    return send_from_directory(
        os.path.join(current_app.instance_path, 'audio'),
        filename
    )


# API endpoints for the frontend

@main_bp.route('/api/stats')
def api_stats():
    """
    Get dictionary statistics.
    """
    try:
        dict_service = injector.get(DictionaryService)
        entry_count = dict_service.count_entries()
        sense_count, example_count = dict_service.count_senses_and_examples()
        
        return jsonify({
            'entries': entry_count,
            'senses': sense_count,
            'examples': example_count
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/system/status')
def api_system_status():
    """
    Get system status.
    """
    try:
        dict_service = injector.get(DictionaryService)
        return jsonify(dict_service.get_system_status())
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/activity')
def api_activity():
    """
    Get recent activity.
    """
    try:
        # Get limit parameter
        limit = request.args.get('limit', 5, type=int)
        
        dict_service = injector.get(DictionaryService)
        activities = dict_service.get_recent_activity(limit=limit)
        
        return jsonify({
            'activities': activities
        })
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/pronunciations/generate', methods=['POST'])
def api_generate_pronunciation():
    """
    Generate pronunciation audio.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        word = data.get('word')
        ipa = data.get('ipa')
        
        if not word:
            return jsonify({'error': 'Word is required'}), 400
        
        # This would typically generate audio using TTS
        # For now, just return a placeholder
        
        # Create a unique filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"pronunciation_{timestamp}.mp3"
        
        # Return the audio URL
        return jsonify({
            'audio_url': f"/audio/{filename}",
            'word': word,
            'ipa': ipa
        })
    except Exception as e:
        logger.error(f"Error generating pronunciation: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/test-search')
def test_search():
    """
    Test search functionality with a visual interface.
    """
    query = request.args.get('query', '')
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    entries = []
    total = 0
    error = None
    
    if query:
        try:
            dict_service = injector.get(DictionaryService)
            entries, total = dict_service.search_entries(
                query=query,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Error testing search: {e}", exc_info=True)
            error = str(e)
    
    return render_template('test_search.html', 
                           query=query,
                           entries=entries,
                           total=total,
                           limit=limit,
                           offset=offset,
                           error=error)


@main_bp.route('/api/test-search')
def api_test_search():
    """
    Test search functionality.
    """
    try:
        query = request.args.get('query', '')
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if not query:
            return jsonify({'error': 'No search query provided'}), 400
        
        dict_service = injector.get(DictionaryService)
        entries, total = dict_service.search_entries(
            query=query,
            limit=limit,
            offset=offset
        )
        
        # Convert entries to dictionaries for JSON response
        entry_dicts = [entry.to_dict() for entry in entries]
        
        return jsonify({
            'entries': entry_dicts,
            'total': total,
            'query': query,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error testing search: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500



