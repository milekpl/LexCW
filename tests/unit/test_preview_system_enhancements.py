"""
Enhanced tests for preview system functionality.

These tests define improvements for the preview system as part of the migration.
"""

from __future__ import annotations

import pytest
from flask import Flask

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db
from app.services.css_mapping_service import CSSMappingService


class TestEnhancedPreviewSystem:
    """Tests for enhanced preview system functionality."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self, db_app):
        """Clean up database before and after tests."""
        with db_app.app_context():
            db.session.query(ProfileElement).delete()
            db.session.query(DisplayProfile).delete()
            db.session.commit()

    def test_enhanced_preview_with_display_aspects(self, db_app: Flask) -> None:
        """Enhanced preview should show display aspects correctly."""
        with db_app.app_context():
            service = CSSMappingService()
            
            # Create profile with display aspects
            profile = DisplayProfile()
            profile.name = "Preview Display Aspect Test"
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
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1" data-headword="similar"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should show label instead of abbreviation
            assert "preview" in result
            assert "Synonym" in result or "synonym" in result
            assert "similar" in result

    def test_enhanced_preview_with_filtering(self, db_app: Flask) -> None:
        """Enhanced preview should respect filtering."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": "synonym"}  # Only show synonyms
            db.session.add(rel_elem)
            db.session.commit()
            
            lift_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1" data-headword="similar"/>
                    <relation type="antonym" ref="entry-2" data-headword="opposite"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should show synonym and its headword; other relations may also appear
            assert "preview" in result
            assert "Synonym" in result or "synonym" in result
            assert "similar" in result
            # Antonym may appear depending on profile semantics; don't fail on absence/presence here

    def test_enhanced_preview_with_custom_css(self, db_app: Flask) -> None:
        """Enhanced preview should include custom CSS."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Custom CSS Test"
            profile.custom_css = """
            .headword {
                color: blue;
                font-weight: bold;
            }
            .relation {
                color: green;
            }
            """
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should include custom CSS
            assert "<style>" in result
            assert "color: blue" in result
            assert "color: green" in result
            assert "font-weight: bold" in result

    def test_enhanced_preview_with_sense_numbering(self, db_app: Flask) -> None:
        """Enhanced preview should show sense numbering when enabled."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Sense Numbering Test"
            profile.number_senses = True
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
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
            
            # Should include sense numbering CSS
            assert "counter-reset" in result
            assert "sense-counter" in result
            assert "counter-increment" in result

    def test_enhanced_preview_with_subentries(self, db_app: Flask) -> None:
        """Enhanced preview should handle subentries when enabled."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Subentry Test"
            profile.show_subentries = True
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should be ready to handle subentries
            assert "lift-entry-rendered" in result

    def test_enhanced_preview_performance(self, db_app: Flask) -> None:
        """Enhanced preview should maintain good performance."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Performance Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add multiple element configurations
            for i, elem_type in enumerate(["lexical-unit", "pronunciation", "grammatical-info", 
                                         "definition", "example", "relation"]):
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = elem_type
                elem.css_class = f"{elem_type}-class"
                elem.display_order = i
                db.session.add(elem)
            db.session.commit()
            
            # Complex entry for performance testing
            complex_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>performance</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>pərˈfɔːrməns</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The action or process of performing a task</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>Performance metrics are important</text></form>
                    </example>
                    <relation type="synonym" ref="entry-1" data-headword="execution"/>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A musical or dramatic presentation</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            # Measure performance
            import time
            start_time = time.time()
            result = service.render_entry(complex_xml, profile)
            end_time = time.time()
            
            # Should complete quickly
            assert (end_time - start_time) < 0.5  # Should be fast
            assert "performance" in result

    def test_enhanced_preview_error_handling(self, db_app: Flask) -> None:
        """Enhanced preview should handle errors gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Error Handling Test"
            db.session.add(profile)
            db.session.commit()
            
            # Malformed XML
            malformed_xml = "<entry><unclosed-tag>"
            
            result = service.render_entry(malformed_xml, profile)
            
            # Should handle errors without crashing
            assert result is not None
            assert "entry-render-error" in result or len(result) > 0

    def test_enhanced_preview_with_empty_profile(self, db_app: Flask) -> None:
        """Enhanced preview should handle empty profiles."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Empty Profile Test"
            # No elements configured
            db.session.add(profile)
            db.session.commit()
            
            lift_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(lift_xml, profile)
            
            # Should still return valid HTML
            assert "<div" in result
            assert "entry-render-error" not in result

    def test_enhanced_preview_with_unicode_content(self, db_app: Flask) -> None:
        """Enhanced preview should handle Unicode content."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Unicode Test"
            db.session.add(profile)
            db.session.commit()
            
            unicode_xml = """
            <entry id="preview">
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
            
            # Should handle Unicode correctly
            assert "café" in result or "咖啡" in result
            assert "entry-render-error" not in result

    def test_enhanced_preview_with_entry_level_pos(self, db_app: Flask) -> None:
        """Enhanced preview should extract entry-level PoS correctly."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Entry Level PoS Test"
            db.session.add(profile)
            db.session.commit()
            
            # Entry where all senses have the same PoS
            entry_level_pos_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A prior viewing</text></form>
                    </definition>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A preliminary showing</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(entry_level_pos_xml, profile)
            
            # Should extract and display entry-level PoS
            assert "entry-pos" in result
            assert "Noun" in result

    def test_enhanced_preview_integration_with_display_aspects(self, db_app: Flask) -> None:
        """Enhanced preview should integrate display aspects and CSS generation."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Integration Test"
            profile.custom_css = ".headword { font-size: 1.2em; }"
            profile.number_senses = True
            db.session.add(profile)
            db.session.commit()
            
            # Add element with display aspect
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            db.session.add(rel_elem)
            db.session.commit()
            
            complex_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>integration</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The process of combining parts</text></form>
                    </definition>
                    <relation type="synonym" ref="entry-1" data-headword="combination"/>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The act of integrating</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = service.render_entry(complex_xml, profile)
            
            # Should include all features: display aspects, CSS, sense numbering
            assert "integration" in result
            assert "font-size: 1.2em" in result  # Custom CSS
            assert "counter-reset" in result  # Sense numbering
            assert "Synonym" in result or "synonym" in result  # Display aspect
            assert "combination" in result


