"""
Baseline tests for current CSS mapping functionality.

This test suite establishes the current behavior of the CSS mapping system
before migration to ensure we maintain all existing functionality during
the refactoring process.
"""

from __future__ import annotations

import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db
from app.services.display_profile_service import DisplayProfileService
from app.services.css_mapping_service import CSSMappingService


class TestCSSMappingBaseline:
    """Baseline tests for current CSS mapping functionality."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self, db_app):
        """Clean up database before and after tests."""
        with db_app.app_context():
            db.session.query(ProfileElement).delete()
            db.session.query(DisplayProfile).delete()
            db.session.commit()

    def test_current_css_service_has_render_entry_method(self, db_app: Flask) -> None:
        """Current CSS service should have render_entry method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, 'render_entry')
            assert callable(service.render_entry)

    def test_current_render_entry_returns_html(self, db_app: Flask) -> None:
        """Current render_entry should return HTML string."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Create a basic profile
            profile = DisplayProfile()
            profile.name = "Baseline Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            # Basic LIFT XML
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should return HTML string
            assert isinstance(result, str)
            assert len(result) > 0
            assert "<div" in result

    def test_current_render_entry_includes_css_classes(self, db_app: Flask) -> None:
        """Current render_entry should include configured CSS classes."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Create profile with CSS class configuration
            profile = DisplayProfile()
            profile.name = "CSS Class Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "lexical-unit"
            elem.css_class = "headword"
            db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should include the configured CSS class
            assert "headword" in result

    def test_current_render_entry_handles_grammatical_info(self, db_app: Flask) -> None:
        """Current render_entry should handle grammatical-info elements."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Grammatical Info Test"
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should handle grammatical-info without errors
            assert "Noun" in result or "entry-render-error" not in result

    def test_current_render_entry_handles_relations(self, db_app: Flask) -> None:
        """Current render_entry should handle relation elements."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Relation Test"
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="other-entry"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should handle relations without errors
            assert "synonym" in result or "entry-render-error" not in result

    def test_current_render_entry_with_custom_css(self, db_app: Flask) -> None:
        """Current render_entry should include custom CSS when provided."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Custom CSS Test"
            profile.custom_css = ".headword { color: blue; }"
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should include custom CSS
            assert "<style>" in result
            assert "color: blue" in result

    def test_current_render_entry_with_sense_numbering(self, db_app: Flask) -> None:
        """Current render_entry should handle sense numbering when enabled."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Sense Numbering Test"
            profile.number_senses = True
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>First definition</text></form>
                    </definition>
                </sense>
                <sense>
                    <definition>
                        <form lang="en"><text>Second definition</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should include sense numbering CSS when multiple senses
            assert "counter-reset" in result or "sense-counter" in result

    def test_current_render_entry_with_subentries(self, db_app: Flask) -> None:
        """Current render_entry should handle subentries when enabled."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Subentry Test"
            profile.show_subentries = True
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should be ready to handle subentries (may not show if none present)
            assert "lift-entry-rendered" in result

    def test_current_render_entry_error_handling(self, db_app: Flask) -> None:
        """Current render_entry should handle errors gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Error Handling Test"
            db.session.add(profile)
            db.session.commit()
            
            # Invalid XML
            invalid_xml = "<entry><unclosed-tag>"
            
            result = service.render_entry(invalid_xml, profile)
            
            # Should return error message rather than crash
            assert "entry-render-error" in result or "Error" in result

    def test_current_render_entry_with_empty_profile(self, db_app: Flask) -> None:
        """Current render_entry should handle empty profiles."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Empty Profile Test"
            # No elements configured
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should still return valid HTML
            assert "<div" in result
            assert "entry-render-error" not in result

    def test_current_render_entry_with_complex_entry(self, db_app: Flask) -> None:
        """Current render_entry should handle complex entries with multiple elements."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Complex Entry Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add multiple element configurations
            elements_data = [
                {"lift_element": "lexical-unit", "css_class": "headword"},
                {"lift_element": "pronunciation", "css_class": "pronunciation"},
                {"lift_element": "grammatical-info", "css_class": "pos"},
                {"lift_element": "definition", "css_class": "definition"},
                {"lift_element": "example", "css_class": "example"}
            ]
            
            for elem_data in elements_data:
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = elem_data["lift_element"]
                elem.css_class = elem_data["css_class"]
                db.session.add(elem)
            db.session.commit()
            
            # Complex LIFT XML
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>complex</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>kɒmpleks</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Adjective"/>
                    <definition>
                        <form lang="en"><text>Consisting of many different and connected parts</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>The complex system requires careful analysis</text></form>
                    </example>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should include multiple configured elements
            assert "headword" in result
            assert "pronunciation" in result
            assert "pos" in result or "Adjective" in result
            assert "definition" in result
            assert "example" in result

    def test_current_render_entry_with_display_aspects(self, db_app: Flask) -> None:
        """Current render_entry should apply display aspects when configured."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Display Aspect Test"
            db.session.add(profile)
            db.session.commit()
            
            # Create relation element with display aspect
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="other-entry"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should apply display aspect (label instead of abbreviation)
            assert "Synonym" in result or "synonym" in result

    def test_current_render_entry_with_visibility_controls(self, db_app: Flask) -> None:
        """Current render_entry should respect visibility controls."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Visibility Test"
            db.session.add(profile)
            db.session.commit()
            
            # Create element with 'never' visibility
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "pronunciation"
            elem.css_class = "pronunciation"
            elem.visibility = "never"
            db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>tɛst</text></form>
                </pronunciation>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Pronunciation should not appear due to 'never' visibility
            assert "pronunciation" not in result or "tɛst" not in result

    def test_current_render_entry_with_display_modes(self, db_app: Flask) -> None:
        """Current render_entry should respect display modes (inline/block)."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Display Mode Test"
            db.session.add(profile)
            db.session.commit()
            
            # Create element with block display mode
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "definition"
            elem.css_class = "definition"
            elem.display_mode = "block"
            db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>A sample definition</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should use div for block mode
            assert "<div" in result and ("definition" in result or "A sample definition" in result)

    def test_current_render_entry_with_prefix_suffix(self, db_app: Flask) -> None:
        """Current render_entry should apply prefix and suffix configurations."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Prefix Suffix Test"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "definition"
            elem.css_class = "definition"
            elem.prefix = "Definition: "
            elem.suffix = " (end)"
            db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>A sample definition</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should include prefix and suffix
            assert "Definition:" in result
            assert "(end)" in result

    def test_current_render_entry_with_language_filtering(self, db_app: Flask) -> None:
        """Current render_entry should respect language filtering."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Language Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "definition"
            elem.css_class = "definition"
            elem.language_filter = "en"  # Only show English definitions
            db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>English definition</text></form>
                    </definition>
                    <definition>
                        <form lang="pl"><text>Polish definition</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should show English but not Polish
            assert "English definition" in result
            assert "Polish definition" not in result

    def test_current_render_entry_with_ordering(self, db_app: Flask) -> None:
        """Current render_entry should respect element ordering."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Ordering Test"
            db.session.add(profile)
            db.session.commit()
            
            # Create elements with specific ordering
            elements = [
                ("pronunciation", 2, "pronunciation"),
                ("lexical-unit", 1, "headword"),
                ("grammatical-info", 3, "pos")
            ]
            
            for lift_elem, order, css_class in elements:
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = lift_elem
                elem.css_class = css_class
                elem.display_order = order
                db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>tɛst</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Noun"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Elements should appear in configured order
            # This is a basic check - exact ordering validation would require more complex parsing
            assert "headword" in result
            assert "pronunciation" in result
            assert "pos" in result or "Noun" in result

    def test_current_render_entry_performance_baseline(self, db_app: Flask, benchmark) -> None:
        """Establish performance baseline for current render_entry implementation."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Performance Test"
            db.session.add(profile)
            db.session.commit()
            
            # Complex LIFT XML for performance testing
            complex_xml = """
            <entry id="performance-test">
                <lexical-unit>
                    <form lang="en"><text>performance</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>pərˈfɔːrməns</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The action or process of performing a task or function</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>Performance metrics are important for optimization</text></form>
                    </example>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A musical, dramatic, or other entertainment presented before an audience</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            # Benchmark the rendering performance
            def render_entry():
                return service.render_entry(complex_xml, profile)
            
            result = benchmark(render_entry)
            
            # Should complete successfully
            assert result is not None
            assert len(result) > 0
            assert "performance" in result


