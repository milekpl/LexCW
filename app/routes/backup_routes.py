from flask import Blueprint, render_template, current_app, flash, redirect, url_for
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

    Delegates to ``BackupService.download_backup`` — the SAME implementation
    as the API endpoint — so the ZIP bundles the sidecars (ranges, settings,
    validation rules, meta, media) instead of the raw .lift only.
    """
    try:
        service = get_backup_service()
        db_name = current_app.config.get('BASEX_DATABASE', 'dictionary')

        service.create_backup(
            db_name=db_name,
            backup_type='manual'
        )

        # Resolve the just-created backup (async creation may not return a
        # file_path directly) and serve it via the shared download path.
        backups = service.list_backups(db_name=db_name) or []
        if not backups:
            flash('Backup file was not created successfully.', 'error')
            return redirect(url_for('backup.backup_management'))

        result = service.download_backup(backups[0]['id'])
        if isinstance(result, tuple):
            flash(f'Backup download failed: {result[1]}', 'error')
            return redirect(url_for('backup.backup_management'))
        return result

    except Exception as e:
        current_app.logger.error(f"Error creating backup for download: {e}")
        flash(f'Backup creation failed: {str(e)}', 'error')
        return redirect(url_for('backup.backup_management'))