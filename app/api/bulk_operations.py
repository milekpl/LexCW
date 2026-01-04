"""
API endpoints for bulk operations on dictionary entries.

Provides endpoints for:
- /bulk/traits/convert - Convert traits across multiple entries
- /bulk/pos/update - Update part-of-speech tags across multiple entries
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from typing import Any

from app.services.bulk_operations_service import BulkOperationsService

logger = logging.getLogger(__name__)

# Create the bulk operations blueprint
bulk_bp = Blueprint('bulk_operations', __name__, url_prefix='/bulk')


def get_bulk_operations_service() -> BulkOperationsService:
    """
    Get an instance of the BulkOperationsService from the current app context.

    Returns:
        BulkOperationsService instance.
    """
    return current_app.injector.get(BulkOperationsService)


@bulk_bp.route('/traits/convert', methods=['POST'])
def convert_traits() -> Any:
    """
    Convert traits across multiple entries.

    Request body:
        {
            "entry_ids": ["entry-1", "entry-2", ...],
            "from_trait": "verb",
            "to_trait": "noun"
        }

    Returns:
        {
            "operation_id": "op-YYYYMMDD-N",
            "summary": {
                "requested": 3,
                "success": 2,
                "failed": 1
            },
            "results": [
                {"id": "entry-1", "status": "success", "data": {...}},
                {"id": "entry-2", "status": "error", "error": "..."}
            ]
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    entry_ids = data.get('entry_ids', [])
    from_trait = data.get('from_trait')
    to_trait = data.get('to_trait')

    # Validate required fields
    if not entry_ids:
        return jsonify({'error': 'Missing required field: entry_ids'}), 400
    if not from_trait:
        return jsonify({'error': 'Missing required field: from_trait'}), 400
    if not to_trait:
        return jsonify({'error': 'Missing required field: to_trait'}), 400

    try:
        service = get_bulk_operations_service()
        result = service.convert_traits(entry_ids, from_trait, to_trait)

        # Calculate summary
        summary = {
            'requested': result['total'],
            'success': sum(1 for r in result['results'] if r['status'] == 'success'),
            'failed': sum(1 for r in result['results'] if r['status'] == 'error')
        }

        # Generate operation ID
        from datetime import datetime
        operation_id = f'op-{datetime.utcnow().strftime("%Y%m%d")}-{result["total"]}'

        return jsonify({
            'operation_id': operation_id,
            'summary': summary,
            'results': result['results']
        })

    except Exception as e:
        logger.error("Error in convert_traits: %s", str(e))
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/pos/update', methods=['POST'])
def update_pos_bulk() -> Any:
    """
    Update part-of-speech tags across multiple entries.

    Request body:
        {
            "entry_ids": ["entry-1", "entry-2", ...],
            "pos_tag": "noun"
        }

    Returns:
        {
            "operation_id": "op-YYYYMMDD-N",
            "summary": {
                "requested": 3,
                "success": 2,
                "failed": 1
            },
            "results": [
                {"id": "entry-1", "status": "success", "data": {...}},
                {"id": "entry-2", "status": "error", "error": "..."}
            ]
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    entry_ids = data.get('entry_ids', [])
    pos_tag = data.get('pos_tag')

    # Validate required fields
    if not entry_ids:
        return jsonify({'error': 'Missing required field: entry_ids'}), 400
    if not pos_tag:
        return jsonify({'error': 'Missing required field: pos_tag'}), 400

    try:
        service = get_bulk_operations_service()
        result = service.update_pos_bulk(entry_ids, pos_tag)

        # Calculate summary
        summary = {
            'requested': result['total'],
            'success': sum(1 for r in result['results'] if r['status'] == 'success'),
            'failed': sum(1 for r in result['results'] if r['status'] == 'error')
        }

        # Generate operation ID
        from datetime import datetime
        operation_id = f'op-{datetime.utcnow().strftime("%Y%m%d")}-{result["total"]}'

        return jsonify({
            'operation_id': operation_id,
            'summary': summary,
            'results': result['results']
        })

    except Exception as e:
        logger.error("Error in update_pos_bulk: %s", str(e))
        return jsonify({'error': str(e)}), 500
