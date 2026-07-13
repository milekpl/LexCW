"""
API endpoints for bulk operations on dictionary entries.

Provides endpoints for:
- /bulk/traits/convert - Convert traits across multiple entries
- /bulk/pos/update - Update part-of-speech tags across multiple entries
- /bulk/query - Query entries matching conditions
- /bulk/execute - Execute bulk actions on matching entries
- /bulk/pipeline - Execute chained operations
- /bulk/preview - Preview effects without applying
- /bulk/rollback - Rollback a bulk operation
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

def get_rollback_service():
    from app.services.bulk_rollback_service import BulkRollbackService
    from app.services.dictionary_service import DictionaryService
    ds = current_app.injector.get(DictionaryService)
    return BulkRollbackService(dictionary_service=ds)


def _snapshot_for_bulk_op(entry_ids: list[str]) -> str | None:
    """Snapshot entries before a bulk operation.

    Returns a bulk_op_id string, or None if no entries to snapshot
    or if the injector is not available (e.g. in tests).
    """
    if not entry_ids:
        return None
    from flask import current_app
    try:
        injector = getattr(current_app, 'injector', None)
        if injector is None:
            return None
        from app.services.dictionary_service import DictionaryService
        from app.services.bulk_rollback_service import BulkRollbackService
        ds = injector.get(DictionaryService)
        rs = BulkRollbackService(dictionary_service=ds)
        op_id = rs.generate_op_id()
        rs.record_bulk_op_snapshots(op_id, entry_ids)
        return op_id
    except Exception as exc:
        logger.warning('bulk snapshot skipped: %s', exc)
        return None

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
        # Snapshot entries before the operation
        bulk_op_id = _snapshot_for_bulk_op(entry_ids)

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
        operation_id = bulk_op_id or f'op-{datetime.utcnow().strftime("%Y%m%d")}-{result["total"]}'

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
        # Snapshot entries before the operation
        bulk_op_id = _snapshot_for_bulk_op(entry_ids)

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
        operation_id = bulk_op_id or f'op-{datetime.utcnow().strftime("%Y%m%d")}-{result["total"]}'

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

        # Snapshot entries before execution (skip in preview mode)
        bulk_op_id = None if preview else _snapshot_for_bulk_op(entry_ids)

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
        operation_id = bulk_op_id or f'op-{datetime.utcnow().strftime("%Y%m%d")}-{len(entry_ids)}'

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

        # Snapshot entries before pipeline (skip in preview mode)
        bulk_op_id = None if preview else _snapshot_for_bulk_op(entry_ids)

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
        operation_id = bulk_op_id or f'op-{datetime.utcnow().strftime("%Y%m%d")}-{len(entry_ids)}'

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


@bulk_bp.route('/batch-update', methods=['POST'])
def batch_update_entries() -> Any:
    """
    Execute atomic batch updates for spreadsheet/grid cell edits.

    Request body:
        {
            "updates": [
                {
                    "id": "entry-123",
                    "changes": {
                        "lexical_unit": "new headword",
                        "pos": "noun",
                        "citation_form": "cf",
                        "pronunciation": "ipa",
                        "definition": "definition string",
                        "definition_pl": "polski opis"
                    }
                }
            ]
        }

    Returns:
        {
            "operation_id": "op-YYYYMMDD-batch",
            "summary": { "requested": 5, "success": 5, "failed": 0 },
            "results": [ {"id": "entry-123", "status": "success"}, ... ]
        }
    """
    data = request.get_json()
    if not data or 'updates' not in data:
        return jsonify({'error': 'Missing required updates payload'}), 400

    updates = data.get('updates', [])
    if not isinstance(updates, list) or len(updates) == 0:
        return jsonify({'error': 'Updates list cannot be empty'}), 400

    try:
        # Snapshot all entries before batch updates
        entry_ids = [u.get('id') or u.get('entry_id') for u in updates if u.get('id') or u.get('entry_id')]
        bulk_op_id = _snapshot_for_bulk_op(entry_ids)

        from app.services.dictionary_service import DictionaryService
        dict_service = current_app.injector.get(DictionaryService)

        results = []
        success_count = 0
        failed_count = 0

        for item in updates:
            entry_id = item.get('id') or item.get('entry_id')
            changes = item.get('changes', {})
            if not entry_id or not changes:
                results.append({'id': entry_id, 'status': 'error', 'error': 'Invalid entry_id or empty changes'})
                failed_count += 1
                continue

            try:
                entry = dict_service.get_entry(entry_id)
                if not entry:
                    results.append({'id': entry_id, 'status': 'error', 'error': 'Entry not found'})
                    failed_count += 1
                    continue

                # Apply changes
                if 'lexical_unit' in changes:
                    val = changes['lexical_unit']
                    if isinstance(val, dict):
                        entry.lexical_unit = val
                    elif isinstance(entry.lexical_unit, dict):
                        lang = next(iter(entry.lexical_unit.keys()), 'en')
                        entry.lexical_unit[lang] = str(val)
                    else:
                        entry.lexical_unit = {'en': str(val)}

                if 'citation_form' in changes:
                    entry.citation_form = str(changes['citation_form'])

                if 'pos' in changes or 'part_of_speech' in changes:
                    new_pos = str(changes.get('pos') or changes.get('part_of_speech'))
                    if hasattr(entry, 'grammatical_info') and entry.grammatical_info:
                        if isinstance(entry.grammatical_info, dict):
                            entry.grammatical_info['part_of_speech'] = new_pos
                        else:
                            setattr(entry.grammatical_info, 'part_of_speech', new_pos)
                    else:
                        entry.grammatical_info = {'part_of_speech': new_pos}

                if 'pronunciation' in changes:
                    new_pron = str(changes['pronunciation'])
                    if hasattr(entry, 'pronunciations') and isinstance(entry.pronunciations, dict):
                        lang = next(iter(entry.pronunciations.keys()), 'seh-fonipa')
                        entry.pronunciations[lang] = new_pron
                    else:
                        entry.pronunciations = {'seh-fonipa': new_pron}

                if 'definition' in changes or 'definition_en' in changes or 'definition_pl' in changes:
                    def_str = changes.get('definition') or changes.get('definition_en')
                    def_pl = changes.get('definition_pl')

                    if entry.senses and len(entry.senses) > 0:
                        first_sense = entry.senses[0]
                        if not hasattr(first_sense, 'definitions') or not isinstance(first_sense.definitions, dict):
                            first_sense.definitions = {}
                        if def_str is not None:
                            first_sense.definitions['en'] = str(def_str)
                        if def_pl is not None:
                            first_sense.definitions['pl'] = str(def_pl)
                    else:
                        from app.models.dictionary_models import Sense
                        defs = {}
                        if def_str is not None:
                            defs['en'] = str(def_str)
                        if def_pl is not None:
                            defs['pl'] = str(def_pl)
                        entry.senses = [Sense(id=f"{entry_id}-s1", definitions=defs)]

                if 'gloss' in changes or 'gloss_en' in changes or 'gloss_pl' in changes:
                    gloss_en = changes.get('gloss') or changes.get('gloss_en')
                    gloss_pl = changes.get('gloss_pl')
                    if entry.senses and len(entry.senses) > 0:
                        first_sense = entry.senses[0]
                        if not hasattr(first_sense, 'glosses') or not isinstance(first_sense.glosses, dict):
                            first_sense.glosses = {}
                        if gloss_en is not None:
                            first_sense.glosses['en'] = str(gloss_en)
                        if gloss_pl is not None:
                            first_sense.glosses['pl'] = str(gloss_pl)

                if 'notes' in changes or 'note' in changes:
                    note_val = str(changes.get('notes') if 'notes' in changes else changes.get('note'))
                    if hasattr(entry, 'notes'):
                        entry.notes = [note_val] if note_val else []

                if 'etymology' in changes:
                    etym_val = str(changes['etymology'])
                    if hasattr(entry, 'etymologies'):
                        entry.etymologies = [etym_val] if etym_val else []

                if 'homograph_number' in changes or 'order' in changes:
                    hn_val = changes.get('homograph_number') if 'homograph_number' in changes else changes.get('order')
                    try:
                        parsed_val = int(hn_val) if (hn_val is not None and str(hn_val).strip() != '') else None
                    except (ValueError, TypeError):
                        parsed_val = None
                    if hasattr(entry, 'homograph_number'):
                        entry.homograph_number = parsed_val
                    if hasattr(entry, 'order'):
                        entry.order = parsed_val

                dict_service.update_entry(entry)
                results.append({'id': entry_id, 'status': 'success'})
                success_count += 1

            except Exception as e:
                logger.error("Failed to update entry %s: %s", entry_id, str(e))
                results.append({'id': entry_id, 'status': 'error', 'error': str(e)})
                failed_count += 1

        from datetime import datetime
        operation_id = bulk_op_id or f'op-{datetime.utcnow().strftime("%Y%m%d")}-batch-{len(updates)}'

        return jsonify({
            'operation_id': operation_id,
            'summary': {
                'requested': len(updates),
                'success': success_count,
                'failed': failed_count
            },
            'results': results
        }), 200

    except Exception as e:
        logger.error("Error in batch_update_entries: %s", str(e))
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/rollback', methods=['POST'])
def bulk_rollback() -> Any:
    """
    Roll back a bulk operation by restoring pre-op snapshots.

    Request body:
        {
            "operation_id": "op-20260101-10"
        }

    Returns:
        {
            "restored": 3,
            "failed": 0,
            "skipped": 0,
            "total": 3,
            "message": "Rolled back operation op-20260101-10"
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    operation_id = data.get('operation_id')
    if not operation_id:
        return jsonify({'error': 'Missing required field: operation_id'}), 400

    try:
        rollback_service = get_rollback_service()
        result = rollback_service.rollback(operation_id)

        message = f"Rolled back operation {operation_id}"
        if result['skipped'] > 0:
            message += f" ({result['skipped']} entries skipped — no longer exist)"
        if result['failed'] > 0:
            message += f" ({result['failed']} entries failed)"

        return jsonify({
            **result,
            'message': message,
        })

    except Exception as e:
        logger.error("Error in bulk_rollback: %s", str(e))
        return jsonify({'error': str(e)}), 500

