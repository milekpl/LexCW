"""
API endpoints for word sketch functionality.

Provides:
- Word sketch browser endpoints
- Coverage checking for entries and worksets
- Enrichment suggestions
- Cache management
"""
from __future__ import annotations

import logging
from flask import Blueprint, request, jsonify, current_app
from flasgger import swag_from
from typing import Dict

from app.services.word_sketch import WordSketchClient, WordSketchResult
from app.services.word_sketch.coverage_service import CoverageService

logger = logging.getLogger(__name__)

word_sketch_bp = Blueprint('word_sketch', __name__, url_prefix='/api/word-sketch')

# Rate limiter instance - configured in app factory via init_limiter()
# If Flask-Limiter is not installed/configured, these will be no-op decorators
limiter = None


def init_limiter(limiter_instance):
    """Initialize the rate limiter instance.

    Must be called in app factory after Flask app is created:
        from app.api.word_sketch_api import init_limiter
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        limiter = Limiter(app, key_func=get_remote_address)
        init_limiter(limiter)
    """
    global limiter
    limiter = limiter_instance


def _check_limiter():
    """Check if rate limiter is configured, return decorator or passthrough."""
    if limiter is None:
        # Return a no-op decorator if limiter not configured
        def noop_decorator(f):
            return f
        return noop_decorator
    return limiter.limit


def get_ws_client() -> WordSketchClient:
    """Get or create word sketch client from app context."""
    if hasattr(current_app, 'word_sketch_client'):
        return current_app.word_sketch_client
    return WordSketchClient()


def get_enrichment_service():
    """Get or create enrichment service from app context.

    Services are request-scoped - a new instance is created per request if not
    cached in app context. For production, initialize in app context:

        from app.api.word_sketch_api import get_enrichment_service
        current_app.enrichment_service = EnrichmentService()

    Returns:
        EnrichmentService: Service instance for this request
    """
    if hasattr(current_app, 'enrichment_service') and current_app.enrichment_service:
        return current_app.enrichment_service
    from app.services.word_sketch.enrichment_service import EnrichmentService
    return EnrichmentService()


def get_coverage_service() -> CoverageService:
    """Get or create coverage service from app context.

    Services are request-scoped - a new instance is created per request if not
    cached in app context. For production, initialize in app context:

        from app.api.word_sketch_api import get_coverage_service
        current_app.coverage_service = CoverageService()

    Returns:
        CoverageService: Service instance for this request
    """
    if hasattr(current_app, 'coverage_service') and current_app.coverage_service:
        return current_app.coverage_service
    return CoverageService()


def json_success(data: Dict, status: int = 200) -> tuple:
    """Create success JSON response."""
    return jsonify({"status": "ok", **data}), status


def json_error(message: str, status: int = 400) -> tuple:
    """Create error JSON response."""
    return jsonify({"status": "error", "message": message}), status


# ============================================================================
# Enrichment Endpoints
# ============================================================================

@word_sketch_bp.route('/enrich/<lemma>', methods=['GET'])
@swag_from({
    'tags': ['Word Sketch'],
    'summary': 'Get enrichment proposals for a lemma',
    'parameters': [
        {'name': 'lemma', 'in': 'path', 'type': 'string', 'required': True},
        {'name': 'pos', 'in': 'query', 'type': 'string', 'required': False},
        {'name': 'include_examples', 'in': 'query', 'type': 'boolean', 'required': False},
        {'name': 'max', 'in': 'query', 'type': 'integer', 'required': False, 'maximum': 100}
    ],
    'responses': {
        200: {'description': 'List of enrichment proposals'},
        400: {'description': 'Invalid request'},
        429: {'description': 'Rate limit exceeded'},
        503: {'description': 'Service unavailable'}
    }
})
@(_check_limiter()("100/hour") if limiter else lambda f: f)
def get_enrichments(lemma: str):
    """
    Get enrichment proposals for a lemma.

    Returns collocations, examples, and suggestions for enriching entries.
    """
    if not lemma or not lemma.strip():
        return json_error("Lemma is required")

    lemma = lemma.strip().lower()
    pos = request.args.get('pos')
    include_examples = request.args.get('include_examples', 'true').lower() == 'true'

    # Bounds checking for max_proposals (max 100)
    raw_max = int(request.args.get('max', 20))
    max_proposals = min(max(1, raw_max), 100)

    service = get_enrichment_service()

    try:
        proposals = service.get_enrichment_proposals(
            lemma=lemma,
            pos=pos,
            include_examples=include_examples,
            max_proposals=max_proposals
        )

        return jsonify({
            "lemma": lemma,
            "pos": pos or "",
            "proposals": service.proposals_to_dict(proposals),
            "total": len(proposals),
            "available": True
        })
    except Exception as e:
        logger.error(f"Enrichment request failed for {lemma}: {e}")
        return json_error("Enrichment analysis failed", 503)


