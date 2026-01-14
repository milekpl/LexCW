"""Display profile management API endpoints.

Provides REST API for CRUD operations on display profiles.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app
from typing import Dict, Any

from app.services.display_profile_service import DisplayProfileService
from app.services.lift_element_registry import LIFTElementRegistry

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
    try:
        service = get_service()
        profile = service.set_default_profile(profile_id)
        return jsonify(profile.to_dict())
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error setting default profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@profiles_bp.route("/create-default", methods=["POST"])
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
    
    try:
        service = get_service()
        profile = service.create_from_registry_default(name)
        return jsonify(profile.to_dict()), 201
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating default profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


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
        
        return jsonify({"html": html}), 200
    
    except Exception as e:
        current_app.logger.error(f"Error generating preview: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
