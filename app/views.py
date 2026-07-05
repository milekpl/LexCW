"""
Views for the Lexicographic Curation Workbench's frontend.
"""

import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
    session,
    send_from_directory,
    Response,
    g,
)

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app.models.entry import Entry, RelationGroups
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data
from app.utils.language_utils import get_project_languages, get_language_choices_for_forms

logger = logging.getLogger(__name__)

# Create blueprints
main_bp = Blueprint("main", __name__)
workbench_bp = Blueprint("workbench", __name__, url_prefix="/workbench")

# Unified cache key for dashboard stats (must match dashboard.py)
DASHBOARD_CACHE_KEY = 'dashboard_stats_v2'
OLD_CACHE_KEYS = ['dashboard_stats', 'dashboard_stats_api']


@main_bp.app_template_global()
def safe_url_for(endpoint: str, **values: object) -> str:
    """Template-global safe url builder that returns a harmless placeholder
    when the endpoint is not registered. This ensures templates render even
    when certain blueprints are not present in unit test fixtures.
    """
    from werkzeug.routing import BuildError
    try:
        return url_for(endpoint, **values)
    except BuildError:
        return "#"


@main_bp.route("/corpus-management")
def corpus_management():
    """Render corpus management interface with async stats loading."""
    # Return page immediately with loading indicators
    # Stats will be loaded via AJAX from Lucene service
    lucene_status = {"connected": False, "error": None}
    corpus_stats = {
        "total_records": 0,
        "avg_source_length": "0.00",
        "avg_target_length": "0.00",
        "last_updated": "Loading...",
    }

    return render_template(
        "corpus_management.html",
        corpus_stats=corpus_stats,
        lucene_status=lucene_status,
    )


@main_bp.route("/validation-rules-admin")
def validation_rules_admin():
    """Render the validation rules admin interface."""
    from app.models.project_settings import ProjectSettings

    # Get all projects for the dropdown
    try:
        from flask import current_app
        from app.models.workset_models import db

        projects = db.session.query(ProjectSettings).order_by(ProjectSettings.project_name).all()
        projects_list = [
            {'id': p.id, 'project_name': p.project_name}
            for p in projects
        ]
    except Exception:
        projects_list = []

    return render_template(
        "admin/validation_rules_admin.html",
        projects=projects_list,
        critical_count=0,
        warning_count=0
    )


@main_bp.route("/validation")
def validation_tool():
    """Render the validation tool interface for batch checking entries."""
    from app.models.project_settings import ProjectSettings

    # Get all projects for the dropdown
    try:
        from flask import current_app
        from app.models.workset_models import db

        projects = db.session.query(ProjectSettings).order_by(ProjectSettings.project_name).all()
        projects_list = [
            {'id': p.id, 'name': p.project_name}
            for p in projects
        ]
    except Exception:
        projects_list = []

    # Get selected project from session
    from flask import session
    selected_project_id = session.get('project_id')

    return render_template(
        "validation_tool.html",
        projects=projects_list,
        selected_project_id=selected_project_id
    )


@main_bp.route("/")
def index():
    """
    Render the dashboard/home page with cached stats for performance.
    """
    import json

    # Default data for dashboard if DB connection fails
    stats = {"entries": 0, "senses": 0, "examples": 0}

    system_status = {
        "db_connected": False,
        "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "storage_percent": 0,
    }

    recent_activity = []

    # Try to get cached dashboard data first (new key, then old keys for migration)
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
            try:
                # Cached data may already be deserialized by CacheService.get() (dict),
                # or it may be a JSON string. Handle both cases gracefully.
                if isinstance(cached_data, (str, bytes)):
                    cached_stats = json.loads(cached_data)
                else:
                    cached_stats = cached_data

                stats = cached_stats.get("stats", stats)
                system_status = cached_stats.get("system_status", system_status)
                recent_activity = cached_stats.get("recent_activity", recent_activity)
                logger.info("Using cached dashboard stats")
                return render_template(
                    "index.html",
                    stats=stats,
                    system_status=system_status,
                    recent_activity=recent_activity,
                )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Invalid cached dashboard data: {e}")

    # Get actual stats from the database if possible
    try:
        dict_service = current_app.injector.get(DictionaryService)
        entry_count = dict_service.count_entries()
        stats["entries"] = entry_count

        # Get sense and example counts
        sense_count, example_count = dict_service.count_senses_and_examples()
        stats["senses"] = sense_count
        stats["examples"] = example_count

        # Get recent activity
        recent_activity = dict_service.get_recent_activity(limit=5)

        # Get system status
        system_status = dict_service.get_system_status()
        logger.info(f"System status retrieved: {system_status}")

        # Check system_status type to debug issues
        logger.info(f"system_status type: {type(system_status)}")
        logger.info(
            f"system_status keys: {system_status.keys() if hasattr(system_status, 'keys') else 'N/A'}"
        )
        logger.info(f"db_connected value: {system_status.get('db_connected', 'ERROR')}")
        logger.info(f"last_backup value: {system_status.get('last_backup', 'ERROR')}")
        logger.info(
            f"storage_percent value: {system_status.get('storage_percent', 'ERROR')}"
        )

        # Cache the dashboard data for 10 minutes (600 seconds)
        if cache.is_available():
            cache_data = {
                "stats": stats,
                "system_status": system_status,
                "recent_activity": recent_activity,
            }
            # Store the Python object directly; CacheService handles JSON serialization.
            cache.set(cache_key, cache_data, ttl=600)
            logger.info("Cached dashboard stats for 10 minutes")

    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}", exc_info=True)
        flash(f"Error loading dashboard data: {str(e)}", "danger")

    return render_template(
        "index.html",
        stats=stats,
        system_status=system_status,
        recent_activity=recent_activity,
    )


@main_bp.route("/entries")
def entries():
    """
    Render the entries list page.
    """
    return render_template("entries.html")


@main_bp.route("/entries/<entry_id>")
def view_entry(entry_id):
    """
    Render the entry detail page.

    All sections are rendered server-side; view-mode toggling
    (default / annotations / all) happens client-side for
    instant switching.  Modes control visibility of:
        - annotations: annotations + custom fields cards
        - all:         + structured senses view

    Args:
        entry_id: ID of the entry to view.
    """
    try:
        # Determine initial view mode hint for client-side JS.
        # URL param > workset context > session > default.
        valid_modes = ('default', 'annotations', 'all')
        initial_view_mode = request.args.get('view')
        if initial_view_mode in valid_modes:
            session['entry_view_mode'] = initial_view_mode
        elif request.args.get('workset_id'):
            initial_view_mode = 'annotations'
        else:
            initial_view_mode = session.get('entry_view_mode', 'default')

        # Get dictionary service
        dict_service = current_app.injector.get(DictionaryService)

        # Get entry (use non-validating method to allow viewing invalid entries)
        entry = dict_service.get_entry_for_editing(entry_id)

        # Batch-resolve all relation ref IDs to headwords in one query
        all_ref_ids = list(set(
            str(r.ref) for r in entry.relations
            if hasattr(r, 'ref') and r.ref
        ))
        headword_cache = dict_service.resolve_headwords_batch(all_ref_ids) if all_ref_ids else {}

        # Get component relations (main entries this is a subentry of)
        component_relations = entry.get_component_relations(dict_service, headword_cache=headword_cache)

        # Get subentries (reverse component relations)
        subentries = entry.get_subentries(dict_service)

        # Get LIFT ranges for relation type grouping
        project_id = session.get('project_id', 1)
        ranges = dict_service.get_lift_ranges(project_id=project_id)

        # Enrich entry-level relations (grouped_relations) with display text
        enriched_grouped_relations = RelationGroups(entry.relations, ranges)
        enriched_grouped_relations.enrich_with_display_text(dict_service, headword_cache=headword_cache)

        # Variant relations (both directions) — always rendered
        variant_relations = entry.get_complete_variant_relations(dict_service)

        # Annotations and custom fields — always rendered (hidden by default in client JS)
        custom_fields = entry.custom_fields
        annotations = entry.annotations

        # Get CSS-rendered HTML for the entry using default profile
        from app.services.css_mapping_service import CSSMappingService
        from app.services.display_profile_service import DisplayProfileService

        css_service = current_app.injector.get(CSSMappingService)
        profile_service = DisplayProfileService()

        # Get default profile or create one if it doesn't exist
        default_profile = profile_service.get_default_profile()
        if not default_profile:
            # Create a default profile from registry
            default_profile = profile_service.create_from_registry_default(
                name="Default Display Profile",
                description="Auto-created default profile"
            )
            profile_service.set_default_profile(default_profile.id)

        # Build a headword map from already resolved relations
        # so the CSS pipeline can skip re-resolving them
        headword_map = {}
        for rel in enriched_grouped_relations.all_relations:
            ref = rel.get('ref')
            text = rel.get('ref_display_text')
            if ref and text:
                headword_map[ref] = text
        for rel in variant_relations:
            ref = rel.get('ref')
            text = rel.get('ref_display_text')
            if ref and text:
                headword_map[ref] = text
        for comp in component_relations:
            ref = comp.get('ref')
            text = comp.get('ref_display_text')
            if ref and text:
                headword_map[ref] = text

        # Render entry with CSS using the raw XML from the parsed entry
        css_html = None
        try:
            entry_xml = getattr(entry, '_raw_xml', None)
            if entry_xml:
                # Check Redis cache for rendered CSS HTML
                cache_key_css = f"entry_css:v1:{entry_id}:{getattr(default_profile, 'id', 'default')}"
                cache = CacheService()
                cached_css = cache.get(cache_key_css) if cache.is_available() else None
                if cached_css:
                    css_html = cached_css
                else:
                    css_html = css_service.render_entry(
                        entry_xml,
                        profile=default_profile,
                        dict_service=dict_service,
                        headword_map=headword_map
                    )
                    # Cache for 5 minutes
                    if css_html and cache.is_available():
                        cache.set(cache_key_css, css_html, ttl=300)

                # If show_subentries is enabled, fetch and render all subentries in one query
                if default_profile.show_subentries and subentries:
                    try:
                        subentry_html_parts = []
                        ids = [s["id"] for s in subentries if s.get("id")]
                        if ids:
                            preds = " or ".join(f"@id='{i}'" for i in ids)
                            subentries_xml = dict_service.db_connector.execute_query(
                                f"xquery collection()//entry[{preds}]"
                            )
                            if subentries_xml:
                                wrapped = f"<root>{subentries_xml}</root>"
                                root = ET.fromstring(wrapped)
                                for child, sub_id in zip(root, ids):
                                    full_xml = ET.tostring(child, encoding="unicode")
                                    rendered = css_service.render_entry(
                                        full_xml,
                                        profile=default_profile,
                                        dict_service=dict_service,
                                    )
                                    subentry_html_parts.append(
                                        f'<div class="subentry" data-subentry-id="{sub_id}">{rendered}</div>'
                                    )
                        if subentry_html_parts:
                            css_html += "\n".join(subentry_html_parts)
                    except Exception as e:
                        logger.warning("Error rendering subentries: %s", e)

        except Exception as e:
            logger.warning("Error rendering entry with CSS: %s", e)

        return render_template("entry_view.html", entry=entry, css_html=css_html,
                             component_relations=component_relations, subentries=subentries,
                             variant_relations=variant_relations, custom_fields=custom_fields,
                             annotations=annotations,
                             enriched_grouped_relations=enriched_grouped_relations,
                             initial_view_mode=initial_view_mode)

    except NotFoundError:
        flash(f"Entry with ID {entry_id} not found.", "danger")
        return redirect(url_for("main.entries"))

    except Exception as e:
        logger.error(f"Error viewing entry {entry_id}: {e}")
        # Rollback any failed PostgreSQL transaction so subsequent queries work.
        try:
            from app.models.workset_models import db as _db
            _db.session.rollback()
        except Exception:
            pass
        flash(f"Error loading entry: {str(e)}", "danger")
        return redirect(url_for("main.entries"))


