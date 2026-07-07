"""
POS Tagger API Endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from flask import Blueprint, jsonify, request, current_app

from app.services.pos_tagger_service import get_pos_tagger_service

pos_bp = Blueprint("pos_api", __name__, url_prefix="/pos")
logger = logging.getLogger(__name__)


@pos_bp.route("/tag-text", methods=["POST"])
def tag_text() -> Any:
    """Tag raw text input with POS labels."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    lang = data.get("lang", "en")
    if not text:
        return jsonify({"error": "text is required"}), 400

    service = get_pos_tagger_service()
    tokens = service.tag_text(text, lang=lang)
    return jsonify({"success": True, "tokens": tokens, "count": len(tokens)})


@pos_bp.route("/tag-entry", methods=["POST"])
def tag_entry() -> Any:
    """Predict top POS category for a dictionary entry."""
    data = request.get_json(silent=True) or {}
    entry = data.get("entry") or data
    if not entry:
        return jsonify({"error": "entry data is required"}), 400

    service = get_pos_tagger_service()
    prediction = service.predict_entry_pos(entry)
    return jsonify({"success": True, "prediction": prediction})


@pos_bp.route("/batch-tag", methods=["POST"])
def batch_tag() -> Any:
    """Predict POS for multiple entries."""
    data = request.get_json(silent=True) or {}
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return jsonify({"error": "entries list is required"}), 400

    service = get_pos_tagger_service()
    results = service.tag_entries_batch(entries)
    return jsonify({"success": True, "results": results, "count": len(results)})


@pos_bp.route("/apply-tags", methods=["POST"])
def apply_tags() -> Any:
    """Apply predicted POS tags directly or return proposed tags."""
    data = request.get_json(silent=True) or {}
    entries = data.get("entries", [])
    mode = data.get("mode", "proposal")  # 'proposal' or 'direct'

    if not isinstance(entries, list) or not entries:
        return jsonify({"error": "entries list is required"}), 400

    service = get_pos_tagger_service()
    predictions = service.tag_entries_batch(entries)

    if mode == "proposal":
        proposals = []
        for pred in predictions:
            proposals.append({
                "entry_id": pred["entry_id"],
                "proposal_type": "pos",
                "field_name": "grammatical_info",
                "proposed_value": pred["predicted_pos"],
                "confidence": pred["confidence"],
                "source_script": "pos_tagger_service",
            })

        # Create proposal workset if requested
        if data.get("create_workset", True):
            from app.services.workset_service import WorksetService
            workset_svc = WorksetService()
            workset = workset_svc.create_proposal_workset(
                name=data.get("workset_name", "POS Tag Proposals"),
                source_script="pos_tagger_service",
                proposals=proposals,
            )
            return jsonify({
                "success": True,
                "mode": "proposal",
                "workset_id": workset.id,
                "total_proposals": len(proposals),
                "proposals": proposals,
            })

        return jsonify({
            "success": True,
            "mode": "proposal",
            "proposals": proposals,
        })

    # Direct mode: apply tags directly via DictionaryService
    from app.api.entries import get_dictionary_service
    dict_svc = get_dictionary_service()
    updated_ids = []
    for pred in predictions:
        eid = pred["entry_id"]
        if eid and pred.get("predicted_pos"):
            try:
                entry = dict_svc.get_entry(eid)
                if entry:
                    entry_dict = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
                    entry_dict["grammatical_info"] = pred["predicted_pos"]
                    dict_svc.update_entry(eid, entry_dict)
                    updated_ids.append(eid)
            except Exception as e:
                logger.warning(f"Failed to auto-apply POS to {eid}: {e}")

    return jsonify({
        "success": True,
        "mode": "direct",
        "updated_count": len(updated_ids),
        "updated_ids": updated_ids,
    })


@pos_bp.route("/mappings", methods=["GET"])
def get_mappings() -> Any:
    """Retrieve POS tagset mappings for a language or all languages."""
    lang = request.args.get("lang")
    service = get_pos_tagger_service()
    mappings = service.get_tagset_mappings(lang)
    return jsonify({"success": True, "lang": lang or "all", "mappings": mappings})


@pos_bp.route("/mappings", methods=["POST", "PUT"])
def save_mappings() -> Any:
    """Save/update custom POS tagset mapping for a language."""
    data = request.get_json(silent=True) or {}
    lang = data.get("lang", "en")
    mappings = data.get("mappings")
    if not isinstance(mappings, dict):
        return jsonify({"error": "mappings dict is required"}), 400

    service = get_pos_tagger_service()
    updated = service.save_tagset_mappings(lang, mappings)
    return jsonify({"success": True, "lang": lang, "mappings": updated})


@pos_bp.route("/validate-definition-coherence", methods=["POST"])
def validate_definition_coherence() -> Any:
    """Analyze phrase-level consistency for comma-separated definition segments."""
    data = request.get_json(silent=True) or {}
    definition = data.get("definition", "").strip()
    lang = data.get("lang", "en")
    expected_pos = data.get("expected_pos")
    delimiter = data.get("delimiter")

    if not definition:
        return jsonify({"error": "definition is required"}), 400

    service = get_pos_tagger_service()
    result = service.analyze_definition_phrases(
        definition, lang=lang, expected_pos=expected_pos, delimiter=delimiter
    )

    return jsonify({"success": True, "analysis": result})


