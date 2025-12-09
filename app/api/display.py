from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app
from functools import wraps
from typing import Any, Dict

from app.services.display_profile_service import DisplayProfileService
from app.services.dictionary_service import DictionaryService

def require_authentication(f):
    """Decorator to require authentication for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if authentication is enabled in config
        auth_enabled = current_app.config.get('REQUIRE_API_AUTHENTICATION', False)

        if auth_enabled:
            # Check for API key in headers or query parameters
            api_key = request.headers.get('X-API-KEY') or request.args.get('api_key')

            if not api_key:
                return jsonify({"error": "Authentication required", "auth_required": True}), 401

            # In a real implementation, validate the API key against a database
            # For now, accept any non-empty API key
            if not api_key.strip():
                return jsonify({"error": "Invalid API key", "auth_required": True}), 401

        return f(*args, **kwargs)
    return decorated_function

display_bp = Blueprint("display", __name__, url_prefix="/api/display-profiles")

@display_bp.route("", methods=["POST"])
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
            properties:
              profile_name:
                type: string
                description: Name of the display profile
                example: "Default Dictionary View"
              view_type:
                type: string
                description: Type of view (root-based, list, etc.)
                example: "root-based"
              elements:
                type: array
                description: Array of element configurations
                items:
                  type: object
                  properties:
                    lift_element:
                      type: string
                      description: LIFT element name
                      example: "lexical-unit"
                    display_order:
                      type: integer
                      description: Display order priority
                      example: 1
                    css_class:
                      type: string
                      description: CSS class to apply
                      example: "headword"
    responses:
      201:
        description: Profile created successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                profile_id:
                  type: string
                  description: Unique identifier for the profile
                profile_name:
                  type: string
                  description: Name of the profile
                view_type:
                  type: string
                  description: Type of view
                elements:
                  type: array
                  description: Element configurations
      400:
        description: Invalid request data
    """
    service = DisplayProfileService()
    data = request.json
    profile = service.create_profile(
        name=data.get('name') or data.get('profile_name', 'Unnamed Profile'),
        description=data.get('description'),
        elements=data.get('elements', []),
        custom_css=data.get('custom_css'),
        show_subentries=data.get('show_subentries', False),
        number_senses=data.get('number_senses', True),
        number_senses_if_multiple=data.get('number_senses_if_multiple', False)
    )
    return jsonify(profile.to_dict()), 201

@display_bp.route("/<string:profile_id>", methods=["GET"])
def get_profile(profile_id: str):
    """
    Get a display profile by ID
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        description: Unique identifier of the display profile
        schema:
          type: string
          example: "abc123-def456"
    responses:
      200:
        description: Profile retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                profile_id:
                  type: string
                  description: Unique identifier for the profile
                profile_name:
                  type: string
                  description: Name of the profile
                view_type:
                  type: string
                  description: Type of view
                elements:
                  type: array
                  description: Element configurations
      404:
        description: Profile not found
    """
    service = DisplayProfileService()
    try:
        profile_id_int = int(profile_id)
    except ValueError:
        return jsonify({"error": "Invalid profile ID"}), 400
    
    profile = service.get_profile(profile_id_int)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile.to_dict())

@display_bp.route("", methods=["GET"])
def list_profiles():
    """
    List all display profiles
    ---
    tags:
      - Display Profiles
    responses:
      200:
        description: List of display profiles retrieved successfully
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  profile_id:
                    type: string
                    description: Unique identifier for the profile
                  profile_name:
                    type: string
                    description: Name of the profile
                  view_type:
                    type: string
                    description: Type of view
                  elements:
                    type: array
                    description: Element configurations
    """
    service = DisplayProfileService()
    profiles = service.list_profiles()
    return jsonify([p.to_dict() for p in profiles]), 200