def _sanitize_submitted_senses(senses):
    """Drop empty/template senses from a submission.

    Guards against a race where a rapid delete + save includes a just-deleted
    sense in the POST payload. Keeps only senses carrying a non-empty definition
    or gloss. On any unexpected error the input is returned unchanged.
    """
    try:
        sanitized_senses = []
        for s in senses or []:
            has_definition = False
            has_gloss = False
            defs = s.get('definition') or {}
            # Handle both 'gloss' (singular) and 'glosses' (plural) from form data
            glosses = s.get('glosses') or s.get('gloss') or {}

            for val in defs.values() if isinstance(defs, dict) else []:
                if isinstance(val, dict) and val.get('text', '').strip():
                    has_definition = True
                    break
                if isinstance(val, str) and val.strip():
                    has_definition = True
                    break

            for val in glosses.values() if isinstance(glosses, dict) else []:
                if isinstance(val, dict) and val.get('text', '').strip():
                    has_gloss = True
                    break
                if isinstance(val, str) and val.strip():
                    has_gloss = True
                    break

            if has_definition or has_gloss:
                sanitized_senses.append(s)
            else:
                logger.info(f"[EDIT_ENTRY] Dropping empty/template sense from submission: id={s.get('id')}")

        return sanitized_senses
    except Exception as e:
        logger.warning(f"[EDIT_ENTRY] Failed to sanitize senses: {e}")
        return senses


def _handle_edit_entry_post(dict_service, entry_id):
    """Handle a POST to the entry edit endpoint: merge form data and persist.

    Returns a Flask JSON response. May raise NotFoundError/ValidationError,
    which the caller (:func:`edit_entry`) maps to the appropriate HTTP response.
    """
    # Handle both JSON and form data
    data = None
    try:
        data = request.get_json()
    except Exception:
        # If JSON parsing fails, fallback to form data
        pass

    if not data:
        # If no JSON, try to get form data
        if request.form:
            data = dict(request.form)
        else:
            return jsonify({"error": "No data provided"}), 400

    # Get existing entry data for merging (use non-validating method for editing)
    project_id = session.get('project_id')
    existing_entry = None
    try:
        existing_entry = dict_service.get_entry_for_editing(entry_id, project_id=project_id)
    except NotFoundError:
        # Entry doesn't exist yet - will be created instead of updated
        pass

    existing_data = existing_entry.to_dict() if existing_entry else {}

    # Merge form data with existing entry data, processing multilingual notes
    merged_data = merge_form_data_with_entry_data(data, existing_data)

    # SANITIZE: Drop empty/template senses to avoid race conditions where
    # a rapid delete + save might include a deleted sense in the POST payload
    merged_data['senses'] = _sanitize_submitted_senses(merged_data.get('senses', []))

    entry = Entry.from_dict(merged_data)
    entry.id = entry_id

    # Use XMLEntryService directly to avoid database lock issues
    # This creates fresh sessions and doesn't hold persistent connections
    from app.services.xml_entry_service import XMLEntryService
    db_name = dict_service.db_connector.database
    logger.info(f"[EDIT_ENTRY] Using database: {db_name}")
    xml_service = XMLEntryService(
        database=db_name  # Use the same database as DictionaryService!
    )

    # Prepare the entry XML using DictionaryService's method
    entry_xml = dict_service._prepare_entry_xml(entry)

    try:
        # Try to update, fall back to create if entry doesn't exist
        try:
            logger.info(f"[EDIT_ENTRY] Calling XMLEntryService.update_entry for {entry_id}")
            xml_service.update_entry(entry_id, entry_xml)
            logger.info(f"[EDIT_ENTRY] XMLEntryService.update_entry succeeded for {entry_id}")
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                logger.info(f"[EDIT_ENTRY] Entry {entry_id} not found, creating instead")
                xml_service.create_entry(entry_xml)
                logger.info(f"[EDIT_ENTRY] XMLEntryService.create_entry succeeded for {entry_id}")
            else:
                raise

        return jsonify({"id": entry_id, "message": "Entry updated successfully"})
    except Exception as update_error:
        logger.error(f"[EDIT_ENTRY] Update/create failed: {update_error}", exc_info=True)
        return jsonify({"error": f"Failed to save entry: {str(update_error)}"}), 500
    finally:
        # Close the XMLEntryService session to release the database lock,
        # otherwise subsequent requests hang with "Database opened by another process"
        try:
            xml_service.close()
        except Exception:
            pass