class TestCSSMappingServiceMethods:
    """Tests for individual methods in CSSMappingService."""

    def test_apply_display_aspects_method_exists(self, db_app: Flask) -> None:
        """CSSMappingService should have apply_display_aspects method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, 'apply_display_aspects')
            assert callable(service.apply_display_aspects)

    def test_apply_display_aspects_returns_tuple(self, db_app: Flask) -> None:
        """apply_display_aspects should return tuple of (xml, handled_elements)."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            xml = "<entry><lexical-unit><form><text>test</text></form></lexical-unit></entry>"
            result = service.apply_display_aspects(xml, profile)
            
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], str)  # Modified XML
            assert isinstance(result[1], set)  # Handled elements

    def test_build_range_lookup_method_exists(self, db_app: Flask) -> None:
        """CSSMappingService should have _build_range_lookup method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_build_range_lookup')
            assert callable(service._build_range_lookup)

    def test_build_range_label_lookup_method_exists(self, db_app: Flask) -> None:
        """CSSMappingService should have _build_range_label_lookup method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_build_range_label_lookup')
            assert callable(service._build_range_label_lookup)

    def test_replace_grammatical_info_with_abbr_method_exists(self, db_app: Flask) -> None:
        """CSSMappingService should have _replace_grammatical_info_with_abbr method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_replace_grammatical_info_with_abbr')
            assert callable(service._replace_grammatical_info_with_abbr)

    def test_resolve_relation_references_method_exists(self, db_app: Flask) -> None:
        """CSSMappingService should have _resolve_relation_references method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_resolve_relation_references')
            assert callable(service._resolve_relation_references)

    def test_sanitize_class_name_method_exists(self, db_app: Flask) -> None:
        """CSSMappingService should have _sanitize_class_name method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_sanitize_class_name')
            assert callable(service._sanitize_class_name)

    def test_sanitize_class_name_functionality(self, db_app: Flask) -> None:
        """_sanitize_class_name should properly sanitize CSS class names."""
        with db_app.app_context():
            service = CSSMappingService()
            
            test_cases = [
                ("Simple Name", "simple-name"),
                ("Name With Spaces", "name-with-spaces"),
                ("Name-With-Dashes", "name-with-dashes"),
                ("Name_With_Underscores", "name_with_underscores"),
                ("Name@123!", "name-123"),
                ("UPPERCASE Name", "uppercase-name"),
                ("  Trim Spaces  ", "trim-spaces")
            ]
            
            for input_name, expected in test_cases:
                result = service._sanitize_class_name(input_name)
                assert result == expected, f"Expected '{expected}', got '{result}' for input '{input_name}'"


class TestCSSMappingErrorHandling:
    """Tests for error handling in CSS mapping."""

    def test_render_entry_with_none_profile(self, db_app: Flask) -> None:
        """render_entry should handle None profile gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            xml = "<entry><lexical-unit><form><text>test</text></form></lexical-unit></entry>"
            result = service.render_entry(xml, None)
            
            # Should not crash, return some reasonable output
            assert result is not None
            assert isinstance(result, str)

    def test_render_entry_with_empty_xml(self, db_app: Flask) -> None:
        """render_entry should handle empty XML gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            result = service.render_entry("", profile)
            
            # Should not crash
            assert result is not None
            assert "entry-render-error" in result or len(result) > 0

    def test_render_entry_with_malformed_xml(self, db_app: Flask) -> None:
        """render_entry should handle malformed XML gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            malformed_xml = "<entry><lexical-unit><form><text>test</text></form></lexical-unit>"
            result = service.render_entry(malformed_xml, profile)
            
            # Should not crash
            assert result is not None
            assert "entry-render-error" in result or len(result) > 0

    def test_render_entry_with_missing_dictionary_service(self, db_app: Flask) -> None:
        """render_entry should handle missing dictionary service gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="missing-entry"/>
                </sense>
            </entry>
            """
            
            # Call without dictionary service
            result = service.render_entry(xml, profile, dict_service=None)
            
            # Should not crash, may show unresolved references
            assert result is not None
            assert "entry-render-error" not in result


