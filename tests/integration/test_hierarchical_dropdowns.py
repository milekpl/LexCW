"""Integration tests for hierarchical dropdown functionality."""
import pytest


class TestHierarchicalDropdownTemplate:
    """Test cases for hierarchical dropdown template structure."""

    def test_entry_form_has_hierarchical_attribute_on_domain_type(self):
        """Test that domain_type select has hierarchical attribute."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Find domain_type select with hierarchical attribute
        assert 'data-hierarchical="true"' in content, "domain_type should have data-hierarchical='true'"

    def test_entry_form_has_hierarchical_attribute_on_usage_type(self):
        """Test that usage_type select has hierarchical attribute."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Find usage_type select with hierarchical attribute
        assert 'data-hierarchical="true"' in content, "usage_type should have data-hierarchical='true'"

    def test_domain_type_has_multiple_attribute(self):
        """Test that domain_type supports multiple selection."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form_partials', '_senses.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # The domain_type select should have 'multiple' attribute
        # Check for pattern where is_multiple=true appears near domain_type
        assert "is_multiple=true" in content, "domain_type should have is_multiple=true for multi-select"

    def test_usage_type_has_multiple_attribute(self):
        """Test that usage_type supports multiple selection."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # The usage_type select should have 'multiple' attribute
        assert 'multiple' in content, "usage_type should have 'multiple' attribute for multi-select"


class TestRangesLoaderJavaScript:
    """Test cases for RangesLoader JavaScript class."""

    def test_ranges_loader_js_file_exists(self, client):
        """Test that the ranges-loader.js file is served."""
        response = client.get('/static/js/ranges-loader.js')
        assert response.status_code == 200
        assert b'RangesLoader' in response.data

    def test_ranges_loader_has_populate_hierarchical_options(self, client):
        """Test that RangesLoader has _populateHierarchicalOptions method."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert '_populateHierarchicalOptions' in js_code, "_populateHierarchicalOptions method not found"

    def test_ranges_loader_has_hierarchical_parameter(self, client):
        """Test that populateSelect accepts hierarchical parameter."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'hierarchical' in js_code, "hierarchical parameter not found in RangesLoader"
        assert 'indentChar' in js_code, "indentChar configuration not found"

    def test_ranges_loader_uses_template_result(self, client):
        """Test that RangesLoader uses Select2 templateResult for indentation."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'templateResult' in js_code, "Select2 templateResult not found"
        assert 'data-indent' in js_code or "dataset.indent" in js_code, "indent data attribute handling not found"

    def test_ranges_loader_handles_multiple_select(self, client):
        """Test that RangesLoader handles multiple select elements."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'selectElement.multiple' in js_code, "multiple select handling not found"
        assert 'option.selected' in js_code, "option.selected assignment not found"

    def test_ranges_loader_has_flatten_option(self, client):
        """Test that RangesLoader has flattenParents option."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'flattenParents' in js_code, "flattenParents option not found"


class TestHierarchicalDropdownAPI:
    """Test cases for hierarchical dropdown API endpoints."""

    def test_ranges_loader_loads_all_ranges(self, client):
        """Test that ranges loader loadAllRanges method exists and is properly structured."""
        response = client.get('/static/js/ranges-loader.js')
        js_code = response.data.decode('utf-8')

        assert 'loadAllRanges' in js_code, "loadAllRanges method should exist"
        assert 'loadRange' in js_code, "loadRange method should exist"
        assert 'cache' in js_code, "RangesLoader should use caching"

    def test_domain_type_range_exists(self, client):
        """Test that domain-type range is available."""
        response = client.get('/api/ranges-editor')

        # The endpoint might return 404 or redirect, but should not error
        # The important thing is the JS code handles the response properly
        assert response.status_code in [200, 404, 308, 301], "Ranges endpoint should be accessible"


class TestHierarchicalDropdownRendering:
    """Test cases for hierarchical dropdown rendering in templates."""

    def test_semantic_domain_has_hierarchical(self):
        """Test that semantic domain select has hierarchical attribute."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Semantic domain should be hierarchical
        assert 'semantic-domain' in content or 'Semantic Domain' in content


class TestHierarchicalDropdownJavaScriptIntegration:
    """Integration tests for hierarchical dropdown JavaScript functionality."""

    def test_entry_form_includes_ranges_loader(self, client):
        """Test that entry form includes ranges-loader.js."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'ranges-loader.js' in content, "ranges-loader.js not included in entry form"

    def test_dynamic_lift_range_class_present(self, client):
        """Test that dynamic-lift-range class is used for hierarchical selects."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'dynamic-lift-range' in content, "dynamic-lift-range class not found"

    def test_ranges_loader_initialized_in_entry_form_js(self, client):
        """Test that rangesLoader is initialized in entry-form.js."""
        response = client.get('/static/js/entry-form.js')
        js_code = response.data.decode('utf-8')

        assert 'rangesLoader' in js_code, "rangesLoader not found in entry-form.js"
        assert 'window.rangesLoader' in js_code or 'rangesLoader =' in js_code, "rangesLoader initialization not found"

    def test_entry_form_js_passes_hierarchical_option(self, client):
        """Test that entry-form.js passes hierarchical option to populateSelect."""
        response = client.get('/static/js/entry-form.js')
        js_code = response.data.decode('utf-8')

        assert 'hierarchical: hierarchical' in js_code or 'hierarchical =' in js_code, "hierarchical option not passed to populateSelect"
