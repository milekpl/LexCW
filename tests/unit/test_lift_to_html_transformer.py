"""Unit tests for LIFT to HTML transformer with hierarchical processing."""

from __future__ import annotations

import pytest
from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer, ElementConfig


class TestLIFTToHTMLTransformer:
    """Test cases for the LIFT to HTML transformer."""

    def test_basic_entry_with_sense_hierarchy(self):
        """Test that sense elements properly wrap their children."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en">
                    <text>attest to sth</text>
                </form>
            </lexical-unit>
            <sense>
                <definition>
                    <form lang="pl">
                        <text>świadczyć o czymś</text>
                    </form>
                </definition>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig(
                lift_element="lexical-unit",
                display_order=10,
                css_class="headword lexical-unit",
                visibility="if-content",
                display_mode="inline"
            ),
            ElementConfig(
                lift_element="sense",
                display_order=20,
                css_class="sense",
                visibility="if-content",
                display_mode="block"
            ),
            ElementConfig(
                lift_element="definition",
                display_order=30,
                css_class="definition",
                visibility="if-content",
                display_mode="inline"
            ),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Check that sense wraps definition
        assert '<div class="sense">' in result
        assert '<span class="definition">świadczyć o czymś</span>' in result
        
        # Check that lexical-unit is rendered
        assert '<span class="headword lexical-unit">attest to sth</span>' in result
        
        # Ensure no duplication of definition text outside sense
        parts = result.split('<div class="sense">')
        assert 'świadczyć o czymś' not in parts[0]  # Not before sense div

    def test_multiple_senses(self):
        """Test that multiple sense elements are rendered separately."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>bank</text></form>
            </lexical-unit>
            <sense>
                <definition><form lang="pl"><text>brzeg rzeki</text></form></definition>
            </sense>
            <sense>
                <definition><form lang="pl"><text>instytucja finansowa</text></form></definition>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
            ElementConfig("sense", 20, "sense", visibility="if-content", display_mode="block"),
            ElementConfig("definition", 30, "definition", visibility="if-content", display_mode="inline"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Should have two sense divs
        assert result.count('<div class="sense">') == 2
        assert 'brzeg rzeki' in result
        assert 'instytucja finansowa' in result

    def test_unconfigured_parent_elements(self):
        """Test that unconfigured parent elements pass through to their children."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
        </entry>
        """
        
        # Only configure lexical-unit, not entry or form
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Should still extract text even though entry and form aren't configured
        assert 'test' in result
        assert '<span class="headword">' in result

    def test_empty_entry(self):
        """Test that empty entries return appropriate message."""
        lift_xml = """
        <entry id="test">
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        assert 'entry-empty' in result or not result.strip()

    def test_if_content_visibility(self):
        """Test that if-content visibility hides empty elements."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <sense>
                <definition>
                    <form lang="pl"><text></text></form>
                </definition>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
            ElementConfig("sense", 20, "sense", visibility="if-content", display_mode="block"),
            ElementConfig("definition", 30, "definition", visibility="if-content", display_mode="inline"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Empty sense should be hidden due to if-content
        assert '<div class="sense">' not in result

    def test_prefix_suffix(self):
        """Test that prefix and suffix are added correctly."""
        lift_xml = """
        <entry id="test">
            <pronunciation>
                <form lang="seh-fonipa"><text>test</text></form>
            </pronunciation>
        </entry>
        """
        
        configs = [
            ElementConfig(
                "pronunciation", 
                10, 
                "pronunciation", 
                prefix="/",
                suffix="/",
                visibility="if-content", 
                display_mode="inline"
            ),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        assert '<span class="prefix">/</span>' in result
        assert '<span class="suffix">/</span>' in result
        assert 'test' in result

    def test_display_mode_block_vs_inline(self):
        """Test that display_mode controls div vs span output."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <sense>
                <definition><form lang="pl"><text>test</text></form></definition>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
            ElementConfig("sense", 20, "sense", visibility="if-content", display_mode="block"),
            ElementConfig("definition", 30, "definition", visibility="if-content", display_mode="inline"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Inline should use span
        assert '<span class="headword">' in result
        # Block should use div
        assert '<div class="sense">' in result

    def test_grammatical_info_from_attribute(self):
        """Test that grammatical-info extracts value from attribute."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <sense>
                <grammatical-info value="Noun">
                </grammatical-info>
                <definition>
                    <form lang="pl"><text>rzecz</text></form>
                </definition>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
            ElementConfig("sense", 20, "sense", visibility="if-content", display_mode="block"),
            ElementConfig("grammatical-info", 25, "pos", visibility="if-content", display_mode="inline"),
            ElementConfig("definition", 30, "definition", visibility="if-content", display_mode="inline"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Should extract "Noun" from value attribute
        assert '<span class="pos">Noun</span>' in result
        assert 'rzecz' in result

    def test_example_with_translation(self):
        """Test that examples render with their translations."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>contest</text></form>
            </lexical-unit>
            <sense>
                <definition>
                    <form lang="pl"><text>zawody</text></form>
                </definition>
                <example>
                    <form lang="en"><text>It's no contest.</text></form>
                    <translation type="Free translation">
                        <form lang="pl"><text>Z góry wiadomo, kto zwycięży.</text></form>
                    </translation>
                </example>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
            ElementConfig("sense", 20, "sense", visibility="if-content", display_mode="block"),
            ElementConfig("definition", 30, "definition", visibility="if-content", display_mode="inline"),
            ElementConfig("example", 40, "example", visibility="if-content", display_mode="block"),
            ElementConfig("translation", 50, "translation", visibility="if-content", display_mode="block"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Should have example text
        assert "It's no contest." in result
        # Should have translation text (not the type attribute)
        assert "Z góry wiadomo, kto zwycięży." in result
        # Should NOT extract 'type' attribute as content
        assert "Free translation" not in result or '<div class="translation">Z góry wiadomo' in result

    def test_trait_and_field_elements(self):
        """Test that trait and field elements render their attributes correctly."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <trait name="morph-type" value="stem"/>
            <sense>
                <definition>
                    <form lang="pl"><text>test</text></form>
                </definition>
                <field type="FTFlags">
                    <form lang="pl"><text>REVIEW_ME</text></form>
                </field>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
            ElementConfig("trait", 20, "trait", visibility="if-content", display_mode="inline"),
            ElementConfig("sense", 30, "sense", visibility="if-content", display_mode="block"),
            ElementConfig("definition", 40, "definition", visibility="if-content", display_mode="inline"),
            ElementConfig("field", 50, "custom-field", visibility="if-content", display_mode="block"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs)
        
        # Trait should show just its value (the transformer itself doesn't add data attributes)
        assert "stem" in result
        # Field should show its content
        assert "REVIEW_ME" in result

    def test_entry_level_pos_display(self):
        """Test that entry-level PoS is displayed before senses when all senses have same PoS."""
        lift_xml = """
        <entry id="test">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <sense>
                <grammatical-info value="Noun"></grammatical-info>
                <definition>
                    <form lang="pl"><text>first definition</text></form>
                </definition>
            </sense>
            <sense>
                <grammatical-info value="Noun"></grammatical-info>
                <definition>
                    <form lang="pl"><text>second definition</text></form>
                </definition>
            </sense>
        </entry>
        """
        
        configs = [
            ElementConfig("lexical-unit", 10, "headword", visibility="if-content", display_mode="inline"),
            ElementConfig("sense", 20, "sense", visibility="if-content", display_mode="block"),
            ElementConfig("grammatical-info", 25, "pos", visibility="if-content", display_mode="inline"),
            ElementConfig("definition", 30, "definition", visibility="if-content", display_mode="inline"),
        ]
        
        transformer = LIFTToHTMLTransformer()
        result = transformer.transform(lift_xml, configs, entry_level_pos="Noun")
        
        # Should have entry-level PoS displayed once
        assert '<span class="entry-pos">Noun</span>' in result
        # Should NOT have sense-level PoS repeated (since they match entry-level)
        # Count how many times "Noun" appears - should be 1 (entry-level) not 3 (entry + 2 senses)
        noun_count = result.count('Noun')
        assert noun_count == 1, f"Expected 1 occurrence of 'Noun', found {noun_count}"