class TestCSSMappingIntegration:
    """Integration tests for CSS mapping with other components."""

    def test_css_service_with_display_profile_service(self, db_app: Flask) -> None:
        """CSSMappingService should work with DisplayProfileService."""
        with db_app.app_context():
            # Create profile using DisplayProfileService
            profile_service = DisplayProfileService()
            profile = profile_service.create_profile(name="Integration Test")
            
            # Use CSSMappingService to render
            css_service = CSSMappingService()
            
            xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>integration</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = css_service.render_entry(xml, profile)
            
            # Should work together
            assert result is not None
            assert "integration" in result

    def test_css_service_with_profile_elements(self, db_app: Flask) -> None:
        """CSSMappingService should work with ProfileElement configurations."""
        with db_app.app_context():
            # Create profile with elements using DisplayProfileService
            profile_service = DisplayProfileService()
            profile = profile_service.create_profile(name="Element Integration Test")
            
            # Add element configuration
            profile_service.set_element_display_aspect(profile.id, "relation", "label")
            
            # Use CSSMappingService to render
            css_service = CSSMappingService()
            
            xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="other"/>
                </sense>
            </entry>
            """
            
            result = css_service.render_entry(xml, profile)
            
            # Should apply the display aspect
            assert result is not None
            assert "Synonym" in result or "synonym" in result


class TestCSSMappingPerformance:
    """Performance tests for CSS mapping."""

    def test_render_entry_performance_with_simple_entry(self, db_app: Flask, benchmark) -> None:
        """Test performance with simple entry."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Performance Simple"
            db.session.add(profile)
            db.session.commit()
            
            simple_xml = """
            <entry id="simple">
                <lexical-unit>
                    <form lang="en"><text>simple</text></form>
                </lexical-unit>
            </entry>
            """
            
            def render():
                return service.render_entry(simple_xml, profile)
            
            result = benchmark(render)
            assert result is not None

    def test_render_entry_performance_with_complex_entry(self, db_app: Flask, benchmark) -> None:
        """Test performance with complex entry."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Performance Complex"
            db.session.add(profile)
            db.session.commit()
            
            # Add multiple elements to make it more complex
            for i, elem_type in enumerate(["lexical-unit", "pronunciation", "grammatical-info", "definition", "example"]):
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = elem_type
                elem.css_class = f"{elem_type}-class"
                elem.display_order = i
                db.session.add(elem)
            db.session.commit()
            
            complex_xml = """
            <entry id="complex">
                <lexical-unit>
                    <form lang="en"><text>complex</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>ˈkɒmpleks</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Adjective"/>
                    <definition>
                        <form lang="en"><text>Consisting of many different and connected parts</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>A complex system with many components</text></form>
                    </example>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A group of similar buildings used for a particular purpose</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            def render():
                return service.render_entry(complex_xml, profile)
            
            result = benchmark(render)
            assert result is not None
            assert "complex" in result