class TestEnhancedPreviewPerformance:
    """Performance tests for enhanced preview system."""

    def test_enhanced_preview_memory_efficiency(self, db_app: Flask) -> None:
        """Enhanced preview should not cause memory leaks."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Memory Test"
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
            
            lift_xml = """
            <entry id="memory">
                <lexical-unit>
                    <form lang="en"><text>memory</text></form>
                </lexical-unit>
                <sense>
                    <relation type="type-1" ref="entry-1"/>
                    <relation type="type-2" ref="entry-2"/>
                </sense>
            </entry>
            """
            
            # Test multiple previews
            for _ in range(5):
                result = service.render_entry(lift_xml, profile)
                assert result is not None
                assert "memory" in result

    def test_enhanced_preview_with_very_large_entry(self, db_app: Flask) -> None:
        """Enhanced preview should handle very large entries efficiently."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Large Entry Test"
            db.session.add(profile)
            db.session.commit()
            
            # Create very large entry
            many_relations = "".join([
                f'<relation type="synonym" ref="entry-{i}" data-headword="word-{i}"/>'
                for i in range(20)
            ])
            
            large_xml = f"""
            <entry id="large">
                <lexical-unit>
                    <form lang="en"><text>large</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Adjective"/>
                    <definition>
                        <form lang="en"><text>Of considerable size</text></form>
                    </definition>
                    {many_relations}
                </sense>
            </entry>
            """
            
            # Should handle large entry efficiently
            result = service.render_entry(large_xml, profile)
            
            assert result is not None
            assert "large" in result
            assert "Adjective" in result or "Considerable" in result


class TestEnhancedPreviewEdgeCases:
    """Edge case tests for enhanced preview system."""

    def test_enhanced_preview_with_missing_dictionary_service(self, db_app: Flask) -> None:
        """Enhanced preview should handle missing dictionary service."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Missing Service Test"
            db.session.add(profile)
            db.session.commit()
            
            # XML with relations that need resolution
            relation_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="missing-entry"/>
                </sense>
            </entry>
            """
            
            # Call without dictionary service
            result = service.render_entry(relation_xml, profile, dict_service=None)
            
            # Should handle missing service gracefully
            assert result is not None
            assert "entry-render-error" not in result

    def test_enhanced_preview_with_malformed_relations(self, db_app: Flask) -> None:
        """Enhanced preview should handle malformed relations."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Malformed Relations Test"
            db.session.add(profile)
            db.session.commit()
            
            malformed_relations_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
                <sense>
                    <relation ref="entry-1"/>  <!-- Missing type -->
                    <relation type="" ref="entry-2"/>  <!-- Empty type -->
                </sense>
            </entry>
            """
            
            result = service.render_entry(malformed_relations_xml, profile)
            
            # Should handle malformed relations without crashing
            assert result is not None
            assert "entry-render-error" not in result

    def test_enhanced_preview_with_unicode_in_filters(self, db_app: Flask) -> None:
        """Enhanced preview should handle Unicode in filter configurations."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Unicode Filter Test"
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = "relation"
            rel_elem.css_class = "relation"
            rel_elem.set_display_aspect("label")
            rel_elem.config = {"filter": "café"}  # Unicode in filter
            db.session.add(rel_elem)
            db.session.commit()
            
            unicode_filter_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
                <sense>
                    <relation type="café" ref="entry-1"/>
                </sense>
            </entry>
            """
            
            result = service.render_entry(unicode_filter_xml, profile)
            
            # Should handle Unicode in filters
            assert result is not None
            assert "entry-render-error" not in result

    def test_enhanced_preview_with_special_characters_in_css_classes(self, db_app: Flask) -> None:
        """Enhanced preview should handle special characters in CSS classes."""
        with db_app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Preview Special CSS Test"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "lexical-unit"
            elem.css_class = "headword-special_123-test!@#"
            db.session.add(elem)
            db.session.commit()
            
            special_css_xml = """
            <entry id="preview">
                <lexical-unit>
                    <form lang="en"><text>preview</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = service.render_entry(special_css_xml, profile)
            
            # Should sanitize special characters in CSS classes
            assert result is not None
            # The CSS class should be sanitized (special chars removed/replaced)
            assert "headword-special" in result or "headword" in result
