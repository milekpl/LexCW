"""
Word Sketch Browser Routes

Routes for the standalone word sketch browser page.
"""

from __future__ import annotations

import logging

from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

word_sketch_browser_bp = Blueprint('word_sketch_browser', __name__)


@word_sketch_browser_bp.route('/browser')
def browser() -> str:
    """Display the standalone word sketch browser page.

    This page allows lexicographers to explore corpus collocations
    and grammatical relations for any lemma.
    """
    return render_template('word_sketch/browser.html')