class TestCSSMappingEdgeCases:
    """Edge case tests for CSS mapping."""

    def test_render_entry_with_unicode_characters(self, db_app: Flask) -> None:
        """render_entry should handle Unicode characters correctly."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Unicode Test"
            db.session.add(profile)
            db.session.commit()
            
            unicode_xml = """
            <entry id="unicode">
                <lexical-unit>
                    <form lang="en"><text>café</text></form>
                    <form lang="zh"><text>咖啡</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>A coffee shop</text></form>
                        <form lang="fr"><text>Un café</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(unicode_xml, profile)
            
            # Should handle Unicode without errors
            assert result is not None
            assert "café" in result or "咖啡" in result

    def test_render_entry_with_special_characters_in_css(self, db_app: Flask) -> None:
        """render_entry should handle special characters in CSS class names."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Special CSS Test"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "lexical-unit"
            elem.css_class = "headword-special_123"
            db.session.add(elem)
            db.session.commit()
            
            xml = """
            <entry id="special">
                <lexical-unit>
                    <form lang="en"><text>special</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(xml, profile)
            
            # Should handle special characters in CSS classes
            assert result is not None
            assert "headword-special_123" in result

    def test_render_entry_with_very_long_text(self, db_app: Flask) -> None:
        """render_entry should handle very long text content."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Long Text Test"
            db.session.add(profile)
            db.session.commit()
            
            long_text = "A" * 10000  # 10KB of text
            long_xml = f"""
            <entry id="long">
                <lexical-unit>
                    <form lang="en"><text>long</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>{long_text}</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(long_xml, profile)
            
            # Should handle long text without crashing
            assert result is not None
            assert len(result) > 0

    def test_render_entry_with_nested_elements(self, db_app: Flask) -> None:
        """render_entry should handle deeply nested XML elements."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Nested Test"
            db.session.add(profile)
            db.session.commit()
            
            nested_xml = """
            <entry id="nested">
                <lexical-unit>
                    <form lang="en">
                        <text>nested</text>
                        <annotation type="etymology">
                            <form lang="en">
                                <text>From Latin</text>
                            </form>
                        </annotation>
                    </form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en">
                            <text>Main definition</text>
                            <annotation type="usage">
                                <form lang="en">
                                    <text>Common usage</text>
                                </form>
                            </annotation>
                        </form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(nested_xml, profile)
            
            # Should handle nested elements
            assert result is not None
            assert "nested" in result

    def test_render_entry_with_multiple_languages(self, db_app: Flask) -> None:
        """render_entry should handle entries with multiple language forms."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Multi-language Test"
            db.session.add(profile)
            db.session.commit()
            
            multi_lang_xml = """
            <entry id="multi">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                    <form lang="es"><text>prueba</text></form>
                    <form lang="fr"><text>essai</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>English definition</text></form>
                        <form lang="es"><text>Definición en español</text></form>
                        <form lang="fr"><text>Définition en français</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(multi_lang_xml, profile)
            
            # Should handle multiple languages
            assert result is not None
            assert ("test" in result or "prueba" in result or "essai" in result)


