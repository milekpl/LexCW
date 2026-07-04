"""
API endpoints for Relation Discovery — find definition-similar entries with different headwords.
"""

import json
import logging
import os
import threading
import uuid
from flask import Blueprint, jsonify, request, current_app, url_for
from werkzeug.routing import BuildError

from app.services.dictionary_service import DictionaryService
from app.utils.exceptions import JobCancelled

logger = logging.getLogger(__name__)

discovery_bp = Blueprint('discovery_api', __name__, url_prefix='/discovery')

SCAN_JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'instance', 'scan_jobs')


def _job_path(job_id: str) -> str:
    return os.path.join(SCAN_JOBS_DIR, f'{job_id}.json')


def _read_job(job_id: str):
    try:
        with open(_job_path(job_id)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_job(job_id: str, data: dict) -> None:
    os.makedirs(SCAN_JOBS_DIR, exist_ok=True)
    tmp = _job_path(job_id) + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _job_path(job_id))


def _run_discovery_job(app, base_url, job_id, project_id, pos, threshold, min_confidence, sample_size, relation_type):
    def _check_cancelled():
        data = _read_job(job_id)
        if data and data.get('cancelled'):
            raise JobCancelled('Job cancelled by user')

    def _progress(total, processed, phase):
        _check_cancelled()
        data = _read_job(job_id) or {}
        data.update({'total': total, 'processed': processed, 'phase': phase})
        _write_job(job_id, data)

    try:
        _progress(0, 0, 'Starting')
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            result = dict_service.discover_related_entries(
                pos=pos, threshold=threshold,
                min_confidence=min_confidence, project_id=project_id,
                sample_size=sample_size, relation_type=relation_type,
                progress_callback=_progress,
            )
            # Add entry URLs
            for c in result.get('candidates', []):
                for key in ('source', 'target'):
                    e = c.get(key, {})
                    eid = e.get('entry_id')
                    if eid:
                        e['entry_url'] = f'{base_url}/entries/{eid}'

            final = {
                'done': True, 'phase': 'Complete',
                'total': result.get('scanned_entries', 0),
                'processed': result.get('scanned_entries', 0),
                'candidates': result.get('candidates', []),
                'total_candidates': result.get('total_candidates', 0),
                'scanned_entries': result.get('scanned_entries', 0),
                'sample_size': result.get('sample_size'),
            }
            _write_job(job_id, final)
    except JobCancelled:
        _write_job(job_id, {'done': True, 'phase': 'Cancelled', 'error': 'Cancelled'})
    except Exception as e:
        logger.error("Discovery job %s failed: %s", job_id, e, exc_info=True)
        _write_job(job_id, {'done': True, 'phase': 'Error', 'error': str(e)})


@discovery_bp.route('/scan', methods=['POST'])
def start_discovery_scan():
    try:
        data = request.get_json(force=True, silent=True) or {}
        job_id = str(uuid.uuid4())

        project_id = request.args.get('project_id', type=int)
        if not project_id:
            raw_pid = data.get('project_id')
            if raw_pid is not None:
                project_id = int(raw_pid)
        if not project_id:
            from flask import session as s
            project_id = s.get('project_id')

        pos = data.get('pos')
        threshold = int(data.get('threshold', 1))
        min_confidence = float(data.get('min_confidence', 0.3))
        raw_sample = data.get('sample_size')
        sample_size = int(raw_sample) if raw_sample else None
        relation_type = data.get('relation_type', 'synonym')

        _write_job(job_id, {'done': False, 'phase': 'Queued', 'total': 0, 'processed': 0})

        from flask import current_app
        app = current_app._get_current_object()
        base_url = request.host_url.rstrip('/')

        thread = threading.Thread(
            target=_run_discovery_job,
            args=(app, base_url, job_id, project_id, pos, threshold, min_confidence, sample_size, relation_type),
            daemon=True,
        )
        thread.start()

        return jsonify({'success': True, 'job_id': job_id}), 202
    except Exception as e:
        logger.error("Error starting discovery scan: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@discovery_bp.route('/progress/<job_id>', methods=['GET'])
def get_discovery_progress(job_id):
    job = _read_job(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    resp = {
        'success': True,
        'done': job.get('done', False),
        'phase': job.get('phase', ''),
        'total': job.get('total', 0),
        'processed': job.get('processed', 0),
        'error': job.get('error'),
    }
    if job.get('done'):
        resp['data'] = {
            'candidates': job.get('candidates', []),
            'total_candidates': job.get('total_candidates', 0),
            'scanned_entries': job.get('scanned_entries', 0),
            'sample_size': job.get('sample_size'),
        }
        try:
            os.remove(_job_path(job_id))
        except OSError:
            pass
    return jsonify(resp)


@discovery_bp.route('/scan/<job_id>/cancel', methods=['POST'])
def cancel_discovery_scan(job_id):
    """Cancel a running discovery scan job."""
    job = _read_job(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    if job.get('done'):
        return jsonify({'success': True, 'message': 'Job already finished'})

    _write_job(job_id, {**job, 'cancelled': True})
    return jsonify({'success': True, 'message': 'Cancellation requested'})


@discovery_bp.route('/relations', methods=['POST'])
def create_relation():
    try:
        data = request.get_json(force=True, silent=True) or {}
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        relation_type = data.get('relation_type', 'synonym')
        source_sense_id = data.get('source_sense_id')
        target_sense_id = data.get('target_sense_id')
        level = data.get('level')  # 'entry' or 'sense' or None for auto-detect

        if not source_id or not target_id:
            return jsonify({'success': False, 'error': 'source_id and target_id are required'}), 400

        project_id = request.args.get('project_id', type=int)
        if not project_id:
            from flask import session
            project_id = session.get('project_id')

        dict_service = current_app.injector.get(DictionaryService)
        result = dict_service._create_relation(
            source_id, target_id, relation_type,
            source_sense_id=source_sense_id,
            target_sense_id=target_sense_id,
            project_id=project_id,
        )

        level_label = result.get('level', 'entry')
        if level_label == 'sense':
            msg = f'Relation "{relation_type}" created between senses {result["source_sense_id"]} and {result["target_sense_id"]}'
        else:
            msg = f'Entry-level relation "{relation_type}" created between {source_id} and {target_id}'

        return jsonify({
            'success': True,
            'message': msg,
            'level': level_label,
            'source_sense_id': result.get('source_sense_id'),
            'target_sense_id': result.get('target_sense_id'),
        })
    except Exception as e:
        logger.error("Error creating relation: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
