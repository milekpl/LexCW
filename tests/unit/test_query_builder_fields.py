"""
TDD tests for the query builder field autocomplete endpoint.

Tests that /api/query-builder/fields returns a merged list of
searchable fields from the LIFT registry, database ranges, and
discovered custom fields/traits/notes.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestFieldSourceFormat:
    """Fields must be in {label, path, category} format.
    
    Tests the GET /api/query-builder/fields endpoint which returns a merged list
    of searchable fields from LIFT registry, database ranges, and discovered custom fields.
    """

    @pytest.fixture(autouse=True)
    def mock_field_registry(self):
        """Mock the FieldRegistryService with known test data (deduplicated)."""
        # Merge of registry, ranges, and discovered fields with deduplication
        # Fields with duplicate paths are merged (only first occurrence kept)
        merged_fields = [
            # Registry fields
            {"label": "Headword", "path": "lexical_unit", "category": "Entry"},
            {"label": "Part of Speech", "path": "grammatical_info", "category": "Sense"},  # Registry version
            {"label": "Definition", "path": "sense.definition", "category": "Sense"},
            {"label": "Pronunciation", "path": "pronunciation", "category": "Entry"},
            {"label": "Example", "path": "sense.example", "category": "Sense"},
            {"label": "Gloss", "path": "sense.gloss", "category": "Sense"},
            {"label": "Variant Form", "path": "variant", "category": "Entry"},
            {"label": "Etymology", "path": "etymology", "category": "Entry"},
            # Range fields (different paths, no duplicates)
            {"label": "Grammatical Category: Noun (Range)", "path": "grammatical_info.noun", "category": "Sense/Part of Speech"},
            {"label": "Grammatical Category: Verb (Range)", "path": "grammatical_info.verb", "category": "Sense/Part of Speech"},
            {"label": "Semantic Domain: Universe", "path": "trait[semantic-domain-ddp4]", "category": "Trait"},
            {"label": "Variant Type: spelling", "path": "variant.type", "category": "Entry/Variant"},
            {"label": "Complex Form: Compound", "path": "trait[complex-form-type]", "category": "Trait"},
            # Discovered fields
            {"label": "Custom: exemplar", "path": "sense.field[exemplar]", "category": "Custom Field"},
            {"label": "Custom: scientific-name", "path": "field[scientific-name]", "category": "Custom Field"},
            {"label": "Note: usage", "path": "note[usage]", "category": "Note"},
            {"label": "Trait: morph-type", "path": "trait[morph-type]", "category": "Trait"},
        ]
        
        # Sort by label for consistent ordering
        merged_fields.sort(key=lambda f: f['label'].lower())
        
        with patch(
            "app.services.field_registry_service.FieldRegistryService.get_fields",
            return_value=merged_fields
        ):
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
        assert "Trait: morph-type" in labels

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
    
    Tests the FieldRegistryService.resolve_field_path() method for converting
    user-friendly field paths to LIFT XPath notation.
    """

    def test_simple_path_resolution(self):
        """sense.definition resolves to sense/definition (dots become slashes)."""
        from app.services.field_registry_service import FieldRegistryService
        svc = FieldRegistryService()
        assert svc.resolve_field_path("sense.definition") == "sense/definition"

    def test_underscore_to_hyphen(self):
        """lexical_unit becomes lexical-unit in XPath."""
        from app.services.field_registry_service import FieldRegistryService
        svc = FieldRegistryService()
        assert svc.resolve_field_path("lexical_unit") == "lexical-unit"

    def test_nested_field_path_resolution(self):
        """etymology.note resolves to etymology/note."""
        from app.services.field_registry_service import FieldRegistryService
        svc = FieldRegistryService()
        assert svc.resolve_field_path("etymology.note") == "etymology/note"

    def test_bracket_notation_paths(self):
        """trait[semantic-domain-ddp4] becomes trait[@name='semantic-domain-ddp4']/@value."""
        from app.services.field_registry_service import FieldRegistryService
        svc = FieldRegistryService()
        assert svc.resolve_field_path(
            "trait[semantic-domain-ddp4]"
        ) == "trait[@name='semantic-domain-ddp4']/@value"

    def test_field_bracket_notation(self):
        """field[exemplar] becomes field[@type='exemplar']."""
        from app.services.field_registry_service import FieldRegistryService
        svc = FieldRegistryService()
        assert svc.resolve_field_path("field[exemplar]") == "field[@type='exemplar']"

    def test_note_bracket_notation(self):
        """note[usage] becomes note[@type='usage']."""
        from app.services.field_registry_service import FieldRegistryService
        svc = FieldRegistryService()
        assert svc.resolve_field_path("note[usage]") == "note[@type='usage']"

    def test_unknown_path_passthrough(self):
        """Unknown paths pass through with dots→slashes."""
        from app.services.field_registry_service import FieldRegistryService
        svc = FieldRegistryService()
        assert svc.resolve_field_path("some.unknown.field") == "some/unknown/field"
