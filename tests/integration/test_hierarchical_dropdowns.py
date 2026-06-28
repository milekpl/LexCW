"""Integration tests for range-backed dropdowns (Alpine.js variant).

After the Alpine refactor, range-backed selects use Alpine's loadRanges()
→ flattenRangeValues() → x-for with :key on <option> elements. The old
Select2 + data-hierarchical + dynamic-lift-range patterns are replaced.
"""
import pytest
import os


_ENTRY_FORM_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'templates')
_ALPINE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'static', 'js', 'alpine')


def _read_template(name):
    with open(os.path.join(_ENTRY_FORM_DIR, name), 'r') as f:
        return f.read()


class TestAlpineRangeDropdowns:
    """Alpine components load ranges asynchronously and render via x-for."""

    def test_sense_tree_has_domain_type_options(self):
        """senseTree exposes domainTypeOptions from rangeData['domain-type']."""
        content = _read_template('entry_form_partials/_senses.html')
        assert 'domainTypeOptions' in content

    def test_sense_tree_has_usage_type_options(self):
        """senseTree exposes usageTypeOptions from rangeData['usage-type']."""
        content = _read_template('entry_form_partials/_senses.html')
        assert 'usageTypeOptions' in content

    def test_sense_tree_has_semantic_domain_options(self):
        """senseTree exposes semanticDomainOptions from rangeData['semantic-domain-ddp4']."""
        content = _read_template('entry_form_partials/_senses.html')
        assert 'semanticDomainOptions' in content

    def test_sense_tree_supports_multiple_select(self):
        """Domain type and usage type use Alpine's multiple select with arrays."""
        with open(os.path.join(_ALPINE_DIR, 'sense-tree.js'), 'r') as f:
            js_code = f.read()
        assert 'domainType' in js_code
        assert 'usageType' in js_code

    def test_entry_relations_has_lexical_relation_options(self):
        """entryRelations exposes relationTypeOptions from rangeData['lexical-relation']."""
        content = _read_template('entry_form_partials/_relations.html')
        assert 'relationTypeOptions' in content

    def test_entry_variant_relations_has_variant_type_options(self):
        """entryVariantRelations exposes variantTypeOptions from rangeData['variant-type']."""
        content = _read_template('entry_form_partials/_variants.html')
        assert 'variantTypeOptions' in content


class TestRangesLoaderJavaScript:
    """Test cases for RangesLoader JavaScript class."""

    def test_ranges_loader_js_file_exists(self, client):
        """Test that the ranges-loader.js file is served."""
        response = client.get('/static/js/ranges-loader.js')
        assert response.status_code == 200
        assert b'RangesLoader' in response.data

    def test_ranges_loader_has_load_range_method(self, client):
        """Test that RangesLoader has loadRange method (used by Alpine components)."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'loadRange' in js_code, "loadRange method not found"

    def test_ranges_loader_has_flatten_parents_option(self, client):
        """Test that RangesLoader has flattenParents option."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'flattenParents' in js_code, "flattenParents option not found"

    def test_ranges_loader_uses_caching(self, client):
        """Test that RangesLoader caches loaded ranges."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'cache' in js_code or 'Cache' in js_code, "caching not found"


class TestEntryFormTemplate:
    """Test cases for entry form template — Alpine-era patterns."""

    def test_entry_form_includes_ranges_loader(self):
        """Test that entry form includes ranges-loader.js."""
        content = _read_template('entry_form.html')
        assert 'ranges-loader.js' in content, "ranges-loader.js not included"

    def test_entry_form_includes_alpine_components(self):
        """Test that entry form includes Alpine component scripts."""
        content = _read_template('entry_form.html')
        assert 'sense-tree.js' in content
        assert 'alpine-to-serializer.js' in content
        assert 'normalize-entry.js' in content

    def test_entry_form_registers_senses_section(self):
        """Test that merge harness registers senses."""
        content = _read_template('entry_form.html')
        assert "registerAlpineSection('senses')" in content

    def test_entry_form_includes_entry_relations(self):
        """Test that entry form includes the entry-relations Alpine component."""
        content = _read_template('entry_form.html')
        assert 'entry-relations.js' in content
        assert "registerAlpineSection('relations')" in content

    def test_entry_form_includes_entry_variant_relations(self):
        """Test that entry form includes the entry-variant-relations Alpine component."""
        content = _read_template('entry_form.html')
        assert 'entry-variant-relations.js' in content
        assert "registerAlpineSection('variant_relations')" in content

    def test_entry_form_includes_entry_direct_variants(self):
        """Test that entry form includes the entry-direct-variants Alpine component."""
        content = _read_template('entry_form.html')
        assert 'entry-direct-variants.js' in content
        assert "registerAlpineSection('variants')" in content


class TestAlpineSenseTreeJS:
    """Tests for the sense-tree.js Alpine component source."""

    def test_loadRanges_exists(self):
        with open(os.path.join(_ALPINE_DIR, 'sense-tree.js'), 'r') as f:
            js_code = f.read()
        assert 'loadRanges' in js_code
        assert 'flattenRangeValues' in js_code

    def test_range_data_keys(self):
        with open(os.path.join(_ALPINE_DIR, 'sense-tree.js'), 'r') as f:
            js_code = f.read()
        assert 'grammatical-info' in js_code
        assert 'domain-type' in js_code
        assert 'lexical-relation' in js_code
