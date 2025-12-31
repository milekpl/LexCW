"""Display profile management API endpoints.

Provides REST API for CRUD operations on display profiles.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request, current_app
from typing import Dict, Any

from app.services.display_profile_service import DisplayProfileService
from app.services.lift_element_registry import LIFTElementRegistry
from app.utils.api_response_handler import api_response_handler, get_service

profiles_bp = Blueprint("display_profiles", __name__, url_prefix="/api/profiles")

# Create singleton instances
_service: DisplayProfileService | None = None
_registry: LIFTElementRegistry | None = None


def get_service() -> DisplayProfileService:
    """Get or create the singleton service instance."""
    global _service, _registry
    if _service is None:
        if _registry is None:
            _registry = LIFTElementRegistry()
        _service = DisplayProfileService(_registry)
    return _service


@profiles_bp.route("", methods=["GET"])
def list_profiles():
    """
    List all display profiles
    ---
    tags:
      - Display Profiles
    parameters:
      - name: include_system
        in: query
        schema:
          type: boolean
          default: true
      - name: only_user
        in: query
        schema:
          type: boolean
          default: false
    responses:
      200:
        description: List of display profiles
        content:
          application/json:
            schema:
              type: object
              properties:
                profiles:
                  type: array
                  items:
                    type: object
                count:
                  type: integer
    """
    include_system = request.args.get('include_system', 'true').lower() == 'true'
    only_user = request.args.get('only_user', 'false').lower() == 'true'
    
    service = get_service()
    profiles = service.list_profiles(
        include_system=include_system,
        only_user_profiles=only_user
    )
    
    return jsonify({
        "profiles": [p.to_dict() for p in profiles],
        "count": len(profiles)
    })


@profiles_bp.route("/<int:profile_id>", methods=["GET"])
def get_profile(profile_id: int):
    """
    Get a specific display profile
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Profile details
      404:
        description: Profile not found
    """
    service = get_service()
    profile = service.get_profile(profile_id)
    
    if not profile:
        return jsonify({"error": f"Profile with ID {profile_id} not found"}), 404
    
    return jsonify(profile.to_dict())


@profiles_bp.route("/default", methods=["GET"])
def get_default_profile():
    """
    Get the default display profile
    ---
    tags:
      - Display Profiles
    responses:
      200:
        description: Default profile
      404:
        description: No default profile set
    """
    service = get_service()
    profile = service.get_default_profile()
    
    if not profile:
        return jsonify({"error": "No default profile configured"}), 404
    
    return jsonify(profile.to_dict())


@profiles_bp.route("", methods=["POST"])
def create_profile():
    """
    Create a new display profile
    ---
    tags:
      - Display Profiles
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - name
            properties:
              name:
                type: string
              description:
                type: string
              elements:
                type: array
                items:
                  type: object
              is_default:
                type: boolean
              is_system:
                type: boolean
    responses:
      201:
        description: Profile created successfully
      400:
        description: Invalid request data
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    if 'name' not in data:
        return jsonify({"error": "Profile name is required"}), 400
    
    try:
        service = get_service()
        profile = service.create_profile(
            name=data['name'],
            description=data.get('description'),
            custom_css=data.get('custom_css'),
            show_subentries=data.get('show_subentries', False),
            number_senses=data.get('number_senses', True),
            elements=data.get('elements', []),
            is_default=data.get('is_default', False),
            is_system=data.get('is_system', False)
        )
        
        return jsonify(profile.to_dict()), 201
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@profiles_bp.route("/<int:profile_id>", methods=["PUT", "PATCH"])
def update_profile(profile_id: int):
    """
    Update a display profile
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
              description:
                type: string
              elements:
                type: array
                items:
                  type: object
              is_default:
                type: boolean
    responses:
      200:
        description: Profile updated successfully
      400:
        description: Invalid request data
      404:
        description: Profile not found
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    try:
        service = get_service()
        profile = service.update_profile(
            profile_id=profile_id,
            name=data.get('name'),
            description=data.get('description'),
            custom_css=data.get('custom_css'),
            show_subentries=data.get('show_subentries'),
            number_senses=data.get('number_senses'),
            is_default=data.get('is_default'),
            elements=data.get('elements')
        )
        
        return jsonify(profile.to_dict())
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400 if "not found" not in str(e).lower() else 404
    except Exception as e:
        current_app.logger.error(f"Error updating profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@profiles_bp.route("/<int:profile_id>", methods=["DELETE"])
def delete_profile(profile_id: int):
    """
    Delete a display profile
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      204:
        description: Profile deleted successfully
      400:
        description: Cannot delete system profile
      404:
        description: Profile not found
    """
    try:
        service = get_service()
        service.delete_profile(profile_id)
        return '', 204
    
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        else:
            return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error deleting profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@profiles_bp.route("/<int:profile_id>/default", methods=["POST"])
@api_response_handler(handle_not_found=True)
def set_default_profile(profile_id: int):
    """
    Set a profile as the default
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Profile set as default
      404:
        description: Profile not found
    """
    service = get_service()
    profile = service.set_default_profile(profile_id)
    return profile.to_dict()


@profiles_bp.route("/create-default", methods=["POST"])
@api_response_handler(success_status=201)
def create_default_from_registry():
    """
    Create a profile from the registry's default configuration
    ---
    tags:
      - Display Profiles
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                default: "Default Profile"
    responses:
      201:
        description: Default profile created
      400:
        description: Invalid request
    """
    data = request.get_json() or {}
    name = data.get('name', 'Default Profile')

    service = get_service()
    profile = service.create_from_registry_default(name)
    return profile.to_dict()


@profiles_bp.route("/<int:profile_id>/export", methods=["GET"])
def export_profile(profile_id: int):
    """
    Export a profile as JSON
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Profile export data
      404:
        description: Profile not found
    """
    try:
        service = get_service()
        data = service.export_profile(profile_id)
        return jsonify(data)
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error exporting profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@profiles_bp.route("/import", methods=["POST"])
def import_profile():
    """
    Import a profile from JSON
    ---
    tags:
      - Display Profiles
    parameters:
      - name: overwrite
        in: query
        schema:
          type: boolean
          default: false
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - name
            properties:
              name:
                type: string
              description:
                type: string
              elements:
                type: array
              is_default:
                type: boolean
    responses:
      201:
        description: Profile imported successfully
      400:
        description: Invalid data or profile exists
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    overwrite = request.args.get('overwrite', 'false').lower() == 'true'
    
    try:
        service = get_service()
        profile = service.import_profile(data, overwrite=overwrite)
        return jsonify(profile.to_dict()), 201
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error importing profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@profiles_bp.route("/preview", methods=["POST"])
def preview_profile():
    """
    Preview a profile configuration with a sample entry
    ---
    tags:
      - Display Profiles
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              elements:
                type: array
              custom_css:
                type: string
              entry_id:
                type: string
                description: Optional specific entry ID to preview
    responses:
      200:
        description: Rendered HTML preview
      400:
        description: Invalid data
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    try:
        from app.services.css_mapping_service import CSSMappingService
        from app.services.dictionary_service import DictionaryService
        from app.models.display_profile import DisplayProfile, ProfileElement
        import hashlib
        import json

        # Generate cache key from profile configuration
        cache_data = {
            'elements': data.get('elements', []),
            'custom_css': data.get('custom_css', ''),
            'show_subentries': data.get('show_subentries', False),
            'number_senses': data.get('number_senses', True),
            'entry_id': data.get('entry_id', '')
        }
        cache_key = f"preview:{hashlib.sha256(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()}"

        cache_service = None
        # Try to get cached result
        try:
            cache_service = current_app.injector.get('cache_service')
            if hasattr(cache_service, 'get') and cache_service.is_available():
                cached_result = cache_service.get(cache_key)
                if cached_result:
                    current_app.logger.debug(f"Preview cache hit: {cache_key[:16]}...")
                    return jsonify(cached_result), 200
        except Exception as e:
            current_app.logger.debug(f"Preview cache unavailable: {e}")

        # Create a temporary profile object (not saved to database)
        temp_profile = DisplayProfile(
            id=0,
            name="Preview",
            description="Temporary preview profile",
            custom_css=data.get('custom_css', ''),
            show_subentries=data.get('show_subentries', False),
            number_senses=data.get('number_senses', True),
            is_default=False,
            is_system=False
        )

        # Add elements to temporary profile
        temp_profile.elements = []
        for elem_config in data.get('elements', []):
            elem = ProfileElement(
                profile_id=0,
                lift_element=elem_config.get('lift_element', ''),
                css_class=elem_config.get('css_class', ''),
                visibility=elem_config.get('visibility', 'if-content'),
                display_order=elem_config.get('display_order', 0),
                language_filter=elem_config.get('language_filter', '*'),
                prefix=elem_config.get('prefix', ''),
                suffix=elem_config.get('suffix', ''),
                config=elem_config.get('config')
            )
            temp_profile.elements.append(elem)

        # Get a sample entry or specified entry
        dict_service = current_app.injector.get(DictionaryService)
        entry_id = data.get('entry_id')

        if not entry_id:
            # Get a clean, simple entry (skip test entries)
            query = """
                for $entry in collection('dictionary')//entry
                where not(contains($entry/@id, 'test'))
                  and $entry/sense
                  and count($entry/sense) <= 3
                order by string-length(serialize($entry))
                return $entry
            """
            result = dict_service.db_connector.execute_query(query)

            # Take just the first entry from the result
            if result and '<entry' in result:
                # Extract first complete entry element
                import re
                match = re.search(r'<entry[^>]*>.*?</entry>', result, re.DOTALL)
                if match:
                    entry_xml = match.group(0)
                else:
                    entry_xml = result
            else:
                entry_xml = result
        else:
            # Get specific entry
            db_name = dict_service.db_connector.database
            has_ns = dict_service._detect_namespace_usage()
            query = dict_service._query_builder.build_entry_by_id_query(
                entry_id, db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)

        if not entry_xml or not entry_xml.strip():
            return jsonify({"error": "No entry found for preview"}), 404

        # Ensure entry_xml is wrapped in a root element if it's not already valid XML
        # BaseX might return just the entry element without a root wrapper
        if not entry_xml.strip().startswith('<?xml'):
            # Wrap in a temporary root to ensure valid XML parsing
            entry_xml = f'<root>{entry_xml}</root>'

        # Render with CSS mapping service
        css_service = CSSMappingService()
        html = css_service.render_entry(entry_xml, temp_profile, dict_service=dict_service)

        # Cache the result
        result_data = {"html": html}
        try:
            if cache_service is not None and cache_service.is_available():
                cache_service.set(cache_key, result_data, ttl=300)  # 5 minute TTL for preview
                current_app.logger.debug(f"Cached preview result: {cache_key[:16]}...")
        except Exception as e:
            current_app.logger.debug(f"Failed to cache preview: {e}")

        return jsonify(result_data), 200

    except Exception as e:
        current_app.logger.error(f"Error generating preview: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@profiles_bp.route("/validate-css", methods=["POST"])
def validate_css():
    """
    Validate custom CSS syntax before saving a profile
    ---
    tags:
      - Display Profiles
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              custom_css:
                type: string
                description: CSS code to validate
    responses:
      200:
        description: Validation result
        content:
          application/json:
            schema:
              type: object
              properties:
                valid:
                  type: boolean
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      message:
                        type: string
                      line:
                        type: integer
                warnings:
                  type: array
                  items:
                    type: object
      400:
        description: Invalid request
    """
    data = request.get_json(silent=True)

    if not data:
        # Empty request is valid (empty CSS)
        return jsonify({
            "valid": True,
            "errors": [],
            "warnings": []
        })

    custom_css = data.get('custom_css', '')

    # Empty CSS is valid (no custom styling)
    if not custom_css or not custom_css.strip():
        return jsonify({
            "valid": True,
            "errors": [],
            "warnings": []
        })

    errors = []
    warnings = []

    try:
        import re

        # Check for basic CSS syntax issues
        lines = custom_css.split('\n')

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('/*') or stripped.startswith('*'):
                continue

            # Check for unclosed braces
            open_braces = stripped.count('{')
            close_braces = stripped.count('}')

            if stripped.endswith('{') and close_braces == 0:
                pass  # Opening brace line - will be balanced later

            if stripped.count('{') > stripped.count('}') + 1:
                errors.append({
                    "message": "Too many opening braces",
                    "line": i
                })

            # Check for unclosed strings
            single_quotes = stripped.count("'") - stripped.count("\\'")
            double_quotes = stripped.count('"') - stripped.count('\\"')

            if single_quotes % 2 != 0:
                errors.append({
                    "message": "Unclosed single quote",
                    "line": i
                })
            if double_quotes % 2 != 0:
                errors.append({
                    "message": "Unclosed double quote",
                    "line": i
                })

            # Check for common typos
            if ':;' in stripped:
                warnings.append({
                    "message": "Suspicious ':;' pattern - possible typo",
                    "line": i
                })

            # Check for invalid property separators
            if re.search(r'[^:];', stripped):
                warnings.append({
                    "message": "Extra semicolon found - properties may not parse correctly",
                    "line": i
                })

        # Final brace balance check
        total_open = custom_css.count('{')
        total_close = custom_css.count('}')

        if total_open > total_close:
            errors.append({
                "message": f"Unclosed CSS block(s): {total_open - total_close} missing closing brace(s)",
                "line": len(lines)
            })
        elif total_close > total_open:
            errors.append({
                "message": f"Extra closing brace(s): {total_close - total_open} without matching opening",
                "line": len(lines)
            })

        # Try to use cssutils for more thorough validation if available
        try:
            import cssutils
            # Suppress cssutils logging
            cssutils.log.setLevel(logging.CRITICAL)

            sheet = cssutils.parseString(custom_css)

            for error in sheet.cssRules:
                if error.type == cssutils.css.CSSRule.STYLE_RULE:
                    # Valid rule
                    pass
                elif error.type == cssutils.css.CSSRule.IMPORT_RULE:
                    warnings.append({
                        "message": "@import rules may not work in all contexts",
                        "line": error.linenumber if hasattr(error, 'linenumber') else 0
                    })

        except Exception as e:
            # cssutils parsing failed - already caught by our basic checks
            pass

        return jsonify({
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        })

    except Exception as e:
        current_app.logger.error(f"Error validating CSS: {e}", exc_info=True)
        return jsonify({
            "valid": False,
            "errors": [{"message": f"Validation error: {str(e)}", "line": 0}],
            "warnings": []
        })