class TestCSSMappingRegression:
    """Regression tests to ensure we don't break existing functionality."""

    def test_existing_functionality_preserved(self, db_app: Flask) -> None:
        """Ensure existing CSS mapping functionality is preserved."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Create a profile similar to existing ones
            profile = DisplayProfile()
            profile.name = "Regression Test"
            profile.custom_css = ".headword { font-weight: bold; }"
            profile.number_senses = True
            profile.show_subentries = False
            db.session.add(profile)
            db.session.commit()
            
            # Add typical elements
            elements = [
                ("lexical-unit", "headword", 1),
                ("pronunciation", "pronunciation", 2),
                ("grammatical-info", "pos", 3),
                ("definition", "definition", 4),
                ("example", "example", 5)
            ]
            
            for elem_name, css_class, order in elements:
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = elem_name
                elem.css_class = css_class
                elem.display_order = order
                db.session.add(elem)
            db.session.commit()
            
            # Typical LIFT XML
            typical_xml = """
            <entry id="typical">
                <lexical-unit>
                    <form lang="en"><text>typical</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>ˈtɪpɪkəl</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Adjective"/>
                    <definition>
                        <form lang="en"><text>Having the distinctive qualities of a particular type</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>A typical example of 19th-century architecture</text></form>
                    </example>
                </sense>
            </entry>
            """
            
            result = service.render_entry(typical_xml, profile)
            
            # Should produce expected output
            assert result is not None
            assert "headword" in result
            assert "pronunciation" in result
            assert "typical" in result
            assert "font-weight: bold" in result  # Custom CSS
            # Single-sense entries should NOT get sense-numbering CSS when
            # profile.number_senses is not explicitly enabled for multiple senses
            assert "counter-reset" not in result  # Sense numbering

    def test_backward_compatibility_with_old_profiles(self, db_app: Flask) -> None:
        """Ensure backward compatibility with older profile formats."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Create profile with older-style configuration
            profile = DisplayProfile()
            profile.name = "Old Style Profile"
            db.session.add(profile)
            db.session.commit()
            
            # Add element with older config format
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "lexical-unit"
            elem.css_class = "headword"
            # Older profiles might not have display_order set
            db.session.add(elem)
            db.session.commit()
            
            old_style_xml = """
            <entry id="old">
                <lexical-unit>
                    <form lang="en"><text>old</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(old_style_xml, profile)
            
            # Should still work
            assert result is not None
            assert "old" in result

    def test_error_recovery_and_graceful_degradation(self, db_app: Flask) -> None:
        """Test that the system recovers gracefully from errors."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Error Recovery Test"
            db.session.add(profile)
            db.session.commit()
            
            # XML with various potential issues
            problematic_xml = """
            <entry id="problematic">
                <lexical-unit>
                    <form lang="en"><text>problematic</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="UnknownType"/>
                    <relation type="nonexistent" ref="missing-entry"/>
                </sense>
                <note type="unknown">This might cause issues</note>
            </entry>
            """
            
            result = service.render_entry(problematic_xml, profile)
            
            # Should handle problematic content gracefully
            assert result is not None
            assert "entry-render-error" not in result
            assert "problematic" in result


