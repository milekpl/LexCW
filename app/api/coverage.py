"""
Coverage checking API endpoints.

Provides REST API for resource coverage, text coverage,
systematicity checks, sense alignment, and gap analysis.
"""
from __future__ import annotations

import os
import tempfile
import logging

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from app.services.coverage_check.coverage_service import CoverageService

logger = logging.getLogger(__name__)

coverage_bp = Blueprint("coverage_api", __name__)

# Allowed upload extensions
ALLOWED_EXTENSIONS = {"txt", "csv", "tsv", "json", "yaml", "yml", "xml"}


def _get_service() -> CoverageService:
    """Get or create CoverageService instance."""
    if not hasattr(coverage_bp, "_service"):
        coverage_bp._service = CoverageService()
    return coverage_bp._service


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@coverage_bp.route("/api/coverage/resource", methods=["POST"])
def check_resource_coverage():
    """Check coverage of an uploaded resource file.

    ---
    tags: [Coverage]
    consumes: [multipart/form-data]
    parameters:
      - name: file
        type: file
        required: true
        description: Resource file (txt, csv, tsv)
      - name: resource_type
        type: string
        required: true
        enum: [text, subtlex]
        description: Type of resource
      - name: language
        type: string
        default: en
        description: Source language code
      - name: target_language
        type: string
        description: Target language code for translations
    responses:
      200:
        description: Coverage results
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    resource_type = request.form.get("resource_type", "text")
    language = request.form.get("language", "en")
    target_language = request.form.get("target_language")

    # Save uploaded file to temp
    filename = secure_filename(file.filename)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{filename}"
    ) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        service = _get_service()
        result = service.check_resource_coverage(
            source_path=tmp_path,
            resource_type=resource_type,
            language=language,
            target_language=target_language,
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("Resource coverage check failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)


@coverage_bp.route("/api/coverage/text", methods=["POST"])
def check_text_coverage():
    """Check coverage of submitted text.

    ---
    tags: [Coverage]
    consumes: [application/json]
    parameters:
      - in: body
        schema:
          type: object
          required: [text]
          properties:
            text:
              type: string
              description: Text to analyze
            language:
              type: string
              default: en
            target_language:
              type: string
    responses:
      200:
        description: Coverage results
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data["text"]
    if not text.strip():
        return jsonify({"error": "Empty text"}), 400

    language = data.get("language", "en")
    target_language = data.get("target_language")

    try:
        service = _get_service()
        result = service.check_text_coverage(
            text=text,
            language=language,
            target_language=target_language,
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("Text coverage check failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@coverage_bp.route("/api/coverage/systematicity", methods=["GET"])
def check_systematicity():
    """Run systematicity checks.

    ---
    tags: [Coverage]
    parameters:
      - name: language
        in: query
        type: string
        default: en
    responses:
      200:
        description: Systematicity results
    """
    language = request.args.get("language", "en")

    try:
        service = _get_service()
        result = service.check_systematicity(language=language)
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("Systematicity check failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@coverage_bp.route("/api/coverage/alignment", methods=["GET"])
def check_sense_alignment():
    """Check WordNet sense alignment.

    ---
    tags: [Coverage]
    parameters:
      - name: language
        in: query
        type: string
        default: en
      - name: target_language
        in: query
        type: string
      - name: threshold_low
        in: query
        type: number
        default: 0.5
      - name: threshold_high
        in: query
        type: number
        default: 2.0
      - name: word
        in: query
        type: string
        description: Single word to check (optional)
    responses:
      200:
        description: Sense alignment results
    """
    language = request.args.get("language", "en")
    target_language = request.args.get("target_language")
    threshold_low = float(request.args.get("threshold_low", 0.5))
    threshold_high = float(request.args.get("threshold_high", 2.0))
    word = request.args.get("word")

    try:
        service = _get_service()

        if word:
            # Single word query
            entry = service.get_wordnet_entry(word, language, target_language)
            synset_count = service.get_wordnet_synset_count(word, language)
            if entry:
                return jsonify({
                    "success": True,
                    "word": word,
                    "synset_count": synset_count,
                    "entry": entry.to_dict(),
                })
            else:
                return jsonify({"success": True, "word": word, "synset_count": 0, "entry": None})

        result = service.check_sense_alignment(
            language=language,
            target_language=target_language,
            threshold_low=threshold_low,
            threshold_high=threshold_high,
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("Sense alignment check failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@coverage_bp.route("/api/coverage/wordnet/<word>", methods=["GET"])
def get_wordnet_word(word: str):
    """Get WordNet data for a specific word with dictionary coverage status.

    ---
    tags: [Coverage]
    parameters:
      - name: word
        in: path
        type: string
        required: true
      - name: language
        in: query
        type: string
        default: en
      - name: target_language
        in: query
        type: string
    responses:
      200:
        description: WordNet data with coverage status
    """
    language = request.args.get("language", "en")
    target_language = request.args.get("target_language")

    try:
        service = _get_service()
        entry = service.get_wordnet_entry(word, language, target_language)
        synset_count = service.get_wordnet_synset_count(word, language)

        if entry:
            # Check coverage against dictionary
            dict_clsf = service._load_dictionary_with_senses_from_basex()
            covered_senses = []
            missing_senses = []

            if dict_clsf:
                # Find dictionary entry for this word
                dict_entry = None
                for e in dict_clsf.entries:
                    if e.headword.lower() == word.lower():
                        dict_entry = e
                        break

                if dict_entry:
                    for sense in entry.senses:
                        # Check if any dictionary sense has a matching translation
                        is_covered = False
                        for dict_sense in dict_entry.senses:
                            if not dict_sense.translations:
                                continue
                            for dict_trans in dict_sense.translations:
                                if not sense.translations:
                                    continue
                                for wn_trans in sense.translations:
                                    # Case-insensitive exact match or substring
                                    if (dict_trans.lower() == wn_trans.lower() or
                                        dict_trans.lower() in wn_trans.lower() or
                                        wn_trans.lower() in dict_trans.lower()):
                                        is_covered = True
                                        break
                                if is_covered:
                                    break
                            if is_covered:
                                break

                        covered_senses.append({
                            "definition": sense.definition,
                            "synset_id": sense.synset_id,
                            "covered": is_covered,
                            "translations": sense.translations,
                        })
                else:
                    # Word not in dictionary at all
                    for sense in entry.senses:
                        covered_senses.append({
                            "definition": sense.definition,
                            "synset_id": sense.synset_id,
                            "covered": False,
                            "translations": sense.translations,
                        })
            else:
                # No dictionary available
                for sense in entry.senses:
                    covered_senses.append({
                        "definition": sense.definition,
                        "synset_id": sense.synset_id,
                        "covered": None,  # None = no dictionary to compare
                        "translations": sense.translations,
                    })

            return jsonify({
                "success": True,
                "word": word,
                "synset_count": synset_count,
                "entry": entry.to_dict(),
                "coverage_status": {
                    "senses": covered_senses,
                    "covered_count": sum(1 for s in covered_senses if s["covered"] is True),
                    "missing_count": sum(1 for s in covered_senses if s["covered"] is False),
                    "not_compared_count": sum(1 for s in covered_senses if s["covered"] is None),
                },
            })
        else:
            return jsonify({
                "success": True,
                "word": word,
                "synset_count": 0,
                "entry": None,
                "coverage_status": None,
            })
    except Exception as e:
        logger.error("WordNet lookup failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@coverage_bp.route("/api/coverage/wordnet-gap", methods=["GET"])
def check_wordnet_gap():
    """Run or filter gap analysis comparing WordNet against the BaseX dictionary.

    Supports caching, pagination, search, and filtering.

    ---
    tags: [Coverage]
    parameters:
      - name: language
        in: query
        type: string
        default: en
      - name: target_language
        in: query
        type: string
      - name: search
        in: query
        type: string
      - name: priority
        in: query
        type: string
      - name: pos
        in: query
        type: string
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 50
      - name: refresh
        in: query
        type: boolean
        default: false
        description: Force recompute cached analysis
    responses:
      200:
        description: Gap analysis results
    """
    language = request.args.get("language", "en")
    target_language = request.args.get("target_language")
    search = request.args.get("search", "").strip().lower()
    priority = request.args.get("priority", "")
    pos = request.args.get("pos", "").strip().lower()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    refresh = request.args.get("refresh", "false").lower() == "true"

    try:
        service = _get_service()

        # Use cached result if available and not refreshing
        cached = service.get_cached_gap_analysis(language, target_language)
        if cached and not refresh:
            result = cached
        else:
            result = service.compute_and_cache_gap_analysis(language, target_language)

        # Filter and paginate from cached result
        filtered = service.filter_gap_analysis(
            result, search=search, priority=priority, pos=pos,
            page=page, per_page=per_page,
        )
        return jsonify({"success": True, **filtered})
    except Exception as e:
        logger.error("WordNet gap analysis failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@coverage_bp.route("/api/coverage/import-clsf", methods=["POST"])
def import_clsf():
    """Import a CLSF file (JSON or YAML) as a baseline resource.

    ---
    tags: [Coverage]
    consumes: [multipart/form-data]
    parameters:
      - name: file
        type: file
        required: true
        description: CLSF file (JSON or YAML)
    responses:
      200:
        description: Import results
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in ("json", "yaml", "yml"):
        return jsonify({"error": "File type not allowed. Use: json, yaml, yml"}), 400

    # Save uploaded file to temp
    filename = secure_filename(file.filename)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{filename}"
    ) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        service = _get_service()
        clsf = service.import_clsf_file(tmp_path)
        if clsf:
            return jsonify({
                "success": True,
                "metadata": clsf.metadata.to_dict(),
                "entry_count": len(clsf.entries),
                "senses_count": sum(len(e.senses) for e in clsf.entries),
            })
        else:
            return jsonify({"error": "Failed to parse CLSF file"}), 400
    except Exception as e:
        logger.error("CLSF import failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)


@coverage_bp.route("/api/coverage/import-dante", methods=["POST"])
def import_dante():
    """Import a DANTE XML file as a baseline resource.

    ---
    tags: [Coverage]
    consumes: [multipart/form-data]
    parameters:
      - name: file
        type: file
        required: true
        description: DANTE XML file
    responses:
      200:
        description: Import results
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith('.xml'):
        return jsonify({"error": "File type not allowed. Use: xml"}), 400

    # Save uploaded file to temp
    filename = secure_filename(file.filename)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{filename}"
    ) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        from app.services.coverage_check.providers.dante_provider import DanteProvider
        service = _get_service()
        provider = DanteProvider(tmp_path)
        clsf = provider.to_clsf()
        return jsonify({
            "success": True,
            "metadata": clsf.metadata.to_dict(),
            "entry_count": len(clsf.entries),
            "senses_count": sum(len(e.senses) for e in clsf.entries),
        })
    except Exception as e:
        logger.error("DANTE import failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)
