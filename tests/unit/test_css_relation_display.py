"""
Unit tests for CSS display of relations in LIFT entries.
"""

from __future__ import annotations

import pytest
from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer, ElementConfig


@pytest.mark.unit
class TestCSSRelationDisplay:
    """Test suite for CSS rendering of lexical relations."""

    def test_relation_element_displays_type_and_ref(self) -> None:
        """Test that relation elements display both type and ref attributes."""
        # Sample LIFT XML with a relation
        lift_xml = '''
        <entry id="test_entry">
            <lexical-unit>
                <form lang="en">
                    <text>test word</text>
                </form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="en">
                        <text>A test definition</text>
                    </form>
                </definition>
                <relation type="Synonym" ref="other_entry_123" data-headword="synonym word"/>
            </sense>
        </entry>
        '''
        
        # Configure elements including relation
        element_configs = [
            ElementConfig(
                lift_element="lexical-unit",
                display_order=1,
                css_class="headword",
                visibility="always"
            ),
            ElementConfig(
                lift_element="sense",
                display_order=2,
                css_class="sense",
                visibility="always"
            ),
            ElementConfig(
                lift_element="definition",
                display_order=3,
                css_class="definition",
                visibility="if-content"
            ),
            ElementConfig(
                lift_element="relation",
                display_order=4,
                css_class="relation",
                prefix="See also: ",
                visibility="if-content"
            ),
        ]
        
        # Transform to HTML
        transformer = LIFTToHTMLTransformer()
        html = transformer.transform(lift_xml, element_configs)
        
        # Verify relation is displayed with headword, not ref ID
        assert 'relation' in html, "Relation CSS class should be in output"
        assert 'Synonym' in html, "Relation type should be displayed"
        assert 'synonym word' in html, "Relation headword should be displayed"
        assert 'other_entry_123' not in html, "Relation ref ID should NOT be displayed when headword is available"
        assert 'See also:' in html, "Relation prefix should be displayed"

    def test_relation_with_only_type(self) -> None:
        """Test that relation displays correctly with only type attribute."""
        lift_xml = '''
        <entry id="test_entry">
            <sense id="sense1">
                <relation type="Antonym"/>
            </sense>
        </entry>
        '''
        
        element_configs = [
            ElementConfig(
                lift_element="sense",
                display_order=1,
                css_class="sense",
                visibility="always"
            ),
            ElementConfig(
                lift_element="relation",
                display_order=2,
                css_class="relation",
                visibility="if-content"
            ),
        ]
        
        transformer = LIFTToHTMLTransformer()
        html = transformer.transform(lift_xml, element_configs)
        
        # Should display the type
        assert 'Antonym' in html

    def test_multiple_relations_in_sense(self) -> None:
        """Test that multiple relations in a sense are all displayed."""
        lift_xml = '''
        <entry id="test_entry">
            <sense id="sense1">
                <definition>
                    <form lang="en">
                        <text>Test</text>
                    </form>
                </definition>
                <relation type="Synonym" ref="entry_1" data-headword="first word"/>
                <relation type="Antonym" ref="entry_2" data-headword="opposite word"/>
                <relation type="Compare" ref="entry_3" data-headword="similar word"/>
            </sense>
        </entry>
        '''
        
        element_configs = [
            ElementConfig(
                lift_element="sense",
                display_order=1,
                css_class="sense",
                visibility="always"
            ),
            ElementConfig(
                lift_element="definition",
                display_order=2,
                css_class="definition",
                visibility="if-content"
            ),
            ElementConfig(
                lift_element="relation",
                display_order=3,
                css_class="relation",
                visibility="if-content"
            ),
        ]
        
        transformer = LIFTToHTMLTransformer()
        html = transformer.transform(lift_xml, element_configs)
        
        # All three relations should be displayed with headwords
        assert 'Synonym' in html
        assert 'first word' in html
        assert 'Antonym' in html
        assert 'opposite word' in html
        assert 'Compare' in html
        assert 'similar word' in html
        # IDs should not be displayed
        assert 'entry_1' not in html
        assert 'entry_2' not in html
        assert 'entry_3' not in html

    def test_entry_level_relation(self) -> None:
        """Test that relations at entry level are displayed."""
        lift_xml = '''
        <entry id="test_entry">
            <lexical-unit>
                <form lang="en">
                    <text>test word</text>
                </form>
            </lexical-unit>
            <relation type="Derivation" ref="root_entry" data-headword="root word"/>
        </entry>
        '''
        
        element_configs = [
            ElementConfig(
                lift_element="lexical-unit",
                display_order=1,
                css_class="headword",
                visibility="always"
            ),
            ElementConfig(
                lift_element="relation",
                display_order=2,
                css_class="relation",
                visibility="if-content"
            ),
        ]
        
        transformer = LIFTToHTMLTransformer()
        html = transformer.transform(lift_xml, element_configs)
        
        # Entry-level relation should be displayed with headword
        assert 'Derivation' in html
        assert 'root word' in html
        assert 'root_entry' not in html
    
    def test_relation_fallback_to_ref_when_no_headword(self) -> None:
        """Test that relation falls back to showing ref when headword is not resolved."""
        lift_xml = '''
        <entry id="test_entry">
            <sense id="sense1">
                <relation type="See also" ref="unresolved_entry_id"/>
            </sense>
        </entry>
        '''
        
        element_configs = [
            ElementConfig(
                lift_element="sense",
                display_order=1,
                css_class="sense",
                visibility="always"
            ),
            ElementConfig(
                lift_element="relation",
                display_order=2,
                css_class="relation",
                visibility="if-content"
            ),
        ]
        
        transformer = LIFTToHTMLTransformer()
        html = transformer.transform(lift_xml, element_configs)
        
        # Should fall back to showing the ref when headword is not available
        assert 'See also' in html
        assert 'unresolved_entry_id' in html
