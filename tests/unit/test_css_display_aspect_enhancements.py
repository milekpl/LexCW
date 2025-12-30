"""
Enhanced tests for CSS display aspect functionality.

These tests define the new functionality we want to implement
for display aspect resolution as part of the migration.

NOTE: The specific relation types (synonym, antonym, hypernym) and trait names
used in these tests are just examples for testing purposes. The actual implementation
is completely data-driven and doesn't hard-code any specific values. All filter
values come from the profile configuration and are compared against the actual
values in the XML.
"""

from __future__ import annotations

import pytest
from flask import Flask

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db
from app.services.css_mapping_service import CSSMappingService


class TestEnhancedDisplayAspectResolution:
    """Tests for enhanced display aspect resolution functionality."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self, db_app):
        """Clean up database before and after tests."""
        with db_app.app_context():
            db.session.query(ProfileElement).delete()
            db.session.query(DisplayProfile).delete()
            db.session.commit()

    def test_enhanced_relation_display_aspect_with_filter(self, db_app: Flask) -> None:
        """Enhanced relation display aspect should respect filters."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Create profile with filtered relation display aspect
            profile = DisplayProfile()
            profile.name = "Enhanced Relation Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": "synonym,antonym"}  # Only process these types
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                    <relation type="hypernym" ref="entry-3"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should apply label display to filtered relations
            assert "Synonym" in result or "synonym" in result
            assert "Antonym" in result or "antonym" in result
            # Hypernym should not appear in output (not in filter, so not processed by transformer)
            assert "hypernym" not in result  # Should not appear since it wasn't matched by any profile config

    def test_enhanced_grammatical_info_display_aspect(self, db_app: Flask) -> None:
        """Enhanced grammatical-info display aspect should work with all aspects."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Enhanced Grammatical Info Test"
            db.session.add(profile)
            db.session.commit()
            
            gram_elem = ProfileElement()
            gram_elem.profile_id = profile.id
            gram_elem.lift_element = "grammatical-info"
            gram_elem.css_class = "pos"
            gram_elem.set_display_aspect("full")  # Use full labels
            db.session.add(gram_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should use full label instead of abbreviation
            assert "Noun" in result

    def test_enhanced_variant_display_aspect(self, db_app: Flask) -> None:
        """Enhanced variant display aspect should work with all aspects."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Enhanced Variant Test"
            db.session.add(profile)
            db.session.commit()
            
            variant_elem = ProfileElement()
            variant_elem.profile_id = profile.id
            variant_elem.lift_element = "variant"
            variant_elem.css_class = "variant"
            variant_elem.set_display_aspect("label")
            db.session.add(variant_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <variant type="spelling">
                    <form lang="en"><text>teste</text></form>
                </variant>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should use label for variant type
            assert "Spelling" in result or "spelling" in result

    def test_enhanced_trait_display_aspect_with_filter(self, db_app: Flask) -> None:
        """Enhanced trait display aspect should work with filters."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Enhanced Trait Test"
            db.session.add(profile)
            db.session.commit()
            
            trait_elem = ProfileElement()
            trait_elem.profile_id = profile.id
            trait_elem.lift_element = "trait"
            trait_elem.css_class = "trait"
            trait_elem.set_display_aspect("label")
            trait_elem.config = {"filter": "semantic-domain"}  # Only process semantic-domain traits
            db.session.add(trait_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <trait name="semantic-domain" value="science"/>
                    <trait name="register" value="formal"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should apply label to filtered trait
            assert "Science" in result or "science" in result
            # Other trait should not be processed
            assert "formal" in result

    def test_enhanced_display_aspect_with_language_filter(self, db_app: Flask) -> None:
        """Enhanced display aspect should work with language filters."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Enhanced Language Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.set_display_language("pl")  # Polish labels
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should use Polish labels if available
            assert "relation" in result

    def test_enhanced_display_aspect_fallback_behavior(self, db_app: Flask) -> None:
        """Enhanced display aspect should have proper fallback behavior."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Enhanced Fallback Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")  # Request label but none available
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="unknown-relation-type" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should fall back gracefully (humanize the type)
            assert "Unknown Relation Type" in result or "unknown-relation-type" in result

    def test_enhanced_display_aspect_performance(self, db_app: Flask) -> None:
        """Enhanced display aspect resolution should maintain good performance."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Enhanced Performance Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add multiple elements with display aspects
            elements = [
                ("relation", "label", {"filter": "synonym,antonym"}),
                ("grammatical-info", "full", {}),
                ("variant", "label", {}),
                ("trait", "label", {"filter": "semantic-domain"})
            ]
            
            for lift_elem, aspect, config in elements:
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = lift_elem
                elem.css_class = f"{lift_elem}-class"
                elem.set_display_aspect(aspect)
                elem.config = config
                db.session.add(elem)
            db.session.commit()
            
            # Complex XML with many elements
            complex_xml = """
            <entry id="performance">
                <lexical-unit>
                    <form lang="en"><text>performance</text></form>
                </lexical-unit>
                <variant type="spelling">
                    <form lang="en"><text>performence</text></form>
                </variant>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The action of performing</text></form>
                    </definition>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                    <relation type="hypernym" ref="entry-3"/>
                    <trait name="semantic-domain" value="activity"/>
                    <trait name="register" value="neutral"/>
                    <example>
                        <form lang="en"><text>Performance metrics are important</text></form>
                    </example>
                </sense>
            </entry>
            """
            
            result = service.render_entry(complex_xml, profile)
            
            # Should complete successfully and maintain good performance
            assert result is not None
            assert "performance" in result

    def test_enhanced_display_aspect_with_multiple_filters(self, db_app: Flask) -> None:
        """Enhanced display aspect should handle multiple filters correctly."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Multiple Filters Test"
            db.session.add(profile)
            db.session.commit()
            
            # Multiple relation elements with different filters
            synonym_elem = ProfileElement()
            synonym_elem.profile_id = profile.id
            synonym_elem.lift_element = "relation"
            synonym_elem.css_class = "synonym"
            synonym_elem.set_display_aspect("label")
            synonym_elem.config = {"filter": "synonym"}
            db.session.add(synonym_elem)
            
            antonym_elem = ProfileElement()
            antonym_elem.profile_id = profile.id
            antonym_elem.lift_element = "relation"
            antonym_elem.css_class = "antonym"
            antonym_elem.set_display_aspect("label")
            antonym_elem.config = {"filter": "antonym"}
            db.session.add(antonym_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                    <relation type="hypernym" ref="entry-3"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should apply different CSS classes based on filters
            assert "synonym" in result
            assert "antonym" in result
            # Hypernym should not appear (no matching filter)
            assert "hypernym" not in result

    def test_enhanced_display_aspect_exclusion_filters(self, db_app: Flask) -> None:
        """Enhanced display aspect should handle exclusion filters."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Exclusion Filters Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": "!hypernym"}  # Exclude hypernym
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                    <relation type="hypernym" ref="entry-3"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should process all except hypernym
            assert "Synonym" in result or "synonym" in result
            assert "Antonym" in result or "antonym" in result
            # Hypernym should be excluded (not appear in output)
            assert "hypernym" not in result

    def test_enhanced_display_aspect_priority_ordering(self, db_app: Flask) -> None:
        """Enhanced display aspect should process filters in correct priority order."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Priority Ordering Test"
            db.session.add(profile)
            db.session.commit()
            
            # Specific filter should take priority over general
            specific_elem = ProfileElement()
            specific_elem.profile_id = profile.id
            specific_elem.lift_element = "relation"
            specific_elem.css_class = "specific-synonym"
            specific_elem.set_display_aspect("label")
            specific_elem.config = {"filter": "synonym"}
            specific_elem.display_order = 1
            db.session.add(specific_elem)
            
            general_elem = ProfileElement()
            general_elem.profile_id = profile.id
            general_elem.lift_element = "relation"
            general_elem.css_class = "general-relation"
            general_elem.set_display_aspect("abbr")
            # No filter - should apply to all relations not caught by specific filters
            general_elem.display_order = 2
            db.session.add(general_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Synonym should use specific configuration
            assert "specific-synonym" in result
            # Antonym should use general configuration
            assert "general-relation" in result
            assert "ant" in result  # Abbreviation for antonym


class TestEnhancedDisplayAspectIntegration:
    """Integration tests for enhanced display aspect functionality."""

    def test_enhanced_display_aspect_with_lift_transformer(self, db_app: Flask) -> None:
        """Enhanced display aspects should integrate properly with LIFT transformer."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Integration Test"
            db.session.add(profile)
            db.session.commit()
            
            # Configure multiple elements with display aspects
            elements_config = [
                ("relation", "label", {"filter": "synonym"}),
                ("grammatical-info", "full", {}),
                ("lexical-unit", "abbr", {})
            ]
            
            for lift_elem, aspect, config in elements_config:
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = lift_elem
                elem.css_class = f"{lift_elem}-class"
                elem.set_display_aspect(aspect)
                elem.config = config
                db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>integration</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The process of combining parts</text></form>
                    </definition>
                    <relation type="synonym" ref="entry-1"/>
                    <relation type="antonym" ref="entry-2"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should apply all display aspects correctly
            assert "integration" in result
            assert "Noun" in result  # Full label for grammatical-info
            assert "Synonym" in result or "synonym" in result  # Label for synonym
            # Antonym is filtered out (not in filter list), so should not appear in output
            assert "antonym" not in result

    def test_enhanced_display_aspect_with_css_generation(self, db_app: Flask) -> None:
        """Enhanced display aspects should work with CSS generation."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "CSS Generation Test"
            profile.custom_css = ".relation { color: blue; }"
            profile.number_senses = True
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                </sense>
                <sense>
                    <relation type="antonym" ref="entry-2"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should include both custom CSS and display aspects
            assert "color: blue" in result  # Custom CSS
            assert "counter-reset" in result  # Sense numbering CSS
            assert "Synonym" in result or "synonym" in result  # Display aspect

    def test_enhanced_display_aspect_with_error_handling(self, db_app: Flask) -> None:
        """Enhanced display aspects should handle errors gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Error Handling Test"
            db.session.add(profile)
            db.session.commit()
            
            # Create element with invalid display aspect (should be handled gracefully)
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "relation"
            elem.css_class = "relation"
            # Don't set display aspect - should use default
            db.session.add(elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should handle missing display aspect gracefully
            assert result is not None
            assert "entry-render-error" not in result
            assert "synonym" in result


class TestEnhancedDisplayAspectPerformance:
    """Performance tests for enhanced display aspect functionality."""

    def test_enhanced_display_aspect_memory_usage(self, db_app: Flask) -> None:
        """Enhanced display aspect should not cause memory leaks."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Memory Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add complex configuration
            for i in range(10):
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = "relation"
                elem.css_class = f"relation-{i}"
                elem.set_display_aspect("label")
                elem.config = {"filter": f"type-{i}"}
                db.session.add(elem)
            db.session.commit()
            
            # Test with multiple renders to check for memory issues
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>memory</text></form>
                </lexical-unit>
                <sense>
                    <relation type="type-1" ref="entry-1"/>
                    <relation type="type-2" ref="entry-2"/>
                </sense>
            </entry>
            """
            
            # Render multiple times
            for _ in range(5):
                result = service.render_entry(lift_xml, profile)
                assert result is not None
                assert "memory" in result

    def test_enhanced_display_aspect_with_large_entry(self, db_app: Flask, benchmark) -> None:
        """Enhanced display aspect should handle large entries efficiently."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Large Entry Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add configuration for multiple element types
            element_types = ["relation", "grammatical-info", "variant", "trait"]
            for elem_type in element_types:
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = elem_type
                elem.css_class = f"{elem_type}-class"
                elem.set_display_aspect("label")
                db.session.add(elem)
            db.session.commit()
            
            # Create large entry with many elements
            relations = "".join([
                f'<relation type="synonym" ref="entry-{i}"/>'
                for i in range(20)
            ])
            
            traits = "".join([
                f'<trait name="semantic-domain" value="domain-{i}"/>'
                for i in range(10)
            ])
            
            large_xml = f"""
            <entry id="large">
                <lexical-unit>
                    <form lang="en"><text>large</text></form>
                </lexical-unit>
                <variant type="spelling">
                    <form lang="en"><text>lage</text></form>
                </variant>
                <sense>
                    <grammatical-info value="Adjective"/>
                    <definition>
                        <form lang="en"><text>Of considerable size</text></form>
                    </definition>
                    {relations}
                    {traits}
                    <example>
                        <form lang="en"><text>This is a large entry with many elements</text></form>
                    </example>
                </sense>
            </entry>
            """
            
            def render_large_entry():
                return service.render_entry(large_xml, profile)
            
            result = benchmark(render_large_entry)
            
            # Should handle large entry efficiently
            assert result is not None
            assert "large" in result


class TestEnhancedDisplayAspectEdgeCases:
    """Edge case tests for enhanced display aspect functionality."""

    def test_enhanced_display_aspect_with_empty_filter(self, db_app: Flask) -> None:
        """Enhanced display aspect should handle empty filters correctly."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Empty Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": ""}  # Empty filter
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Empty filter should match all relations
            assert "Synonym" in result or "synonym" in result

    def test_enhanced_display_aspect_with_none_filter(self, db_app: Flask) -> None:
        """Enhanced display aspect should handle None filters correctly."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "None Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": None}  # None filter
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # None filter should match all relations
            assert "Synonym" in result or "synonym" in result

    def test_enhanced_display_aspect_with_malformed_filter(self, db_app: Flask) -> None:
        """Enhanced display aspect should handle malformed filters gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Malformed Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": "!!invalid!!filter!!"}  # Malformed filter
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should handle malformed filter gracefully
            assert result is not None
            assert "entry-render-error" not in result

    def test_enhanced_display_aspect_with_missing_range_data(self, db_app: Flask) -> None:
        """Enhanced display aspect should handle missing range data gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Missing Range Data Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")  # Request label but no range data available
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="nonexistent-type" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should fall back gracefully when range data is missing
            assert result is not None
            assert "entry-render-error" not in result
            assert "nonexistent-type" in result or "Nonexistent Type" in result

    def test_enhanced_display_aspect_with_unicode_in_filters(self, db_app: Flask) -> None:
        """Enhanced display aspect should handle Unicode characters in filters."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Unicode Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": "café,naïve"}  # Unicode in filter
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="café" ref="entry-1"/>
                    <relation type="naïve" ref="entry-2"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should handle Unicode in filters
            assert result is not None
            assert "entry-render-error" not in result
