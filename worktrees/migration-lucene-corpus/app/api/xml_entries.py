"""
API endpoints for managing dictionary entries via LIFT XML.

This module provides XML-based CRUD operations for dictionary entries,
using the XMLEntryService to interact directly with BaseX.
"""

import logging
import os
from typing import Any
from flask import Blueprint, request, jsonify, current_app
from flasgger import swag_from

from app.services.xml_entry_service import (
    XMLEntryService,
    XMLEntryServiceError,
    EntryNotFoundError,
    InvalidXMLError,
    DatabaseConnectionError,
    DuplicateEntryError,
)

# Create blueprint
xml_entries_bp = Blueprint("xml_entries", __name__, url_prefix="/api/xml")
logger = logging.getLogger(__name__)


def get_xml_entry_service() -> XMLEntryService:
    """
    Get an instance of the XML entry service from the current app context.

    Returns:
        XMLEntryService instance configured with BaseX credentials.

    Note: Creates a new XMLEntryService instance with the same BaseX configuration
    as the DictionaryService to ensure they connect to the same database.
    """
    # Get BaseX configuration from app config
    config = current_app.config

    # Prefer the explicit TEST_DB_NAME env var during testing (set by fixtures)
    env_db = os.environ.get("TEST_DB_NAME") or os.environ.get("BASEX_DATABASE")
    database = env_db or config.get("BASEX_DATABASE", "dictionary")

    # Important: Use the same database configuration as Dictionary Service
    # to ensure both services see the same data
    logger.info(
        f"[XML API] Creating XMLEntryService with database: database={database}, TEST_DB_NAME={os.environ.get('TEST_DB_NAME')}, BASEX_DATABASE={os.environ.get('BASEX_DATABASE')}"
    )

    return XMLEntryService(
        host=config.get("BASEX_HOST", "localhost"),
        port=config.get("BASEX_PORT", 1984),
        username=config.get("BASEX_USERNAME", "admin"),
        password=config.get("BASEX_PASSWORD", "admin"),
        database=database,
    )


