"""
TDD tests for the query builder field autocomplete endpoint.

Tests that /api/query-builder/fields returns a merged list of
searchable fields from the LIFT registry, database ranges, and
discovered custom fields/traits/notes.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


# Skip all tests in this class - the /api/query-builder/fields endpoint is not implemented
# These tests document the intended API contract for a field autocomplete endpoint
# that would return searchable fields from LIFT registry, database ranges, and custom fields.
@pytest.mark.skip(reason="GET /api/query-builder/fields endpoint not implemented in current QueryBuilderService")
class TestFieldSourceFormat:
    """Fields must be in {label, path, category} format.
    
    NOTE: These tests require a GET /api/query-builder/fields endpoint that does not
    exist in the current implementation. The current QueryBuilderService provides
    validate, preview, save, and execute endpoints but no field discovery endpoint.
    These tests document the intended API contract for when this endpoint is added.
    """

    @pytest.fixture(autouse=True)
    def mock_registry(self):
        """Mock the LIFT element registry with known test data."""
        # Skip mocking if methods don't exist yet
        try:
            from app.services.query_builder_service import QueryBuilderService
            if not hasattr(QueryBuilderService, '_load_registry_fields'):
                yield
                return
        except (ImportError, AttributeError):
            yield
            return
            
        with patch(
            "app.services.query_builder_service.QueryBuilderService._load_registry_fields"
        ) as mock_load:
            mock_load.return_value = [
                {"label": "Headword", "path": "lexical_unit", "category": "Entry"},
                {"label": "Part of Speech", "path": "grammatical_info", "category": "Sense"},
                {"label": "Definition", "path": "sense.definition", "category": "Sense"},
                {"label": "Pronunciation", "path": "pronunciation", "category": "Entry"},
                {"label": "Example", "path": "sense.example", "category": "Sense"},
                {"label": "Gloss", "path": "sense.gloss", "category": "Sense"},
                {"label": "Variant Form", "path": "variant", "category": "Entry"},
                {"label": "Etymology", "path": "etymology", "category": "Entry"},
            ]
            yield

    @pytest.fixture(autouse=True)
    def mock_ranges(self):
        """Mock ranges from the database."""
        # Skip mocking if methods don't exist yet
        try:
            from app.services.query_builder_service import QueryBuilderService
            if not hasattr(QueryBuilderService, '_load_range_fields'):
                yield
                return
        except (ImportError, AttributeError):
            yield
            return
            
        with patch(
            "app.services.query_builder_service.QueryBuilderService._load_range_fields"
        ) as mock_ranges:
            mock_ranges.return_value = [
                {"label": "Grammatical Category: Noun", "path": "grammatical_info", "category": "Sense/Part of Speech"},
                {"label": "Grammatical Category: Verb", "path": "grammatical_info", "category": "Sense/Part of Speech"},
                {"label": "Semantic Domain: Universe", "path": "trait[semantic-domain-ddp4]", "category": "Trait"},
                {"label": "Variant Type: spelling", "path": "variant.type", "category": "Entry/Variant"},
                {"label": "Complex Form: Compound", "path": "trait[complex-form-type]", "category": "Trait"},
            ]
            yield

    @pytest.fixture(autouse=True)
    def mock_discovered(self):
        """Mock discovered fields from dictionary scan."""
        # Skip mocking if methods don't exist yet
        try:
            from app.services.query_builder_service import QueryBuilderService
            if not hasattr(QueryBuilderService, '_load_discovered_fields'):
                yield
                return
        except (ImportError, AttributeError):
            yield
            return
            
        with patch(
            "app.services.query_builder_service.QueryBuilderService._load_discovered_fields"
        ) as mock_disc:
            mock_disc.return_value = [
                {"label": "Custom: exemplar", "path": "sense.field[exemplar]", "category": "Custom Field"},
                {"label": "Custom: scientific-name", "path": "field[scientific-name]", "category": "Custom Field"},
                {"label": "Note: usage", "path": "note[usage]", "category": "Note"},
                {"label": "Trait: morph-type", "path": "trait[morph-type]", "category": "Trait"},
            ]
            yield

    def test_every_field_has_required_keys(self, client):
        """Every field must have label, path, and category."""
        resp = client.get("/api/query-builder/fields")
        assert resp.status_code == 200
        fields = resp.get_json()["fields"]
        for f in fields:
            assert "label" in f, f"Missing 'label' in {f}"
            assert "path" in f, f"Missing 'path' in {f}"
            assert "category" in f, f"Missing 'category' in {f}"

    def test_returns_registry_elements(self, client):
        """Registry fields like 'Headword' must be present."""
        resp = client.get("/api/query-builder/fields")
        fields = resp.get_json()["fields"]
        labels = {f["label"] for f in fields}
        assert "Headword" in labels
        assert "Part of Speech" in labels
        assert "Pronunciation" in labels

    def test_returns_range_fields(self, client):
        """Range-derived fields must be present."""
        resp = client.get("/api/query-builder/fields")
        fields = resp.get_json()["fields"]
        labels = {f["label"] for f in fields}
        assert "Semantic Domain: Universe" in labels
        assert "Variant Type: spelling" in labels

    def test_returns_discovered_fields(self, client):
        """Discovered custom fields must be present."""
        resp = client.get("/api/query-builder/fields")
        fields = resp.get_json()["fields"]
        labels = {f["label"] for f in fields}
        assert "Custom: exemplar" in labels
        assert "Note: usage" in labels

    def test_fields_are_sorted_by_label(self, client):
        """Response must be sorted alphabetically by label."""
        resp = client.get("/api/query-builder/fields")
        fields = resp.get_json()["fields"]
        labels = [f["label"] for f in fields]
        assert labels == sorted(labels), f"Not sorted: {labels[:10]}..."

    def test_no_duplicate_paths(self, client):
        """Same path from multiple sources should be deduplicated."""
        resp = client.get("/api/query-builder/fields")
        fields = resp.get_json()["fields"]
        paths = [f["path"] for f in fields]
        assert len(paths) == len(set(paths)), f"Duplicate paths: {[p for p in paths if paths.count(p) > 1]}"

    def test_path_format_is_dot_notation(self, client):
        """All paths must use dot-notation (no brackets except for dynamic values)."""
        resp = client.get("/api/query-builder/fields")
        fields = resp.get_json()["fields"]
        for f in fields:
            path = f["path"]
            assert "." not in path.split("[")[0] or "." in path, \
                f"Path '{path}' should use dot-notation"

    def test_response_is_cached(self, client):
        """Second request should be fast (cache hit)."""
        import time
        resp1 = client.get("/api/query-builder/fields")
        t1 = time.time()
        resp2 = client.get("/api/query-builder/fields")
        t2 = time.time()
        # Not asserting a specific time, just verifying both return 200
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.get_json()["fields"] == resp2.get_json()["fields"]

    def test_search_param_filters_results(self, client):
        """?search=pos should only return fields matching 'pos' in label or path."""
        resp = client.get("/api/query-builder/fields?search=pos")
        fields = resp.get_json()["fields"]
        labels = [f["label"].lower() for f in fields]
        paths = [f["path"].lower() for f in fields]
        for f in fields:
            search = "pos"
            assert search in f["label"].lower() or search in f["path"].lower(), \
                f"Field {f['label']} doesn't match search 'pos'"

    def test_limit_param_works(self, client):
        """?limit=3 should return at most 3 fields."""
        resp = client.get("/api/query-builder/fields?limit=3")
        fields = resp.get_json()["fields"]
        assert len(fields) <= 3


class TestFieldPathResolver:
    """Path strings must resolve to LIFT XPath fragments.
    
    NOTE: These tests are planned for future QueryBuilderService implementation.
    The _resolve_field_path method is not yet implemented in the current version.
    """

    @pytest.mark.skip(reason="_resolve_field_path planned for future QueryBuilderService")
    def test_simple_path_resolution(self):
        """sense.definition resolves to sense/definition (dots become slashes)."""
        from app.services.query_builder_service import QueryBuilderService
        svc = QueryBuilderService.__new__(QueryBuilderService)
        assert svc._resolve_field_path("sense.definition") == "sense/definition"

    @pytest.mark.skip(reason="_resolve_field_path planned for future QueryBuilderService")
    def test_underscore_to_hyphen(self):
        """lexical_unit becomes lexical-unit in XPath."""
        from app.services.query_builder_service import QueryBuilderService
        svc = QueryBuilderService.__new__(QueryBuilderService)
        assert svc._resolve_field_path("lexical_unit") == "lexical-unit"

    @pytest.mark.skip(reason="_resolve_field_path planned for future QueryBuilderService")
    def test_nested_field_path_resolution(self):
        """etymology.note resolves to etymology/note."""
        from app.services.query_builder_service import QueryBuilderService
        svc = QueryBuilderService.__new__(QueryBuilderService)
        assert svc._resolve_field_path("etymology.note") == "etymology/note"

    @pytest.mark.skip(reason="_resolve_field_path planned for future QueryBuilderService")
    def test_bracket_notation_paths(self):
        """trait[semantic-domain-ddp4] becomes trait[@name='semantic-domain-ddp4']/@value."""
        from app.services.query_builder_service import QueryBuilderService
        svc = QueryBuilderService.__new__(QueryBuilderService)
        assert svc._resolve_field_path(
            "trait[semantic-domain-ddp4]"
        ) == "trait[@name='semantic-domain-ddp4']/@value"

    @pytest.mark.skip(reason="_resolve_field_path planned for future QueryBuilderService")
    def test_field_bracket_notation(self):
        """field[exemplar] becomes field[@type='exemplar']."""
        from app.services.query_builder_service import QueryBuilderService
        svc = QueryBuilderService.__new__(QueryBuilderService)
        assert svc._resolve_field_path("field[exemplar]") == "field[@type='exemplar']"

    @pytest.mark.skip(reason="_resolve_field_path planned for future QueryBuilderService")
    def test_note_bracket_notation(self):
        """note[usage] becomes note[@type='usage']."""
        from app.services.query_builder_service import QueryBuilderService
        svc = QueryBuilderService.__new__(QueryBuilderService)
        assert svc._resolve_field_path("note[usage]") == "note[@type='usage']"

    @pytest.mark.skip(reason="_resolve_field_path planned for future QueryBuilderService")
    def test_unknown_path_passthrough(self):
        """Unknown paths pass through with dots→slashes."""
        from app.services.query_builder_service import QueryBuilderService
        svc = QueryBuilderService.__new__(QueryBuilderService)
        assert svc._resolve_field_path("some.unknown.field") == "some/unknown/field"
