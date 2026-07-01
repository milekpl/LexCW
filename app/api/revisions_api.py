"""
API endpoints for entry revision history and analytics.

Endpoints:
  GET  /api/entries/{entry_id}/revisions          — paginated list
  GET  /api/entries/{entry_id}/revisions/{num}    — single revision detail
  GET  /api/revisions/stats                       — aggregate stats
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from app.services.entry_revision_service import EntryRevisionService

revisions_bp = Blueprint('revisions', __name__, url_prefix='/api/entries')


@revisions_bp.route('/<entry_id>/revisions', methods=['POST'])
def create_revision(entry_id: str):
    """Store a new revision from a snapshot JSON payload."""
    data = request.get_json(silent=True)
    if not data or 'snapshot' not in data:
        return jsonify({'error': 'snapshot is required'}), 400

    user_id = data.get('user_id')
    created_by = data.get('created_by')

    try:
        revision = EntryRevisionService.save_revision(
            entry_id=entry_id,
            snapshot=data['snapshot'],
            user_id=user_id,
            created_by=created_by,
        )
        return jsonify({
            'revision_number': revision.revision_number,
            'change_count': len(revision.change_report) if revision.change_report else 0,
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@revisions_bp.route('/<entry_id>/revisions', methods=['GET'])
def list_revisions(entry_id: str):
    """Paginated list of revisions for one entry."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    revisions, total = EntryRevisionService.get_revisions(
        entry_id, page=page, per_page=per_page
    )
    return jsonify({
        'entry_id': entry_id,
        'revisions': [r.to_dict(include_snapshot=False) for r in revisions],
        'page': page,
        'per_page': per_page,
        'total': total,
    })


@revisions_bp.route('/<entry_id>/revisions/<int:revision_number>', methods=['GET'])
def get_revision(entry_id: str, revision_number: int):
    """Full detail for a single revision (with snapshot + change_report)."""
    r = EntryRevisionService.get_revision(entry_id, revision_number)
    if not r:
        return jsonify({'error': 'Revision not found'}), 404
    return jsonify({
        'revision': r.to_dict(include_snapshot=True),
    })


# ---- Stats (separate blueprint to avoid per-entry prefix) ----

stats_bp = Blueprint('revision_stats', __name__, url_prefix='/api/revisions')


@stats_bp.route('/stats', methods=['GET'])
def revision_stats():
    """Aggregate revision stats over a time range."""
    stats = EntryRevisionService.get_stats(
        from_date=request.args.get('from'),
        to_date=request.args.get('to'),
        user_id=request.args.get('user_id'),
        entry_id=request.args.get('entry_id'),
        granularity=request.args.get('granularity', 'day'),
    )
    return jsonify(stats)