def _handle_edit_entry_get(dict_service, entry_id):
    """Render the entry edit page (GET).

    Loads the entry (creating an empty one if it does not exist yet), enriches
    its relations with display text, renders the CSS preview and returns the
    populated ``entry_form.html`` template.
    """
    # Try to load the entry for editing
    entry = None
    project_id = session.get('project_id')
    try:
        entry = dict_service.get_entry_for_editing(
            entry_id, project_id=project_id
        )  # Use non-validating method for editing
    except NotFoundError:
        logger.debug("Entry %s not found in database %s", entry_id, dict_service.db_connector.database)
        try:
            all_entries, count = dict_service.list_entries(project_id=project_id, limit=100)
            logger.debug("Available entries (%d): %s", count, [e.id for e in all_entries])
        except Exception as e:
            logger.debug("Error listing entries: %s", e)
        # Entry doesn't exist yet - create a new empty entry with the given ID
        entry = Entry(id_=entry_id)

    # Apply POS inheritance when loading entry for editing
    if entry:
        entry._apply_pos_inheritance()

    ranges = dict_service.get_lift_ranges(project_id=project_id)

    # Get validation results for the entry to show as guidance (not as blockers)
    validation_result = None
    if entry:
        from app.services.validation_engine import ValidationEngine

        validation_engine = ValidationEngine()
        validation_result = validation_engine.validate_entry(entry)

    # Explicitly extract enriched variant_relations for template (with display text and error markers)
    variant_relations_data = []
    component_relations_data = []
    forward_component_relations_data = []
    subentries_data = []
    if entry:
        logger.debug("========== [DEBUG VIEW EDIT] Entry %s ==========", entry.id)
        logger.debug("[DEBUG VIEW] Number of entry relations: %d", len(entry.relations))
        for rel in entry.relations:
            logger.debug("  Relation: type=%s, ref=%s, traits=%s", rel.type, rel.ref, rel.traits)

        # Batch-resolve all relation ref IDs to headwords in one query
        all_ref_ids = list(set(
            str(r.ref) for r in entry.relations
            if hasattr(r, 'ref') and r.ref
        ))
        headword_cache = dict_service.resolve_headwords_batch(all_ref_ids) if all_ref_ids else {}

        variant_relations_data = entry.get_complete_variant_relations(dict_service)
        logger.debug("[DEBUG VIEW] variant_relations_data returned: %d items", len(variant_relations_data))
        # Extract enriched component_relations for template (with display text for main entries)
        component_relations_data = entry.get_component_relations(dict_service, headword_cache=headword_cache)
        # Extract forward component relations (where this entry HAS components)
        forward_component_relations_data = entry.get_forward_component_relations(dict_service)
        # Extract subentries (reverse component relations)
        subentries_data = entry.get_subentries(dict_service)

        # Create enriched grouped_relations for template (can't set on entry because it's a property)
        enriched_grouped_relations = RelationGroups(entry.relations, ranges)
        enriched_grouped_relations.enrich_with_display_text(dict_service, headword_cache=headword_cache)

        # Enrich sense relations with display text
        for sense in entry.senses:
            if hasattr(sense, 'relations') and sense.relations:
                sense.relations = sense.enrich_relations_with_display_text(dict_service)

    # Get project languages for multilingual fields
    languages = get_project_languages()
    available_languages = get_language_choices_for_forms()

    # Define note types for the dropdown
    note_types = [
        ('general', 'General'),
        ('usage', 'Usage'),
        ('semantic', 'Semantic'),
        ('etymology', 'Etymology'),
        ('cultural', 'Cultural'),
        ('anthropology', 'Anthropology'),
        ('discourse', 'Discourse'),
        ('phonology', 'Phonology'),
        ('sociolinguistics', 'Sociolinguistics'),
        ('bibliography', 'Bibliography')
    ]

    # Get CSS-rendered HTML for the entry using default profile
    css_html = None
    try:
        from app.services.css_mapping_service import CSSMappingService
        from app.services.display_profile_service import DisplayProfileService

        css_service = current_app.injector.get(CSSMappingService)
        profile_service = DisplayProfileService()

        # Get default profile or create one if it doesn't exist
        default_profile = profile_service.get_default_profile()
        if not default_profile:
            # Create a default profile from registry
            default_profile = profile_service.create_from_registry_default(
                name="Default Display Profile",
                description="Auto-created default profile"
            )
            profile_service.set_default_profile(default_profile.id)

        # Build a headword map from already resolved relations
        headword_map = {}
        if entry:
            for rel in enriched_grouped_relations.all_relations:
                ref = rel.get('ref')
                text = rel.get('ref_display_text')
                if ref and text:
                    headword_map[ref] = text
            for rel in variant_relations_data:
                ref = rel.get('ref')
                text = rel.get('ref_display_text')
                if ref and text:
                    headword_map[ref] = text
            for comp in component_relations_data:
                ref = comp.get('ref')
                text = comp.get('ref_display_text')
                if ref and text:
                    headword_map[ref] = text

        # Render entry with CSS using the raw XML from the parsed entry
        entry_xml = getattr(entry, '_raw_xml', None) if entry else None
        if entry_xml:
            css_html = css_service.render_entry(
                entry_xml,
                profile=default_profile,
                dict_service=dict_service,
                headword_map=headword_map
            )

            # If show_subentries is enabled, fetch and render all subentries in one query
            if default_profile.show_subentries and subentries_data:
                try:
                    subentry_html_parts = []
                    ids = [s["id"] for s in subentries_data if s.get("id")]
                    if ids:
                        preds = " or ".join(f"@id='{i}'" for i in ids)
                        subentries_xml = dict_service.db_connector.execute_query(
                            f"xquery collection()//entry[{preds}]"
                        )
                        if subentries_xml:
                            wrapped = f"<root>{subentries_xml}</root>"
                            root = ET.fromstring(wrapped)
                            for child, sub_id in zip(root, ids):
                                full_xml = ET.tostring(child, encoding="unicode")
                                rendered = css_service.render_entry(
                                    full_xml,
                                    profile=default_profile,
                                    dict_service=dict_service,
                                )
                                subentry_html_parts.append(
                                    f'<div class="subentry" data-subentry-id="{sub_id}">{rendered}</div>'
                                )
                    if subentry_html_parts:
                        css_html += "\n".join(subentry_html_parts)
                except Exception as e:
                    logger.warning("Error rendering subentries: %s", e)

    except Exception as e:
        logger.warning("Error rendering entry with CSS: %s", e)

    logger.debug("[DEBUG VIEW] RENDERING with variant_relations=%d items", len(variant_relations_data))
    logger.debug("[DEBUG VIEW] variant_relations_data: %s", variant_relations_data)

    return render_template(
        "entry_form.html",
        entry=entry,
        ranges=ranges,
        variant_relations=variant_relations_data,
        component_relations=component_relations_data,
        forward_component_relations=forward_component_relations_data,
        subentries=subentries_data,
        enriched_grouped_relations=enriched_grouped_relations,
        validation_result=validation_result,
        project_languages=languages,
        available_languages=available_languages,
        note_types=note_types,
        css_html=css_html,
    )


@main_bp.route("/entries/<entry_id>/edit", methods=["GET", "POST"])
def edit_entry(entry_id):
    """
    Edit an existing dictionary entry
    ---
    tags:
      - Entries
    parameters:
      - name: entry_id
        in: path
        type: string
        required: true
        description: ID of the entry to edit
      - name: body
        in: body
        required: false
        description: Entry data (for POST requests)
        schema:
          type: object
          properties:
            lexical_unit:
              type: object
              description: Lexical unit forms by language code
              example: {"en": "house", "pt": "casa"}
            notes:
              type: object
              description: |
                Entry notes, supporting both legacy string format and multilingual object format.
                Form field format: notes[type][language][text]
              additionalProperties:
                oneOf:
                  - type: string
                    description: Legacy format - simple string note
                  - type: object
                    description: Multilingual format - notes by language code
                    additionalProperties:
                      type: string
              example: {
                "general": {"en": "Updated note in English", "pt": "Nota atualizada em português"},
                "usage": "Updated usage note"
              }
            grammatical_info:
              type: string
              description: Grammatical information
            senses:
              type: array
              description: Array of sense objects
    responses:
      200:
        description: |
          Entry form page (GET request) or entry updated successfully (POST request)
        content:
          text/html:
            schema:
              type: string
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: string
                  description: ID of the updated entry
                message:
                  type: string
                  description: Success message
      400:
        description: Invalid input data
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      404:
        description: Entry not found
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
    """
    logger.debug("="*60)
    logger.debug("EDIT_ENTRY CALLED FOR %s", entry_id)
    logger.debug("="*60)
    try:
        dict_service = current_app.injector.get(DictionaryService)
        logger.debug("Flask app database name: %s", dict_service.db_connector.database)
        logger.debug("Environment TEST_DB_NAME: %s", os.environ.get('TEST_DB_NAME'))
        if request.method == "POST":
            return _handle_edit_entry_post(dict_service, entry_id)
        return _handle_edit_entry_get(dict_service, entry_id)
    except NotFoundError as e:
        logger.warning(f"Entry with ID {entry_id} not found: {e}")
        flash(f"Entry with ID {entry_id} not found.", "danger")
        return redirect(url_for("main.entries"))
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error editing entry {entry_id}: {e}")
        flash(f"Error loading entry: {str(e)}", "danger")
        return redirect(url_for("main.entries"))


@main_bp.route("/entries/add", methods=["GET", "POST"])
def add_entry():
    """
    Add a new dictionary entry
    ---
    tags:
      - Entries
    parameters:
      - name: body
        in: body
        required: false
        description: Entry data (for POST requests)
        schema:
          type: object
          properties:
            lexical_unit:
              type: object
              description: Lexical unit forms by language code
              example: {"en": "house", "pt": "casa"}
            notes:
              type: object
              description: |
                Entry notes, supporting both legacy string format and multilingual object format.
                Form field format: notes[type][language][text]
              additionalProperties:
                oneOf:
                  - type: string
                    description: Legacy format - simple string note
                  - type: object
                    description: Multilingual format - notes by language code
                    additionalProperties:
                      type: string
              example: {
                "general": {"en": "A general note in English", "pt": "Uma nota geral em português"},
                "usage": "Simple usage note"
              }
            grammatical_info:
              type: string
              description: Grammatical information
            senses:
              type: array
              description: Array of sense objects
    responses:
      200:
        description: Entry form page (GET request)
        content:
          text/html:
            schema:
              type: string
      201:
        description: Entry created successfully (POST request)
        schema:
          type: object
          properties:
            id:
              type: string
              description: ID of the created entry
            message:
              type: string
              description: Success message
      400:
        description: Invalid input data
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
    """
    """
    Render the add entry page.
    """
    try:
        # Get dictionary service
        dict_service = current_app.injector.get(DictionaryService)

        if request.method == "POST":
            # Handle both JSON and form data
            data = None
            try:
                data = request.get_json()
            except Exception:
                # If JSON parsing fails, fallback to form data
                pass

            if not data:
                # If no JSON, try to get form data
                if request.form:
                    data = dict(request.form)
                else:
                    return jsonify({"error": "No data provided"}), 400

            # Process multilingual form data (starting with empty entry data for new entries)
            empty_entry_data = {}
            merged_data = merge_form_data_with_entry_data(data, empty_entry_data)

            # Create entry object
            entry = Entry.from_dict(merged_data)

            # Create entry
            project_id = session.get('project_id')
            entry_id = dict_service.create_entry(entry, project_id=project_id)

            # Return appropriate response format
            if request.is_json:
                return jsonify(
                    {"id": entry_id, "message": "Entry created successfully"}
                )
            else:
                flash("Entry created successfully!", "success")
                return redirect(url_for("main.view_entry", entry_id=entry_id))

        # Create an empty entry for the form (without ID for new entries)
        entry = Entry(id_="")  # Use empty string to prevent UUID generation
        entry.id = ""  # Explicitly set to empty string

        # Get LIFT ranges for dropdowns
        project_id = session.get('project_id')
        ranges = dict_service.get_lift_ranges(project_id=project_id)

        # Get project languages for multilingual fields
        languages = get_project_languages()
        available_languages = get_language_choices_for_forms()
        configured_languages_codes = [lang[0] for lang in languages]

        # Define note types for the dropdown
        note_types = [
            ('general', 'General'),
            ('usage', 'Usage'),
            ('semantic', 'Semantic'),
            ('etymology', 'Etymology'),
            ('cultural', 'Cultural'),
            ('anthropology', 'Anthropology'),
            ('discourse', 'Discourse'),
            ('phonology', 'Phonology'),
            ('sociolinguistics', 'Sociolinguistics'),
            ('bibliography', 'Bibliography')
        ]
            
        # Ensure ranges is JSON-serializable for template JS (tests may mock service returning Mock)
        import json as _json
        try:
            _json.dumps(ranges)
            ranges_for_template = ranges
        except Exception:
            logger.warning("Non-serializable ranges object returned by DictionaryService.get_lift_ranges; using empty dict for template")
            ranges_for_template = {}

        return render_template("entry_form.html",
                              entry=entry,
                              ranges=ranges_for_template,
                              variant_relations=[],
                              component_relations=[],
                              project_languages=languages,
                              available_languages=available_languages,
                              note_types=note_types,
                              configured_languages_codes=configured_languages_codes,
                              project_id=project_id,
                              current_user_id=g.current_user.id if hasattr(g, 'current_user') and g.current_user else None)

    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Error adding entry: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        if request.method == "POST":
            return jsonify({"error": str(e)}), 500

        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("main.entries"))