@word_sketch_bp.route('/enrich/<lemma>/collocations', methods=['GET'])
def get_collocations(lemma: str):
    """Get collocation proposals for a lemma."""
    if not lemma:
        return json_error("Lemma is required")

    pos = request.args.get('pos')
    min_logdice = float(request.args.get('min_logdice', 6.0))

    service = get_enrichment_service()

    try:
        collocations = service.get_collocations_for_entry(lemma, pos, min_logdice)

        return jsonify({
            "lemma": lemma,
            "pos": pos or "",
            "collocations": service.proposals_to_dict(collocations),
            "total": len(collocations)
        })
    except Exception as e:
        logger.error(f"Collocations request failed for {lemma}: {e}")
        return json_error("Failed to get collocations", 503)


@word_sketch_bp.route('/enrich/<lemma>/subentries', methods=['GET'])
def get_subentry_drafts(lemma: str):
    """
    Get suggested subentry drafts for a lemma.

    Identifies high-value collocates that could become subentries.
    """
    if not lemma:
        return json_error("Lemma is required")

    pos = request.args.get('pos')
    min_logdice = float(request.args.get('min_logdice', 7.0))
    # Bounds checking for max_drafts (max 100)
    raw_max_drafts = int(request.args.get('max', 10))
    max_drafts = min(max(1, raw_max_drafts), 100)

    service = get_enrichment_service()

    try:
        drafts = service.get_suggested_subentries(lemma, pos, min_logdice, max_drafts)

        return jsonify({
            "lemma": lemma,
            "pos": pos or "",
            "drafts": service.drafts_to_dict(drafts),
            "total": len(drafts),
            "note": "Drafts are suggestions - review and edit before saving"
        })
    except Exception as e:
        logger.error(f"Subentry drafts failed for {lemma}: {e}")
        return json_error("Failed to generate subentry drafts", 503)


@word_sketch_bp.route('/enrich/<lemma>/examples', methods=['GET'])
def get_examples_with_translations(lemma: str):
    """Get example sentences with translations for a lemma."""
    if not lemma:
        return json_error("Lemma is required")

    collocate = request.args.get('collocate')
    # Bounds checking for limit (max 100)
    raw_limit = int(request.args.get('limit', 10))
    limit = min(max(1, raw_limit), 100)

    service = get_enrichment_service()

    try:
        examples = service.get_examples_with_translations(lemma, collocate, limit)

        return jsonify({
            "lemma": lemma,
            "collocate": collocate or "",
            "examples": examples,
            "total": len(examples)
        })
    except Exception as e:
        logger.error(f"Examples request failed for {lemma}: {e}")
        return json_error("Failed to get examples", 503)


@word_sketch_bp.route('/draft-subentry', methods=['POST'])
@swag_from({
    'tags': ['Word Sketch'],
    'summary': 'Create a subentry draft from collocation data',
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'schema': {
            'type': 'object',
            'properties': {
                'lemma': {'type': 'string'},
                'collocate': {'type': 'string'},
                'relation': {'type': 'string'},
                'relation_name': {'type': 'string'},
                'examples': {'type': 'array', 'items': {'type': 'string'}}
            },
            'required': ['lemma', 'collocate', 'relation']
        }}
    ],
    'responses': {
        200: {'description': 'Draft created successfully'},
        400: {'description': 'Invalid request'},
        429: {'description': 'Rate limit exceeded'},
        503: {'description': 'Service unavailable'}
    }
})
@(_check_limiter()("50/hour") if limiter else lambda f: f)
def draft_subentry():
    """
    Create a subentry draft from collocation data.

    Request body:
    {
        "lemma": "house",
        "collocate": "big",
        "relation": "noun_modifiers",
        "relation_name": "Adjectives modifying",
        "examples": ["big house", "the big house"]
    }
    """
    data = request.get_json()

    if not data:
        return json_error("Request body required")

    lemma = data.get('lemma', '').strip().lower()
    collocate = data.get('collocate', '').strip()
    relation = data.get('relation', '')
    relation_name = data.get('relation_name', '')
    examples = data.get('examples', [])

    if not all([lemma, collocate, relation]):
        return json_error("lemma, collocate, and relation are required")

    service = get_enrichment_service()

    try:
        draft = service.draft_subentry(
            parent_lemma=lemma,
            collocate=collocate,
            relation=relation,
            relation_name=relation_name,
            examples=examples
        )

        return jsonify({
            "draft": draft.to_dict(),
            "ready_for_review": True,
            "next_steps": [
                "Review the definition template",
                "Add appropriate gloss/definition",
                "Set the complex-form-type trait",
                "Save as subentry"
            ]
        })
    except Exception as e:
        logger.error(f"Subentry draft failed: {e}")
        return json_error("Failed to create draft", 503)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@word_sketch_bp.route('/status', methods=['GET'])
