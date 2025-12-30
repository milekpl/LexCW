"""Integration tests for Field Visibility Modal functionality."""
import pytest
from bs4 import BeautifulSoup


class TestFieldVisibilityModal:
    """Test cases for the Field Visibility Modal feature."""

    def test_macro_file_exists(self):
        """Test that the field visibility modal macro file exists."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        assert os.path.exists(macro_path), f"Macro file not found at {macro_path}"

    def test_macro_file_not_empty(self):
        """Test that the macro file is not empty."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        with open(macro_path, 'r') as f:
            content = f.read()
        assert len(content) > 100, "Macro file is empty or too small"

    def test_macro_has_required_sections(self):
        """Test that the macro defines all required sections."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        with open(macro_path, 'r') as f:
            content = f.read()

        # Check for required sections
        assert 'basic-info' in content, "basic-info section not found"
        assert 'custom-fields' in content, "custom-fields section not found"
        assert 'notes' in content, "notes section not found"
        assert 'pronunciation' in content, "pronunciation section not found"
        assert 'variants' in content, "variants section not found"
        assert 'direct-variants' in content, "direct-variants section not found"
        assert 'relations' in content, "relations section not found"
        assert 'senses' in content, "senses section not found"

    def test_macro_has_modal_structure(self):
        """Test that the macro has proper modal structure."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        with open(macro_path, 'r') as f:
            content = f.read()

        # Check for Bootstrap modal structure
        assert 'modal-dialog' in content, "modal-dialog not found"
        assert 'modal-content' in content, "modal-content not found"
        assert 'modal-header' in content, "modal-header not found"
        assert 'modal-body' in content, "modal-body not found"
        assert 'modal-footer' in content, "modal-footer not found"

    def test_macro_has_checkboxes(self):
        """Test that the macro has checkboxes for visibility toggles."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        with open(macro_path, 'r') as f:
            content = f.read()

        assert 'field-visibility-toggle' in content, "field-visibility-toggle class not found"
        assert 'data-section-id' in content, "data-section-id attribute not found"
        assert 'data-target' in content, "data-target attribute not found"

    def test_macro_has_action_buttons(self):
        """Test that the macro has action buttons."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        with open(macro_path, 'r') as f:
            content = f.read()

        assert 'reset-field-visibility-btn' in content, "reset button not found"
        assert 'hide-empty-sections-btn' in content, "hide empty button not found"
        assert 'show-all-sections-btn' in content, "show all button not found"


class TestFieldVisibilityJavaScript:
    """Test cases for the FieldVisibilityManager JavaScript class."""

    def test_js_file_exists(self, client):
        """Test that the field-visibility-manager.js file is served."""
        response = client.get('/static/js/field-visibility-manager.js')
        assert response.status_code == 200
        assert b'FieldVisibilityManager' in response.data

    def test_js_class_exports(self, client):
        """Test that the JS class is properly exported."""
        response = client.get('/static/js/field-visibility-manager.js')
        js_code = response.data.decode('utf-8')

        assert 'window.FieldVisibilityManager = FieldVisibilityManager' in js_code
        assert 'class FieldVisibilityManager' in js_code

    def test_js_has_required_methods(self, client):
        """Test that the JS class has required methods."""
        response = client.get('/static/js/field-visibility-manager.js')
        js_code = response.data.decode('utf-8')

        required_methods = [
            'setSectionVisibility',
            'getSettings',
            'updateSettings',
            'isVisible',
            'toggle',
            'resetToDefaults',
            'showAllSections'
        ]

        for method in required_methods:
            assert f'{method}(' in js_code, f"Method {method} not found"

    def test_js_uses_custom_events(self, client):
        """Test that the JS class uses CustomEvents for communication."""
        response = client.get('/static/js/field-visibility-manager.js')
        js_code = response.data.decode('utf-8')

        assert 'CustomEvent' in js_code
        assert 'fieldVisibilityChanged' in js_code
        assert 'dispatchEvent' in js_code

    def test_js_handles_localstorage(self, client):
        """Test that the JS class handles localStorage."""
        response = client.get('/static/js/field-visibility-manager.js')
        js_code = response.data.decode('utf-8')

        assert 'localStorage' in js_code
        assert 'getItem' in js_code
        assert 'setItem' in js_code


class TestDirectVariantsJavaScript:
    """Test cases for the DirectVariantsManager JavaScript class."""

    def test_js_file_exists(self, client):
        """Test that the direct-variants.js file is served."""
        response = client.get('/static/js/direct-variants.js')
        assert response.status_code == 200
        assert b'DirectVariantsManager' in response.data

    def test_js_class_exports(self, client):
        """Test that the JS class is properly exported."""
        response = client.get('/static/js/direct-variants.js')
        js_code = response.data.decode('utf-8')

        assert 'window.DirectVariantsManager = DirectVariantsManager' in js_code
        assert 'class DirectVariantsManager' in js_code

    def test_js_has_required_methods(self, client):
        """Test that the JS class has required methods."""
        response = client.get('/static/js/direct-variants.js')
        js_code = response.data.decode('utf-8')

        required_methods = [
            'add',
            'remove',
            'reindex',
            'addLanguage',
            'addTrait',
            'addGrammaticalTrait',
            'getCount'
        ]

        for method in required_methods:
            assert f'{method}(' in js_code, f"Method {method} not found"

    def test_js_uses_custom_events(self, client):
        """Test that the JS class emits events."""
        response = client.get('/static/js/direct-variants.js')
        js_code = response.data.decode('utf-8')

        assert 'CustomEvent' in js_code
        assert 'directVariants:' in js_code