@main_bp.route("/search")
def search():
    """
    Render the search page.
    """
    query = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    entries = []
    total = 0

    semantic = request.args.get("semantic", "0") in ("1", "true", "True")

    if query:
        try:
            dict_service = current_app.injector.get(DictionaryService)
            offset = (page - 1) * per_page
            entries, total = dict_service.search_entries(
                query=query, limit=per_page, offset=offset, semantic=semantic
            )
        except Exception as e:
            logger.error(f"Error searching entries: {e}", exc_info=True)
            flash(f"Error searching entries: {str(e)}", "danger")

    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    has_prev = page > 1
    has_next = page < total_pages

    return render_template(
        "search.html",
        query=query,
        entries=entries,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
    )


@main_bp.route("/import/lift", methods=["GET", "POST"])
def import_lift():
    """
    Render the LIFT import page and handle LIFT file uploads.
    Supports uploading both LIFT file and optional ranges file.
    """
    if request.method == "POST":
        # Check if a LIFT file was uploaded
        if "lift_file" not in request.files:
            flash("No LIFT file selected", "danger")
            return redirect(request.url)

        lift_file = request.files["lift_file"]

        # Check if LIFT file is empty
        if lift_file.filename == "":
            flash("No LIFT file selected", "danger")
            return redirect(request.url)

        # Check LIFT file extension
        if not lift_file.filename.lower().endswith(".lift"):
            flash("Invalid file type. Please upload a .lift file.", "danger")
            return redirect(request.url)

        # Handle optional ranges file
        ranges_file = None
        ranges_temp_path = None
        if "ranges_file" in request.files and request.files["ranges_file"].filename:
            ranges_file = request.files["ranges_file"]
            if not ranges_file.filename.lower().endswith(".lift-ranges"):
                flash("Invalid ranges file type. Please upload a .lift-ranges file or leave empty.", "warning")
                ranges_file = None

        # Handle optional list.xml file (FieldWorks abbreviation data)
        list_file = None
        list_temp_path = None
        if "list_xml_file" in request.files and request.files["list_xml_file"].filename:
            list_file = request.files["list_xml_file"]

        try:
            # Save the LIFT file temporarily
            lift_filepath = os.path.join(current_app.instance_path, "uploads", lift_file.filename)
            os.makedirs(os.path.dirname(lift_filepath), exist_ok=True)
            lift_file.save(lift_filepath)

            # Save the ranges file temporarily if provided
            if ranges_file:
                ranges_temp_path = os.path.join(current_app.instance_path, "uploads", ranges_file.filename)
                ranges_file.save(ranges_temp_path)

            # Save the list.xml file temporarily if provided
            if list_file:
                list_temp_path = os.path.join(current_app.instance_path, "uploads", list_file.filename)
                list_file.save(list_temp_path)

            # Get dictionary service
            dict_service = current_app.injector.get(DictionaryService)

            # Determine import mode based on checkbox
            overwrite_existing = request.form.get('overwrite_existing') == 'on'
            mode = 'replace' if overwrite_existing else 'merge'

            # Import the LIFT file with optional ranges file
            entry_count = dict_service.import_lift(lift_filepath, mode=mode, ranges_path=ranges_temp_path)

            # If list.xml was provided, import it to get real abbreviations
            if list_temp_path:
                try:
                    from app.services.ranges_service import RangesService
                    ranges_service = current_app.injector.get(RangesService)
                    result = ranges_service.import_list_xml(list_temp_path)
                    if result["ranges_imported"] > 0:
                        flash(
                            f"Imported {result['ranges_imported']} ranges from list.xml "
                            f"({result['values_imported']} values with real abbreviations).",
                            "success",
                        )
                except Exception as list_e:
                    logger.warning("Error importing list.xml: %s", list_e)
                    flash(
                        f"Warning: Could not import list.xml: {list_e}",
                        "warning",
                    )

            flash(
                f"Successfully imported {entry_count} entries from LIFT file.",
                "success",
            )
            return redirect(url_for("main.entries"))

        except Exception as e:
            logger.error(f"Error importing LIFT file: {e}")
            flash(f"Error importing LIFT file: {str(e)}", "danger")
            return redirect(request.url)

        finally:
            # Clean up temporary files
            try:
                if os.path.exists(lift_filepath):
                    os.unlink(lift_filepath)
                if ranges_temp_path and os.path.exists(ranges_temp_path):
                    os.unlink(ranges_temp_path)
                if list_temp_path and os.path.exists(list_temp_path):
                    os.unlink(list_temp_path)
            except Exception:
                pass

    return render_template("import_lift.html")


@main_bp.route("/import/list-xml")
def import_list_xml():
    """Standalone page for importing FieldWorks list.xml abbreviations."""
    return render_template("import_list_xml.html")


# -- Shoebox / SFM import --------------------------------------------------


LIFT_ELEMENT_OPTIONS = [
    # Entry-level
    "lexeme", "citation",
    "entry_note", "entry_trait", "entry_field",
    # Pronunciation
    "pronunciation_form", "pronunciation_media",
    # Sense-level
    "gloss", "definition", "grammatical_info",
    "sense_note", "sense_trait", "sense_field",
    "sense_relation", "reversal", "illustration",
    # Example-level
    "example_form", "example_translation", "example_note",
    # Variant
    "variant_form", "variant_note", "variant_trait", "variant_field",
    # Etymology
    "etymology_form", "etymology_gloss",
    # General
    "annotation",
]

FIELD_TYPE_OPTIONS = [
    "normal", "cross-ref-source", "cross-ref-target",
    "variant-target", "variant-type",
]


@main_bp.route("/import/shoebox", methods=["GET", "POST"])
def import_shoebox():
    """Two-step SFM import: upload → preview markers → map → import."""
    from app.services.sfm_parser import SFMParser, _parse_marker_line
    from collections import Counter

    if request.method == "POST":
        if "sfm_file" not in request.files:
            flash("No SFM file selected", "danger")
            return redirect(request.url)

        sfm_file = request.files["sfm_file"]
        if sfm_file.filename == "":
            flash("No SFM file selected", "danger")
            return redirect(request.url)

        try:
            text = sfm_file.read().decode("utf-8", errors="replace")
        except Exception as e:
            flash(f"Could not read file: {e}", "danger")
            return redirect(request.url)

        # Auto-detect markers and collect stats
        parser = SFMParser.auto_detect(text)
        doc = parser.parse(text)

        # Build marker stats: frequency, sample values, suggested mapping
        marker_values: dict[str, list[str]] = {}
        marker_counts: Counter = Counter()
        for entry in doc.entries[:100]:
            for f in entry.fields:
                marker_counts[f.marker] += 1
                if f.marker not in marker_values:
                    marker_values[f.marker] = []
                if len(marker_values[f.marker]) < 5:
                    marker_values[f.marker].append(f.value[:60])
            for sense in entry.senses:
                for f in sense.fields:
                    marker_counts[f.marker] += 1
                    if f.marker not in marker_values:
                        marker_values[f.marker] = []
                    if len(marker_values[f.marker]) < 5:
                        marker_values[f.marker].append(f.value[:60])
            for pron in entry.pronunciations:
                for f in pron.fields:
                    marker_counts[f.marker] += 1
                    if f.marker not in marker_values:
                        marker_values[f.marker] = []
                    if len(marker_values[f.marker]) < 5:
                        marker_values[f.marker].append(f.value[:60])

        from app.services.import_mapping_service import _guess_lift_element

        marker_stats = {}
        for marker in sorted(marker_counts):
            samples = marker_values.get(marker, [])
            marker_stats[marker] = {
                "count": marker_counts[marker],
                "samples": samples,
                "suggested_element": _guess_lift_element(marker, "entry"),
                "suggested_level": (
                    "entry" if marker in parser.entry_keys
                    else "sense" if marker in parser.sense_keys
                    else "example" if marker in parser.example_keys
                    else "pronunciation" if marker in parser.pronun_keys
                    else "variant" if marker in parser.variant_keys
                    else "entry"
                ),
                "suggested_key": marker in parser.entry_keys or marker in parser.sense_keys or marker in parser.variant_keys,
                "suggested_field_type": (
                    "cross-ref-source" if marker in parser.cross_ref_source
                    else "cross-ref-target" if marker in parser.cross_ref_target
                    else "variant-target" if marker in parser.variant_target
                    else "variant-type" if marker in parser.variant_type
                    else "normal"
                ),
                "suggested_lang": None,
            }

        # Build entry previews (first 10) — flatten all fields
        entry_previews = []
        for entry in doc.entries[:10]:
            preview = {}
            for f in entry.fields:
                preview[f.marker] = f.value[:60]
            for sense in entry.senses:
                for f in sense.fields:
                    preview[f.marker] = f.value[:60]
                for ex in sense.examples:
                    for f in ex.fields:
                        preview[f.marker] = f.value[:60]
            for pron in entry.pronunciations:
                for f in pron.fields:
                    preview[f.marker] = f.value[:60]
            # Sort by marker for consistent display
            preview = dict(sorted(preview.items()))
            entry_previews.append(preview)

        # Save text to temp file for the execute step
        import uuid, os
        import_key = str(uuid.uuid4())
        uploads_dir = os.path.join(
            current_app.instance_path, "uploads", "sfm_imports"
        )
        os.makedirs(uploads_dir, exist_ok=True)
        temp_path = os.path.join(uploads_dir, f"{import_key}.sfm")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(text)

        try:
            project_langs = get_project_languages()
        except Exception:
            project_langs = []

        return render_template(
            "import_shoebox_map.html",
            import_key=import_key,
            file_name=sfm_file.filename,
            entry_count=len(doc.entries),
            marker_stats=marker_stats,
            entry_previews=entry_previews,
            lift_element_options=LIFT_ELEMENT_OPTIONS,
            field_type_options=FIELD_TYPE_OPTIONS,
            project_languages=project_langs,
        )

    return render_template("import_shoebox.html")