def service_status():
    """Get word sketch service status."""
    client = get_ws_client()
    health = client.health()

    return jsonify({
        "available": client.is_available(),
        "health": health
    })


@word_sketch_bp.route('/relations', methods=['GET'])
@swag_from({
    'tags': ['Word Sketch'],
    'summary': 'Get available grammatical relations',
    'responses': {
        200: {'description': 'List of grammatical relations by POS group'},
        503: {'description': 'Service unavailable'}
    }
})
def get_relations():
    """Get available grammatical relations from the service."""
    client = get_ws_client()

    if not client.is_available():
        return jsonify({
            "available": False,
            "relations": {},
            "message": "Word sketch service unavailable"
        }), 503

    try:
        relations = client.relations()
        return jsonify({
            "available": True,
            "relations": relations
        })
    except Exception as e:
        logger.error(f"Failed to get relations: {e}")
        return json_error(str(e), 503)


# ============================================================================
# Word Sketch Browser Endpoints
# ============================================================================

@word_sketch_bp.route('/sketch/<lemma>', methods=['GET'])
@swag_from({
    'tags': ['Word Sketch'],
    'summary': 'Get word sketch for a lemma',
    'parameters': [
        {'name': 'lemma', 'in': 'path', 'type': 'string', 'required': True},
        {'name': 'pos', 'in': 'query', 'type': 'string', 'required': False},
        {'name': 'min_logdice', 'in': 'query', 'type': 'number', 'required': False},
        {'name': 'limit', 'in': 'query', 'type': 'integer', 'required': False, 'maximum': 100}
    ],
    'responses': {
        200: {'description': 'Word sketch data'},
        400: {'description': 'Invalid request'},
        503: {'description': 'Service unavailable'}
    }
})
def get_word_sketch(lemma: str):
    """
    Get word sketch for a lemma.

    Returns collocations grouped by grammatical relation.
    """
    if not lemma or not lemma.strip():
        return json_error("Lemma is required")

    lemma = lemma.strip().lower()
    pos = request.args.get('pos')
    min_logdice = float(request.args.get('min_logdice', 0))
    # Bounds checking for limit (max 100)
    raw_limit = int(request.args.get('limit', 10))
    limit = min(max(1, raw_limit), 100)

    client = get_ws_client()

    sketch = client.word_sketch(lemma, pos, min_logdice, limit)

    if not sketch:
        return jsonify({
            "lemma": lemma,
            "pos": pos or "",
            "available": False,
            "message": "Word sketch unavailable - service may be down or no data found"
        }), 503

    # Group collocations by relation
    relations = {}
    for coll in sketch.collocations:
        rel_key = coll.relation
        if rel_key not in relations:
            relations[rel_key] = {
                "id": rel_key,
                "name": coll.relation_name or rel_key,
                "collocations": []
            }
        relations[rel_key]["collocations"].append({
            "lemma": coll.collocate,
            "logdice": round(coll.logdice, 2),
            "frequency": coll.frequency,
            "examples": coll.examples[:2]  # Limit examples
        })

    return jsonify({
        "lemma": sketch.lemma,
        "pos": sketch.pos,
        "available": True,
        "relations": list(relations.values()),
        "total_collocations": len(sketch.collocations),
        "total_examples": sketch.total_examples
    })


@word_sketch_bp.route('/sketch/query', methods=['POST'])
@swag_from({
    'tags': ['Word Sketch'],
    'summary': 'Execute custom CQL pattern query',
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'schema': {
            'type': 'object',
            'properties': {
                'lemma': {'type': 'string'},
                'pattern': {'type': 'string'},
                'min_logdice': {'type': 'number'},
                'limit': {'type': 'integer', 'maximum': 100}
            },
            'required': ['lemma', 'pattern']
        }}
    ],
    'responses': {
        200: {'description': 'Custom query results'},
        400: {'description': 'Invalid request'},
        503: {'description': 'Service unavailable'}
    }
})
def custom_query():
    """Execute custom CQL pattern query."""
    data = request.get_json()

    if not data:
        return json_error("Request body required")

    lemma = data.get('lemma', '').strip().lower()
    pattern = data.get('pattern', '').strip()

    if not lemma or not pattern:
        return json_error("lemma and pattern are required")

    min_logdice = float(data.get('min_logdice', 0))
    # Bounds checking for limit (max 100)
    raw_limit = int(data.get('limit', 50))
    limit = min(max(1, raw_limit), 100)

    client = get_ws_client()
    sketch = client.custom_query(lemma, pattern, min_logdice, limit)

    if not sketch:
        return jsonify({
            "lemma": lemma,
            "pattern": pattern,
            "available": False,
            "message": "Query failed - service may be unavailable"
        }), 503

    collocations = [
        {
            "lemma": coll.collocate,
            "logdice": round(coll.logdice, 2),
            "frequency": coll.frequency,
            "examples": coll.examples[:2]
        }
        for coll in sketch.collocations
    ]

    return jsonify({
        "lemma": sketch.lemma,
        "pattern": pattern,
        "available": True,
        "collocations": collocations,
        "total": len(collocations)
    })


