from __future__ import annotations

from flask import Blueprint, jsonify, request

from app import injector
from app.services.css_mapping_service import CSSMappingService

display_bp = Blueprint("display", __name__, url_prefix="/api/display-profiles")


@display_bp.route("", methods=["POST"])
def create_profile():
    service = injector.get(CSSMappingService)
    profile = service.create_profile(request.json)
    return jsonify(profile.dict()), 201


@display_bp.route("/<string:profile_id>", methods=["GET"])
def get_profile(profile_id: str):
    service = injector.get(CSSMappingService)
    profile = service.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile.dict())


@display_bp.route("", methods=["GET"])
def list_profiles():
    service = injector.get(CSSMappingService)
    profiles = service.list_profiles()
    return jsonify([p.dict() for p in profiles])


@display_bp.route("/<string:profile_id>", methods=["PUT"])
def update_profile(profile_id: str):
    raise NotImplementedError


@display_bp.route("/<string:profile_id>", methods=["DELETE"])
def delete_profile(profile_id: str):
    raise NotImplementedError