@main_bp.route("/import/shoebox/execute", methods=["POST"])
def import_shoebox_execute():
    """Execute the SFM import with user-specified marker mapping."""
    from app.services.sfm_parser import SFMParser
    from app.services.import_converter import import_parsed_document

    import_key = request.form.get("import_key", "")
    if not import_key:
        flash("Missing import key.", "danger")
        return redirect(url_for("main.import_shoebox"))

    temp_path = os.path.join(
        current_app.instance_path, "uploads", "sfm_imports", f"{import_key}.sfm"
    )
    if not os.path.exists(temp_path):
        flash("Import session expired. Please upload the file again.", "danger")
        return redirect(url_for("main.import_shoebox"))

    try:
        with open(temp_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        flash(f"Could not read temp file: {e}", "danger")
        return redirect(url_for("main.import_shoebox"))
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass

    # Reconstruct field_map from form data
    field_map = {}
    key_markers: set[str] = set()

    for raw_marker, value in request.form.items():
        if raw_marker.startswith("el_"):
            m = raw_marker[3:]
            field_map.setdefault(m, {})["lift_element"] = value
        elif raw_marker.startswith("lv_"):
            m = raw_marker[3:]
            field_map.setdefault(m, {})["level"] = value
        elif raw_marker.startswith("lang_"):
            m = raw_marker[5:]
            field_map.setdefault(m, {})["lang"] = value or None
        elif raw_marker.startswith("ft_"):
            m = raw_marker[3:]
            field_map.setdefault(m, {})["field_type"] = value
        elif raw_marker.startswith("key_"):
            m = raw_marker[4:]
            if value == "1":
                key_markers.add(m)
                field_map.setdefault(m, {})["is_key"] = True
            else:
                field_map.setdefault(m, {})["is_key"] = False

    # Fill in defaults for any missing keys
    for marker in list(field_map.keys()):
        fm = field_map[marker]
        fm.setdefault("lift_element", "field")
        fm.setdefault("level", "entry")
        fm.setdefault("is_key", False)
        fm.setdefault("field_type", "normal")

    # Build parser from the user's mapping
    entry_keys = {m for m, c in field_map.items() if c["is_key"] and c["level"] == "entry"}
    sense_keys = {m for m, c in field_map.items() if c["is_key"] and c["level"] == "sense"}
    example_keys = {m for m, c in field_map.items() if c["is_key"] and c["level"] == "example"}
    pronun_keys = {m for m, c in field_map.items() if c["is_key"] and c["level"] == "pronunciation"}
    variant_keys = {m for m, c in field_map.items() if c["is_key"] and c["level"] == "variant"}
    cross_ref_source = {m for m, c in field_map.items() if c["field_type"] == "cross-ref-source"}
    cross_ref_target = {m for m, c in field_map.items() if c["field_type"] == "cross-ref-target"}
    variant_target = {m for m, c in field_map.items() if c["field_type"] == "variant-target"}
    variant_type = {m for m, c in field_map.items() if c["field_type"] == "variant-type"}
    example_field_keys = example_keys | {m for m, c in field_map.items() if c["level"] == "example"}

    mode = request.form.get("mode", "merge")

    try:
        variant_field_keys = variant_keys | {m for m, c in field_map.items() if c["level"] == "variant"}
        parser = SFMParser(
            entry_keys=entry_keys,
            sense_keys=sense_keys,
            example_keys=example_keys,
            pronun_keys=pronun_keys,
            variant_keys=variant_keys,
            pronun_field_keys=pronun_keys,
            example_field_keys=example_field_keys,
            variant_field_keys=variant_field_keys,
            cross_ref_source=cross_ref_source,
            cross_ref_target=cross_ref_target,
            variant_target=variant_target,
            variant_type=variant_type,
        )
        doc = parser.parse(text)

        dict_service = current_app.injector.get(DictionaryService)

        # Build user POS mapping from saved profile (if one was selected)
        user_pos_map: dict = {}
        mapping_id = request.form.get("mapping_id", type=int)
        if mapping_id:
            from app.services.import_mapping_service import ImportMappingService
            _msvc = ImportMappingService()
            _im = _msvc.get_by_id(mapping_id)
            if _im:
                user_pos_map = _msvc.to_pos_map_dict(_im)

        result = import_parsed_document(doc, field_map, {}, dict_service, mode=mode,
                                        user_pos_map=user_pos_map or None)

        # Optionally save the mapping
        save_name = request.form.get("save_mapping_name", "").strip()
        if save_name:
            from app.services.import_mapping_service import ImportMappingService
            mapping_svc = ImportMappingService()
            field_mappings_list = []
            for marker, cfg in field_map.items():
                field_mappings_list.append({
                    "field_marker": marker,
                    "lift_element": cfg["lift_element"],
                    "level": cfg["level"],
                    "lang": cfg.get("lang"),
                    "is_key": cfg.get("is_key", False),
                    "field_type": cfg.get("field_type", "normal"),
                })
            try:
                mapping_svc.create(
                    name=save_name,
                    file_type="sfm",
                    field_mappings=field_mappings_list,
                    owner_id=getattr(g, "user", None) and g.user.get("id"),
                )
                flash(f"Mapping saved as '{save_name}'.", "success")
            except Exception as e:
                logger.warning("Could not save mapping: %s", e)

        flash(
            f"Imported {result['imported']} entries from SFM file.",
            "success",
        )
        return redirect(url_for("main.entries"))

    except Exception as e:
        logger.error(f"Error importing SFM file: {e}")
        flash(f"Error importing SFM file: {str(e)}", "danger")
        return redirect(url_for("main.import_shoebox"))


# -- CSV import ------------------------------------------------------------


@main_bp.route("/import/csv", methods=["GET", "POST"])
def import_csv():
    """Import a CSV file using a column mapping."""
    from app.services.csv_parser import CSVParser
    from app.services.import_converter import import_csv_data
    from app.services.import_mapping_service import ImportMappingService

    mapping_svc = ImportMappingService()
    mappings = [m for m in mapping_svc.get_all() if m.file_type == "csv"]

    if request.method == "POST":
        if "csv_file" not in request.files:
            flash("No CSV file selected", "danger")
            return redirect(request.url)

        csv_file = request.files["csv_file"]
        if csv_file.filename == "":
            flash("No CSV file selected", "danger")
            return redirect(request.url)

        mapping_id = request.form.get("mapping_id", type=int)
        mode = request.form.get("mode", "merge")
        delim_raw = request.form.get("delimiter", ",")
        delimiter = "\t" if delim_raw == "\\t" else delim_raw

        mapping = mapping_svc.get_by_id(mapping_id) if mapping_id else None
        if mapping is None:
            flash("Please select a column mapping.", "danger")
            return redirect(request.url)

        try:
            text = csv_file.read().decode("utf-8", errors="replace")
            parser = CSVParser(delimiter=delimiter)
            data = parser.parse(text)
            field_map = mapping_svc.to_field_map_dict(mapping)
            lang_map = mapping_svc.to_language_map_dict(mapping)

            dict_service = current_app.injector.get(DictionaryService)
            result = import_csv_data(data, field_map, lang_map, dict_service, mode=mode)

            flash(
                f"Imported {result['imported']} entries from CSV file.",
                "success",
            )
            return redirect(url_for("main.entries"))

        except Exception as e:
            logger.error(f"Error importing CSV file: {e}")
            flash(f"Error importing CSV file: {str(e)}", "danger")
            return redirect(request.url)

    return render_template(
        "import_csv.html",
        mappings=mappings,
        selected_mapping_id=None,
    )


# -- Import mapping management ---------------------------------------------


@main_bp.route("/import/mappings")
def import_mappings():
    """List all saved import mappings."""
    from app.services.import_mapping_service import ImportMappingService
    mapping_svc = ImportMappingService()
    mappings = mapping_svc.get_all()
    return render_template("import_mappings.html", mappings=mappings)


@main_bp.route("/import/mappings/new", methods=["GET", "POST"])
def import_mapping_new():
    """Create a new import mapping."""
    from app.services.import_mapping_service import ImportMappingService
    mapping_svc = ImportMappingService()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "danger")
            return redirect(request.url)

        file_type = request.form.get("file_type", "sfm")
        description = request.form.get("description", "").strip() or None

        fm_markers = request.form.getlist("fm_marker[]")
        fm_elements = request.form.getlist("fm_element[]")
        fm_levels = request.form.getlist("fm_level[]")
        fm_langs = request.form.getlist("fm_lang[]")
        fm_keys = request.form.getlist("fm_key[]")
        fm_types = request.form.getlist("fm_type[]")

        field_mappings = []
        for i, marker in enumerate(fm_markers):
            marker = marker.strip()
            if not marker:
                continue
            field_mappings.append({
                "field_marker": marker,
                "lift_element": fm_elements[i].strip() if i < len(fm_elements) else "",
                "level": fm_levels[i].strip() if i < len(fm_levels) else "entry",
                "lang": fm_langs[i].strip() if i < len(fm_langs) and fm_langs[i].strip() else None,
                "is_key": True if fm_keys and fm_keys[i] == "1" else False,
                "field_type": fm_types[i].strip() if i < len(fm_types) else "normal",
            })

        lm_sources = request.form.getlist("lm_source[]")
        lm_targets = request.form.getlist("lm_target[]")
        language_mappings = []
        for i, src in enumerate(lm_sources):
            src = src.strip()
            tgt = lm_targets[i].strip() if i < len(lm_targets) else ""
            if src and tgt:
                language_mappings.append({
                    "source_lang": src,
                    "target_lang": tgt,
                })

        mapping = mapping_svc.create(
            name=name,
            file_type=file_type,
            description=description,
            field_mappings=field_mappings,
            language_mappings=language_mappings,
            owner_id=getattr(g, "user", None) and g.user.get("id"),
        )
        flash(f"Mapping '{mapping.name}' created.", "success")
        return redirect(url_for("main.import_mappings"))

    return render_template("import_mapping_form.html", title="New Import Mapping", mapping=None)


