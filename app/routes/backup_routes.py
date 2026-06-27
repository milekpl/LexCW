import os
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, current_app, flash, redirect, url_for, send_from_directory
from flasgger import swag_from
from app.services.backup_service import get_backup_service

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
        service = get_backup_service()
        db_name = current_app.config.get('BASEX_DATABASE', 'dictionary')

        meta, op_id = service.create_backup(
            db_name=db_name,
            backup_type='manual'
        )

        file_path = meta.get('file_path')
        if not file_path or not os.path.exists(file_path):
            flash('Backup file was not created successfully.', 'error')
            return redirect(url_for('backup.backup_management'))

        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)

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