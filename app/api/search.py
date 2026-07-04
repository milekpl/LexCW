"""
API endpoints for searching dictionary entries.
"""

import csv
import io
import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, session, Response
from flasgger import swag_from

from app.services.dictionary_service import DictionaryService
from flask import g
from app.database.connector_factory import create_database_connector
from app.utils.exceptions import NotFoundError

# Create blueprint
search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)


def _get_saved_searches() -> dict:
    if '_saved_searches' not in session:
        session['_saved_searches'] = {}
    return session['_saved_searches']


def get_dictionary_service():
    if hasattr(current_app, 'dict_service') and current_app.dict_service:
        return current_app.dict_service
    try:
        from app import injector
        return injector.get(DictionaryService)
    except (ImportError, AttributeError):
        pass
    connector = create_database_connector(
        host=current_app.config.get('BASEX_HOST', 'localhost'),
        port=current_app.config.get('BASEX_PORT', 1984),
        username=current_app.config.get('BASEX_USERNAME', 'admin'),
        password=current_app.config.get('BASEX_PASSWORD', 'admin'),
        database=current_app.config.get('BASEX_DATABASE', 'dictionary'),
    )
    return DictionaryService(connector)


def parse_bool(value: str) -> bool:
    return str(value).lower() in ['true', '1', 'yes', 'on']