@main_bp.route("/import/mappings/<int:mapping_id>/edit", methods=["GET", "POST"])
def import_mapping_edit(mapping_id):
    """Edit an existing import mapping."""
    from app.services.import_mapping_service import ImportMappingService
    mapping_svc = ImportMappingService()
    mapping = mapping_svc.get_by_id(mapping_id)
    if mapping is None:
        flash("Mapping not found.", "danger")
        return redirect(url_for("main.import_mappings"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "danger")
            return redirect(request.url)

        file_type = request.form.get("file_type", "sfm")
        description = request.form.get("description", "").strip() or None

        fm_markers = request.form.getlist("fm_marker[]")
        fm_elements = request.form.getlist("fm_element[]")
        fm_levels = request.form.getlist("fm_level[]")
        fm_langs = request.form.getlist("fm_lang[]")
        fm_keys = request.form.getlist("fm_key[]")
        fm_types = request.form.getlist("fm_type[]")

        field_mappings = []
        for i, marker in enumerate(fm_markers):
            marker = marker.strip()
            if not marker:
                continue
            field_mappings.append({
                "field_marker": marker,
                "lift_element": fm_elements[i].strip() if i < len(fm_elements) else "",
                "level": fm_levels[i].strip() if i < len(fm_levels) else "entry",
                "lang": fm_langs[i].strip() if i < len(fm_langs) and fm_langs[i].strip() else None,
                "is_key": True if fm_keys and fm_keys[i] == "1" else False,
                "field_type": fm_types[i].strip() if i < len(fm_types) else "normal",
            })

        lm_sources = request.form.getlist("lm_source[]")
        lm_targets = request.form.getlist("lm_target[]")
        language_mappings = []
        for i, src in enumerate(lm_sources):
            src = src.strip()
            tgt = lm_targets[i].strip() if i < len(lm_targets) else ""
            if src and tgt:
                language_mappings.append({
                    "source_lang": src,
                    "target_lang": tgt,
                })

        mapping_svc.update(
            mapping_id=mapping.id,
            name=name,
            file_type=file_type,
            description=description,
            field_mappings=field_mappings,
            language_mappings=language_mappings,
        )
        flash(f"Mapping '{name}' updated.", "success")
        return redirect(url_for("main.import_mappings"))

    return render_template("import_mapping_form.html", title="Edit Import Mapping", mapping=mapping)


@main_bp.route("/import/mappings/<int:mapping_id>/delete", methods=["POST"])
def import_mapping_delete(mapping_id):
    """Delete an import mapping."""
    from app.services.import_mapping_service import ImportMappingService
    mapping_svc = ImportMappingService()
    if mapping_svc.delete(mapping_id):
        flash("Mapping deleted.", "success")
    else:
        flash("Mapping not found.", "danger")
    return redirect(url_for("main.import_mappings"))


# -- API: import mappings --------------------------------------------------


@main_bp.route("/api/import-mappings", methods=["GET"])
def api_import_mappings_list():
    """List all import mappings as JSON."""
    from app.services.import_mapping_service import ImportMappingService
    mapping_svc = ImportMappingService()
    return jsonify([m.to_dict() for m in mapping_svc.get_all()])


@main_bp.route("/api/import-mappings/<int:mapping_id>", methods=["GET"])
def api_import_mappings_get(mapping_id):
    """Get a single import mapping as JSON."""
    from app.services.import_mapping_service import ImportMappingService
    mapping_svc = ImportMappingService()
    mapping = mapping_svc.get_by_id(mapping_id)
    if mapping is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(mapping.to_dict())


@main_bp.route("/api/import-mappings/auto-detect", methods=["POST"])
def api_import_mappings_auto_detect():
    """Auto-detect markers from uploaded SFM text and create a mapping."""
    from app.services.import_mapping_service import ImportMappingService
    mapping_svc = ImportMappingService()

    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' in request body"}), 400

    name = data.get("name", "Auto-detected")
    try:
        mapping = mapping_svc.auto_detect_mapping_from_sfm(
            data["text"],
            name=name,
            owner_id=getattr(g, "user", None) and g.user.get("id"),
        )
        return jsonify(mapping.to_dict()), 201
    except Exception as e:
        logger.exception("Auto-detect error")
        return jsonify({"error": str(e)}), 500


# -- API: POS value mappings -----------------------------------------------


@main_bp.route("/api/import-mappings/<int:mapping_id>/pos-mappings", methods=["GET"])
def api_pos_mappings_list(mapping_id):
    """List all user-defined POS value mappings for a given ImportMapping."""
    from app.services.import_mapping_service import ImportMappingService
    svc = ImportMappingService()
    pms = svc.get_pos_mappings(mapping_id)
    return jsonify([pm.to_dict() for pm in pms])


@main_bp.route("/api/import-mappings/<int:mapping_id>/pos-mappings", methods=["POST"])
def api_pos_mappings_set(mapping_id):
    """Upsert a POS mapping row.

    Body: {source_value, target_value, note?}
    If a row with that source_value already exists it is updated in-place.
    """
    from app.services.import_mapping_service import ImportMappingService
    svc = ImportMappingService()
    data = request.get_json(silent=True) or {}
    source = (data.get("source_value") or "").strip()
    target = (data.get("target_value") or "").strip()
    if not source or not target:
        return jsonify({"error": "source_value and target_value are required"}), 400
    try:
        pm = svc.set_pos_mapping(mapping_id, source, target, note=data.get("note"))
        return jsonify(pm.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception("POS mapping upsert error")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/import-mappings/pos-mappings/<int:pos_mapping_id>", methods=["DELETE"])
def api_pos_mappings_delete(pos_mapping_id):
    """Delete a single POS mapping row by its own PK."""
    from app.services.import_mapping_service import ImportMappingService
    svc = ImportMappingService()
    if svc.delete_pos_mapping(pos_mapping_id):
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404


@main_bp.route("/api/import-mappings/<int:mapping_id>/pos-mappings/bulk", methods=["PUT"])
def api_pos_mappings_bulk(mapping_id):
    """Replace ALL POS mappings for a profile in one call.

    Body: {mappings: [{source_value, target_value, note?}, ...]}
    """
    from app.services.import_mapping_service import ImportMappingService
    svc = ImportMappingService()
    data = request.get_json(silent=True) or {}
    rows = data.get("mappings", [])
    try:
        svc.update(mapping_id=mapping_id, pos_mappings=rows)
        return jsonify({"success": True, "count": len(rows)})
    except Exception as e:
        logger.exception("POS mapping bulk update error")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/import-mappings/<int:mapping_id>/pos-mappings/detect", methods=["POST"])
def api_pos_mappings_detect(mapping_id):
    """Scan SFM text for \\ps values not yet in the user's POS mapping.

    Body: {text: "<sfm content>", pos_marker?: "ps"}
    Returns [{source_value, suggested, count}] sorted by count desc.
    """
    from app.services.import_mapping_service import ImportMappingService
    svc = ImportMappingService()
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    pos_marker = data.get("pos_marker", "ps")
    if not text:
        return jsonify({"error": "Missing 'text'"}), 400
    try:
        unmapped = svc.detect_unmapped_pos_values(mapping_id, text, pos_marker=pos_marker)
        return jsonify({"unmapped": unmapped, "count": len(unmapped)})
    except Exception as e:
        logger.exception("POS detect error")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/export/lift")
def export_lift():
    """
    Export the dictionary to a LIFT file.
    
    Always exports as dual files (main + ranges) in a ZIP archive.
    This ensures better data integrity and easier management of ranges.
    """
    try:
        from app.services.export_service import get_export_service
        service = get_export_service()
        return service.export_lift(dual_file=True, as_download=True)

    except Exception as e:
        logger.error(f"Error exporting LIFT file: {e}")
        flash(f"Error exporting LIFT file: {str(e)}", "danger")
        return redirect(url_for("main.index"))


@main_bp.route("/export/html")
def export_html():
    """
    Export the dictionary to HTML format with alphabetical navigation.
    """
    try:
        from app.services.export_service import get_export_service
        service = get_export_service()
        exports_dir = os.path.join(current_app.instance_path, "exports")

        title = request.args.get("title", "Dictionary")
        column_layout = request.args.get("column_layout", "single")
        if column_layout not in ("single", "two"):
            column_layout = "single"
        show_subentries = request.args.get("show_subentries", "true").lower() == "true"

        full_path, filename = service.export_html(
            output_path=exports_dir,
            title=title,
            column_layout=column_layout,
            show_subentries=show_subentries,
            return_path_only=False
        )

        flash(f"Dictionary exported to HTML format as {filename}", "success")
        return render_template(
            "export_download.html", export_type="html", files={"html": filename}
        )

    except Exception as e:
        logger.error(f"Error exporting to HTML format: {e}")
        flash(f"Error exporting to HTML format: {str(e)}", "danger")
        return redirect(url_for("main.export_options"))


@main_bp.route("/export/markdown")
def export_markdown():
    """
    Export the dictionary to Pandoc Markdown format (for PDF conversion).
    """
    try:
        from app.services.export_service import get_export_service
        service = get_export_service()
        exports_dir = os.path.join(current_app.instance_path, "exports")

        title = request.args.get("title", "Dictionary")
        profile_id = request.args.get("profile_id", type=int)

        full_path, filename, warnings = service.export_markdown(
            output_path=exports_dir,
            title=title,
            profile_id=profile_id,
            return_path_only=False
        )

        msg = f"Dictionary exported to Markdown as {filename}"
        if warnings:
            msg += f" ({len(warnings)} unmapped value{'s' if len(warnings) != 1 else ''})"
        flash(msg, "success")
        return render_template(
            "export_download.html",
            export_type="markdown",
            files={"markdown": filename},
            export_warnings=warnings,
        )

    except Exception as e:
        logger.error(f"Error exporting to Markdown format: {e}")
        flash(f"Error exporting to Markdown format: {str(e)}", "danger")
        return redirect(url_for("main.export_options"))


@main_bp.route("/export")
def export_options():
    """
    Show export options.
    """
    profiles = []
    from app.services.display_profile_service import DisplayProfileService
    from app.services.lift_element_registry import LIFTElementRegistry
    try:
        registry = LIFTElementRegistry()
        profile_svc = DisplayProfileService(registry=registry)
        profiles = profile_svc.list_profiles()
    except Exception as e:
        current_app.logger.warning("Could not load display profiles: %s", str(e), exc_info=True)
    return render_template("export_options.html", display_profiles=profiles)


@main_bp.route("/export/download/<path:filename>")
def download_export(filename):
    """
    Download an exported file.

    Args:
        filename: Name of the file to download.
    """
    try:
        from app.services.export_service import get_export_service
        service = get_export_service()
        return service.prepare_download_response(
            filename=filename,
            instance_path=current_app.instance_path,
            as_attachment=True
        )

    except FileNotFoundError:
        flash(f"File not found: {filename}", "danger")
        return redirect(url_for("main.export_options"))
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        flash(f"Error downloading file: {str(e)}", "danger")
        return redirect(url_for("main.export_options"))


@main_bp.route("/tools/bulk-edit")
@main_bp.route("/tools/batch-edit")  # Keep old route for backward compatibility
def batch_edit():
    """
    Redirect to the Workbench bulk operations interface.
    """
    return redirect(url_for("workbench.bulk_operations"))


@main_bp.route("/tools/validation")
def validation():
    """
    Redirect to the validation tool interface.
    """
    return redirect(url_for("main.validation_tool"))


@main_bp.route("/tools/pronunciation")
def pronunciation():
    """
    Render the pronunciation management dashboard.
    """
    return render_template("tools/pronunciation.html")


@main_bp.route("/settings")
def settings():
    """
    Render the settings page.
    """
    return redirect("/settings/")


@main_bp.route("/display-profiles")
def display_profiles():
    """
    Render the display profiles management page.
    """
    return render_template("display_profiles.html")


@main_bp.route("/ranges-editor")
def ranges_editor():
    """
    Render the LIFT ranges editor page.
    """
    return render_template("ranges_editor.html")


@main_bp.route('/setup', methods=['GET'])
def setup_wizard():
    """Render the initial setup wizard page."""
    return render_template('setup.html')


@main_bp.route("/activity-log")
def activity_log():
    """
    Render the activity log page with pagination and filtering.
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    # Filter parameters
    action_filter = request.args.get("action", "", type=str)
    search_query = request.args.get("search", "", type=str)
    date_from = request.args.get("date_from", "", type=str)
    date_to = request.args.get("date_to", "", type=str)
    
    try:
        dict_service = current_app.injector.get(DictionaryService)
        offset = (page - 1) * per_page
        
        # Get filtered activities
        activities, total_activities = dict_service.get_filtered_activities(
            limit=per_page, 
            offset=offset,
            action_filter=action_filter if action_filter else None,
            search_query=search_query if search_query else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None
        )
        
        total_pages = (total_activities + per_page - 1) // per_page if total_activities > 0 else 1
        
        return render_template(
            "activity_log.html",
            activities=activities,
            total_activities=total_activities,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            action_filter=action_filter,
            search_query=search_query,
            date_from=date_from,
            date_to=date_to
        )
    except Exception as e:
        logger.error(f"Error loading activity log: {e}")
        flash(f"Error loading activity log: {str(e)}", "danger")
        return redirect(url_for("main.index"))


@main_bp.route("/data-quality")
def data_quality_dashboard():
    """
    Render the data quality dashboard page.
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        metrics = dict_service.get_quality_metrics()
    except Exception as e:
        logger.error(f"Error loading quality metrics: {e}")
        metrics = None
        flash("Could not load quality metrics from database.", "warning")

    return render_template("data_quality_dashboard.html", metrics=metrics)


@main_bp.route("/discovery")
def relation_discovery():
    """
    Render the Relation Discovery dashboard page.
    """
    project_id = session.get('project_id')
    return render_template("discovery_dashboard.html", project_id=project_id)


@main_bp.route("/audio/<filename>")
def audio_file(filename):
    """
    Serve audio files.

    Args:
        filename: Name of the audio file.
    """
    return send_from_directory(
        os.path.join(current_app.instance_path, "audio"), filename
    )


# API endpoints for the frontend


@main_bp.route("/api/stats")
def api_stats():
    """
    Get dictionary statistics.
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        entry_count = dict_service.count_entries()
        sense_count, example_count = dict_service.count_senses_and_examples()

        return jsonify(
            {"entries": entry_count, "senses": sense_count, "examples": example_count}
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/system/status")
def api_system_status():
    """
    Get system status.
    """
    try:
        dict_service = current_app.injector.get(DictionaryService)
        return jsonify(dict_service.get_system_status())
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/activity")
def api_activity():
    """
    Get recent activity.
    """
    try:
        # Get limit parameter
        limit = request.args.get("limit", 5, type=int)

        dict_service = current_app.injector.get(DictionaryService)
        activities = dict_service.get_recent_activity(limit=limit)

        return jsonify({"activities": activities})
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/pronunciations/generate", methods=["POST"])
def api_generate_pronunciation():
    """
    Generate pronunciation audio.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        word = data.get("word")
        ipa = data.get("ipa")

        if not word:
            return jsonify({"error": "Word is required"}), 400

        # This would typically generate audio using TTS
        # For now, just return a placeholder

        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"pronunciation_{timestamp}.mp3"

        # Return the audio URL
        return jsonify({"audio_url": f"/audio/{filename}", "word": word, "ipa": ipa})
    except Exception as e:
        logger.error(f"Error generating pronunciation: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/test-search")
def test_search():
    """
    Test search functionality with a visual interface.
    """
    query = request.args.get("query", "")
    limit = request.args.get("limit", 10, type=int)
    offset = request.args.get("offset", 0, type=int)

    entries = []
    total = 0
    error = None

    if query:
        try:
            dict_service = current_app.injector.get(DictionaryService)
            result = dict_service.search_entries(query=query, limit=limit, offset=offset)
            try:
                entries, total = result
            except Exception:
                logger.warning("search_entries returned unexpected value (type=%s); coercing to ([],0)", type(result))
                entries, total = [], 0
        except Exception as e:
            logger.error(f"Error testing search: {e}", exc_info=True)
            error = str(e)

    return render_template(
        "test_search.html",
        query=query,
        entries=entries,
        total=total,
        limit=limit,
        offset=offset,
        error=error,
    )


@main_bp.route("/api/test-search")
def api_test_search():
    """
    Test search functionality.
    """
    try:
        query = request.args.get("query", "")
        limit = request.args.get("limit", 10, type=int)
        offset = request.args.get("offset", 0, type=int)

        if not query:
            return jsonify({"error": "No search query provided"}), 400

        dict_service = current_app.injector.get(DictionaryService)
        result = dict_service.search_entries(query=query, limit=limit, offset=offset)
        try:
            entries, total = result
        except Exception:
            logger.warning("api_test_search: search_entries returned unexpected value (type=%s); coercing to ([],0)", type(result))
            entries, total = [], 0

        # Convert entries to dictionaries for JSON response
        entry_dicts = []
        for entry in entries:
            try:
                entry_dicts.append(entry.to_dict())
            except Exception:
                logger.debug("api_test_search: skipping non-Entry object in results: %s", type(entry))
                continue

        return jsonify(
            {
                "entries": entry_dicts,
                "total": total,
                "query": query,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        logger.error(f"Error testing search: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# Workbench Routes
@workbench_bp.route("/query-builder")
def query_builder():
    """Render the dynamic query builder interface."""
    try:
        return render_template("workbench/query_builder.html")
    except Exception as e:
        logger.error(f"Error rendering query builder: {e}")
        return render_template(
            "error.html", error_message="Failed to load query builder"
        ), 500


@workbench_bp.route("/worksets")
def worksets():
    """Render the workset management interface."""
    try:
        return render_template("workbench/worksets.html")
    except Exception as e:
        logger.error(f"Error rendering worksets: {e}")
        return render_template(
            "error.html", error_message="Failed to load worksets"
        ), 500


@workbench_bp.route("/analytics")
def change_analytics():
    return render_template("workbench/change_analytics.html")

@workbench_bp.route("/worksets/<int:workset_id>/curation")
@workbench_bp.route("/worksets/<int:workset_id>/curate")
def workset_curate(workset_id: int):
    """Render the workset curation interface."""
    try:
        # Get workset info from database
        from flask import current_app
        with current_app.pg_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name, total_entries FROM worksets WHERE id = %s", (workset_id,))
                row = cur.fetchone()
                if not row:
                    return render_template("error.html", error_message="Workset not found"), 404
                workset_name = row[0]
                total_entries = row[1]

        return render_template(
            "workbench/workset_curation.html",
            workset_id=workset_id,
            workset_name=workset_name,
            total_entries=total_entries
        )
    except Exception as e:
        logger.error(f"Error rendering workset curation: {e}")
        return render_template(
            "error.html", error_message="Failed to load workset curation"
        ), 500


@workbench_bp.route("/bulk-operations")
def bulk_operations():
    """Render the bulk operations interface."""
    try:
        return render_template("workbench/bulk_operations.html")
    except Exception as e:
        logger.error(f"Error rendering bulk operations: {e}")
        return render_template(
            "error.html", error_message="Failed to load bulk operations"
        ), 500


@main_bp.route("/debug/ranges")
def debug_ranges():
    """Debug page for testing ranges loading."""
    return render_template("ranges_test.html")


@main_bp.route("/tools")
def tools():
    """Render the main tools page."""
    return render_template("tools.html")


@main_bp.route("/tools/clear-cache")
def clear_cache():
    """Clear the application cache."""
    try:
        cache = CacheService()
        if cache.is_available():
            cache.clear()
            flash("Cache cleared successfully.", "success")
        else:
            flash("Cache service is not available.", "warning")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        flash(f"Error clearing cache: {str(e)}", "danger")
    return redirect(url_for("main.tools"))


@main_bp.route("/help")
def help_page():
    """Render the comprehensive help page about LIFT and application features."""
    return render_template("help.html")


@main_bp.route("/api/live-preview", methods=["POST"])
def live_preview():
    """
    Generate a live preview of an entry from form data.
    
    Accepts form data, serializes it to LIFT XML, and returns CSS-rendered HTML.
    Used for live preview functionality in the entry form.
    """
    try:
        from app.services.css_mapping_service import CSSMappingService
        from app.services.display_profile_service import DisplayProfileService
        from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer
        
        logger.info("Live preview request received")
        
        # Get form data
        form_data = request.get_json()
        logger.info(f"Raw form data received: {form_data}")
        
        # Debug: Log the structure of form data
        if form_data:
            logger.info(f"Form data keys: {list(form_data.keys())}")
            if 'lexical_unit' in form_data:
                logger.info(f"Lexical unit: {form_data['lexical_unit']}")
            if 'senses' in form_data:
                logger.info(f"Number of senses: {len(form_data['senses']) if form_data['senses'] else 0}")
                if form_data['senses']:
                    # Senses dict uses __INDEX__ keys, not integer indices
                    first_sense = next(iter(form_data['senses'].values())) if isinstance(form_data['senses'], dict) else None
                    logger.info(f"First sense keys: {list(first_sense.keys()) if first_sense else 'None'}")
        
        if not form_data:
            logger.warning("No form data provided in live preview request")
            return jsonify({
                "success": False,
                "error": "No form data provided",
                "debug": {
                    "form_data": None,
                    "request_method": request.method,
                    "content_type": request.content_type,
                    "headers": dict(request.headers)
                }
            }), 400
            
        # Get services
        css_service = current_app.injector.get(CSSMappingService)
        profile_service = DisplayProfileService()
        
        # Get default profile or create one
        default_profile = profile_service.get_default_profile()
        if not default_profile:
            default_profile = profile_service.create_from_registry_default(
                name="Default Display Profile",
                description="Auto-created default profile"
            )
            profile_service.set_default_profile(default_profile.id)
        
        # Serialize form data to LIFT XML using the same serializer as the frontend
        # We'll use the LIFTToHTMLTransformer to generate XML from form data
        transformer = LIFTToHTMLTransformer()
        
        # Generate LIFT XML from form data
        # For now, we'll create a simple XML structure - this should be enhanced
        # to match the full LIFTXMLSerializer functionality
        try:
            entry_xml = transformer.generate_lift_xml_from_form_data(form_data)
            logger.info(f"Generated LIFT XML: {entry_xml[:500]}...")
            
            if not entry_xml:
                logger.error("Empty XML generated from form data")
                return jsonify({
                    "success": False,
                    "error": "Failed to generate LIFT XML from form data",
                    "debug": {
                        "form_data_keys": list(form_data.keys()) if form_data else None,
                        "form_data_sample": {k: v for k, v in list(form_data.items())[:5]} if form_data else None,
                        "lexical_unit": form_data.get('lexical_unit') if form_data else None
                    }
                }), 400
            
            # Debug: Log the generated XML
            logger.info(f"Generated XML length: {len(entry_xml)}")
            logger.info(f"Generated XML preview: {entry_xml[:500]}")
            
            # Check if XML contains expected elements
            if '<lexical-unit>' not in entry_xml:
                logger.error("Generated XML missing lexical-unit element")
            if '<form' not in entry_xml:
                logger.error("Generated XML missing form element")
        except Exception as e:
            logger.error(f"Error generating LIFT XML: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Error generating LIFT XML: {str(e)}",
                "debug": {
                    "form_data": form_data,
                    "error_type": type(e).__name__
                }
            }), 500
            
        # Render the entry with CSS using the EXACT same method as the regular preview
        logger.info("Rendering entry with CSS")
        try:
            # Get dict_service from the application context, same as static view
            dict_service = current_app.injector.get(DictionaryService) if hasattr(current_app, 'injector') else None
            logger.info(f"Using dict_service: {dict_service is not None}")
            
            logger.info("Calling css_service.render_entry...")
            logger.info(f"Input XML length: {len(entry_xml)}")
            
            # Check if input XML has the lexical unit
            if '<lexical-unit>' in entry_xml and '<form' in entry_xml:
                logger.info("Input XML contains lexical-unit with form")
            else:
                logger.error("Input XML missing lexical-unit or form - this is the root cause!")
            
            css_html = css_service.render_entry(
                entry_xml,
                profile=default_profile,
                dict_service=dict_service
            )
            logger.info(f"CSS rendering completed, length: {len(css_html) if css_html else 0}")
            logger.debug(f"Full CSS HTML: {css_html}")
            
            # Debug: Check if CSS HTML contains expected elements
            if css_html:
                # More robust presence checks: look for class names or generic identifiers
                if 'headword' in css_html or 'lexical-unit' in css_html:
                    logger.info("CSS HTML contains headword/lexical-unit")
                else:
                    logger.error("CSS HTML missing headword/lexical-unit elements")
                
                if 'class="sense"' in css_html or '<div class="sense"' in css_html or 'definition' in css_html:
                    logger.info("CSS HTML contains senses")
                else:
                    logger.error("CSS HTML missing sense elements")
            else:
                logger.error("CSS rendering returned empty HTML")
            
            # The CSS service should already handle the rendering properly
            # Don't manipulate the HTML - let the CSS service do its job
            if css_html:
                # Just return the HTML as-is from the CSS service
                # It should already be properly formatted
                pass
            
            logger.info("Live preview generated successfully")
            
            # Debug: Check final response and attempt one quick retry if headword is missing
            retry_attempted = False
            retry_success = False
            initial_html_snippet = (css_html[:500] if css_html else None)

            def _html_contains_headword(html: str) -> bool:
                """Robust detection for headword presence: look for class attributes
                containing 'headword' or 'lexical-unit' instead of naive substring
                matching which can be fooled by text like 'No headword'."""
                import re
                if not html:
                    return False
                # Match class="... headword ..." or class='... lexical-unit ...'
                class_pattern = re.compile(r"class\s*=\s*['\"][^'\"]*\b(headword|lexical-unit)\b[^'\"]*['\"]")
                if class_pattern.search(html):
                    return True
                # As a fallback, look for element names commonly used in CSS output
                if '<span class="headword' in html or '<span class="lexical-unit' in html:
                    return True
                return False

            if css_html:
                logger.info(f"Final HTML length: {len(css_html)}")
                if _html_contains_headword(css_html):
                    logger.info("Final response contains headword")
                    retry_success = True
                else:
                    logger.error("Final response missing headword - attempting one retry")
                    # Try one quick retry of the CSS renderer to reduce flakiness
                    try:
                        retry_attempted = True
                        import time
                        time.sleep(0.2)
                        css_html_retry = css_service.render_entry(
                            entry_xml,
                            profile=default_profile,
                            dict_service=dict_service,
                        )
                        logger.info(f"Retry CSS rendering completed, length: {len(css_html_retry) if css_html_retry else 0}")
                        logger.debug(f"Retry CSS HTML: {css_html_retry}")
                        if css_html_retry and _html_contains_headword(css_html_retry):
                            logger.info("Retry successful: headword found in retry HTML")
                            css_html = css_html_retry
                            retry_success = True
                        else:
                            logger.error("Retry did not produce headword")
                    except Exception as e:
                        logger.error(f"Exception during retry render: {e}", exc_info=True)

            return jsonify({
                "success": True,
                "html": css_html,
                "xml": entry_xml,  # Return XML for debugging
                "debug": {
                    "has_headword": '<span class="headword"' in css_html if css_html else False,
                    "has_lexical_unit": '<span class="lexical-unit"' in css_html if css_html else False,
                    "html_length": len(css_html) if css_html else 0,
                    "retry_attempted": retry_attempted,
                    "retry_success": retry_success,
                    "initial_html_snippet": initial_html_snippet
                }
            })
        except Exception as e:
            logger.error(f"Error rendering CSS: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"CSS rendering error: {str(e)}",
                "debug": {
                    "entry_xml": entry_xml[:500] if entry_xml else None,
                    "error_type": type(e).__name__
                }
            }), 500
        
    except Exception as e:
        logger.error(f"Error generating live preview: {e}", exc_info=True)
        return jsonify({
            "error": f"Failed to generate preview: {str(e)}",
            "details": str(e)
        }), 500
