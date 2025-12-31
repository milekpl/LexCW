"""
LIFT Element Registry API.

Provides endpoints for accessing LIFT element metadata
to support display profile configuration in the admin UI.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, current_app
from typing import Dict, Any

from app.services.lift_element_registry import LIFTElementRegistry

registry_bp = Blueprint("lift_registry", __name__, url_prefix="/api/lift")

# Create a singleton registry instance
_registry: LIFTElementRegistry | None = None


def get_registry() -> LIFTElementRegistry:
    """Get or create the singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = LIFTElementRegistry()
    return _registry


@registry_bp.route("/elements", methods=["GET"])
def list_elements():
    """
    Get all LIFT elements
    ---
    tags:
      - LIFT Registry
    responses:
      200:
        description: List of all LIFT elements with metadata
        content:
          application/json:
            schema:
              type: object
              properties:
                elements:
                  type: array
                  items:
                    type: object
                    properties:
                      name:
                        type: string
                        example: "lexical-unit"
                      display_name:
                        type: string
                        example: "Lexical Unit / Headword"
                      category:
                        type: string
                        example: "entry"
                      description:
                        type: string
                      level:
                        type: integer
                      parent:
                        type: string
                      allowed_children:
                        type: array
                        items:
                          type: string
                      default_css:
                        type: string
                      default_visibility:
                        type: string
                      typical_order:
                        type: integer
    """
    registry = get_registry()
    elements = registry.get_all_elements()
    element_dicts = [elem.to_dict() for elem in elements]
    
    return jsonify({
        "elements": element_dicts,
        "count": len(element_dicts)
    })


@registry_bp.route("/elements/displayable", methods=["GET"])
def list_displayable_elements():
    """
    Get elements suitable for display profile configuration
    ---
    tags:
      - LIFT Registry
    responses:
      200:
        description: List of displayable LIFT elements
        content:
          application/json:
            schema:
              type: object
              properties:
                elements:
                  type: array
                  items:
                    type: object
    """
    registry = get_registry()
    elements = registry.get_displayable_elements()
    element_dicts = [elem.to_dict() for elem in elements]
    
    return jsonify({
        "elements": element_dicts,
        "count": len(element_dicts)
    })


@registry_bp.route("/categories", methods=["GET"])
def list_categories():
    """
    Get all element categories
    ---
    tags:
      - LIFT Registry
    responses:
      200:
        description: List of element categories
        content:
          application/json:
            schema:
              type: object
              additionalProperties:
                type: object
                properties:
                  name:
                    type: string
                  description:
                    type: string
    """
    registry = get_registry()
    categories = registry.get_categories()
    
    # Convert dict to array format
    # Each category has {name: display_name, description: desc}
    # We want to return [{name: category_key, display_name: ..., description: ...}]
    categories_array = [
        {"name": key, "display_name": data.get("name", key), "description": data.get("description", "")}
        for key, data in categories.items()
    ]
    
    return jsonify({"categories": categories_array})


@registry_bp.route("/visibility-options", methods=["GET"])
def list_visibility_options():
    """
    Get available visibility options
    ---
    tags:
      - LIFT Registry
    responses:
      200:
        description: List of visibility options
        content:
          application/json:
            schema:
              type: object
              properties:
                options:
                  type: array
                  items:
                    type: object
                    properties:
                      value:
                        type: string
                      label:
                        type: string
                      description:
                        type: string
    """
    registry = get_registry()
    options = registry.get_visibility_options()
    
    return jsonify({"options": options})


@registry_bp.route("/hierarchy", methods=["GET"])
def get_hierarchy():
    """
    Get element parent-child hierarchy
    ---
    tags:
      - LIFT Registry
    responses:
      200:
        description: Element hierarchy mapping
        content:
          application/json:
            schema:
              type: object
              additionalProperties:
                type: array
                items:
                  type: string
    """
    registry = get_registry()
    hierarchy = registry.get_element_hierarchy()
    
    return jsonify({"hierarchy": hierarchy})


@registry_bp.route("/metadata", methods=["GET"])
def get_metadata():
    """
    Get all registry metadata (lexical relations, note types, etc.)
    ---
    tags:
      - LIFT Registry
    responses:
      200:
        description: Registry metadata
        content:
          application/json:
            schema:
              type: object
              properties:
                lexical_relations:
                  type: array
                  items:
                    type: string
                note_types:
                  type: array
                  items:
                    type: string
                grammatical_categories:
                  type: array
                  items:
                    type: string
    """
    registry = get_registry()

    # Dynamically load relation types from the lexical-relation range
    # This allows projects to define their own relation types via ranges
    relation_types = ["_component-lexeme"]  # Always include this implicit SIL type
    try:
        from flask import current_app
        from app.services.dictionary_service import DictionaryService
        dict_service = current_app.injector.get(DictionaryService)
        ranges = dict_service.get_ranges()

        # Get relation types from the lexical-relation range
        lexical_rel_range = ranges.get("lexical-relation", {})
        values = lexical_rel_range.get("values", [])
        for val in values:
            rel_id = val.get("id", "")
            if rel_id and rel_id not in relation_types:
                relation_types.append(rel_id)
    except Exception as e:
        current_app.logger.debug(f"Could not load relation types from ranges: {e}")

    return jsonify({
        "lexical_relations": relation_types,
        "note_types": registry.get_note_types(),
        "grammatical_categories": registry.get_grammatical_categories()
    })


@registry_bp.route("/default-profile", methods=["GET"])
def get_default_profile():
    """
    Get default profile element configuration
    ---
    tags:
      - LIFT Registry
    responses:
      200:
        description: Default profile elements
        content:
          application/json:
            schema:
              type: object
              properties:
                elements:
                  type: array
                  items:
                    type: object
                    properties:
                      lift_element:
                        type: string
                      display_order:
                        type: integer
                      css_class:
                        type: string
                      visibility:
                        type: string
    """
    registry = get_registry()
    profile_elements = registry.create_default_profile_elements()
    
    return jsonify({
        "profile": profile_elements,
        "name": "default",
        "description": "Default display profile for LIFT entries"
    })


@registry_bp.route("/elements/category/<string:category>", methods=["GET"])
def list_elements_by_category(category: str):
    """
    Get elements in a specific category
    ---
    tags:
      - LIFT Registry
    parameters:
      - name: category
        in: path
        required: true
        schema:
          type: string
          example: "entry"
    responses:
      200:
        description: List of elements in the category
        content:
          application/json:
            schema:
              type: object
              properties:
                category:
                  type: string
                elements:
                  type: array
                  items:
                    type: object
    """
    registry = get_registry()
    
    # Validate category exists
    categories = registry.get_categories()
    if category not in categories:
        return jsonify({"error": f"Invalid category '{category}'"}), 400
    
    elements = registry.get_elements_by_category(category)
    element_dicts = [elem.to_dict() for elem in elements]
    
    return jsonify({
        "category": category,
        "elements": element_dicts,
        "count": len(element_dicts)
    })


@registry_bp.route("/elements/<string:element_name>", methods=["GET"])
def get_element(element_name: str):
    """
    Get a specific LIFT element by name
    ---
    tags:
      - LIFT Registry
    parameters:
      - name: element_name
        in: path
        required: true
        schema:
          type: string
          example: "lexical-unit"
    responses:
      200:
        description: Element metadata
        content:
          application/json:
            schema:
              type: object
      404:
        description: Element not found
    """
    registry = get_registry()
    element = registry.get_element(element_name)
    
    if not element:
        return jsonify({"error": f"Element '{element_name}' not found"}), 404
    
    return jsonify(element.to_dict())
