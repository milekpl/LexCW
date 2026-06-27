"""
API endpoints for backup functionality.
"""

from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app
from typing import Union, Tuple, Dict, Any

from app.services.backup_service import get_backup_service
from app.utils.exceptions import ValidationError

# Create the blueprint for backup API routes
backup_api = Blueprint('backup_api', __name__, url_prefix='/api/backup')


@backup_api.route('/operations', methods=['GET'])
def get_operation_history() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        entry_id = request.args.get('entry_id')
        limit = request.args.get('limit', type=int)
        operations = service.get_operation_history(entry_id=entry_id, limit=limit)
        return jsonify({
            'success': True,
            'data': operations,
            'count': len(operations)
        })
    except Exception as e:
        current_app.logger.exception('Unhandled error in get_operation_history: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/operations/undo', methods=['POST'])
def undo_last_operation() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        result = service.undo_last_operation()
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Operation undone successfully'
            })
        return jsonify({
            'success': False,
            'error': 'No operations available to undo'
        }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/operations/redo', methods=['POST'])
def redo_last_operation() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        result = service.redo_last_operation()
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Operation redone successfully'
            })
        return jsonify({
            'success': False,
            'error': 'No operations available to redo'
        }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/create', methods=['POST'])
def create_backup() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No request body provided'}), 400

        db_name = data.get('db_name')
        if not db_name:
            return jsonify({'success': False, 'error': 'Database name is required'}), 400

        service = get_backup_service()
        meta, op_id = service.create_backup(
            db_name=db_name,
            backup_type=data.get('backup_type', 'manual'),
            description=data.get('description'),
            include_media=data.get('include_media', False),
        )

        return jsonify({
            'success': True,
            'data': meta,
            'op_id': op_id,
            'message': f'Backup created successfully for {db_name}'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/ping', methods=['GET'])
def ping() -> Dict[str, Any]:
    """Lightweight health-check endpoint for backup API."""
    return jsonify({'success': True, 'status': 'ok'})


@backup_api.route('/history', methods=['GET'])
def get_backup_history() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        db_name = request.args.get('db_name')
        backups = service.list_backups(db_name=db_name)
        return jsonify({'success': True, 'data': backups, 'count': len(backups)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/restore/<backup_id>', methods=['POST'])
def restore_backup(backup_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No request body provided'}), 400

        db_name = data.get('db_name')
        backup_file_path = data.get('backup_file_path')
        if not db_name or not backup_file_path:
            return jsonify({
                'success': False,
                'error': 'Database name and backup file path are required'
            }), 400

        service = get_backup_service()
        try:
            success = service.restore_database(
                db_name=db_name,
                backup_id=backup_id,
                backup_file_path=backup_file_path
            )
        except ValidationError as ve:
            return jsonify({'success': False, 'error': str(ve)}), 400

        if success:
            return jsonify({
                'success': True,
                'message': f'Database {db_name} restored successfully from backup {backup_id}'
            })
        return jsonify({
            'success': False,
            'error': f'Failed to restore database {db_name} from backup {backup_id}'
        }), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/validate/<path:backup_file_path>', methods=['GET'])
def validate_backup(backup_file_path: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        return jsonify(service.validate_backup(backup_file_path))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/schedule', methods=['POST'])
def schedule_backup() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No request body provided'}), 400

        service = get_backup_service()
        success, scheduled_backup, error = service.schedule_backup(data)

        if success:
            return jsonify({
                'success': True,
                'data': scheduled_backup.to_dict(),
                'message': f'Backup scheduled successfully for {scheduled_backup.db_name}'
            })
        return jsonify({'success': False, 'error': error or 'Failed to schedule backup'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/history/<backup_id>', methods=['GET'])
def get_backup_details(backup_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        return jsonify(service.get_backup_by_id(backup_id))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404


@backup_api.route('/validate_id/<backup_id>', methods=['GET'])
def validate_backup_by_id(backup_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        return jsonify(service.validate_backup_by_id(backup_id))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/download/<backup_id>', methods=['GET'])
def download_backup(backup_id: str):
    try:
        service = get_backup_service()
        return service.download_backup(backup_id)
    except Exception as e:
        current_app.logger.exception('Error downloading backup %s: %s', backup_id, e)
        return jsonify({'success': False, 'error': str(e)}), 404


@backup_api.route('/status/<op_id>', methods=['GET'])
def backup_status(op_id: str):
    try:
        service = get_backup_service()
        op = service.backup_status(op_id)
        if op is None:
            return jsonify({'success': False, 'error': 'Operation not found'}), 404
        return jsonify({'success': True, 'op': op})
    except Exception as e:
        current_app.logger.exception('Error looking up op %s: %s', op_id, e)
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/dir', methods=['GET', 'POST'])
def backup_directory():
    try:
        cfg = current_app.config_manager
        if request.method == 'POST':
            data = request.get_json() or {}
            directory = data.get('directory', '')
            new = {'backup_settings': {'directory': directory}}
            cfg.update_current_settings(new)
            return jsonify({'success': True, 'directory': directory})

        configured = cfg.get_backup_settings().get('directory', '')
        try:
            service = get_backup_service()
            effective = str(service.get_backup_directory())
        except Exception:
            effective = None

        return jsonify({
            'success': True,
            'configured_directory': configured,
            'effective_directory': effective
        })
    except Exception as e:
        current_app.logger.exception('Error handling backup directory request: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/<backup_id>', methods=['DELETE'])
def delete_backup(backup_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        success = service.delete_backup(backup_id)
        if success:
            return jsonify({'success': True, 'message': f'Backup {backup_id} deleted'})
        return jsonify({'success': False, 'error': f'Failed to delete {backup_id}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/scheduled', methods=['GET'])
def get_scheduled_backups() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        scheduled_info = service.get_scheduled_backups()
        return jsonify({'success': True, 'data': scheduled_info, 'count': len(scheduled_info)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_api.route('/scheduled/<schedule_id>', methods=['DELETE'])
def cancel_scheduled_backup(schedule_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        service = get_backup_service()
        success = service.cancel_scheduled_backup(schedule_id)
        if success:
            return jsonify({
                'success': True,
                'message': f'Scheduled backup {schedule_id} cancelled successfully'
            })
        return jsonify({
            'success': False,
            'error': f'Failed to cancel scheduled backup {schedule_id}'
        }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
