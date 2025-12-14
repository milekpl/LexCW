"""
API endpoints for backup functionality.
"""

from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app
from typing import Union, Tuple, Dict, Any
from datetime import datetime
import json

from app.services.operation_history_service import OperationHistoryService
from app.services.basex_backup_manager import BaseXBackupManager
from app.services.backup_scheduler import BackupScheduler
from app.models.backup_models import Backup, ScheduledBackup, OperationHistory

# Create the blueprint for backup API routes
backup_api = Blueprint('backup_api', __name__, url_prefix='/api/backup')


@backup_api.route('/operations', methods=['GET'])
def get_operation_history() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Get operation history for undo/redo functionality.
    
    Query Parameters:
        entry_id: Optional entry ID to filter operations
        limit: Optional limit on number of operations to return
    
    Returns:
        JSON response with operation history
    """
    try:
        # Get query parameters
        entry_id = request.args.get('entry_id')
        limit = request.args.get('limit', type=int)
        
        # Get operation history service
        operation_service = current_app.injector.get(OperationHistoryService)
        
        # Get operation history
        operations = operation_service.get_operation_history(entry_id=entry_id)
        
        # Apply limit if specified
        if limit and len(operations) > limit:
            operations = operations[:limit]
        
        return jsonify({
            'success': True,
            'data': operations,
            'count': len(operations)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/operations/undo', methods=['POST'])
def undo_last_operation() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Undo the last operation.
    
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Get operation history service
        operation_service = current_app.injector.get(OperationHistoryService)
        
        # Attempt to undo the last operation
        result = operation_service.undo_last_operation()
        
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Operation undone successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No operations available to undo'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/operations/redo', methods=['POST'])
def redo_last_operation() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Redo the last undone operation.
    
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Get operation history service
        operation_service = current_app.injector.get(OperationHistoryService)
        
        # Attempt to redo the last operation
        result = operation_service.redo_last_operation()
        
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Operation redone successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No operations available to redo'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/create', methods=['POST'])
def create_backup() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Create a manual backup of the database.
    
    Request Body:
        {
            "db_name": "database_name",
            "backup_type": "full|incremental|manual",
            "description": "Optional description of the backup"
        }
    
    Returns:
        JSON response with backup details
    """
    try:
        # Get request body
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No request body provided'
            }), 400
            
        db_name = data.get('db_name')
        backup_type = data.get('backup_type', 'manual')
        description = data.get('description', f'Manual backup at {datetime.now().isoformat()}')
        
        if not db_name:
            return jsonify({
                'success': False,
                'error': 'Database name is required'
            }), 400
        
        # Get backup manager
        backup_manager = current_app.injector.get(BaseXBackupManager)
        
        # Create the backup
        backup = backup_manager.backup_database(
            db_name=db_name,
            backup_type=backup_type,
            description=description
        )
        
        return jsonify({
            'success': True,
            'data': backup.to_dict(),
            'message': f'Backup created successfully for {db_name}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/history', methods=['GET'])
def get_backup_history() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Get backup history.
    
    Query Parameters:
        db_name: Optional database name to filter backups
    
    Returns:
        JSON response with backup history
    """
    try:
        # Get query parameters
        db_name = request.args.get('db_name')
        
        # Get backup manager
        backup_manager = current_app.injector.get(BaseXBackupManager)
        
        # Get backup history
        backups = backup_manager.list_backups(db_name=db_name)
        
        return jsonify({
            'success': True,
            'data': backups,
            'count': len(backups)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/restore/<backup_id>', methods=['POST'])
def restore_backup(backup_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Restore database from a backup.
    
    Path Parameters:
        backup_id: ID of the backup to restore from
    
    Request Body:
        {
            "db_name": "target_database_name",
            "backup_file_path": "path_to_backup_file"
        }
    
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Get request body
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No request body provided'
            }), 400
            
        db_name = data.get('db_name')
        backup_file_path = data.get('backup_file_path')
        
        if not db_name or not backup_file_path:
            return jsonify({
                'success': False,
                'error': 'Database name and backup file path are required'
            }), 400
        
        # Get backup manager
        backup_manager = current_app.injector.get(BaseXBackupManager)
        
        # Restore from backup
        success = backup_manager.restore_database(
            db_name=db_name,
            backup_id=backup_id,
            backup_file_path=backup_file_path
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Database {db_name} restored successfully from backup {backup_id}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to restore database {db_name} from backup {backup_id}'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/validate/<path:backup_file_path>', methods=['GET'])
def validate_backup(backup_file_path: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Validate a backup file.
    
    Path Parameters:
        backup_file_path: Path to the backup file to validate
    
    Returns:
        JSON response with validation results
    """
    try:
        # Get backup manager
        backup_manager = current_app.injector.get(BaseXBackupManager)
        
        # Validate the backup
        validation_result = backup_manager.validate_backup(backup_file_path)
        
        return jsonify({
            'success': True,
            'data': validation_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/schedule', methods=['POST'])
def schedule_backup() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Schedule a cyclical backup.
    
    Request Body:
        {
            "db_name": "database_name",
            "interval": "hourly|daily|weekly",
            "time": "HH:MM or cron format",
            "type": "full|incremental",
            "active": true
        }
    
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Get request body
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No request body provided'
            }), 400
        
        # Create a ScheduledBackup model instance
        scheduled_backup = ScheduledBackup(
            db_name=data.get('db_name'),
            interval=data.get('interval', 'daily'),
            time_=data.get('time', '02:00'),  # Default to 2 AM
            type_=data.get('type', 'full'),
            next_run=datetime.now(),  # Will be updated by the scheduler
            active=data.get('active', True)
        )
        
        # Get backup scheduler
        backup_scheduler = current_app.injector.get(BackupScheduler)
        
        # Schedule the backup
        success = backup_scheduler.schedule_backup(scheduled_backup)
        
        if success:
            return jsonify({
                'success': True,
                'data': scheduled_backup.to_dict(),
                'message': f'Backup scheduled successfully for {scheduled_backup.db_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to schedule backup for {scheduled_backup.db_name}'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/scheduled', methods=['GET'])
def get_scheduled_backups() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Get information about scheduled backups.
    
    Returns:
        JSON response with scheduled backup information
    """
    try:
        # Get backup scheduler
        backup_scheduler = current_app.injector.get(BackupScheduler)
        
        # Get scheduled backups info
        scheduled_info = backup_scheduler.get_scheduled_backups()
        
        return jsonify({
            'success': True,
            'data': scheduled_info,
            'count': len(scheduled_info)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_api.route('/scheduled/<schedule_id>', methods=['DELETE'])
def cancel_scheduled_backup(schedule_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """
    Cancel a scheduled backup.
    
    Path Parameters:
        schedule_id: ID of the scheduled backup to cancel
    
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Get backup scheduler
        backup_scheduler = current_app.injector.get(BackupScheduler)
        
        # Cancel the scheduled backup
        success = backup_scheduler.cancel_backup(schedule_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Scheduled backup {schedule_id} cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to cancel scheduled backup {schedule_id}'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