@xml_entries_bp.route("/entries", methods=["POST"], strict_slashes=False)
@swag_from(
    {
        "tags": ["XML Entries"],
        "summary": "Create a new dictionary entry from LIFT XML",
        "consumes": ["application/xml"],
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "description": "LIFT XML entry to create",
            }
        ],
        "responses": {
            "201": {"description": "Entry created successfully"},
            "400": {"description": "Invalid XML or validation error"},
            "500": {"description": "Internal server error"},
        },
    }
)
def create_entry() -> Any:
    """Create a new dictionary entry from LIFT XML"""
    try:
        # Get XML from request body
        xml_string = request.get_data(as_text=True)

        if not xml_string or not xml_string.strip():
            return jsonify({"error": "No XML data provided"}), 400

        logger.info("[XML API] Received CREATE request")
        logger.debug("[XML API] XML length: %d characters", len(xml_string))

        # Get XML entry service
        xml_service = get_xml_entry_service()

        # Create entry
        result = xml_service.create_entry(xml_string)

        logger.info("[XML API] Entry created: %s", result["id"])

        # Clear entries cache after successful creation
        from app.services.cache_service import CacheService

        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern("entries:*")
            logger.info(
                "[XML API] Cleared entries cache after creating entry %s", result["id"]
            )

        # Return response
        return jsonify(
            {
                "success": True,
                "entry_id": result["id"],
                "filename": result.get("filename"),
                "status": result.get("status"),
            }
        ), 201

    except InvalidXMLError as e:
        logger.error("[XML API] Invalid XML: %s", str(e))
        return jsonify({"error": f"Invalid XML: {str(e)}"}), 400
    except DuplicateEntryError as e:
        logger.error("[XML API] Duplicate entry: %s", str(e))
        return jsonify({"error": str(e)}), 409
    except DatabaseConnectionError as e:
        logger.error("[XML API] Database connection error: %s", str(e))
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except XMLEntryServiceError as e:
        logger.error("[XML API] Service error: %s", str(e))
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(
            "[XML API] Unexpected error creating entry: %s", str(e), exc_info=True
        )
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@xml_entries_bp.route("/entries/<string:entry_id>", methods=["PUT"])
@swag_from(
    {
        "tags": ["XML Entries"],
        "summary": "Update a dictionary entry from LIFT XML",
        "consumes": ["application/xml"],
        "parameters": [
            {
                "name": "entry_id",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "ID of the entry to update",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "description": "LIFT XML entry (updated)",
            },
        ],
        "responses": {
            "200": {"description": "Entry updated successfully"},
            "400": {"description": "Invalid XML or ID mismatch"},
            "404": {"description": "Entry not found"},
        },
    }
)
def update_entry(entry_id: str) -> Any:
    """Update a dictionary entry from LIFT XML"""
    try:
        # Get XML from request body
        xml_string = request.get_data(as_text=True)

        if not xml_string or not xml_string.strip():
            return jsonify({"error": "No XML data provided"}), 400

        logger.info("[XML API] Received UPDATE request for entry: %s", entry_id)
        logger.debug("[XML API] XML length: %d characters", len(xml_string))
        try:
            sense_count = xml_string.count("<sense ")
        except Exception:
            sense_count = -1
        logger.info(
            f"[XML API] Approximate sense count in submitted XML: {sense_count}"
        )

        # Get XML entry service
        xml_service = get_xml_entry_service()

        # Try to update entry, if not found then create it
        try:
            result = xml_service.update_entry(entry_id, xml_string)
        except EntryNotFoundError:
            # If entry doesn't exist, create it instead
            logger.info("[XML API] Entry %s not found, creating new entry", entry_id)
            result = xml_service.create_entry(xml_string)

        logger.info("[XML API] Entry saved: %s", result["id"])

        # Clear entries cache after successful update or create
        from app.services.cache_service import CacheService

        cache = CacheService()
        if cache.is_available():
            cache.clear_pattern("entries:*")
            logger.info(
                "[XML API] Cleared entries cache after saving entry %s", result["id"]
            )

        # Return response
        return jsonify(
            {
                "success": True,
                "entry_id": result["id"],
                "filename": result.get("filename"),
                "status": result.get("status"),
            }
        ), 200

    except EntryNotFoundError as e:
        logger.warning("[XML API] Entry not found: %s", entry_id)
        return jsonify({"error": f"Entry not found: {entry_id}"}), 404
    except InvalidXMLError as e:
        logger.error("[XML API] Invalid XML: %s", str(e))
        return jsonify({"error": f"Invalid XML: {str(e)}"}), 400
    except ValueError as e:
        # ID mismatch or other validation error
        logger.error("[XML API] Validation error: %s", str(e))
        return jsonify({"error": str(e)}), 400
    except DatabaseConnectionError as e:
        logger.error("[XML API] Database connection error: %s", str(e))
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except XMLEntryServiceError as e:
        logger.error("[XML API] Service error: %s", str(e))
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(
            "[XML API] Unexpected error updating entry %s: %s",
            entry_id,
            str(e),
            exc_info=True,
        )
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@xml_entries_bp.route("/entries/<string:entry_id>", methods=["DELETE"])
@swag_from(
    {
        "tags": ["XML Entries"],
        "summary": "Delete a dictionary entry by ID",
        "parameters": [
            {
                "name": "entry_id",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "ID of the entry to delete",
            }
        ],
        "responses": {
            "200": {"description": "Entry deleted successfully"},
            "404": {"description": "Entry not found"},
            "500": {"description": "Internal server error"},
        },
    }
)
def delete_entry(entry_id: str) -> Any:
    """Delete a dictionary entry"""
    try:
        logger.info("[XML API] Received DELETE request for entry: %s", entry_id)

        # Get XML entry service
        xml_service = get_xml_entry_service()

        # Delete entry
        result = xml_service.delete_entry(entry_id)

        logger.info("[XML API] Entry deleted: %s", entry_id)

        # Return response
        return jsonify(
            {"success": True, "entry_id": result["id"], "status": result.get("status")}
        ), 200

    except EntryNotFoundError as e:
        logger.warning("[XML API] Entry not found: %s", entry_id)
        return jsonify({"error": f"Entry not found: {entry_id}"}), 404
    except DatabaseConnectionError as e:
        logger.error("[XML API] Database connection error: %s", str(e))
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except XMLEntryServiceError as e:
        logger.error("[XML API] Service error: %s", str(e))
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(
            "[XML API] Unexpected error deleting entry %s: %s",
            entry_id,
            str(e),
            exc_info=True,
        )
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@xml_entries_bp.route("/entries/<string:entry_id>", methods=["GET"])
@swag_from(
    {
        "tags": ["XML Entries"],
        "summary": "Get an entry by its LIFT ID in XML format",
        "parameters": [
            {
                "name": "entry_id",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "ID of the entry to retrieve",
            }
        ],
        "responses": {
            "200": {"description": "Entry retrieved successfully"},
            "404": {"description": "Entry not found"},
        },
    }
)
def get_entry(entry_id: str) -> Any:
    """
    Get a dictionary entry as LIFT XML
    ---
    tags:
      - XML Entries
    produces:
      - application/xml
      - application/json
    parameters:
      - name: entry_id
        in: path
        type: string
        required: true
        description: ID of the entry to retrieve
        example: "test_001"
      - name: format
        in: query
        type: string
        required: false
        description: Response format (xml or json)
        enum: [xml, json]
        default: xml
    responses:
      200:
        description: Entry retrieved successfully
        content:
          application/xml:
            schema:
              type: string
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: string
                xml:
                  type: string
                lexical_units:
                  type: array
                senses:
                  type: array
      404:
        description: Entry not found
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        logger.info("[XML API] Received GET request for entry: %s", entry_id)

        # Get XML entry service
        xml_service = get_xml_entry_service()

        # Get entry
        entry_data = xml_service.get_entry(entry_id)

        logger.info("[XML API] Entry retrieved: %s", entry_id)

        # Check requested format
        format_param = request.args.get("format", "xml").lower()

        if format_param == "json":
            # Return JSON representation
            return jsonify(entry_data), 200
        else:
            # Return XML string
            from flask import Response

            return Response(
                entry_data["xml"],
                mimetype="application/xml",
                headers={"Content-Disposition": f'inline; filename="{entry_id}.xml"'},
            )

    except EntryNotFoundError as e:
        logger.warning("[XML API] Entry not found: %s", entry_id)
        return jsonify({"error": f"Entry not found: {entry_id}"}), 404
    except DatabaseConnectionError as e:
        logger.error("[XML API] Database connection error: %s", str(e))
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except XMLEntryServiceError as e:
        logger.error("[XML API] Service error: %s", str(e))
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(
            "[XML API] Unexpected error getting entry %s: %s",
            entry_id,
            str(e),
            exc_info=True,
        )
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@xml_entries_bp.route("/entries", methods=["GET"])
def search_entries() -> Any:
    """
    Search dictionary entries with pagination
    ---
    tags:
      - XML Entries
    parameters:
      - name: q
        in: query
        type: string
        required: false
        description: Search query text
        example: "test"
      - name: limit
        in: query
        type: integer
        required: false
        description: Maximum number of results
        default: 50
        example: 10
      - name: offset
        in: query
        type: integer
        required: false
        description: Number of results to skip
        default: 0
        example: 0
    responses:
      200:
        description: Search results
        schema:
          type: object
          properties:
            entries:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  lexical_units:
                    type: array
                  senses:
                    type: array
            total:
              type: integer
              description: Total number of matching entries
            limit:
              type: integer
            offset:
              type: integer
            count:
              type: integer
              description: Number of entries in this page
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        query_text = request.args.get("q", "")
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Validate parameters
        if limit <= 0 or limit > 1000:
            limit = 50
        if offset < 0:
            offset = 0

        logger.info(
            "[XML API] Search request: q=%s, limit=%d, offset=%d",
            query_text,
            limit,
            offset,
        )

        # Get XML entry service
        xml_service = get_xml_entry_service()

        # Search entries
        results = xml_service.search_entries(
            query_text=query_text, limit=limit, offset=offset
        )

        logger.info(
            "[XML API] Search returned %d results (total: %d)",
            results["count"],
            results["total"],
        )

        return jsonify(results), 200

    except DatabaseConnectionError as e:
        logger.error("[XML API] Database connection error: %s", str(e))
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except XMLEntryServiceError as e:
        logger.error("[XML API] Service error: %s", str(e))
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(
            "[XML API] Unexpected error searching entries: %s", str(e), exc_info=True
        )
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@xml_entries_bp.route("/stats", methods=["GET"])
def get_stats() -> Any:
    """
    Get database statistics
    ---
    tags:
      - XML Entries
    responses:
      200:
        description: Database statistics
        schema:
          type: object
          properties:
            entries:
              type: integer
              description: Total number of entries
            senses:
              type: integer
              description: Total number of senses
            avg_senses:
              type: number
              description: Average senses per entry
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        logger.info("[XML API] Stats request")

        # Get XML entry service
        xml_service = get_xml_entry_service()

        # Get stats
        stats = xml_service.get_database_stats()

        logger.info("[XML API] Stats: %s", stats)

        return jsonify(stats), 200

    except DatabaseConnectionError as e:
        logger.error("[XML API] Database connection error: %s", str(e))
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except XMLEntryServiceError as e:
        logger.error("[XML API] Service error: %s", str(e))
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(
            "[XML API] Unexpected error getting stats: %s", str(e), exc_info=True
        )
        return jsonify({"error": f"Internal error: {str(e)}"}), 500
