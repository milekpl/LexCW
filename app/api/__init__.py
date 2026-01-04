"""
API package for the Lexicographic Curation Workbench.
"""

from flask import Blueprint
from app.api.entries import entries_bp
from app.api.search import search_bp
from app.api.export import export_bp
from app.api.dashboard import dashboard_bp
from app.api.display import display_bp
from app.api.validation_rules_api import validation_rules_bp
from app.api.bulk_operations import bulk_bp

# Create the API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Register blueprints
api_bp.register_blueprint(entries_bp, url_prefix='/entries')
api_bp.register_blueprint(search_bp, url_prefix='/search')
api_bp.register_blueprint(export_bp, url_prefix='/export')
api_bp.register_blueprint(dashboard_bp)
api_bp.register_blueprint(display_bp)
api_bp.register_blueprint(validation_rules_bp)
api_bp.register_blueprint(bulk_bp, url_prefix='/bulk')