@display_bp.route("/<string:profile_id>", methods=["PUT"])
@require_authentication
def update_profile(profile_id: str):
    """
    Update an existing display profile
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        description: Unique identifier of the display profile to update
        schema:
          type: string
          example: "abc123-def456"
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              profile_name:
                type: string
                description: Updated name of the display profile
                example: "Updated Dictionary View"
              elements:
                type: array
                description: Updated element configurations
                items:
                  type: object
                  properties:
                    lift_element:
                      type: string
                      description: LIFT element name
                      example: "lexical-unit"
                    display_order:
                      type: integer
                      description: Display order priority
                      example: 1
                    css_class:
                      type: string
                      description: CSS class to apply
                      example: "headword"
    responses:
      200:
        description: Profile updated successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                profile_id:
                  type: string
                  description: Unique identifier for the profile
                profile_name:
                  type: string
                  description: Updated name of the profile
                view_type:
                  type: string
                  description: Type of view
                elements:
                  type: array
                  description: Updated element configurations
      400:
        description: Invalid request data
      404:
        description: Profile not found
    """
    service = DisplayProfileService()
    try:
        profile_id_int = int(profile_id)
    except ValueError:
        return jsonify({"error": "Invalid profile ID"}), 400
    
    update_data = request.json

    # Validate required fields
    if not update_data:
        return jsonify({"error": "Request data is required"}), 400

    try:
        profile = service.update_profile(
            profile_id_int,
            name=update_data.get('name') or update_data.get('profile_name'),
            description=update_data.get('description'),
            elements=update_data.get('elements'),
            custom_css=update_data.get('custom_css'),
            show_subentries=update_data.get('show_subentries'),
            number_senses=update_data.get('number_senses'),
            number_senses_if_multiple=update_data.get('number_senses_if_multiple')
        )
    except ValueError as e:
        if "not found" in str(e):
            return jsonify({"error": "Profile not found"}), 404
        return jsonify({"error": str(e)}), 400

    return jsonify(profile.to_dict())

@display_bp.route("/<string:profile_id>", methods=["DELETE"])
@require_authentication
def delete_profile(profile_id: str):
    """
    Delete a display profile
    ---
    tags:
      - Display Profiles
    parameters:
      - name: profile_id
        in: path
        required: true
        description: Unique identifier of the display profile to delete
        schema:
          type: string
          example: "abc123-def456"
    responses:
      200:
        description: Profile deleted successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  description: Operation success status
                  example: true
                message:
                  type: string
                  description: Confirmation message
                  example: "Profile deleted successfully"
      404:
        description: Profile not found
    """
    service = DisplayProfileService()
    try:
        profile_id_int = int(profile_id)
    except ValueError:
        return jsonify({"error": "Invalid profile ID"}), 400
    
    try:
        service.delete_profile(profile_id_int)
        return jsonify({"success": True, "message": "Profile deleted successfully"}), 200
    except ValueError as e:
        if "not found" in str(e):
            return jsonify({"error": "Profile not found"}), 404
        return jsonify({"error": str(e)}), 400

@display_bp.route("/entries/<string:entry_id>/preview")
@require_authentication
def preview_entry(entry_id: str):
    """
    Preview an entry with a specific display profile
    ---
    tags:
      - Display Profiles
      - Entry Preview
    parameters:
      - name: entry_id
        in: path
        required: true
        description: Unique identifier of the entry to preview
        schema:
          type: string
          example: "entry-123"
      - name: profile_id
        in: query
        required: true
        description: Unique identifier of the display profile to use for rendering
        schema:
          type: string
          example: "profile-456"
    responses:
      200:
        description: Entry preview generated successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  description: Operation success status
                  example: true
                entry_id:
                  type: string
                  description: ID of the previewed entry
                  example: "entry-123"
                profile_id:
                  type: string
                  description: ID of the display profile used
                  example: "profile-456"
                html:
                  type: string
                  description: HTML representation of the entry
                  example: "<div class='entry'>...</div>"
      400:
        description: Missing required parameters
      404:
        description: Entry or profile not found
      500:
        description: Internal server error during preview generation
    """
    profile_id = request.args.get("profile_id")
    if not profile_id:
        return jsonify({"error": "profile_id query parameter is required"}), 400

    service = current_app.injector.get(CSSMappingService)

    # Get the profile
    profile = service.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Get the entry XML from the dictionary service
    dict_service = current_app.injector.get(DictionaryService)
    try:
        # Get the entry object first
        entry = dict_service.get_entry(entry_id)
        if not entry:
            return jsonify({"error": "Entry not found"}), 404

        # Convert entry to XML for rendering using the LIFT parser
        from app.parsers.lift_parser import LIFTParser
        lift_parser = LIFTParser(validate=False)
        entry_xml = lift_parser.generate_lift_string([entry])

        if not entry_xml:
            return jsonify({"error": "Failed to generate entry XML"}), 500

        # Render the entry with the profile
        html_output = service.render_entry(entry_xml, profile)
        return jsonify({
            "success": True,
            "entry_id": entry_id,
            "profile_id": profile_id,
            "html": html_output
        })

    except Exception as e:
        return jsonify({"error": f"Failed to preview entry: {str(e)}"}), 500