# ============================================================================
# Coverage Endpoints
# ============================================================================

@word_sketch_bp.route('/coverage/entry/<entry_id>', methods=['GET'])
@swag_from({
    'tags': ['Word Sketch'],
    'summary': 'Check word sketch coverage for an entry',
    'parameters': [
        {'name': 'entry_id', 'in': 'path', 'type': 'string', 'required': True},
        {'name': 'lemma', 'in': 'query', 'type': 'string', 'required': False},
        {'name': 'pos', 'in': 'query', 'type': 'string', 'required': False}
    ],
    'responses': {
        200: {'description': 'Coverage result'},
        503: {'description': 'Service unavailable'}
    }
})
def check_entry_coverage(entry_id: str):
    """
    Check word sketch coverage for a single entry.

    Used to show coverage status on entry view/edit pages.
    """
    lemma = request.args.get('lemma', '').strip()
    pos = request.args.get('pos')

    if not lemma:
        return json_error("Lemma parameter required")

    coverage_service = get_coverage_service()
    result = coverage_service.check_entry_coverage(lemma, pos)

    return jsonify({
        "entry_id": entry_id,
        "lemma": result.lemma,
        "pos": result.pos,
        "has_coverage": result.has_coverage,
        "corpus_count": result.corpus_count,
        "coverage_score": round(result.coverage_score, 2),
        "collocations_count": result.collocations_count,
        "needs_enrichment": result.needs_enrichment,
        "available": True
    })


@word_sketch_bp.route('/coverage/workset/<int:workset_id>', methods=['GET'])
@swag_from({
    'tags': ['Word Sketch'],
    'summary': 'Get word sketch coverage report for a workset',
    'parameters': [
        {'name': 'workset_id', 'in': 'path', 'type': 'integer', 'required': True},
        {'name': 'min_logdice', 'in': 'query', 'type': 'number', 'required': False}
    ],
    'responses': {
        200: {'description': 'Coverage report'},
        400: {'description': 'Invalid workset ID'},
        503: {'description': 'Service unavailable'}
    }
})
def get_workset_coverage(workset_id: int):
    """
    Get word sketch coverage report for a workset.

    Returns:
    - Coverage percentage
    - Missing entries (priority sorted)
    - Enrichment opportunities
    """
    min_logdice = float(request.args.get('min_logdice', 6.0))

    try:
        coverage_service = get_coverage_service()
        report = coverage_service.analyze_workset(workset_id, min_logdice)

        return jsonify({
            "workset_id": report.workset_id,
            "workset_name": report.workset_name,
            "total_entries": report.total_entries,
            "covered_entries": report.covered_entries,
            "coverage_percentage": report.coverage_percentage,
            "missing_count": len(report.priority_items),
            "needs_enrichment_count": len(report.missing_entries),
            "priority_items": report.priority_items[:20],
            "available": True
        })
    except ValueError as e:
        return json_error(str(e), 400)
    except Exception as e:
        logger.error(f"Coverage report failed: {e}")
        return json_error("Coverage analysis failed", 503)


@word_sketch_bp.route('/coverage/workset/<int:workset_id>/missing', methods=['GET'])
def get_missing_lemmas(workset_id: int):
    """Get lemmas missing word sketch coverage in a workset."""
    try:
        coverage_service = get_coverage_service()
        missing = coverage_service.get_missing_lemmas(workset_id)

        return jsonify({
            "workset_id": workset_id,
            "missing_lemmas": missing,
            "count": len(missing)
        })
    except Exception as e:
        logger.error(f"Failed to get missing lemmas: {e}")
        return json_error("Failed to get missing lemmas", 503)


# ============================================================================
# Cache Management
# ============================================================================

@word_sketch_bp.route('/cache', methods=['DELETE'])
def clear_cache():
    """Clear all word sketch cache entries."""
    client = get_ws_client()
    count = client.clear_cache()

    return jsonify({
        "status": "ok",
        "message": f"Cleared {count} cache entries"
    })


@word_sketch_bp.route('/cache/<lemma>', methods=['DELETE'])
def clear_lemma_cache(lemma: str):
    """Clear cache for a specific lemma."""
    if not lemma:
        return json_error("Lemma required")

    client = get_ws_client()
    count = client.clear_cache(lemma.lower())

    return jsonify({
        "status": "ok",
        "lemma": lemma,
        "message": f"Cleared {count} cache entries"
    })