@search_bp.route('/', methods=['GET'], strict_slashes=False)
@swag_from({
        'tags': ['Search'],
        'parameters': [
                {'name': 'q', 'in': 'query', 'type': 'string', 'required': True, 'description': 'Search query string', 'example': 'test'},
                {'name': 'fields', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Comma-separated list of fields to search in', 'default': 'lexical_unit,glosses,definitions,note', 'example': 'lexical_unit,pronunciations,senses,note'},
                {'name': 'pos', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Part of speech to filter by', 'example': 'noun'},
                {'name': 'exact_match', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Whether to perform exact match (default: false)', 'example': 'false'},
                {'name': 'case_sensitive', 'in': 'query', 'type': 'string', 'required': False, 'description': 'Whether the search should be case-sensitive (default: false)', 'example': 'false'},
                {'name': 'limit', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Maximum number of entries to return', 'default': 100, 'example': 20},
                {'name': 'offset', 'in': 'query', 'type': 'integer', 'required': False, 'description': 'Number of entries to skip for pagination', 'default': 0, 'example': 0}
        ],
        'responses': {
                '200': {'description': 'Search results'},
                '400': {'description': 'Invalid request parameters'},
                '500': {'description': 'Internal server error'}
        }
})
def search_entries():
    """Search for dictionary entries using XQuery-based search"""
    try:
        query = request.args.get('q', '')
        fields_str = request.args.get('fields', 'lexical_unit,glosses,definitions,note,citation_form,example')
        pos = request.args.get('pos')
        exact_match = parse_bool(request.args.get('exact_match', 'false'))
        case_sensitive = parse_bool(request.args.get('case_sensitive', 'false'))
        use_regex = parse_bool(request.args.get('use_regex', 'false'))
        limit_raw = request.args.get('limit', 100)
        offset_raw = request.args.get('offset', 0)

        try:
            limit = int(limit_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'Limit must be an integer'}), 400
        try:
            offset = int(offset_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'Offset must be an integer'}), 400

        if not query.strip():
            return jsonify({'error': 'Query parameter is required and cannot be empty'}), 400
        if limit < 0:
            return jsonify({'error': 'Limit must be non-negative'}), 400
        if offset < 0:
            return jsonify({'error': 'Offset must be non-negative'}), 400

        fields = [field.strip() for field in fields_str.split(',') if field.strip()]

        dict_service = get_dictionary_service()
        project_id = session.get('project_id')

        use_semantic = parse_bool(request.args.get('use_semantic', request.args.get('semantic', 'false')))
        search_type = request.args.get('search_type', 'xquery').lower()

        if use_semantic or search_type == 'semantic':
            try:
                from app.services.embedding_service import get_embedding_service
                embedding_svc = get_embedding_service()
                vector_hits = embedding_svc.semantic_search(
                    query=query,
                    project_id=project_id,
                    top_k=limit + offset + 50,
                    threshold=0.20,
                )
                if vector_hits:
                    vec_ids = [hit['entry_id'] for hit in vector_hits if hit.get('entry_id')]
                    semantic_entries = dict_service.get_entries_by_ids(vec_ids, project_id=project_id)
                    if pos:
                        semantic_entries = [e for e in semantic_entries if (
                            getattr(e, 'grammatical_info', '') == pos or
                            any(getattr(s, 'grammatical_info', '') == pos for s in getattr(e, 'senses', []))
                        )]
                    total_count = len(semantic_entries)
                    paginated_entries = semantic_entries[offset : offset + limit]
                    return jsonify({
                        'query': query,
                        'fields': fields,
                        'entries': [entry.to_dict() for entry in paginated_entries],
                        'total': total_count,
                        'limit': limit,
                        'offset': offset,
                        'pos': pos,
                        'is_semantic': True,
                    })
            except Exception as sem_err:
                logger.warning("Semantic vector search failed, falling back to XQuery: %s", sem_err)

        field_regexes = None
        if use_regex:
            field_regexes = {field: query for field in fields}

        entries, total_count = dict_service.search_entries(
            project_id=project_id,
            query=query,
            fields=fields,
            limit=limit,
            offset=offset,
            pos=pos,
            exact_match=exact_match,
            case_sensitive=case_sensitive,
            field_regexes=field_regexes,
        )

        response = {
            'query': query,
            'fields': fields,
            'entries': [entry.to_dict() for entry in entries],
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'pos': pos,
        }
        return jsonify(response)

    except Exception as e:
        import traceback
        logger.error("Error searching entries: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@search_bp.route('/facets', methods=['GET'])
def get_facets():
    """Get facet counts for the current search query.

    Returns counts of matching entries grouped by grammatical-info,
    semantic-domain, and other range-based categories.
    """
    try:
        query = request.args.get('q', '')
        fields_str = request.args.get('fields', 'lexical_unit,glosses,definitions,note,citation_form,example')
        pos = request.args.get('pos')
        exact_match = parse_bool(request.args.get('exact_match', 'false'))
        case_sensitive = parse_bool(request.args.get('case_sensitive', 'false'))
        use_regex = parse_bool(request.args.get('use_regex', 'false'))

        if not query.strip():
            return jsonify({'facets': {}})

        fields = [field.strip() for field in fields_str.split(',') if field.strip()]

        dict_service = get_dictionary_service()
        project_id = session.get('project_id')

        field_regexes = None
        if use_regex:
            field_regexes = {field: query for field in fields}

        entries, total_count = dict_service.search_entries(
            project_id=project_id,
            query=query,
            fields=fields,
            limit=10000,
            offset=0,
            pos=pos,
            exact_match=exact_match,
            case_sensitive=case_sensitive,
            field_regexes=field_regexes,
        )

        grammatical_counts = {}
        semantic_domain_counts = {}

        def extract_pos(pos_val):
            if not pos_val:
                return None
            if isinstance(pos_val, dict):
                return pos_val.get('value') or pos_val.get('part_of_speech')
            if hasattr(pos_val, 'value'):
                return pos_val.value
            if hasattr(pos_val, 'part_of_speech'):
                return pos_val.part_of_speech
            if isinstance(pos_val, str):
                return pos_val
            return None

        for entry in entries:
            pos_found = False
            gi = getattr(entry, 'grammatical_info', None)
            if gi:
                pos_val = extract_pos(gi)
                if pos_val:
                    grammatical_counts[pos_val] = grammatical_counts.get(pos_val, 0) + 1
                    pos_found = True

            senses = getattr(entry, 'senses', [])
            if senses:
                for sense in senses:
                    if not pos_found:
                        sgi = None
                        if isinstance(sense, dict):
                            sgi = sense.get('grammatical_info')
                        elif hasattr(sense, 'grammatical_info'):
                            sgi = sense.grammatical_info
                        if sgi:
                            pos_val = extract_pos(sgi)
                            if isinstance(pos_val, str):
                                grammatical_counts[pos_val] = grammatical_counts.get(pos_val, 0) + 1
                    sd = None
                    if isinstance(sense, dict):
                        sd = sense.get('semantic_domain') or sense.get('semanticDomains')
                    elif hasattr(sense, 'semantic_domain'):
                        sd = sense.semantic_domain
                    if sd:
                        if isinstance(sd, list):
                            for s in sd:
                                val = s if isinstance(s, str) else (s.get('value') if isinstance(s, dict) else None)
                                if val:
                                    semantic_domain_counts[val] = semantic_domain_counts.get(val, 0) + 1
                        elif isinstance(sd, str):
                            semantic_domain_counts[sd] = semantic_domain_counts.get(sd, 0) + 1

        return jsonify({
            'facets': {
                'grammatical-info': grammatical_counts,
                'semantic-domain': semantic_domain_counts,
            },
            'query': query,
            'total': total_count,
        })

    except Exception as e:
        logger.error("Error getting facets: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/export', methods=['GET'])
def export_results():
    """Export search results as CSV or JSON."""
    try:
        query = request.args.get('q', '')
        fmt = request.args.get('format', 'json').lower()
        fields_str = request.args.get('fields', 'lexical_unit,glosses,definitions,note,citation_form,example')
        pos = request.args.get('pos')
        exact_match = parse_bool(request.args.get('exact_match', 'false'))
        case_sensitive = parse_bool(request.args.get('case_sensitive', 'false'))
        use_regex = parse_bool(request.args.get('use_regex', 'false'))

        if fmt not in ('csv', 'json'):
            return jsonify({'error': 'Format must be csv or json'}), 400

        if not query.strip():
            return jsonify({'error': 'Query parameter is required and cannot be empty'}), 400

        fields = [field.strip() for field in fields_str.split(',') if field.strip()]

        dict_service = get_dictionary_service()
        project_id = session.get('project_id')

        field_regexes = None
        if use_regex:
            field_regexes = {field: query for field in fields}

        entries, total_count = dict_service.search_entries(
            project_id=project_id,
            query=query,
            fields=fields,
            limit=10000,
            offset=0,
            pos=pos,
            exact_match=exact_match,
            case_sensitive=case_sensitive,
            field_regexes=field_regexes,
        )

        entry_dicts = [entry.to_dict() for entry in entries]

        if fmt == 'json':
            output = json.dumps(entry_dicts, indent=2, ensure_ascii=False)
            return Response(
                output,
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment; filename=search-results.json'}
            )
        else:
            output = io.StringIO()
            writer = csv.writer(output)
            headers = ['id', 'headword', 'lexical_unit', 'citation_form', 'part_of_speech']
            writer.writerow(headers)
            for ed in entry_dicts:
                gi = ed.get('grammatical_info', {}) or {}
                pos_val = ''
                if isinstance(gi, dict):
                    pos_val = gi.get('value') or gi.get('part_of_speech', '')
                elif isinstance(gi, str):
                    pos_val = gi
                headword = ed.get('headword', '')
                if not headword:
                    lu = ed.get('lexical_unit', '')
                    headword = lu if isinstance(lu, str) else (lu.get('en', '') if isinstance(lu, dict) else '')
                writer.writerow([
                    ed.get('id', ''),
                    headword,
                    ed.get('lexical_unit', ''),
                    ed.get('citation_form', ''),
                    pos_val,
                ])
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=search-results.csv'}
            )

    except Exception as e:
        logger.error("Error exporting search results: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/save', methods=['POST'])
def save_search():
    """Save the current search query with a name."""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'query' not in data:
            return jsonify({'error': 'Missing required fields: name, query'}), 400

        saved = _get_saved_searches()
        search_id = str(uuid.uuid4())[:8]
        saved[search_id] = {
            'id': search_id,
            'name': data['name'],
            'query': data['query'],
            'created_at': datetime.utcnow().isoformat(),
        }
        session['_saved_searches'] = saved
        return jsonify({'success': True, 'search_id': search_id, 'name': data['name']}), 201

    except Exception as e:
        logger.error("Error saving search: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/saved', methods=['GET'])
def get_saved_searches():
    """List all saved searches."""
    try:
        saved = _get_saved_searches()
        searches = sorted(saved.values(), key=lambda s: s['created_at'], reverse=True)
        return jsonify({'searches': searches})

    except Exception as e:
        logger.error("Error getting saved searches: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/grammatical', methods=['GET'])
def search_by_grammatical_info():
    try:
        grammatical_info = request.args.get('value', '')
        if not grammatical_info:
            return jsonify({'error': 'Missing grammatical information value'}), 400
        dict_service = get_dictionary_service()
        entries = dict_service.get_entries_by_grammatical_info(grammatical_info)
        response = {
            'grammatical_info': grammatical_info,
            'entries': [entry.to_dict() for entry in entries],
            'count': len(entries),
        }
        return jsonify(response)
    except Exception as e:
        logger.error("Error searching entries by grammatical info: %s", str(e))
        return jsonify({'error': str(e)}), 500


@search_bp.route('/ranges', methods=['GET'])
def get_ranges():
    try:
        dict_service = get_dictionary_service()
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        return jsonify({'success': True, 'data': ranges})
    except Exception as e:
        logger.error("Error getting ranges: %s", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@search_bp.route('/ranges/<range_id>', methods=['GET'])
def get_range_values(range_id):
    try:
        dict_service = get_dictionary_service()
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        if range_id not in ranges:
            logger.debug("Range %s not found in cached ranges; forcing refresh", range_id)
            try:
                ranges = dict_service.get_ranges(force_reload=True) if hasattr(dict_service, 'get_ranges') else ranges
            except Exception as e:
                logger.warning("Forced ranges refresh failed: %s", str(e))
            if range_id not in ranges:
                raise NotFoundError(f"Range '{range_id}' not found")
        return jsonify({'success': True, 'data': ranges[range_id]})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting range values for %s: %s", range_id, str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@search_bp.route('/ranges/lexical-relation', methods=['GET'])
def get_relation_types():
    try:
        dict_service = get_dictionary_service()
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        if 'lexical-relation' not in ranges:
            raise NotFoundError("Relation types not found in ranges")
        return jsonify({'success': True, 'data': ranges['lexical-relation']})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting relation types: %s", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@search_bp.route('/ranges/variant-type', methods=['GET'])
def get_variant_types():
    try:
        dict_service = get_dictionary_service()
        ranges = dict_service.get_ranges() if hasattr(dict_service, 'get_ranges') else {}
        if 'variant-type' not in ranges:
            raise NotFoundError("Variant types not found in ranges")
        return jsonify({'success': True, 'data': ranges['variant-type']})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error("Error getting variant types: %s", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
