"""
API endpoints for corpus search operations.

Provides search functionality against the Lucene corpus service,
returning KWIC concordance results for lexicographic work.
"""
import logging
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)

corpus_search_bp = Blueprint('corpus_search', __name__)


@corpus_search_bp.route('/search', methods=['GET'])
def search_corpus():
    """
    Search corpus for KWIC concordance results.

    Query Parameters:
        q: Search query (required)
        limit: Maximum results to return (default: 500, max: 2000)
        context: Words before/after match (default: 8, max: 15)

    Returns:
        JSON object with success status, total count, and results list.
        Each result contains left, match, right, and sentence_id fields.
    """
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: q'
        }), 400

    # Parse and validate parameters
    try:
        limit = int(request.args.get('limit', 500))
        limit = min(limit, 2000)  # Cap at 2000 to prevent abuse
    except ValueError:
        limit = 500

    try:
        context = int(request.args.get('context', 8))
        context = min(context, 15)  # Cap at 15 words context
    except ValueError:
        context = 8

    try:
        total, hits = current_app.lucene_corpus_client.concordance(
            query=query,
            limit=limit,
            context_size=context
        )

        results = [
            {
                'left': hit.left,
                'match': hit.match,
                'right': hit.right,
                'sentence_id': hit.sentence_id
            }
            for hit in hits
        ]

        return jsonify({
            'success': True,
            'query': query,
            'total': total,
            'results': results
        })

    except Exception as e:
        logger.error(f"Corpus search failed for query '{query}': {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@corpus_search_bp.route('/count', methods=['GET'])
def count_corpus():
    """
    Get the count of matching documents for a query.

    Query Parameters:
        q: Search query (required)

    Returns:
        JSON object with success status and count.
    """
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: q'
        }), 400

    try:
        count = current_app.lucene_corpus_client.count(query)
        return jsonify({
            'success': True,
            'query': query,
            'count': count
        })

    except Exception as e:
        logger.error(f"Corpus count failed for query '{query}': {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