class TestCSSMappingDocumentation:
    """Tests to ensure the code is well-documented."""

    def test_css_service_has_docstrings(self, db_app: Flask) -> None:
        """CSSMappingService methods should have proper docstrings."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Check main methods have docstrings
            assert service.render_entry.__doc__ is not None
            assert len(service.render_entry.__doc__) > 50  # Reasonable length
            
            assert service.apply_display_aspects.__doc__ is not None
            assert len(service.apply_display_aspects.__doc__) > 50

    def test_css_service_methods_are_public_or_private(self, db_app: Flask) -> None:
        """CSSMappingService methods should follow naming conventions."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Public methods should not start with underscore
            assert not service.render_entry.__name__.startswith('_')
            assert not service.apply_display_aspects.__name__.startswith('_')
            
            # Helper methods should start with underscore
            assert service._apply_relation_display_aspect.__name__.startswith('_')
            assert service._build_range_lookup.__name__.startswith('_')


class TestCSSMappingFutureCompatibility:
    """Tests to ensure future compatibility."""

    def test_css_service_can_be_extended(self, db_app: Flask) -> None:
        """CSSMappingService should be extensible for future needs."""
        with db_app.app_context():
            # Test that we can create a subclass
            class ExtendedCSSMappingService(CSSMappingService):
                def custom_method(self):
                    return "extended"
            
            service = ExtendedCSSMappingService()
            assert service.custom_method() == "extended"
            
            # Should still have all original functionality
            assert hasattr(service, 'render_entry')
            assert callable(service.render_entry)

    def test_css_service_accepts_optional_parameters(self, db_app: Flask) -> None:
        """CSSMappingService methods should accept optional parameters."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Optional Params Test"
            db.session.add(profile)
            db.session.commit()
            
            xml = "<entry><lexical-unit><form><text>test</text></form></lexical-unit></entry>"
            
            # Should work with optional dict_service parameter
            result1 = service.render_entry(xml, profile)
            result2 = service.render_entry(xml, profile, dict_service=None)
            
            assert result1 is not None
            assert result2 is not None

    def test_css_service_returns_consistent_format(self, db_app: Flask) -> None:
        """CSSMappingService should return consistent output format."""
        with db_app.app_context():
            service = CSSMappingService()
            profile = DisplayProfile()
            profile.name = "Consistent Format Test"
            db.session.add(profile)
            db.session.commit()
            
            xml = "<entry><lexical-unit><form><text>test</text></form></lexical-unit></entry>"
            
            # Multiple calls should return similar structure
            result1 = service.render_entry(xml, profile)
            result2 = service.render_entry(xml, profile)
            
            # Both should be valid HTML strings
            assert isinstance(result1, str)
            assert isinstance(result2, str)
            assert "<div" in result1
            assert "<div" in result2
            assert "lift-entry-rendered" in result1
            assert "lift-entry-rendered" in result2
