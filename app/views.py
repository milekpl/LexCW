"""
Views for the Lexicographic Curation Workbench's frontend.
"""

import logging
import os
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
    send_from_directory,
    Response,
)

from app.services.dictionary_service import DictionaryService
from app.services.cache_service import CacheService
from app.models.entry import Entry
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data
from app.utils.language_utils import get_project_languages, get_language_choices_for_forms

# Create blueprints
main_bp = Blueprint("main", __name__)
workbench_bp = Blueprint("workbench", __name__, url_prefix="/workbench")
logger = logging.getLogger(__name__)


@main_bp.route("/corpus-management")
def corpus_management():
    """Render corpus management interface with async stats loading."""
    # Return page immediately with loading indicators
    # Stats will be loaded via AJAX
    postgres_status = {"connected": False, "error": None}
    corpus_stats = {
        "total_records": 0,
        "avg_source_length": "0.00",
        "avg_target_length": "0.00",
        "last_updated": "Loading...",
    }

    return render_template(
        "corpus_management.html",
        corpus_stats=corpus_stats,
        postgres_status=postgres_status,
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

    recent_activity = [
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "action": "Entry Created",
            "description": 'Added new entry "example"',
        },
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "action": "Entry Updated",
            "description": 'Updated entry "test"',
        },
    ]

    # Try to get cached dashboard data first
    cache = CacheService()
    cache_key = "dashboard_stats"
    if cache.is_available():
        cached_data = cache.get(cache_key)
        if cached_data:
            try:
                cached_stats = json.loads(cached_data)
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
            except (json.JSONDecodeError, KeyError) as e:
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
            cache.set(cache_key, json.dumps(cache_data, default=str), ttl=600)
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

    Args:
        entry_id: ID of the entry to view.
    """
    try:
        # Get dictionary service
        dict_service = current_app.injector.get(DictionaryService)

        # Get entry (use non-validating method to allow viewing invalid entries)
        entry = dict_service.get_entry_for_editing(entry_id)
        
        # Get component relations (main entries this is a subentry of)
        component_relations = entry.get_component_relations(dict_service)
        
        # Get subentries (reverse component relations)
        subentries = entry.get_subentries(dict_service)
        
        # Get CSS-rendered HTML for the entry using default profile
        from app.services.css_mapping_service import CSSMappingService
        from app.services.display_profile_service import DisplayProfileService
        
        css_service = CSSMappingService()
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
        
        # Render entry with CSS - need to get raw XML from database
        css_html = None
        try:
            # Query database for raw XML
            db_name = dict_service.db_connector.database
            has_ns = dict_service._detect_namespace_usage()
            query = dict_service._query_builder.build_entry_by_id_query(
                entry_id, db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)
            
            if entry_xml:
                css_html = css_service.render_entry(
                    entry_xml,
                    profile=default_profile,
                    dict_service=dict_service
                )
                
                # If show_subentries is enabled, append subentry HTML
                if default_profile.show_subentries and subentries:
                    subentry_html_parts = []
                    for subentry_info in subentries:
                        try:
                            # Get subentry XML
                            subentry_query = dict_service._query_builder.build_entry_by_id_query(
                                subentry_info['id'], db_name, has_ns
                            )
                            subentry_xml = dict_service.db_connector.execute_query(subentry_query)
                            
                            if subentry_xml:
                                subentry_rendered = css_service.render_entry(
                                    subentry_xml,
                                    profile=default_profile,
                                    dict_service=dict_service
                                )
                                # Wrap in subentry container with CSS class
                                subentry_html_parts.append(
                                    f'<div class="subentry" data-subentry-id="{subentry_info["id"]}">{subentry_rendered}</div>'
                                )
                        except Exception as e:
                            logger.warning(f"Error rendering subentry {subentry_info['id']}: {e}")
                    
                    # Append all subentries to main entry HTML
                    if subentry_html_parts:
                        css_html += '\n'.join(subentry_html_parts)
                        
        except Exception as e:
            logger.warning(f"Error rendering entry with CSS: {e}")

        return render_template("entry_view.html", entry=entry, css_html=css_html, 
                             component_relations=component_relations, subentries=subentries)

    except NotFoundError:
        flash(f"Entry with ID {entry_id} not found.", "danger")
        return redirect(url_for("main.entries"))

    except Exception as e:
        logger.error(f"Error viewing entry {entry_id}: {e}")
        flash(f"Error loading entry: {str(e)}", "danger")
        return redirect(url_for("main.entries"))


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
    """
    Render the entry edit page.
    
    Args:
        entry_id: ID of the entry to edit.
    """
    print(f"EDIT_ENTRY CALLED FOR {entry_id}")
    try:
        dict_service = current_app.injector.get(DictionaryService)
        print(f"Flask app database name: {dict_service.db_connector.database}")
        print(f"Environment TEST_DB_NAME: {os.environ.get('TEST_DB_NAME')}")
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

            # Get existing entry data for merging (use non-validating method for editing)
            existing_entry = None
            try:
                existing_entry = dict_service.get_entry_for_editing(entry_id)
            except NotFoundError:
                # Entry doesn't exist yet - will be created instead of updated
                pass
            
            existing_data = existing_entry.to_dict() if existing_entry else {}

            # Merge form data with existing entry data, processing multilingual notes
            merged_data = merge_form_data_with_entry_data(data, existing_data)

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
            
            # CRITICAL: Close DictionaryService's persistent connection during update
            # This allows XMLEntryService to get exclusive access to the database
            db_connector = dict_service.db_connector
            was_connected = db_connector.is_connected()
            if was_connected:
                try:
                    db_connector.disconnect()
                    logger.info(f"[EDIT_ENTRY] Disconnected DictionaryService connection before XMLEntryService update")
                except Exception as e:
                    logger.warning(f"[EDIT_ENTRY] Failed to disconnect: {e}")
            
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
                # CRITICAL: Reconnect DictionaryService after update
                if was_connected:
                    try:
                        db_connector.connect()
                        logger.info(f"[EDIT_ENTRY] Reconnected DictionaryService connection after update")
                    except Exception as e:
                        logger.error(f"[EDIT_ENTRY] Failed to reconnect DictionaryService: {e}", exc_info=True)


        # Try to load the entry for editing
        entry = None
        try:
            entry = dict_service.get_entry_for_editing(
                entry_id
            )  # Use non-validating method for editing
        except NotFoundError:
            # Entry doesn't exist yet - create a new empty entry with the given ID
            entry = Entry(id_=entry_id)

        # Apply POS inheritance when loading entry for editing
        if entry:
            entry._apply_pos_inheritance()

        ranges = dict_service.get_lift_ranges()

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
            variant_relations_data = entry.get_complete_variant_relations(dict_service)
            # Extract enriched component_relations for template (with display text for main entries)
            component_relations_data = entry.get_component_relations(dict_service)
            # Extract forward component relations (where this entry HAS components)
            forward_component_relations_data = entry.get_forward_component_relations(dict_service)
            # Extract subentries (reverse component relations)
            subentries_data = entry.get_subentries(dict_service)
            
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
            
            css_service = CSSMappingService()
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
            
            # Render entry with CSS - need to get raw XML from database
            # Query database for raw XML
            db_name = dict_service.db_connector.database
            has_ns = dict_service._detect_namespace_usage()
            query = dict_service._query_builder.build_entry_by_id_query(
                entry_id, db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)
            
            if entry_xml:
                css_html = css_service.render_entry(
                    entry_xml,
                    profile=default_profile,
                    dict_service=dict_service
                )
                
                # If show_subentries is enabled, append subentry HTML
                if default_profile.show_subentries and subentries_data:
                    subentry_html_parts = []
                    for subentry_info in subentries_data:
                        try:
                            # Get subentry XML
                            subentry_query = dict_service._query_builder.build_entry_by_id_query(
                                subentry_info['id'], db_name, has_ns
                            )
                            subentry_xml = dict_service.db_connector.execute_query(subentry_query)
                            
                            if subentry_xml:
                                subentry_rendered = css_service.render_entry(
                                    subentry_xml,
                                    profile=default_profile,
                                    dict_service=dict_service
                                )
                                # Wrap in subentry container with CSS class
                                subentry_html_parts.append(
                                    f'<div class="subentry" data-subentry-id="{subentry_info["id"]}">{subentry_rendered}</div>'
                                )
                        except Exception as e:
                            logger.warning(f"Error rendering subentry {subentry_info['id']}: {e}")
                    
                    # Append all subentries to main entry HTML
                    if subentry_html_parts:
                        css_html += '\n'.join(subentry_html_parts)
                        
        except Exception as e:
            logger.warning(f"Error rendering entry with CSS: {e}")
            
        return render_template(
            "entry_form.html",
            entry=entry,
            ranges=ranges,
            variant_relations=variant_relations_data,
            component_relations=component_relations_data,
            forward_component_relations=forward_component_relations_data,
            subentries=subentries_data,
            validation_result=validation_result,
            project_languages=languages,
            available_languages=available_languages,
            note_types=note_types,
            css_html=css_html,
        )
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
            entry_id = dict_service.create_entry(entry)

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
        ranges = dict_service.get_lift_ranges()

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
            
        return render_template("entry_form.html", 
                              entry=entry, 
                              ranges=ranges, 
                              variant_relations=[],
                              component_relations=[],
                              project_languages=languages,
                              available_languages=available_languages,
                              note_types=note_types,
                              configured_languages_codes=configured_languages_codes)

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

    if query:
        try:
            dict_service = current_app.injector.get(DictionaryService)
            offset = (page - 1) * per_page
            entries, total = dict_service.search_entries(
                query=query, limit=per_page, offset=offset
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

        try:
            # Save the LIFT file temporarily
            lift_filepath = os.path.join(current_app.instance_path, "uploads", lift_file.filename)
            os.makedirs(os.path.dirname(lift_filepath), exist_ok=True)
            lift_file.save(lift_filepath)

            # Save the ranges file temporarily if provided
            if ranges_file:
                ranges_temp_path = os.path.join(current_app.instance_path, "uploads", ranges_file.filename)
                ranges_file.save(ranges_temp_path)

            # Get dictionary service
            dict_service = current_app.injector.get(DictionaryService)

            # Import the LIFT file with optional ranges file
            entry_count = dict_service.import_lift(lift_filepath, ranges_path=ranges_temp_path)

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
            except Exception:
                pass

    return render_template("import_lift.html")


@main_bp.route("/export/lift")
def export_lift():
    """
    Export the dictionary to a LIFT file.
    
    Always exports as dual files (main + ranges) in a ZIP archive.
    This ensures better data integrity and easier management of ranges.
    """
    try:
        # Get dictionary service
        dict_service = current_app.injector.get(DictionaryService)

        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_filename = f"dictionary_export_{timestamp}"
        
        # Always export as dual files for better data integrity
        return _export_dual_file_lift_ui(dict_service, base_filename)

    except Exception as e:
        logger.error(f"Error exporting LIFT file: {e}")
        flash(f"Error exporting LIFT file: {str(e)}", "danger")
        return redirect(url_for("main.index"))


# [Removed _export_single_file_lift_ui - no longer needed as we always use dual-file export]


def _export_dual_file_lift_ui(dict_service, base_filename):
    """Export LIFT as dual files (main + ranges) in a ZIP archive for UI."""
    import zipfile
    import io
    
    # Generate filenames
    lift_filename = f"{base_filename}.lift"
    ranges_filename = f"{base_filename}.lift-ranges"
    zip_filename = f"{base_filename}.zip"
    
    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()
    
    try:
        # Export main LIFT file with range references
        lift_content = dict_service.export_lift(dual_file=True)
        
        # Export ranges file
        ranges_content = dict_service.export_lift_ranges()
        
        # Create ZIP archive with both files
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add main LIFT file
            zipf.writestr(lift_filename, lift_content)
            
            # Add ranges file
            zipf.writestr(ranges_filename, ranges_content)
        
        # Return ZIP file as download
        return Response(
            zip_buffer.getvalue(),
            content_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{zip_filename}"'
            }
        )
        
    except Exception as e:
        # If any error occurs, log it and re-raise
        logger.error(f"Error in dual-file export: {e}")
        raise


@main_bp.route("/export/kindle")
def export_kindle():
    """
    Export the dictionary for Kindle.
    """
    try:
        # Get dictionary service
        dict_service = current_app.injector.get(DictionaryService)

        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(current_app.instance_path, "exports")
        os.makedirs(exports_dir, exist_ok=True)

        # Generate directory name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"kindle_export_{timestamp}"

        # Get Kindle export options from form or use defaults
        title = request.args.get("title", "Dictionary")
        source_lang = request.args.get("source_lang", "en")
        target_lang = request.args.get("target_lang", "pl")
        author = request.args.get("author", "Lexicographic Curation Workbench")

        # Get kindlegen path from config if available
        kindlegen_path = current_app.config.get("KINDLEGEN_PATH")

        # Export to Kindle format
        output_path = os.path.join(exports_dir, dir_name)
        output_dir = dict_service.export_to_kindle(
            output_path,
            title=title,
            source_lang=source_lang,
            target_lang=target_lang,
            author=author,
            kindlegen_path=kindlegen_path,
        )

        # Check if MOBI file was created
        mobi_path = os.path.join(output_dir, "dictionary.mobi")
        mobi_created = os.path.exists(mobi_path)

        flash(f"Dictionary exported to Kindle format in {dir_name}", "success")

        # Return the download page for the exported files
        return render_template(
            "export_download.html",
            export_type="kindle",
            directory=dir_name,
            files={
                "opf": "dictionary.opf",
                "html": "dictionary.html",
                "mobi": "dictionary.mobi" if mobi_created else None,
            },
        )

    except Exception as e:
        logger.error(f"Error exporting to Kindle format: {e}")
        flash(f"Error exporting to Kindle format: {str(e)}", "danger")
        return redirect(url_for("main.export_options"))


@main_bp.route("/export/sqlite")
def export_sqlite():
    """
    Export the dictionary to SQLite for mobile apps.
    """
    try:
        # Get dictionary service
        dict_service = current_app.injector.get(DictionaryService)

        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(current_app.instance_path, "exports")
        os.makedirs(exports_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dictionary_export_{timestamp}.db"

        # Get SQLite export options from form or use defaults
        source_lang = request.args.get("source_lang", "en")
        target_lang = request.args.get("target_lang", "pl")

        # Export to SQLite
        output_path = os.path.join(exports_dir, filename)
        dict_service.export_to_sqlite(
            output_path,
            source_lang=source_lang,
            target_lang=target_lang,
            batch_size=500,
        )

        flash(f"Dictionary exported to SQLite format as {filename}", "success")

        # Return the download page for the exported file
        return render_template(
            "export_download.html", export_type="sqlite", files={"sqlite": filename}
        )

    except Exception as e:
        logger.error(f"Error exporting to SQLite format: {e}")
        flash(f"Error exporting to SQLite format: {str(e)}", "danger")
        return redirect(url_for("main.export_options"))


@main_bp.route("/export")
def export_options():
    """
    Show export options.
    """
    return render_template("export_options.html")


@main_bp.route("/export/download/<path:filename>")
def download_export(filename):
    """
    Download an exported file.

    Args:
        filename: Name of the file to download.
    """
    try:
        # Get the directory and filename
        if "/" in filename:
            directory, filename = filename.split("/", 1)
        else:
            directory = None

        # Construct the path
        if directory:
            file_path = os.path.join(
                current_app.instance_path, "exports", directory, filename
            )
        else:
            file_path = os.path.join(current_app.instance_path, "exports", filename)

        # Check if file exists
        if not os.path.isfile(file_path):
            flash(f"File not found: {filename}", "danger")
            return redirect(url_for("main.export_options"))

        # Determine MIME type based on file extension
        mime_type = "application/octet-stream"  # Default
        if filename.endswith(".lift"):
            mime_type = "application/xml"
        elif filename.endswith(".db"):
            mime_type = "application/x-sqlite3"
        elif filename.endswith(".mobi"):
            mime_type = "application/x-mobipocket-ebook"
        elif filename.endswith(".opf"):
            mime_type = "application/oebps-package+xml"
        elif filename.endswith(".html"):
            mime_type = "text/html"

        # Send file
        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            mimetype=mime_type,
            as_attachment=True,
        )

    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        flash(f"Error downloading file: {str(e)}", "danger")
        return redirect(url_for("main.export_options"))


@main_bp.route("/tools/batch-edit")
def batch_edit():
    """
    Render the batch edit page.
    """
    # To be implemented
    flash("Batch editing is not yet implemented.", "info")
    return redirect(url_for("main.index"))


@main_bp.route("/tools/validation")
def validation():
    """
    Render the validation page.
    """
    # To be implemented
    flash("Validation is not yet implemented.", "info")
    return redirect(url_for("main.index"))


@main_bp.route("/tools/pronunciation")
def pronunciation():
    """
    Render the pronunciation management page.
    """
    # To be implemented
    flash("Pronunciation management is not yet implemented.", "info")
    return redirect(url_for("main.index"))


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
    Render the activity log page with pagination.
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    try:
        dict_service = current_app.injector.get(DictionaryService)
        offset = (page - 1) * per_page
        
        activities = dict_service.get_recent_activity(limit=per_page, offset=offset)
        total_activities = dict_service.get_activity_count()
        
        total_pages = (total_activities + per_page - 1) // per_page if total_activities > 0 else 1
        
        return render_template(
            "activity_log.html",
            activities=activities,
            total_activities=total_activities,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error loading activity log: {e}")
        flash(f"Error loading activity log: {str(e)}", "danger")
        return redirect(url_for("main.index"))


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
            entries, total = dict_service.search_entries(
                query=query, limit=limit, offset=offset
            )
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
        entries, total = dict_service.search_entries(
            query=query, limit=limit, offset=offset
        )

        # Convert entries to dictionaries for JSON response
        entry_dicts = [entry.to_dict() for entry in entries]

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
                    logger.info(f"First sense keys: {list(form_data['senses'][0].keys()) if form_data['senses'] else 'None'}")
        
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
        css_service = CSSMappingService()
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
            
            # Debug: Check if CSS HTML contains expected elements
            if css_html:
                if '<span class="headword"' in css_html or '<span class="lexical-unit"' in css_html:
                    logger.info("CSS HTML contains headword/lexical-unit")
                else:
                    logger.error("CSS HTML missing headword/lexical-unit elements")
                
                if '<div class="sense"' in css_html:
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
            
            # Debug: Check final response
            if css_html:
                logger.info(f"Final HTML length: {len(css_html)}")
                if '<span class="headword"' in css_html or '<span class="lexical-unit"' in css_html:
                    logger.info("Final response contains headword")
                else:
                    logger.error("Final response missing headword - this is the issue!")
            
            return jsonify({
                "success": True,
                "html": css_html,
                "xml": entry_xml,  # Return XML for debugging
                "debug": {
                    "has_headword": '<span class="headword"' in css_html if css_html else False,
                    "has_lexical_unit": '<span class="lexical-unit"' in css_html if css_html else False,
                    "html_length": len(css_html) if css_html else 0
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