class TestEntryFormTemplateFile:
    """Test cases for entry form template file structure."""

    def test_entry_form_has_field_settings_button(self):
        """Test that entry form template has the field settings button."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'Field Settings' in content, "Field Settings button not found"
        assert 'fieldVisibilityModal' in content, "fieldVisibilityModal reference not found"

    def test_entry_form_imports_macro(self):
        """Test that entry form imports the field visibility modal macro."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'field_visibility_modal' in content, "field_visibility_modal import not found"

    def test_entry_form_includes_field_visibility_js(self):
        """Test that entry form includes the field visibility JS."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'field-visibility-manager.js' in content, "field-visibility-manager.js not found"

    def test_entry_form_includes_direct_variants_js(self):
        """Test that entry form includes the direct variants JS."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'direct-variants.js' in content, "direct-variants.js not found"

    def test_entry_form_has_field_sections(self):
        """Test that entry form has field sections with correct classes."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # The entry form includes partials that contain the section classes
        # Check that partials are included
        assert '_basic_info.html' in content, "_basic_info.html include not found"
        assert '_custom_fields.html' in content, "_custom_fields.html include not found"
        assert '_notes.html' in content, "_notes.html include not found"
        assert '_pronunciations.html' in content, "_pronunciations.html include not found"
        assert '_variants.html' in content, "_variants.html include not found"
        assert '_direct_variants.html' in content, "_direct_variants.html include not found"
        assert '_relations.html' in content, "_relations.html include not found"
        assert '_senses.html' in content, "_senses.html include not found"

    def test_entry_form_includes_field_visibility_initialization(self):
        """Test that entry form initializes FieldVisibilityManager."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'FieldVisibilityManager' in content, "FieldVisibilityManager not found in template"
        assert 'window.fieldVisibilityManager' in content, "window.fieldVisibilityManager not found"


class TestEntryFormTemplateIntegration:
    """Integration tests for entry form template with real routes."""

    def test_entries_list_page_has_javascript_files(self, client):
        """Test that entries list page loads (used for JS file verification)."""
        response = client.get('/entries')
        assert response.status_code == 200

        html = response.data.decode('utf-8')
        # The entries list page should have the static files
        assert '.js' in html or '/static/' in html

    def test_entries_page_includes_field_visibility_manager_on_page(self, client):
        """Test that field visibility manager can be loaded."""
        # First verify the JS file is served
        response = client.get('/static/js/field-visibility-manager.js')
        assert response.status_code == 200

        js_code = response.data.decode('utf-8')
        # Verify it's valid JavaScript by checking for class definition
        assert 'class FieldVisibilityManager' in js_code

    def test_direct_variants_js_is_valid(self, client):
        """Test that direct-variants.js is valid JavaScript."""
        response = client.get('/static/js/direct-variants.js')
        assert response.status_code == 200

        js_code = response.data.decode('utf-8')
        # Verify it's valid JavaScript by checking for class definition
        assert 'class DirectVariantsManager' in js_code


class TestFieldVisibilityCheckboxData:
    """Test data attributes on field visibility checkboxes."""

    def test_checkboxes_have_section_ids(self):
        """Test that checkboxes have correct data-section-id attributes."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        with open(macro_path, 'r') as f:
            content = f.read()

        # Check for the macro template patterns (these are Jinja2 templates that will be rendered)
        # The actual values are in the sections list
        assert "'basic-info'" in content or '"basic-info"' in content
        assert "'custom-fields'" in content or '"custom-fields"' in content
        assert "'notes'" in content or '"notes"' in content
        assert "'pronunciation'" in content or '"pronunciation"' in content
        assert "'variants'" in content or '"variants"' in content
        assert "'direct-variants'" in content or '"direct-variants"' in content
        assert "'relations'" in content or '"relations"' in content
        assert "'senses'" in content or '"senses"' in content

    def test_checkboxes_have_targets(self):
        """Test that checkboxes have correct data-target attributes."""
        import os
        macro_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'macros', 'field_visibility_modal.html'
        )
        with open(macro_path, 'r') as f:
            content = f.read()

        # Check for the macro template patterns (these are Jinja2 templates)
        # The actual values are in the sections list
        assert "'.basic-info-section'" in content
        assert "'.custom-fields-section'" in content
        assert "'.notes-section'" in content
        assert "'.pronunciation-section'" in content
        assert "'.variants-section'" in content
        assert "'.direct-variants-section'" in content
        assert "'.relations-section'" in content
        assert "'.senses-section'" in content
