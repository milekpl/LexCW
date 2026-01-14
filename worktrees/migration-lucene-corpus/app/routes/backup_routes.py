from flask import Blueprint, render_template, jsonify, request, current_app, flash, redirect, url_for, send_from_directory
from flasgger import swag_from
import os
from datetime import datetime
from app.services.basex_backup_manager import BaseXBackupManager

# Create blueprint
backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

@backup_bp.route('/management', methods=['GET'])
@swag_from({
    'summary': 'Backup Management Interface',
    'description': 'Render the backup management interface.',
    'tags': ['Backup'],
    'responses': {
        '200': {'description': 'Backup management page rendered.'},
        '500': {'description': 'Internal server error.'}
    }
})
def backup_management():
    """Render the backup management interface."""
    # Use the configured database name from app config, not from project settings
    # This ensures we always use the correct database for backups
    db_name = current_app.config.get('BASEX_DATABASE', 'dictionary')
    return render_template('backup_management.html', title="Backup Management", db_name=db_name)


@backup_bp.route('/download', methods=['GET'])
@swag_from({
    'summary': 'Download Database Backup',
    'description': 'Create and download a backup of the current database.',
    'tags': ['Backup'],
    'responses': {
        '200': {'description': 'Backup file downloaded successfully.'},
        '500': {'description': 'Backup creation failed.'}
    }
})
def download_backup():
    """
    Create a backup and return it as a downloadable file.
    """
    try:
        # Get backup manager service
        backup_manager = current_app.injector.get(BaseXBackupManager)

        # Use configured database name, not hardcoded 'dictionary'
        db_name = current_app.config.get('BASEX_DATABASE', 'dictionary')

        # Create a backup
        backup = backup_manager.create_backup(
            db_name=db_name,
            backup_type='manual'
        )

        # Check if backup file exists
        if not os.path.exists(backup.file_path):
            flash('Backup file was not created successfully.', 'error')
            return redirect(url_for('backup.backup_management'))

        # Return the file as a download
        directory = os.path.dirname(backup.file_path)
        filename = os.path.basename(backup.file_path)

        return send_from_directory(
            directory,
            filename,
            as_attachment=True,
            download_name=f"{db_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.lift"
        )

    except Exception as e:
        current_app.logger.error(f"Error creating backup for download: {e}")
        flash(f'Backup creation failed: {str(e)}', 'error')
        return redirect(url_for('backup.backup_management'))