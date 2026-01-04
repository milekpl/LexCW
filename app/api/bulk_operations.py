"""
API endpoints for bulk operations on dictionary entries.

Provides endpoints for:
- /bulk/traits/convert - Convert traits across multiple entries
- /bulk/pos/update - Update part-of-speech tags across multiple entries
- /bulk/query - Query entries matching conditions
- /bulk/execute - Execute bulk actions on matching entries
- /bulk/pipeline - Execute chained operations
- /bulk/preview - Preview effects without applying
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from typing import Any

# Lazy imports to avoid circular dependency issues
def get_bulk_operations_service():
    from app.services.bulk_operations_service import BulkOperationsService
    return current_app.injector.get(BulkOperationsService)

def get_bulk_query_service():
    from app.services.bulk_query_service import BulkQueryService
    return current_app.injector.get(BulkQueryService)

def get_bulk_action_service():
    from app.services.bulk_action_service import BulkActionService
    return current_app.injector.get(BulkActionService)

logger = logging.getLogger(__name__)

# Create the bulk operations blueprint
bulk_bp = Blueprint('bulk_operations', __name__, url_prefix='/bulk')


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


@bulk_bp.route('/query', methods=['POST'])
def bulk_query() -> Any:
    """
    Query entries matching specified conditions.

    Request body:
        {
            "condition": {
                "and": [
                    {"field": "lexical_unit", "operator": "contains", "value": "test"},
                    {"field": "trait", "type": "part-of-speech", "operator": "equals", "value": "noun"}
                ]
            },
            "limit": 100,
            "offset": 0
        }

    Returns:
        {
            "total": 5,
            "entries": [{"id": "entry-1", "lexical_unit": "test1", ...}, ...]
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    try:
        service = get_bulk_query_service()
        condition = data.get('condition', {})
        limit = data.get('limit', 100)
        offset = data.get('offset', 0)

        result = service.query_entries(condition, limit, offset)
        return jsonify(result)

    except Exception as e:
        logger.error("Error in bulk_query: %s", str(e))
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/execute', methods=['POST'])
def bulk_execute() -> Any:
    """
    Execute a bulk action on entries matching conditions.

    Request body:
        {
            "condition": {...},  // optional - uses condition or entry_ids
            "entry_ids": ["entry-1", ...],  // optional - explicit list
            "action": {
                "type": "set",
                "field": "trait",
                "type": "part-of-speech",
                "value": "verb"
            },
            "preview": false
        }

    Returns:
        {
            "operation_id": "op-YYYYMMDD-N",
            "summary": {
                "matched": 10,
                "success": 9,
                "failed": 1
            },
            "preview": false
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    try:
        query_service = get_bulk_query_service()
        action_service = get_bulk_action_service()

        condition = data.get('condition', {})
        entry_ids = data.get('entry_ids', [])
        action = data.get('action', {})
        preview = data.get('preview', False)

        # Get matching entry IDs if condition provided
        if condition and not entry_ids:
            query_result = query_service.query_entries(condition, limit=10000, offset=0)
            entry_ids = [e['id'] for e in query_result.get('entries', [])]

        if not entry_ids:
            return jsonify({'error': 'No entries matched or provided'}), 400

        # Execute action on each entry
        results = []
        for entry_id in entry_ids:
            result = action_service.execute_action(entry_id, action, dry_run=preview)
            results.append(result)

        summary = {
            'matched': len(entry_ids),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'error')
        }

        from datetime import datetime
        operation_id = f'op-{datetime.utcnow().strftime("%Y%m%d")}-{len(entry_ids)}'

        return jsonify({
            'operation_id': operation_id,
            'summary': summary,
            'results': results,
            'preview': preview
        })

    except Exception as e:
        logger.error("Error in bulk_execute: %s", str(e))
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/pipeline', methods=['POST'])
def bulk_pipeline() -> Any:
    """
    Execute a pipeline of chained operations.

    Request body:
        {
            "condition": {...},  // optional
            "entry_ids": ["entry-1", ...],  // optional
            "steps": [
                {"type": "set", "field": "trait", "value": "noun"},
                {"type": "append", "field": "note", "value": "Updated by bulk pipeline"}
            ],
            "preview": false
        }

    Returns:
        {
            "operation_id": "op-YYYYMMDD-N",
            "summary": {...},
            "steps_results": [...],
            "preview": false
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    try:
        query_service = get_bulk_query_service()
        action_service = get_bulk_action_service()

        condition = data.get('condition', {})
        entry_ids = data.get('entry_ids', [])
        steps = data.get('steps', [])
        preview = data.get('preview', False)

        if not steps:
            return jsonify({'error': 'No pipeline steps provided'}), 400

        # Get matching entry IDs if condition provided
        if condition and not entry_ids:
            query_result = query_service.query_entries(condition, limit=10000, offset=0)
            entry_ids = [e['id'] for e in query_result.get('entries', [])]

        if not entry_ids:
            return jsonify({'error': 'No entries matched or provided'}), 400

        # Execute each step in pipeline
        steps_results = []
        for i, step in enumerate(steps):
            step_results = []
            for entry_id in entry_ids:
                result = action_service.execute_action(entry_id, step, dry_run=preview)
                step_results.append(result)

            steps_results.append({
                'step': i + 1,
                'action': step.get('type'),
                'results': step_results
            })

        total_success = sum(
            sum(1 for r in sr['results'] if r['status'] == 'success')
            for sr in steps_results
        )
        total_failed = sum(
            sum(1 for r in sr['results'] if r['status'] == 'error')
            for sr in steps_results
        )

        from datetime import datetime
        operation_id = f'op-{datetime.utcnow().strftime("%Y%m%d")}-{len(entry_ids)}'

        return jsonify({
            'operation_id': operation_id,
            'summary': {
                'entries': len(entry_ids),
                'steps': len(steps),
                'total_success': total_success,
                'total_failed': total_failed
            },
            'steps_results': steps_results,
            'preview': preview
        })

    except Exception as e:
        logger.error("Error in bulk_pipeline: %s", str(e))
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/preview', methods=['POST'])
def bulk_preview() -> Any:
    """
    Preview what would change without applying modifications.

    Request body:
        {
            "condition": {...},
            "entry_ids": ["entry-1", ...],
            "action": {...}
        }

    Returns:
        {
            "would_affect": 5,
            "entries_preview": [
                {
                    "id": "entry-1",
                    "current_value": "noun",
                    "new_value": "verb",
                    "change_description": "Would change trait part-of-speech from 'noun' to 'verb'"
                }
            ]
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    try:
        query_service = get_bulk_query_service()
        action_service = get_bulk_action_service()

        condition = data.get('condition', {})
        entry_ids = data.get('entry_ids', [])
        action = data.get('action', {})

        # Get matching entry IDs if condition provided
        if condition and not entry_ids:
            query_result = query_service.query_entries(condition, limit=1000, offset=0)
            entry_ids = [e['id'] for e in query_result.get('entries', [])]

        if not entry_ids:
            return jsonify({'error': 'No entries matched or provided'}), 400

        # Generate preview for each entry
        entries_preview = []
        for entry_id in entry_ids:
            preview = action_service.preview_action(entry_id, action)
            if preview.get('would_change'):
                entries_preview.append(preview)

        return jsonify({
            'would_affect': len(entries_preview),
            'entries_preview': entries_preview
        })

    except Exception as e:
        logger.error("Error in bulk_preview: %s", str(e))
        return jsonify({'error': str(e)}), 500
