"""
Enhanced tests for LIFT to HTML transformer functionality.

These tests define the new functionality we want to implement
for the LIFT transformer as part of the migration.
"""

from __future__ import annotations

import pytest
from flask import Flask

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db
from app.services.css_mapping_service import CSSMappingService
from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer, ElementConfig


class TestEnhancedLIFTTransformer:
    """Tests for enhanced LIFT transformer functionality."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self, db_app):
        """Clean up database before and after tests."""
        with db_app.app_context():
            db.session.query(ProfileElement).delete()
            db.session.query(DisplayProfile).delete()
            db.session.commit()

    def test_enhanced_transformer_with_display_aspects(self, db_app: Flask) -> None:
        """Enhanced transformer should properly handle display aspects from CSS service."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            # Create element configs with display aspects
            element_configs = [
                ElementConfig(
                    lift_element="relation",
                    display_order=1,
                    css_class="relation",
                    abbr_format="label"  # Should use labels for relations
                ),
                ElementConfig(
                    lift_element="grammatical-info",
                    display_order=2,
                    css_class="pos",
                    abbr_format="full"  # Should use full labels
                )
            ]
            
            # LIFT XML with relations and grammatical info
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                    <relation type="synonym" ref="entry-1" data-headword="similar"/>
                </sense>
            </entry>
            """
            
            result = transformer.transform(lift_xml, element_configs)
            
            # Should include both elements with proper formatting
            assert "test" in result
            assert "Noun" in result  # Full label for grammatical-info
            assert "synonym" in result or "Synonym" in result  # Label for relation

    def test_enhanced_transformer_with_complex_filtering(self, db_app: Flask) -> None:
        """Enhanced transformer should handle complex filtering scenarios."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            # Create element configs with complex filters
            element_configs = [
                ElementConfig(
                    lift_element="relation",
                    display_order=1,
                    css_class="synonym",
                    filter="synonym",
                    abbr_format="label"
                ),
                ElementConfig(
                    lift_element="relation",
                    display_order=2,
                    css_class="antonym",
                    filter="antonym",
                    abbr_format="label"
                ),
                ElementConfig(
                    lift_element="relation",
                    display_order=3,
                    css_class="other-relation",
                    filter="!synonym,!antonym",  # Exclude synonym and antonym
                    abbr_format="abbr"
                )
            ]
            
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1" data-headword="similar"/>
                    <relation type="antonym" ref="entry-2" data-headword="opposite"/>
                    <relation type="hypernym" ref="entry-3" data-headword="category"/>
                </sense>
            </entry>
            """
            
            result = transformer.transform(lift_xml, element_configs)
            
            # Should apply different CSS classes based on filters
            assert "synonym" in result
            assert "antonym" in result
            assert "other-relation" in result
            assert "hypernym" in result or "hyp" in result  # Should use abbreviation

    def test_enhanced_transformer_with_trait_filtering(self, db_app: Flask) -> None:
        """Enhanced transformer should handle trait filtering correctly."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="trait",
                    display_order=1,
                    css_class="domain-trait",
                    filter="semantic-domain",
                    abbr_format="label"
                ),
                ElementConfig(
                    lift_element="trait",
                    display_order=2,
                    css_class="other-trait",
                    filter="!semantic-domain",  # Exclude semantic-domain
                    abbr_format="abbr"
                )
            ]
            
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
            
            result = transformer.transform(lift_xml, element_configs)
            
            # Should apply different handling based on trait name filters
            assert "domain-trait" in result
            assert "Science" in result or "science" in result  # Label for semantic-domain
            assert "other-trait" in result
            assert "formal" in result  # Abbreviation for other traits

    def test_enhanced_transformer_performance_with_large_entry(self, db_app: Flask) -> None:
        """Enhanced transformer should handle large entries efficiently."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            # Create comprehensive element configurations
            element_configs = []
            for i, elem_type in enumerate(["lexical-unit", "pronunciation", "grammatical-info", 
                                         "definition", "example", "relation", "trait"]):
                config = ElementConfig(
                    lift_element=elem_type,
                    display_order=i,
                    css_class=f"{elem_type}-class",
                    abbr_format="label" if elem_type in ["relation", "trait"] else None
                )
                element_configs.append(config)
            
            # Create large entry with many elements
            relations = "".join([
                f'<relation type="synonym" ref="entry-{i}" data-headword="word-{i}"/>'
                for i in range(10)
            ])
            
            traits = "".join([
                f'<trait name="semantic-domain" value="domain-{i}"/>'
                for i in range(5)
            ])
            
            large_xml = f"""
            <entry id="large">
                <lexical-unit>
                    <form lang="en"><text>large</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>lɑːrdʒ</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Adjective"/>
                    <definition>
                        <form lang="en"><text>Of considerable size or extent</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>A large house with many rooms</text></form>
                    </example>
                    {relations}
                    {traits}
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A large size of clothing</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            # Measure performance (simple timing)
            import time
            start_time = time.time()
            result = transformer.transform(large_xml, element_configs)
            end_time = time.time()
            
            # Should complete in reasonable time
            assert (end_time - start_time) < 1.0  # Should be fast even for large entries
            assert "large" in result
            assert "Adjective" in result or "Noun" in result

    def test_enhanced_transformer_with_entry_level_pos(self, db_app: Flask) -> None:
        """Enhanced transformer should handle entry-level PoS extraction correctly."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="grammatical-info",
                    display_order=1,
                    css_class="pos",
                    abbr_format="full"
                )
            ]
            
            # Entry where all senses have the same PoS
            lift_xml = """
            <entry id="test">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A procedure for testing</text></form>
                    </definition>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>An examination or trial</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = transformer.transform(lift_xml, element_configs, entry_level_pos="Noun")
            
            # Should extract entry-level PoS and not duplicate in senses
            assert "entry-pos" in result
            assert "Noun" in result
            # Should not show Noun twice in each sense (entry-level + sense-level)
            noun_count = result.count("Noun")
            # Legacy behavior changed: when entry-level PoS is present, do not duplicate it in senses
            assert noun_count == 1  # Only the entry-level PoS should be shown

    def test_enhanced_transformer_with_malformed_xml(self, db_app: Flask) -> None:
        """Enhanced transformer should handle malformed XML gracefully."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword"
                )
            ]
            
            # Malformed XML (unclosed tags, missing elements)
            malformed_xml = """
            <entry id="malformed">
                <lexical-unit>
                    <form lang="en"><text>malformed
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>Invalid XML structure
                    </definition>
                </sense>
            </entry>
            """
            
            result = transformer.transform(malformed_xml, element_configs)
            
            # Should handle malformed XML without crashing
            assert result is not None
            assert "entry-error" not in result  # Should not crash, may show partial content

    def test_enhanced_transformer_with_unicode_content(self, db_app: Flask) -> None:
        """Enhanced transformer should handle Unicode content correctly."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword"
                ),
                ElementConfig(
                    lift_element="definition",
                    display_order=2,
                    css_class="definition"
                )
            ]
            
            unicode_xml = """
            <entry id="unicode">
                <lexical-unit>
                    <form lang="en"><text>café</text></form>
                    <form lang="zh"><text>咖啡</text></form>
                    <form lang="ar"><text>قهوة</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>A coffee shop or restaurant</text></form>
                        <form lang="fr"><text>Un café ou restaurant</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = transformer.transform(unicode_xml, element_configs)
            
            # Should preserve Unicode characters
            assert "café" in result or "咖啡" in result or "قهوة" in result
            assert "coffee" in result or "café" in result

    def test_enhanced_transformer_with_empty_elements(self, db_app: Flask) -> None:
        """Enhanced transformer should handle empty elements correctly."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword",
                    visibility="if-content"
                ),
                ElementConfig(
                    lift_element="definition",
                    display_order=2,
                    css_class="definition",
                    visibility="if-content"
                ),
                ElementConfig(
                    lift_element="example",
                    display_order=3,
                    css_class="example",
                    visibility="if-content"
                )
            ]
            
            # Entry with some empty elements
            empty_xml = """
            <entry id="empty">
                <lexical-unit>
                    <form lang="en"><text>empty</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>A definition</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text></text></form>  <!-- Empty example -->
                    </example>
                </sense>
            </entry>
            """
            
            result = transformer.transform(empty_xml, element_configs)
            
            # Should handle empty elements according to visibility settings
            assert "empty" in result
            assert "definition" in result
            # Empty example should not appear due to if-content visibility
            assert "example" not in result or result.count("example") == 1

    def test_enhanced_transformer_with_nested_structures(self, db_app: Flask) -> None:
        """Enhanced transformer should handle complex nested structures."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword"
                ),
                ElementConfig(
                    lift_element="definition",
                    display_order=2,
                    css_class="definition"
                ),
                ElementConfig(
                    lift_element="note",
                    display_order=3,
                    css_class="note"
                )
            ]
            
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
                    <note type="usage">
                        <form lang="en"><text>Used in technical contexts</text></form>
                    </note>
                </sense>
            </entry>
            """
            
            result = transformer.transform(nested_xml, element_configs)
            
            # Should handle nested structures without duplication
            assert "nested" in result
            assert "definition" in result
            assert "Main definition" in result
            # Should extract text from nested forms correctly
            assert "Common usage" in result or "usage" in result

    def test_enhanced_transformer_integration_with_css_service(self, db_app: Flask) -> None:
        """Enhanced transformer should integrate properly with CSS service."""
        with db_app.app_context():
            # Test the full integration
            css_service = CSSMappingService()
            
            # Create a profile with display aspects
            profile = DisplayProfile()
            profile.name = "Integration Test"
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
            <entry id="integration">
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
            </entry>
            """
            
            # Use CSS service to apply display aspects
            enhanced_xml, handled = css_service.apply_display_aspects(lift_xml, profile)
            
            # Then use transformer to convert to HTML
            from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer, ElementConfig
            
            element_configs = [
                ElementConfig(
                    lift_element="relation",
                    display_order=1,
                    css_class="relation",
                    abbr_format="label"  # This should be overridden by CSS service
                )
            ]
            
            transformer = LIFTToHTMLTransformer()
            result = transformer.transform(enhanced_xml, element_configs)
            
            # Should show the label applied by CSS service
            assert "integration" in result
            assert "Synonym" in result or "synonym" in result
            assert "combination" in result


class TestEnhancedTransformerPerformance:
    """Performance tests for enhanced transformer."""

    def test_enhanced_transformer_memory_efficiency(self, db_app: Flask) -> None:
        """Enhanced transformer should not cause memory leaks."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            # Create complex configuration
            element_configs = []
            for i in range(20):
                config = ElementConfig(
                    lift_element=f"element-{i}",
                    display_order=i,
                    css_class=f"class-{i}"
                )
                element_configs.append(config)
            
            # Test with multiple transforms to check for memory issues
            lift_xml = """
            <entry id="memory">
                <lexical-unit>
                    <form lang="en"><text>memory</text></form>
                </lexical-unit>
            </entry>
            """
            
            # Transform multiple times
            for _ in range(10):
                result = transformer.transform(lift_xml, element_configs)
                assert result is not None
                assert "memory" in result

    def test_enhanced_transformer_with_very_large_entry(self, db_app: Flask) -> None:
        """Enhanced transformer should handle very large entries."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            # Create minimal configuration
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword"
                ),
                ElementConfig(
                    lift_element="definition",
                    display_order=2,
                    css_class="definition"
                )
            ]
            
            # Create very large entry (simulated)
            many_senses = "".join([
                f"""
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>Definition {i} with some additional text</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>Example sentence {i} demonstrating the usage</text></form>
                    </example>
                </sense>
                """ for i in range(50)
            ])
            
            large_xml = f"""
            <entry id="very-large">
                <lexical-unit>
                    <form lang="en"><text>very large entry</text></form>
                </lexical-unit>
                {many_senses}
            </entry>
            """
            
            # Should handle large entry without crashing
            result = transformer.transform(large_xml, element_configs)
            
            assert result is not None
            assert "very large entry" in result
            assert "Definition 1" in result
            assert "Definition 49" in result


class TestEnhancedTransformerEdgeCases:
    """Edge case tests for enhanced transformer."""

    def test_enhanced_transformer_with_missing_attributes(self, db_app: Flask) -> None:
        """Enhanced transformer should handle missing attributes gracefully."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="relation",
                    display_order=1,
                    css_class="relation"
                )
            ]
            
            # Relation without type attribute
            missing_attr_xml = """
            <entry id="missing">
                <lexical-unit>
                    <form lang="en"><text>missing</text></form>
                </lexical-unit>
                <sense>
                    <relation ref="entry-1"/>  <!-- Missing type attribute -->
                </sense>
            </entry>
            """
            
            result = transformer.transform(missing_attr_xml, element_configs)
            
            # Should handle missing attributes without crashing
            assert result is not None
            assert "entry-error" not in result

    def test_enhanced_transformer_with_unicode_in_attributes(self, db_app: Flask) -> None:
        """Enhanced transformer should handle Unicode in attributes."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="relation",
                    display_order=1,
                    css_class="relation"
                ),
                ElementConfig(
                    lift_element="trait",
                    display_order=2,
                    css_class="trait"
                )
            ]
            
            unicode_attr_xml = """
            <entry id="unicode-attr">
                <lexical-unit>
                    <form lang="en"><text>unicode</text></form>
                </lexical-unit>
                <sense>
                    <relation type="café" ref="entry-1"/>
                    <trait name="domaine-étymologique" value="français"/>
                </sense>
            </entry>
            """
            
            result = transformer.transform(unicode_attr_xml, element_configs)
            
            # Should preserve Unicode in attributes
            assert "café" in result or "cafe" in result
            assert "français" in result or "francais" in result

    def test_enhanced_transformer_with_special_characters_in_css(self, db_app: Flask) -> None:
        """Enhanced transformer should handle special characters in CSS classes."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword-special_123-test"
                )
            ]
            
            special_css_xml = """
            <entry id="special">
                <lexical-unit>
                    <form lang="en"><text>special</text></form>
                </lexical-unit>
            </entry>
            """
            
            result = transformer.transform(special_css_xml, element_configs)
            
            # Should handle special characters in CSS classes
            assert "headword-special_123-test" in result

    def test_enhanced_transformer_with_empty_entry(self, db_app: Flask) -> None:
        """Enhanced transformer should handle empty entries."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword"
                )
            ]
            
            empty_entry_xml = """
            <entry id="empty-entry">
                <lexical-unit>
                    <form lang="en"><text></text></form>
                </lexical-unit>
            </entry>
            """
            
            result = transformer.transform(empty_entry_xml, element_configs)
            
            # Should handle empty entries gracefully
            assert result is not None
            assert "entry-empty" in result or len(result.strip()) > 0

    def test_enhanced_transformer_with_namespace_issues(self, db_app: Flask) -> None:
        """Enhanced transformer should handle namespace issues."""
        with db_app.app_context():
            transformer = LIFTToHTMLTransformer()
            
            element_configs = [
                ElementConfig(
                    lift_element="lexical-unit",
                    display_order=1,
                    css_class="headword"
                )
            ]
            
            # XML with namespaces
            namespace_xml = """
            <lift:entry xmlns:lift="http://fieldworks.sil.org/schemas/lift/0.13" id="namespace">
                <lift:lexical-unit>
                    <lift:form lang="en"><lift:text>namespace</lift:text></lift:form>
                </lift:lexical-unit>
            </lift:entry>
            """
            
            result = transformer.transform(namespace_xml, element_configs)
            
            # Should handle namespaces correctly
            assert result is not None
            assert "namespace" in result
