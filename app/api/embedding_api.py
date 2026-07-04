"""
API Blueprint for Semantic Embeddings and Vector Search.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Dict, Any

from flask import Blueprint, jsonify, request, g, current_app
from app.services.embedding_service import get_embedding_service, AVAILABLE_MODELS

logger = logging.getLogger(__name__)

embedding_bp = Blueprint("embedding_api", __name__, url_prefix="/api/embeddings")

# In-memory job progress tracking for async index rebuilds
_rebuild_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _update_job(job_id: str, data: Dict[str, Any]):
    with _jobs_lock:
        if job_id not in _rebuild_jobs:
            _rebuild_jobs[job_id] = {}
        _rebuild_jobs[job_id].update(data)


@embedding_bp.route("/models", methods=["GET"])
def get_available_models():
    """List available sentence-transformer models."""
    return jsonify({
        "success": True,
        "models": AVAILABLE_MODELS,
    })


@embedding_bp.route("/status", methods=["GET"])
def get_status():
    """Get current embedding index status."""
    project_id = request.args.get("project_id", type=int) or getattr(g, "project_id", 1)
    try:
        service = get_embedding_service()
        status = service.get_index_status(project_id=project_id)
        return jsonify({
            "success": True,
            "status": status,
        })
    except Exception as e:
        logger.error("Error fetching embedding status: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@embedding_bp.route("/rebuild", methods=["POST"])
def rebuild_index():
    """Start async rebuild of the semantic embedding index."""
    data = request.get_json() or {}
    project_id = data.get("project_id") or getattr(g, "project_id", 1)
    job_id = str(uuid.uuid4())

    _update_job(job_id, {
        "job_id": job_id,
        "status": "queued",
        "processed": 0,
        "total": 0,
        "message": "Queued rebuild job...",
        "error": None,
    })

    app_obj = current_app._get_current_object()

    def _run_rebuild():
        with app_obj.app_context():
            try:
                _update_job(job_id, {"status": "running", "message": "Starting rebuild..."})

                def _progress_cb(processed: int, total: int, message: str):
                    _update_job(job_id, {
                        "processed": processed,
                        "total": total,
                        "message": message,
                    })

                service = get_embedding_service()
                result = service.rebuild_index(
                    project_id=project_id,
                    progress_callback=_progress_cb,
                )

                _update_job(job_id, {
                    "status": "completed",
                    "processed": result.get("indexed", 0),
                    "total": result.get("total", 0),
                    "message": "Index rebuild complete!",
                    "result": result,
                })
            except Exception as e:
                logger.error("Rebuild job %s failed: %s", job_id, e, exc_info=True)
                _update_job(job_id, {
                    "status": "failed",
                    "error": str(e),
                    "message": f"Failed: {e}",
                })

    t = threading.Thread(target=_run_rebuild, daemon=True)
    t.start()

    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Rebuild started",
    }), 202


@embedding_bp.route("/rebuild/progress/<job_id>", methods=["GET"])
def get_rebuild_progress(job_id: str):
    """Poll progress of a background index rebuild job."""
    with _jobs_lock:
        job = _rebuild_jobs.get(job_id)

    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404

    return jsonify({
        "success": True,
        "job": job,
    })


@embedding_bp.route("/search", methods=["GET"])
def search_semantic():
    """Perform semantic similarity search for a query string."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "error": "Query parameter 'q' is required"}), 400

    project_id = request.args.get("project_id", type=int) or getattr(g, "project_id", 1)
    top_k = request.args.get("top_k", default=20, type=int)
    threshold = request.args.get("threshold", default=0.4, type=float)

    try:
        service = get_embedding_service()
        results = service.semantic_search(
            query=query,
            project_id=project_id,
            top_k=top_k,
            threshold=threshold,
        )
        return jsonify({
            "success": True,
            "query": query,
            "count": len(results),
            "results": results,
        })
    except Exception as e:
        logger.error("Semantic search error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@embedding_bp.route("/related/<entry_id>", methods=["GET"])
def get_related_entries(entry_id: str):
    """Find semantically related entries for a given entry ID."""
    project_id = request.args.get("project_id", type=int) or getattr(g, "project_id", 1)
    top_k = request.args.get("top_k", default=10, type=int)
    threshold = request.args.get("threshold", default=0.5, type=float)

    try:
        service = get_embedding_service()
        related = service.find_related(
            entry_id=entry_id,
            project_id=project_id,
            top_k=top_k,
            threshold=threshold,
        )
        return jsonify({
            "success": True,
            "entry_id": entry_id,
            "count": len(related),
            "related": related,
        })
    except Exception as e:
        logger.error("Related entries error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@embedding_bp.route("/", methods=["DELETE"])
def delete_index():
    """Delete vector index for a project."""
    project_id = request.args.get("project_id", type=int) or getattr(g, "project_id", 1)
    try:
        service = get_embedding_service()
        deleted = service.delete_index(project_id=project_id)
        return jsonify({
            "success": True,
            "deleted": deleted,
        })
    except Exception as e:
        logger.error("Delete index error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
