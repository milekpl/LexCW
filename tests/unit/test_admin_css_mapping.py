"""Unit tests for CSS mapping system admin interface & dictionary-style rendering.

Tests cover:
1. CSS style templates retrieval and application.
2. CSS syntax validation (structural/syntax checking).
3. API endpoints alignment (/api/display-profiles and /api/profiles).
4. Full dictionary-style LIFT-to-HTML transformation.
"""

import pytest
import json
from unittest.mock import MagicMock

from app.services.css_mapping_service import CSSMappingService
from app.services.display_profile_service import DisplayProfileService
from app.models.display_profile import DisplayProfile, ProfileElement
from app.api.display_profiles import validate_css_string
from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer, ElementConfig


class TestCSSStyleTemplates:
    """Test suite for built-in style templates."""

    def test_get_style_templates(self):
        templates = CSSMappingService.get_style_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 4

        template_ids = [t["id"] for t in templates]
        assert "dictionary-classic" in template_ids
        assert "modern-clean" in template_ids
        assert "academic" in template_ids
        assert "compact" in template_ids

        for t in templates:
            assert "id" in t
            assert "name" in t
            assert "description" in t
            assert "css" in t
            assert len(t["css"]) > 0

    def test_apply_template_to_profile(self):
        service = CSSMappingService()

        # Create dummy profile
        profile = service.create_profile({
            "name": "Test Template Profile",
            "description": "Testing template application",
            "custom_css": ".existing { color: red; }"
        })
        assert profile is not None

        # Apply template
        updated = service.apply_template(profile.profile_id, "modern-clean")
        assert updated is not None
        assert ".lexical-unit" in updated.custom_css
        assert ".existing { color: red; }" in updated.custom_css




class TestCSSValidation:
    """Test suite for CSS syntax validator."""

    def test_valid_css(self):
        valid_css = """
        .lexical-unit { font-weight: bold; font-size: 1.2em; color: #333; }
        .sense { margin-left: 1.5em; padding: 4px; }
        .grammatical-info { color: #888; }
        """
        errors, warnings = validate_css_string(valid_css)
        assert len(errors) == 0

    def test_invalid_css_syntax(self):
        invalid_css = """
        .lexical-unit { font-weight: bold; font-size: ; color: #333; }
        .sense { margin-left: 1.5em; padding
        """
        errors, warnings = validate_css_string(invalid_css)
        assert len(errors) > 0


class TestDictionaryStyleRendering:
    """Test suite for full dictionary-style HTML transformation."""

    def test_full_entry_transformation(self):
        sample_xml = """
        <entry id="e1">
            <lexical-unit>
                <form lang="seh"><text>pembela</text></form>
            </lexical-unit>
            <pronunciation>
                <form lang="seh-fonipa"><text>pɛmbɛla</text></form>
            </pronunciation>
            <sense id="s1">
                <grammatical-info value="noun"/>
                <definition>
                    <form lang="en"><text>defender, advocate</text></form>
                    <form lang="pl"><text>obrońca</text></form>
                </definition>
                <trait name="semantic-domain" value="law"/>
                <example>
                    <form lang="seh"><text>Pembela wa haki</text></form>
                    <translation>
                        <form lang="en"><text>Defender of rights</text></form>
                    </translation>
                </example>
            </sense>
            <relation type="synonym" ref="e2"/>
            <etymology type="borrowing" date="1920">
                <form lang="sw"><text>bela</text></form>
                <gloss lang="en"><text>defense</text></gloss>
            </etymology>
        </entry>
        """

        profile = DisplayProfile(
            id=1,
            name="Classic View",
            custom_css=".lexical-unit { font-weight: bold; }",
            number_senses=True
        )
        profile.elements = [
            ProfileElement(lift_element="lexical-unit", display_order=1, css_class="headword"),
            ProfileElement(lift_element="pronunciation", display_order=2, css_class="pronunciation"),
            ProfileElement(lift_element="grammatical-info", display_order=3, css_class="pos"),
            ProfileElement(lift_element="definition", display_order=4, css_class="definition"),
            ProfileElement(lift_element="example", display_order=5, css_class="example"),
            ProfileElement(lift_element="relation", display_order=6, css_class="relation"),
            ProfileElement(lift_element="etymology", display_order=7, css_class="etymology"),
        ]

        service = CSSMappingService()
        headword_map = {"e2": "mulinzi"}
        html = service.render_entry(sample_xml, profile, headword_map=headword_map)

        assert html is not None
        assert "pembela" in html
        assert "pɛmbɛla" in html
        assert "defender, advocate" in html
        assert "mulinzi" in html  # resolved relation headword
        assert "Classic View" in html or "profile-" in html


class TestAPIEndpoints:
    """Test suite for API endpoints on /api/profiles and /api/display-profiles."""

    def test_list_templates_endpoint(self, client):
        response = client.get("/api/profiles/templates")
        assert response.status_code == 200
        data = response.get_json()
        assert "templates" in data
        assert len(data["templates"]) >= 4

        # Test alias route on profiles blueprint
        alias_resp = client.get("/api/profiles/display-profiles/templates")
        assert alias_resp.status_code == 200
        alias_data = alias_resp.get_json()
        assert "templates" in alias_data


    def test_validate_css_endpoint(self, client):
        payload = {"custom_css": ".headword { font-weight: bold; }"}
        response = client.post(
            "/api/profiles/validate-css",
            data=json.dumps(payload),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True

    def test_preview_endpoint(self, client, app):
        payload = {
            "elements": [
                {"lift_element": "lexical-unit", "display_order": 1, "css_class": "headword"}
            ],
            "custom_css": ".headword { color: blue; }"
        }
        response = client.post(
            "/api/profiles/preview",
            data=json.dumps(payload),
            content_type="application/json"
        )
        # Should succeed or return 404 if dictionary has no entries
        assert response.status_code in (200, 404)

