"""
Views for the Dictionary Writing System's frontend.
"""

import logging
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory

from app.services.dictionary_service import DictionaryService
from app.database.connector_factory import create_database_connector
from app.models.entry import Entry
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError

# Create blueprint
main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


def get_dictionary_service():
    """
    Get an instance of the dictionary service.
    
    Returns:
        DictionaryService instance.
    """
    # Create a BaseX connector using app config
    connector = BaseXConnector(
        host=current_app.config['BASEX_HOST'],
        port=current_app.config['BASEX_PORT'],
        username=current_app.config['BASEX_USERNAME'],
        password=current_app.config['BASEX_PASSWORD'],
        database=current_app.config['BASEX_DATABASE'],
    )
    
    # Create and return a dictionary service
    return DictionaryService(connector)


@main_bp.route('/')
def index():
    """
    Render the dashboard/home page.
    """
    # Sample data for dashboard (in a real app, this would come from the database)
    stats = {
        'entries': 0,
        'senses': 0,
        'examples': 0
    }
    
    system_status = {
        'db_connected': True,
        'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'storage_percent': 23
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
    
    # Get actual stats from the database if possible
    try:
        dict_service = get_dictionary_service()
        entry_count = dict_service.count_entries()
        stats['entries'] = entry_count
        
        # Get sense and example counts
        sense_count, example_count = dict_service.count_senses_and_examples()
        stats['senses'] = sense_count
        stats['examples'] = example_count
        
        # Get recent activity
        # recent_activity = dict_service.get_recent_activity(limit=5)
        
        # Get system status
        # system_status = dict_service.get_system_status()
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
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
        dict_service = get_dictionary_service()
        
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
        dict_service = get_dictionary_service()
        
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
            dict_service = get_dictionary_service()
            
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
        
        if request.method == 'POST':
            return jsonify({'error': str(e)}), 500
        
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('main.entries'))


@main_bp.route('/search')
def search():
    """
    Render the search page.
    """
    return render_template('search.html')


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
            dict_service = get_dictionary_service()
            
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
        dict_service = get_dictionary_service()
        
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
        dict_service = get_dictionary_service()
        
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
        dict_service = get_dictionary_service()
        
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
        dict_service = get_dictionary_service()
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
        # This would typically come from the database or system monitoring
        return jsonify({
            'db_connected': True,
            'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'storage_percent': 23
        })
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
        
        # This would typically come from the database
        activities = [
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
        
        return jsonify({
            'activities': activities[:limit]
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
