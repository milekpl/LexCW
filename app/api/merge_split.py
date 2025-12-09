 es"""
API endpoints for merge and split operations.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, List, Optional
from app.services.merge_split_service import MergeSplitService
from app.models.merge_split_operations import MergeSplitOperation
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.decorators import require_json, handle_exceptions

merge_split_bp = Blueprint('merge_split', __name__, url_prefix='/api/merge-split')

def get_merge_split_service() -> MergeSplitService:
    """Get the merge/split service instance."""
    # Try to get from current_app first (for testing)
    if hasattr(current_app, 'merge_split_service') and current_app.merge_split_service:
        return current_app.merge_split_service

    # Try to use injector (for production)
    try:
        from app import injector
        return injector.get(MergeSplitService)
    except (ImportError, AttributeError):
        pass

    # Fallback: create a new instance
    from app.services.dictionary_service import DictionaryService
    dict_service = current_app.dict_service if hasattr(current_app, 'dict_service') else None
    if not dict_service:
        # This should not happen in normal operation
        raise RuntimeError("Dictionary service not available")

    return MergeSplitService(dict_service)

@merge_split_bp.route('/operations', methods=['GET'])
@handle_exceptions
def get_operations():
    """
    Get all merge/split operations.

    Returns:
        JSON list of all operations
    """
    service = get_merge_split_service()
    operations = service.get_operation_history()

    return jsonify([
        operation.to_dict() for operation in operations
    ])

@merge_split_bp.route('/operations/<operation_id>', methods=['GET'])
@handle_exceptions
def get_operation(operation_id: str):
    """
    Get a specific merge/split operation by ID.

    Args:
        operation_id: ID of the operation

    Returns:
        JSON representation of the operation
    """
    service = get_merge_split_service()
    operation = service.get_operation_by_id(operation_id)

    if not operation:
        return jsonify({"error": "Operation not found"}), 404

    return jsonify(operation.to_dict())

@merge_split_bp.route('/entries/<entry_id>/split', methods=['POST'])
@require_json
@handle_exceptions
def split_entry(entry_id: str):
    """
    Split an entry by moving senses to a new entry.

    Args:
        entry_id: ID of the source entry

    Request JSON:
        {
            "sense_ids": ["sense_id_1", "sense_id_2"],
            "new_entry_data": {
                "lexical_unit": {"en": "new lexical unit"},
                "pronunciations": {"seh-fonipa": "/ipa/"},
                "grammatical_info": "noun"
            }
        }

    Returns:
        JSON representation of the operation result
    """
    data = request.get_json()
    sense_ids = data.get('sense_ids', [])
    new_entry_data = data.get('new_entry_data', {})
    user_id = data.get('user_id')

    if not sense_ids:
        return jsonify({"error": "sense_ids is required"}), 400

    service = get_merge_split_service()

    try:
        operation = service.split_entry(
            source_entry_id=entry_id,
            sense_ids=sense_ids,
            new_entry_data=new_entry_data,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "operation": operation.to_dict(),
            "message": "Entry split successfully"
        }), 201

    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500

@merge_split_bp.route('/entries/<target_id>/merge', methods=['POST'])
@require_json
@handle_exceptions
def merge_entries(target_id: str):
    """
    Merge senses from source entry into target entry.

    Args:
        target_id: ID of the target entry

    Request JSON:
        {
            "source_entry_id": "source_entry_id",
            "sense_ids": ["sense_id_1", "sense_id_2"],
            "conflict_resolution": {
                "duplicate_senses": "rename"  # or "skip", "overwrite"
            }
        }

    Returns:
        JSON representation of the operation result
    """
    data = request.get_json()
    source_entry_id = data.get('source_entry_id')
    sense_ids = data.get('sense_ids', [])
    conflict_resolution = data.get('conflict_resolution', {})
    user_id = data.get('user_id')

    if not source_entry_id:
        return jsonify({"error": "source_entry_id is required"}), 400

    if not sense_ids:
        return jsonify({"error": "sense_ids is required"}), 400

    service = get_merge_split_service()

    try:
        operation = service.merge_entries(
            target_entry_id=target_id,
            source_entry_id=source_entry_id,
            sense_ids=sense_ids,
            conflict_resolution=conflict_resolution,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "operation": operation.to_dict(),
            "message": "Entries merged successfully"
        }), 200

    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500

@merge_split_bp.route('/entries/<entry_id>/senses/<target_sense_id>/merge', methods=['POST'])
@require_json
@handle_exceptions
def merge_senses(entry_id: str, target_sense_id: str):
    """
    Merge senses within the same entry.

    Args:
        entry_id: ID of the entry
        target_sense_id: ID of the target sense

    Request JSON:
        {
            "source_sense_ids": ["sense_id_1", "sense_id_2"],
            "merge_strategy": "combine_all"  # or "keep_target", "keep_source"
        }

    Returns:
        JSON representation of the operation result
    """
    data = request.get_json()
    source_sense_ids = data.get('source_sense_ids', [])
    merge_strategy = data.get('merge_strategy', 'combine_all')
    user_id = data.get('user_id')

    if not source_sense_ids:
        return jsonify({"error": "source_sense_ids is required"}), 400

    service = get_merge_split_service()

    try:
        operation = service.merge_senses(
            entry_id=entry_id,
            target_sense_id=target_sense_id,
            source_sense_ids=source_sense_ids,
            merge_strategy=merge_strategy,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "operation": operation.to_dict(),
            "message": "Senses merged successfully"
        }), 200

    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500

@merge_split_bp.route('/transfers', methods=['GET'])
@handle_exceptions
def get_transfers():
    """
    Get all sense transfers.

    Returns:
        JSON list of all transfers
    """
    service = get_merge_split_service()
    transfers = service.get_sense_transfer_history()

    return jsonify([
        transfer.to_dict() for transfer in transfers
    ])

@merge_split_bp.route('/transfers/sense/<sense_id>', methods=['GET'])
@handle_exceptions
def get_transfers_by_sense(sense_id: str):
    """
    Get transfers for a specific sense.

    Args:
        sense_id: ID of the sense

    Returns:
        JSON list of transfers for the sense
    """
    service = get_merge_split_service()
    transfers = service.get_transfers_by_sense_id(sense_id)

    return jsonify([
        transfer.to_dict() for transfer in transfers
    ])

@merge_split_bp.route('/transfers/entry/<entry_id>', methods=['GET'])
@handle_exceptions
def get_transfers_by_entry(entry_id: str):
    """
    Get transfers involving a specific entry.

    Args:
        entry_id: ID of the entry

    Returns:
        JSON list of transfers involving the entry
    """
    service = get_merge_split_service()
    transfers = service.get_transfers_by_entry_id(entry_id)

    return jsonify([
        transfer.to_dict() for transfer in transfers
    ])

@merge_split_bp.route('/operations/<operation_id>/status', methods=['GET'])
@handle_exceptions
def get_operation_status(operation_id: str):
    """
    Get the status of a specific operation.

    Args:
        operation_id: ID of the operation

    Returns:
        JSON with operation status
    """
    service = get_merge_split_service()
    operation = service.get_operation_by_id(operation_id)

    if not operation:
        return jsonify({"error": "Operation not found"}), 404

    return jsonify({
        "operation_id": operation.id,
        "status": operation.status,
        "type": operation.operation_type,
        "timestamp": operation.timestamp.isoformat() if hasattr(operation, 'timestamp') else None,
        "metadata": operation.metadata
    })

# Register the blueprint in the main app
def register_merge_split_blueprint(app):
    """Register the merge/split blueprint with the Flask app."""
    app.register_blueprint(merge_split_bp)

    # Initialize service if not already done
    if not hasattr(app, 'merge_split_service'):
        from app.services.dictionary_service import DictionaryService
        dict_service = app.dict_service if hasattr(app, 'dict_service') else None
        if dict_service:
            app.merge_split_service = MergeSplitService(dict_service)