"""
API endpoints for dashboard statistics and system information.
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, url_for
from werkzeug.routing import BuildError
from flasgger import swag_from

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app.models.dismissed_duplicate import DismissedDuplicate
from app.models.workset_models import db
from app.utils.exceptions import JobCancelled

# Create blueprint
dashboard_bp = Blueprint('dashboard_api', __name__, url_prefix='/dashboard')
logger = logging.getLogger(__name__)

# File-based scan job storage (survives reloads, works across workers)
SCAN_JOBS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'instance', 'scan_jobs')
)


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


# Unified cache key for dashboard stats
DASHBOARD_CACHE_KEY = 'dashboard_stats_v2'
OLD_CACHE_KEYS = ['dashboard_stats', 'dashboard_stats_api']


@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """
    Get dashboard statistics with caching for performance
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Dashboard statistics
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Whether the request was successful
            data:
              type: object
              properties:
                entry_count:
                  type: integer
                  description: Total number of entries
                sense_count:
                  type: integer
                  description: Total number of senses
                example_count:
                  type: integer
                  description: Total number of examples
                system_status:
                  type: object
                  properties:
                    baseX_connected:
                      type: boolean
                      description: BaseX database connection status
                    cache_available:
                      type: boolean
                      description: Redis cache availability
                    uptime:
                      type: string
                      description: System uptime
                recent_activity:
                  type: array
                  description: Recent activity log
                timestamp:
                  type: string
                  description: Data timestamp
            cached:
              type: boolean
              description: Whether the data was retrieved from cache
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Request success status (false)
            error:
              type: string
              description: Error message
    """
    try:
        # Try to get cached data first (new key, then old keys for migration)
        cache = CacheService()
        cache_key = DASHBOARD_CACHE_KEY
        if cache.is_available():
            cached_data = cache.get(cache_key)
            # Try old keys for cache migration
            if not cached_data:
                for old_key in OLD_CACHE_KEYS:
                    cached_data = cache.get(old_key)
                    if cached_data:
                        # Migrate to new key
                        cache.set(cache_key, cached_data, ttl=300)
                        logger.info("Migrated dashboard cache from '%s' to '%s'", old_key, cache_key)
                        break
            if cached_data:
                logger.info("Returning cached dashboard stats from API")
                return jsonify({
                    'success': True,
                    'data': cached_data,
                    'cached': True
                })
        
        # Get fresh data from database
        dict_service = current_app.injector.get(DictionaryService)
        
        # Get entry count
        entry_count = dict_service.count_entries()
        
        # Get sense and example counts
        sense_count, example_count = dict_service.count_senses_and_examples()
        
        # Get recent activity
        recent_activity = dict_service.get_recent_activity(limit=5)
        
        # Get system status
        system_status = dict_service.get_system_status()
        
        # Prepare response data
        stats_data = {
            'stats': {
                'entries': entry_count,
                'senses': sense_count,
                'examples': example_count
            },
            'system_status': system_status,
            'recent_activity': recent_activity,
            'last_updated': datetime.now().isoformat()
        }
        
        # Cache the data for 5 minutes (300 seconds) - shorter than view cache
        if cache.is_available():
            cache.set(cache_key, stats_data, ttl=300)
            logger.info("Cached dashboard stats via API for 5 minutes")
        
        return jsonify({
            'success': True,
            'data': stats_data,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats via API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/quality', methods=['GET'])
def get_quality_metrics():
    """
    Get data quality/completeness metrics for the dictionary.
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Quality metrics
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
              properties:
                totals:
                  type: object
                entries_without_senses:
                  type: object
                senses_without_content:
                  type: object
                entries_without_pronunciations:
                  type: object
                senses_without_examples:
                  type: object
      500:
        description: Internal server error
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        metrics = dict_service.get_quality_metrics()
        return jsonify({
            'success': True,
            'data': metrics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/composition', methods=['GET'])
def get_composition_stats():
    """
    Get data-composition statistics: POS distribution, field coverage,
    senses-per-entry histogram, examples-per-sense.
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Composition statistics
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
              properties:
                total_entries:
                  type: integer
                pos_distribution:
                  type: object
                field_coverage:
                  type: object
                senses_per_entry:
                  type: array
                examples_per_sense:
                  type: array
      500:
        description: Internal server error
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        stats = dict_service.get_composition_stats()
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting composition stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    """
    Detect data anomalies in the dictionary.

    Checks performed:
    - Non-canonical POS abbreviations (e.g. 'n', 'v', 'adj' instead of 'Noun', 'Verb', 'Adjective')
    - Duplicate headwords (same text, different entry IDs)
    - Entries with an empty or missing headword
    - Senses with neither a definition nor a gloss
    - ML POS-Definition Coherence Mismatches
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Anomaly report
      500:
        description: Internal server error
    """
    try:
        cache = CacheService()
        cache_key = "dashboard:anomalies:v1"
        if cache.is_available():
            cached = cache.get(cache_key)
            if cached and isinstance(cached, dict):
                return jsonify(cached)

        from app.services.import_converter import SHOEBOX_POS_MAP
        dict_service = current_app.injector.get(DictionaryService)
        project_id = request.args.get('project_id', type=int)
        if not project_id:
            from flask import session as _s
            project_id = _s.get('project_id')

        has_ns = dict_service._detect_namespace_usage()
        prologue = dict_service._query_builder.get_namespace_prologue(has_ns)
        entry_path = dict_service._query_builder.get_element_path('entry', has_ns)
        lu_path = dict_service._query_builder.get_element_path('lexical-unit', has_ns)
        form_path = dict_service._query_builder.get_element_path('form', has_ns)
        text_path = dict_service._query_builder.get_element_path('text', has_ns)
        sense_path = dict_service._query_builder.get_element_path('sense', has_ns)
        gi_path = dict_service._query_builder.get_element_path('grammatical-info', has_ns)
        def_path = dict_service._query_builder.get_element_path('definition', has_ns)
        gloss_path = dict_service._query_builder.get_element_path('gloss', has_ns)

        db_name = dict_service.db_connector.database
        C = f"collection('{db_name}')"

        canonical_pos = set(SHOEBOX_POS_MAP.values())

        anomalies = {
            'non_canonical_pos': [],
            'duplicate_headwords': [],
            'missing_headwords': [],
            'empty_senses': [],
            'pos_coherence_mismatches': [],
        }

        # Unified single-pass XQuery to fetch entry, headword, POS, sense ID, and definition text
        unified_q = (
            f"{prologue} "
            f"for $e in {C}//{entry_path} "
            f"let $eid := string($e/@id) "
            f"let $hw := normalize-space(($e/{lu_path}/{form_path}/{text_path}/string(), '')[1]) "
            f"for $s in $e//{sense_path} "
            f"let $sid := string(($s/@id, '')[1]) "
            f"let $gi := string(($s/{gi_path}/@value/string(), $e/{gi_path}/@value/string())[1]) "
            f"let $dtext := string-join(($s/{def_path}//{text_path}/string(), $s/{gloss_path}//{text_path}/string()), ' ') "
            f"return concat($eid, '|||', $hw, '|||', $gi, '|||', $sid, '|||', normalize-space($dtext))"
        )
        raw = dict_service.db_connector.execute_query(unified_q)

        seen_noncanon: set = set()
        hw_map: dict[str, set[str]] = {}
        missing_hw_entries: set[str] = set()
        ml_data: list[tuple[str, str, str, str]] = []

        for line in (raw or "").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|||")
            if len(parts) < 5:
                continue
            eid, hw, gi, sid, dtext = parts[0], parts[1], parts[2], parts[3], parts[4]

            # 1. Non-canonical POS
            if gi and gi not in canonical_pos:
                key = (eid, gi)
                if key not in seen_noncanon:
                    seen_noncanon.add(key)
                    suggested = SHOEBOX_POS_MAP.get(gi.lower())
                    anomalies['non_canonical_pos'].append({
                        'entry_id': eid,
                        'pos_value': gi,
                        'suggested': suggested,
                    })

            # 2. Missing headwords
            if not hw:
                missing_hw_entries.add(eid)
            else:
                hw_map.setdefault(hw, set()).add(eid)

            # 4. Empty senses
            if not dtext:
                anomalies['empty_senses'].append({'entry_id': eid, 'sense_id': sid})

            # Data for ML POS Coherence model
            if gi and dtext:
                norm_p = SHOEBOX_POS_MAP.get(gi.lower(), gi)
                ml_data.append((eid, hw, norm_p, dtext))

        # 2. Missing headwords list
        for eid in missing_hw_entries:
            anomalies['missing_headwords'].append({'entry_id': eid})

        # 3. Duplicate headwords list
        for hw, ids in hw_map.items():
            if len(ids) > 1:
                anomalies['duplicate_headwords'].append({
                    'headword': hw,
                    'entry_ids': list(ids),
                    'count': len(ids),
                })

        # 5. ML POS-Definition Coherence Mismatches
        try:
            from app.services.pos_coherence_service import get_pos_coherence_service
            coherence_svc = get_pos_coherence_service()
            anomalies['pos_coherence_mismatches'] = coherence_svc.detect_anomalies_from_data(
                ml_data, min_confidence=0.80, limit=50
            )
        except Exception as e:
            logger.warning("Anomaly check (POS coherence) failed: %s", e)

        summary = {
            'non_canonical_pos_count': len(anomalies['non_canonical_pos']),
            'duplicate_headword_groups': len(anomalies['duplicate_headwords']),
            'missing_headword_count': len(anomalies['missing_headwords']),
            'empty_sense_count': len(anomalies['empty_senses']),
            'pos_coherence_mismatch_count': len(anomalies['pos_coherence_mismatches']),
        }

        payload = {
            'success': True,
            'summary': summary,
            'anomalies': anomalies,
            'timestamp': datetime.now().isoformat(),
        }
        if cache.is_available():
            cache.set(cache_key, payload, ttl=300)

        return jsonify(payload)

    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/clear-cache', methods=['POST'])
@swag_from({
    'tags': ['Dashboard'],
    'summary': 'Clear dashboard cache',
    'description': 'Clear the dashboard statistics cache to force fresh data retrieval on next request.',
    'responses': {
        200: {
            'description': 'Cache cleared successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Dashboard cache cleared successfully'}
                }
            }
        },
        500: {
            'description': 'Error clearing cache',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': 'Cache service error'}
                }
            }
        }
    }
})
def clear_dashboard_cache():
    """
    Clear the dashboard statistics cache.
    """
    try:
        cache = CacheService()
        if cache.is_available():
            # Delete new key and all old keys for complete cache invalidation
            cache.delete(DASHBOARD_CACHE_KEY)
            for old_key in OLD_CACHE_KEYS:
                cache.delete(old_key)
            logger.info("Dashboard stats cache cleared")
            return jsonify({
                'success': True,
                'message': 'Dashboard cache cleared successfully'
            })
        else:
            # Cache service not available, but this is not an error in test environments
            logger.info("Cache service not available, skipping dashboard cache clear")
            return jsonify({
                'success': True,
                'message': 'Cache service not available, no cache to clear'
            })
            
    except Exception as e:
        logger.error(f"Error clearing dashboard cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/duplicates/count', methods=['GET'])
def get_duplicate_entry_count():
    """Quick count of non-variant entries for progress estimation."""
    try:
        dict_service = current_app.injector.get(DictionaryService)
        project_id = request.args.get('project_id', type=int)
        if not project_id:
            try:
                from flask import session as s
                project_id = s.get('project_id')
            except Exception:
                pass
        count = dict_service.count_entries(project_id=project_id)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _run_scan_job(app, base_url, job_id, project_id, mode, pos, threshold, min_confidence, sample_size):
    """Background job: run duplicate detection, persist progress to file."""
    def _check_cancelled():
        data = _read_job(job_id)
        if data and data.get('cancelled'):
            raise JobCancelled('Job cancelled by user')

    def _progress(total, processed, phase, groups=None):
        _check_cancelled()
        data = _read_job(job_id) or {}
        data.update({'total': total, 'processed': processed, 'phase': phase})
        if groups is not None:
            data['groups'] = groups
        _write_job(job_id, data)

    try:
        _progress(0, 0, 'Starting')
        with app.app_context():
            dict_service = app.injector.get(DictionaryService)
            result = dict_service.get_duplicate_candidates(
                mode=mode, pos=pos, threshold=threshold,
                min_confidence=min_confidence, project_id=project_id,
                sample_size=sample_size, progress_callback=_progress,
            )
            # Add entry URLs
            for group in result.get('groups', []):
                for entry in group.get('entries', []):
                    entry_id = entry.get('entry_id')
                    if entry_id:
                        entry['entry_url'] = f'{base_url}/entries/{entry_id}'
            # Filter dismissed
            if project_id:
                dismissed = DismissedDuplicate.query.filter_by(project_id=project_id).all()
                dismissed_ids = {d.group_id for d in dismissed}
                result['groups'] = [g for g in result['groups'] if g['id'] not in dismissed_ids]
                result['total_candidates'] = len(result['groups'])

            final = {
                'done': True, 'phase': 'Complete',
                'total': result.get('scanned_entries', 0),
                'processed': result.get('scanned_entries', 0),
                'groups': result.get('groups', []),
                'total_candidates': result.get('total_candidates', 0),
                'scanned_entries': result.get('scanned_entries', 0),
                'sample_size': result.get('sample_size'),
            }
            _write_job(job_id, final)
    except JobCancelled:
        _write_job(job_id, {'done': True, 'phase': 'Cancelled', 'error': 'Cancelled'})
    except Exception as e:
        logger.error("Scan job %s failed: %s", job_id, e, exc_info=True)
        _write_job(job_id, {'done': True, 'phase': 'Error', 'error': str(e)})


@dashboard_bp.route('/duplicates/scan', methods=['POST'])
def start_duplicate_scan():
    """Start a background duplicate-detection scan. Returns job_id for polling."""
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

        mode = data.get('mode', 'all')
        pos = data.get('pos')
        threshold = int(data.get('threshold', 1))
        min_confidence = float(data.get('min_confidence', 0.5))
        raw_sample = data.get('sample_size')
        sample_size = int(raw_sample) if raw_sample else None

        # Write initial state so polling can find it immediately
        _write_job(job_id, {'done': False, 'phase': 'Queued', 'total': 0, 'processed': 0})

        from flask import current_app
        app = current_app._get_current_object()
        base_url = request.host_url.rstrip('/')

        thread = threading.Thread(
            target=_run_scan_job,
            args=(app, base_url, job_id, project_id, mode, pos, threshold, min_confidence, sample_size),
            daemon=True,
        )
        thread.start()

        return jsonify({'success': True, 'job_id': job_id}), 202
    except Exception as e:
        logger.error("Error starting scan: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/duplicates/progress/<job_id>', methods=['GET'])
def get_duplicate_scan_progress(job_id):
    """Poll the progress of a background scan job."""
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
            'groups': job.get('groups', []),
            'total_candidates': job.get('total_candidates', 0),
            'scanned_entries': job.get('scanned_entries', 0),
            'sample_size': job.get('sample_size'),
        }
        # Clean up the file — results are delivered
        try:
            os.remove(_job_path(job_id))
        except OSError:
            pass
    return jsonify(resp)


@dashboard_bp.route('/duplicates/scan/<job_id>/cancel', methods=['POST'])
def cancel_duplicate_scan(job_id):
    """Cancel a running scan job."""
    job = _read_job(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    if job.get('done'):
        return jsonify({'success': True, 'message': 'Job already finished'})

    _write_job(job_id, {**job, 'cancelled': True})
    return jsonify({'success': True, 'message': 'Cancellation requested'})


@dashboard_bp.route('/duplicates', methods=['GET'])
def get_duplicates():
    """
    Run duplicate detection and return candidate groups.
    ---
    tags:
      - Dashboard
    parameters:
      - name: mode
        in: query
        type: string
        enum: [all, exact, near, relaxed]
        default: all
      - name: pos
        in: query
        type: string
        required: false
      - name: threshold
        in: query
        type: integer
        default: 1
      - name: min_confidence
        in: query
        type: number
        default: 0.5
    responses:
      200:
        description: Duplicate candidate groups
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        mode = request.args.get('mode', 'all')
        pos = request.args.get('pos', None)
        threshold = request.args.get('threshold', 1, type=int)
        min_confidence = request.args.get('min_confidence', 0.5, type=float)
        sample_size = request.args.get('sample_size', type=int)

        # Get project ID from session, with query-param fallback for API/E2E testing
        project_id = request.args.get('project_id', type=int)
        if not project_id:
            try:
                from flask import session
                project_id = session.get('project_id')
            except (ImportError, RuntimeError):
                pass

        result = dict_service.get_duplicate_candidates(
            mode=mode,
            pos=pos,
            threshold=threshold,
            min_confidence=min_confidence,
            project_id=project_id,
            sample_size=sample_size,
        )

        # Add view URLs for entry cards so the UI can link to the real entry page.
        for group in result.get('groups', []):
            for entry in group.get('entries', []):
                entry_id = entry.get('entry_id')
                if entry_id:
                    try:
                        entry['entry_url'] = url_for('main.view_entry', entry_id=entry_id)
                    except BuildError:
                        entry['entry_url'] = None

        # Filter out dismissed groups
        if project_id:
            dismissed = DismissedDuplicate.query.filter_by(project_id=project_id).all()
            dismissed_ids = {d.group_id for d in dismissed}
            result['groups'] = [g for g in result['groups'] if g['id'] not in dismissed_ids]
            result['total_candidates'] = len(result['groups'])

        return jsonify({
            'success': True,
            'data': result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error detecting duplicates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/duplicates/<group_id>/dismiss', methods=['POST'])
def dismiss_duplicate_group(group_id):
    """
    Dismiss a duplicate group (hide from future results).
    ---
    tags:
      - Dashboard
    parameters:
      - name: group_id
        in: path
        type: string
        required: true
      - name: project_id
        in: query
        type: integer
        required: false
    responses:
      200:
        description: Group dismissed
    """
    try:
        from flask import session
        project_id = session.get('project_id') or request.args.get('project_id', type=int) or (request.get_json(force=True, silent=True) or {}).get('project_id')
        if not project_id:
            return jsonify({'success': False, 'error': 'No project selected'}), 400

        existing = DismissedDuplicate.query.filter_by(
            project_id=project_id, group_id=group_id
        ).first()
        if not existing:
            dismissed = DismissedDuplicate(project_id=project_id, group_id=group_id)
            db.session.add(dismissed)
            db.session.commit()

        return jsonify({'success': True, 'message': f'Group {group_id} dismissed'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error dismissing duplicate group: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/duplicates/<group_id>/merge', methods=['POST'])
def merge_duplicate_group(group_id):
    """
    Merge entries in a duplicate group. Delegates to the existing merge service.
    ---
    tags:
      - Dashboard
    parameters:
      - name: group_id
        in: path
        type: string
        required: true
      - name: target_entry_id
        in: body
        type: string
        required: true
        description: Entry to keep (target)
      - name: source_entry_id
        in: body
        type: string
        required: true
        description: Entry to merge from (source, will be deleted)
    responses:
      200:
        description: Entries merged
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        from app.services.merge_split_service import MergeSplitService
        from flask import session

        data = request.get_json(force=True, silent=True) or {}
        target_entry_id = data.get('target_entry_id')
        source_entry_id = data.get('source_entry_id')

        if not target_entry_id or not source_entry_id:
            return jsonify({
                'success': False,
                'error': 'Both target_entry_id and source_entry_id are required'
            }), 400

        project_id = session.get('project_id')
        merge_service = MergeSplitService(dict_service)
        result = merge_service.merge_entries(
            target_entry_id=target_entry_id,
            source_entry_id=source_entry_id,
            sense_ids=None,  # merge all senses
            user_id=None,
            conflict_resolution={"duplicate_senses": "rename"},
        )

        return jsonify({
            'success': True,
            'data': {
                'operation_id': result.operation_id if hasattr(result, 'operation_id') else None,
                'message': f'Merged {source_entry_id} into {target_entry_id}',
            }
        })
    except Exception as e:
        logger.error(f"Error merging duplicate group: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/redundant-examples', methods=['GET'])
def get_redundant_examples():
    """
    Get redundant example sentences that duplicate separate subentries.
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        # Get project ID from session, with query-param fallback
        project_id = request.args.get('project_id', type=int)
        if not project_id:
            try:
                from flask import session
                project_id = session.get('project_id')
            except (ImportError, RuntimeError):
                pass

        result = dict_service.get_redundant_examples(project_id=project_id)

        # Add view URLs for linking in UI
        for item in result:
            p_id = item.get('phrase_entry_id')
            ex_e_id = item.get('example_entry_id')
            if p_id:
                try:
                    item['phrase_url'] = url_for('main.view_entry', entry_id=p_id)
                except BuildError:
                    item['phrase_url'] = None
            if ex_e_id:
                try:
                    item['example_entry_url'] = url_for('main.view_entry', entry_id=ex_e_id)
                except BuildError:
                    item['example_entry_url'] = None

        # Filter out dismissed ones using DismissedDuplicate
        if project_id:
            from app.models.models import DismissedDuplicate
            dismissed = DismissedDuplicate.query.filter_by(project_id=project_id).all()
            dismissed_ids = {d.group_id for d in dismissed}
            result = [
                item for item in result
                if f"example-{item['phrase_entry_id']}-{item['example_entry_id']}" not in dismissed_ids
            ]

        return jsonify({
            'success': True,
            'data': result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error detecting redundant examples: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

