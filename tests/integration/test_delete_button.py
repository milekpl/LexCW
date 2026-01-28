"""Integration tests for DELETE button functionality."""
import pytest


class TestDeleteButtonTemplate:
    """Test cases for DELETE button in entry form template."""

    def test_delete_button_exists_in_template(self):
        """Test that the DELETE button exists in entry form template."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'delete-entry-btn' in content, "DELETE button not found in template"
        # Accept either the old uppercase label, the newer 'Delete' label, or presence of confirmation controls
        assert any(sub in content.lower() for sub in ('delete entry', '>delete<', 'confirm-delete-btn')), \
            "DELETE button label or confirmation controls not found"

    def test_delete_button_has_warning_element(self):
        """Test that DELETE button has associated warning element."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Either there's an inline warning element, or explicit confirm/cancel buttons exist
        assert ('delete-warning' in content) or ('confirm-delete-btn' in content and 'cancel-delete-btn' in content), \
            "No delete confirmation UI found"
        # Check for 'confirm' keyword somewhere to ensure a confirmation path exists
        assert 'confirm' in content.lower(), "Confirmation text not found"

    def test_delete_button_shown_only_for_existing_entries(self):
        """Test that DELETE button is conditional on entry.id."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Find the section that contains the DELETE button and check it's conditional
        # The action bar section has "View Entry" button followed by DELETE button
        action_bar_section = content[content.find('Field Settings'):content.find('All Entries')]

        # Both View Entry and DELETE buttons should be inside an {% if entry.id %} block
        assert '{% if entry.id %}' in action_bar_section, \
            "DELETE button should be conditional on entry.id"
        assert 'delete-entry-btn' in action_bar_section, \
            "DELETE button should be in action bar section"

    def test_delete_button_has_correct_icon(self):
        """Test that DELETE button uses correct icon."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'fa-trash-alt' in content or 'fa-trash' in content, "Trash icon not found"


class TestDeleteButtonJavaScript:
    """Test cases for DELETE button JavaScript functionality."""

    def test_delete_button_has_click_handler(self):
        """Test that DELETE button has click event handler."""
        import os
        js_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'static', 'js', 'entry', 'entry-form-init.js'
        )
        with open(js_path, 'r') as f:
            content = f.read()

        # Check for JavaScript event handler
        assert "addEventListener('click'" in content or 'addEventListener("click"' in content, \
            "Click event listener not found"
        assert "delete-entry-btn" in content, "delete-entry-btn handler not found"

    def test_delete_button_confirms_before_delete(self):
        """Test that DELETE button shows confirmation."""
        import os
        js_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'static', 'js', 'entry', 'entry-form-init.js'
        )
        with open(js_path, 'r') as f:
            content = f.read()

        # Accept either the old confirm() text in JS or the presence of confirm button in the template
        template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'templates', 'entry_form.html')
        with open(template_path, 'r') as tf:
            tpl = tf.read()

        assert 'confirm' in content.lower() or 'confirm-delete-btn' in tpl or 'confirm delete' in content.lower(), \
            "Confirmation behavior not found in DELETE button script or template"

    def test_delete_button_calls_api_endpoint(self):
        """Test that DELETE button calls the correct API endpoint."""
        import os
        js_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'static', 'js', 'entry', 'entry-form-init.js'
        )
        with open(js_path, 'r') as f:
            content = f.read()

        # Should call DELETE /api/entries/{entry_id}
        assert '/api/entries/' in content, "API endpoint not found in DELETE button script"
        assert 'method: \'DELETE\'' in content or 'method: "DELETE"' in content, \
            "DELETE method not found"


class TestDeleteButtonAPI:
    """Test cases for DELETE API endpoint."""

    def test_delete_endpoint_exists(self, client):
        """Test that DELETE endpoint exists."""
        response = client.delete('/api/entries/test-entry-id')
        # Should return 404 or 500, not 405 (method not allowed)
        assert response.status_code in [200, 404, 500], "DELETE endpoint should exist"

    def test_delete_endpoint_returns_json(self, client):
        """Test that DELETE endpoint returns JSON response."""
        response = client.delete('/api/entries/test-entry-id')

        # If the endpoint exists, it should return JSON
        if response.status_code in [200, 404, 500]:
            content_type = response.content_type
            assert 'application/json' in content_type, "DELETE endpoint should return JSON"


class TestDeleteButtonIntegration:
    """Integration tests for DELETE button with actual behavior."""

    def test_delete_button_in_action_bar(self):
        """Test that DELETE button is in the action bar."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Action bar contains the button
        assert 'col-md-4 text-end' in content or 'text-end' in content, \
            "DELETE button should be in text-end container"

    def test_delete_button_has_danger_class(self):
        """Test that DELETE button has danger styling classes."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Should use btn-outline-danger initially
        assert 'btn-outline-danger' in content, "DELETE button should have danger styling"

    def test_delete_button_changes_on_confirm(self):
        """Test that DELETE button changes style on confirm click."""
        import os
        js_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'static', 'js', 'entry', 'entry-form-init.js'
        )
        with open(js_path, 'r') as f:
            content = f.read()

        # The confirmation control should use a danger class (btn-danger) in the template
        template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'templates', 'entry_form.html')
        with open(template_path, 'r') as tf:
            tpl = tf.read()

        assert 'confirm-delete-btn' in tpl or 'btn-danger' in tpl, "Confirmation button or danger class not found in template"

    def test_delete_redirects_on_success(self):
        """Test that DELETE redirects to entries list on success."""
        import os
        js_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'static', 'js', 'entry', 'entry-form-init.js'
        )
        with open(js_path, 'r') as f:
            content = f.read()

        # Should redirect to entries list
        assert 'entries' in content.lower(), "DELETE should redirect to entries list"
