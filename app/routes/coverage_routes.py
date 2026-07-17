"""
Coverage Check Routes

Routes for the coverage checking tool page.
"""

from __future__ import annotations

import logging

from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

coverage_routes_bp = Blueprint("coverage_routes", __name__)


@coverage_routes_bp.route("/coverage")
def coverage_page() -> str:
    """Display the coverage checking page."""
    return render_template("coverage.html")
