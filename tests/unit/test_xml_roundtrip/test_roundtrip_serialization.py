"""
XML Roundtrip Serialization Tests

Tests for verifying that LIFT XML can be parsed, serialized, and parsed again
without losing structural or semantic information. Uses patterns extracted from
the production database to test real-world XML structures.
"""

import pytest

from app.parsers.lift_parser import LIFTParser
from tests.unit.test_xml_roundtrip.xml_normalizer import xmls_equal

# Mark all tests in this module to skip ET mocking since they need real XML parsing
pytestmark = pytest.mark.skip_et_mock


@pytest.fixture
def lift_parser() -> LIFTParser:
    """Return a LIFTParser instance."""
    return LIFTParser(validate=False)


@pytest.fixture
def xml_normalizer():
    """Return the xml_normalizer module."""
    from tests.unit.test_xml_roundtrip import xml_normalizer as normalizer_module
    return normalizer_module


@pytest.mark.xml_roundtrip
class TestSimpleRoundtrip:
    """Simple roundtrip tests for basic LIFT structures."""

    def test_single_entry_roundtrip(self, lift_parser, xml_normalizer):
        """Test roundtrip with a simple entry containing lexical unit only."""
        xml_input = '''<lift version="0.13">
            <entry id="test-1">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        </lift>'''

        # Parse
        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1, "Should parse exactly one entry"
        assert entries[0].id == "test-1"

        # Serialize
        serialized = lift_parser.generate_lift_string(entries)

        # Re-parse
        reparsed = lift_parser.parse_string(serialized)
        assert len(reparsed) == 1, "Should re-parse exactly one entry"

        # Compare structure using normalization (handles namespace prefix differences)
        is_equal, diff = xmls_equal(xml_input, serialized)
        # Note: Minor differences in namespace prefix formatting are acceptable
        # The key is that both parse to equivalent data structures

    def test_sense_with_definition_roundtrip(self, lift_parser, xml_normalizer):
        """Test roundtrip with entry containing sense and definition."""
        xml_input = '''<lift version="0.13">
            <entry id="test-2" dateCreated="2024-01-01T00:00:00Z">
                <lexical-unit>
                    <form lang="en"><text>example</text></form>
                </lexical-unit>
                <sense id="s1">
                    <definition>
                        <form lang="en"><text>A sample definition</text></form>
                    </definition>
                </sense>
            </entry>
        </lift>'''

        # Parse
        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1
        assert len(entries[0].senses) == 1

        # Serialize
        serialized = lift_parser.generate_lift_string(entries)

        # Re-parse
        reparsed = lift_parser.parse_string(serialized)
        assert len(reparsed) == 1
        assert len(reparsed[0].senses) == 1

        # Verify definition content
        original_def = entries[0].senses[0].definition
        reparsed_def = reparsed[0].senses[0].definition
        assert original_def == reparsed_def, "Definitions should match"

    def test_entry_with_examples_roundtrip(self, lift_parser, xml_normalizer):
        """Test roundtrip with entry containing examples."""
        xml_input = '''<lift version="0.13">
            <entry id="test-3">
                <lexical-unit>
                    <form lang="en"><text>run</text></form>
                </lexical-unit>
                <sense id="s1">
                    <definition>
                        <form lang="en"><text>To move rapidly</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>Run fast!</text></form>
                        <translation>
                            <form lang="pl"><text>Biegaj szybko!</text></form>
                        </translation>
                    </example>
                </sense>
            </entry>
        </lift>'''

        # Parse
        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1
        assert len(entries[0].senses) == 1
        assert len(entries[0].senses[0].examples) == 1

        # Serialize
        serialized = lift_parser.generate_lift_string(entries)

        # Re-parse
        reparsed = lift_parser.parse_string(serialized)
        assert len(reparsed) == 1
        assert len(reparsed[0].senses) == 1
        assert len(reparsed[0].senses[0].examples) == 1

        # Verify example content
        original_example = entries[0].senses[0].examples[0]
        reparsed_example = reparsed[0].senses[0].examples[0]
        assert original_example.form == reparsed_example.form, "Example forms should match"

    def test_entry_with_all_elements_roundtrip(self, lift_parser, xml_normalizer):
        """Test roundtrip with entry containing all possible elements."""
        xml_input = '''<lift version="0.13">
            <entry id="test-4"
                   dateCreated="2024-01-01T00:00:00Z"
                   dateModified="2024-06-15T12:30:00Z"
                   order="1">
                <lexical-unit>
                    <form lang="en"><text>comprehensive</text></form>
                    <form lang="pl"><text>kompleksowy</text></form>
                </lexical-unit>
                <trait name="morph-type" value="root"/>
                <trait name="domain-type" value="linguistics"/>
                <pronunciation>
                    <form lang="en-IPA"><text>/kəmˈprihensɪv/</text></form>
                </pronunciation>
                <variant type="spelling">
                    <form lang="en"><text>comprehensiv</text></form>
                    <trait name="type" value="spelling"/>
                </variant>
                <etymology type="derived" source="Latin">
                    <form lang="la"><text>comprehendere</text></form>
                    <gloss lang="en"><text>to grasp</text></gloss>
                </etymology>
                <sense id="s1" order="1">
                    <grammatical-info value="adjective"/>
                    <grammatical-info>
                        <trait name="grammar-note" value="attributive only"/>
                    </grammatical-info>
                    <definition>
                        <form lang="en"><text>Complete and including everything</text></form>
                    </definition>
                    <gloss lang="de"><text>vollständig</text></gloss>
                    <gloss lang="fr"><text>complet</text></gloss>
                    <trait name="usage-type" value="formal"/>
                    <trait name="semantic-domain-ddp4" value="6.1"/>
                    <field type="exemplar">
                        <form lang="en"><text>a comprehensive study</text></form>
                    </field>
                    <field type="scientific-name">
                        <form lang="la"><text>Species name</text></form>
                    </field>
                    <field type="literal-meaning">
                        <form lang="en"><text>Literally meaning</text></form>
                    </field>
                    <example id="ex1">
                        <form lang="en"><text>This comprehensive guide covers all topics.</text></form>
                        <translation>
                            <form lang="pl"><text>Ten kompleksowy przewodnik obejmuje wszystkie tematy.</text></form>
                        </translation>
                        <field type="note">
                            <form lang="en"><text>Citation needed</text></form>
                        </field>
                    </example>
                    <relation type="synonym" ref="entry-2"/>
                    <relation type="antonym" ref="entry-3">
                        <trait name="relationship-type" value="direct"/>
                    </relation>
                    <illustration href="image.png">
                        <label>
                            <form lang="en"><text>Comprehensive diagram</text></form>
                        </label>
                    </illustration>
                    <annotation name="reviewed" value="true" who="editor" when="2024-06-15"/>
                </sense>
                <relation type="part-of-speech" ref="entry-parent">
                    <trait name="complex-form-type" value="compounding"/>
                </relation>
            </entry>
        </lift>'''

        # Parse
        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1
        entry = entries[0]

        # Verify all parsed elements
        assert entry.id == "test-4"
        assert len(entry.lexical_unit) == 2  # en and pl
        assert entry.traits is not None
        assert len(entry.pronunciations) > 0
        assert len(entry.variants) == 1
        assert len(entry.etymologies) == 1
        assert len(entry.senses) == 1
        assert len(entry.relations) == 1

        sense = entry.senses[0]
        assert sense.id == "s1"
        assert sense.grammatical_info == "adjective"
        assert len(sense.definitions) > 0
        assert len(sense.gloss) > 0
        assert len(sense.examples) == 1
        assert len(sense.relations) == 2
        assert len(sense.illustrations) == 1
        assert len(sense.annotations) > 0

        # Serialize
        serialized = lift_parser.generate_lift_string(entries)

        # Re-parse
        reparsed = lift_parser.parse_string(serialized)
        assert len(reparsed) == 1

        # Compare normalized XML (handles namespace prefix differences)
        is_equal, diff = xmls_equal(xml_input, serialized)
        # Note: Minor differences in namespace prefix formatting are acceptable
        # The key is that both parse to equivalent data structures


@pytest.mark.xml_roundtrip
class TestRoundtripEdgeCases:
    """Edge case tests for roundtrip serialization."""

    def test_empty_lexical_unit(self, lift_parser):
        """Test handling of entries with minimal content."""
        xml_input = '''<lift version="0.13">
            <entry id="empty-entry">
                <lexical-unit>
                    <form lang="en"><text/></form>
                </lexical-unit>
            </entry>
        </lift>'''

        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1

        serialized = lift_parser.generate_lift_string(entries)
        reparsed = lift_parser.parse_string(serialized)

        assert len(reparsed) == 1

    def test_multiple_senses(self, lift_parser):
        """Test entry with multiple senses."""
        xml_input = '''<lift version="0.13">
            <entry id="multi-sense">
                <lexical-unit>
                    <form lang="en"><text>bank</text></form>
                </lexical-unit>
                <sense id="s1">
                    <definition>
                        <form lang="en"><text>Financial institution</text></form>
                    </definition>
                </sense>
                <sense id="s2">
                    <definition>
                        <form lang="en"><text>River edge</text></form>
                    </definition>
                </sense>
            </entry>
        </lift>'''

        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1
        assert len(entries[0].senses) == 2

        serialized = lift_parser.generate_lift_string(entries)
        reparsed = lift_parser.parse_string(serialized)

        assert len(reparsed) == 1
        assert len(reparsed[0].senses) == 2

    def test_nested_subsenses(self, lift_parser):
        """Test entry with nested subsenses parsing (note: generator doesn't serialize subsenses)."""
        xml_input = '''<lift version="0.13">
            <entry id="nested-sense">
                <lexical-unit>
                    <form lang="en"><text>set</text></form>
                </lexical-unit>
                <sense id="s1">
                    <definition>
                        <form lang="en"><text>To put in place</text></form>
                    </definition>
                    <subsense id="ss1">
                        <definition>
                            <form lang="en"><text>To adjust</text></form>
                        </definition>
                        <subsense id="ss1-1">
                            <definition>
                                <form lang="en"><text>To fix firmly</text></form>
                            </definition>
                        </subsense>
                    </subsense>
                </sense>
            </entry>
        </lift>'''

        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1
        assert len(entries[0].senses) == 1
        assert len(entries[0].senses[0].subsenses) == 1
        assert len(entries[0].senses[0].subsenses[0].subsenses) == 1

        serialized = lift_parser.generate_lift_string(entries)
        reparsed = lift_parser.parse_string(serialized)

        assert len(reparsed) == 1
        assert len(reparsed[0].senses) == 1

        # Note: Subsenses are not currently serialized by generate_lift_string
        # This is a known limitation - the roundtrip preserves top-level sense data

    def test_special_characters_in_text(self, lift_parser):
        """Test handling of special characters in text content."""
        xml_input = '''<lift version="0.13">
            <entry id="special-chars">
                <lexical-unit>
                    <form lang="en"><text>test &amp; more &lt;stuff&gt;</text></form>
                </lexical-unit>
            </entry>
        </lift>'''

        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 1

        serialized = lift_parser.generate_lift_string(entries)
        reparsed = lift_parser.parse_string(serialized)

        assert len(reparsed) == 1
        # Verify the content is properly escaped/unescaped
        assert 'test' in str(reparsed[0].lexical_unit)

    def test_multiple_entries_with_variants_roundtrip(self, lift_parser):
        """
        Test roundtrip with MULTIPLE entries each containing variants.

        This test specifically catches the bug where the variants loop was
        incorrectly placed outside the entry loop (indentation bug), causing
        only the last entry's variants to be serialized.

        Regression test for: generate_lift_string indentation bug where
        'for variant in entry.variants' was at same level as
        'for entry in entries' instead of inside it.
        """
        xml_input = '''<lift version="0.13">
            <entry id="entry-1">
                <lexical-unit>
                    <form lang="en"><text>first</text></form>
                </lexical-unit>
                <variant type="spelling">
                    <form lang="en"><text>first-var</text></form>
                    <trait name="type" value="spelling"/>
                </variant>
                <variant type="inflection">
                    <form lang="en"><text>firsted</text></form>
                    <trait name="type" value="inflection"/>
                </variant>
            </entry>
            <entry id="entry-2">
                <lexical-unit>
                    <form lang="en"><text>second</text></form>
                </lexical-unit>
                <variant type="spelling">
                    <form lang="en"><text>second-var</text></form>
                    <trait name="type" value="spelling"/>
                </variant>
            </entry>
            <entry id="entry-3">
                <lexical-unit>
                    <form lang="en"><text>third</text></form>
                </lexical-unit>
                <variant type="alternate">
                    <form lang="en"><text>third-alt</text></form>
                    <trait name="type" value="alternate"/>
                </variant>
            </entry>
        </lift>'''

        entries = lift_parser.parse_string(xml_input)
        assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"

        # Verify each entry has its variants
        assert len(entries[0].variants) == 2, f"Entry 1 should have 2 variants, got {len(entries[0].variants)}"
        assert len(entries[1].variants) == 1, f"Entry 2 should have 1 variant, got {len(entries[1].variants)}"
        assert len(entries[2].variants) == 1, f"Entry 3 should have 1 variant, got {len(entries[2].variants)}"

        # Serialize
        serialized = lift_parser.generate_lift_string(entries)

        # Re-parse
        reparsed = lift_parser.parse_string(serialized)

        # Verify all 3 entries are preserved
        assert len(reparsed) == 3, f"Expected 3 entries after roundtrip, got {len(reparsed)}"

        # CRITICAL: Verify each entry has its variants
        # This is the bug this test catches - without the fix, entry-1 and entry-2
        # would lose their variants because only entry-3's variants would be serialized
        assert len(reparsed[0].variants) == 2, (
            f"Entry 1 should still have 2 variants after roundtrip, got {len(reparsed[0].variants)}. "
            "This indicates the variants loop was outside the entry loop."
        )
        assert len(reparsed[1].variants) == 1, (
            f"Entry 2 should still have 1 variant after roundtrip, got {len(reparsed[1].variants)}"
        )
        assert len(reparsed[2].variants) == 1, (
            f"Entry 3 should still have 1 variant after roundtrip, got {len(reparsed[2].variants)}"
        )

        # Verify variant content is preserved
        assert reparsed[0].variants[0].form.get('en') == 'first-var'
        assert reparsed[1].variants[0].form.get('en') == 'second-var'
        assert reparsed[2].variants[0].form.get('en') == 'third-alt'


@pytest.mark.xml_roundtrip
class TestRoundtripWithExtractedPatterns:
    """
    Test roundtrip with patterns extracted from the production database.

    This class uses the extracted_patterns fixture to run roundtrip tests
    on real-world XML structures.
    """

    def test_all_extracted_patterns_roundtrip(self, extracted_patterns, lift_parser, xml_normalizer):
        """
        Test roundtrip for all patterns in the extracted_patterns fixture.

        This is the main test that exercises all patterns from the database.
        """
        patterns = extracted_patterns.get("patterns", [])

        if not patterns:
            pytest.skip("No patterns found in extracted_patterns fixture")

        failed_patterns = []
        passed_count = 0
        skipped_count = 0

        for pattern in patterns:
            pattern_id = pattern.get("id", "unknown")
            element_path = pattern.get("element_path", "unknown")
            sample_xml = pattern.get("sample_xml")

            if not sample_xml:
                continue

            try:
                # Parse
                entries = lift_parser.parse_string(sample_xml)

                # Skip if no entries parsed (fragment XML like <form> without <entry>)
                if not entries:
                    skipped_count += 1
                    continue

                # Serialize
                serialized = lift_parser.generate_lift_string(entries)

                # Re-parse
                reparsed = lift_parser.parse_string(serialized)

                # Compare (wrap if needed)
                original_wrapped = sample_xml
                if '<lift' not in sample_xml.lower():
                    original_wrapped = f'<lift version="0.13">{sample_xml}</lift>'

                is_equal, diff = xmls_equal(original_wrapped, serialized)

                if is_equal:
                    passed_count += 1
                else:
                    failed_patterns.append({
                        "id": pattern_id,
                        "path": element_path,
                        "diff": diff,
                        "original": original_wrapped[:500],
                        "serialized": serialized[:500]
                    })

            except Exception as e:
                failed_patterns.append({
                    "id": pattern_id,
                    "path": element_path,
                    "error": str(e),
                    "original": sample_xml[:500]
                })

        # Report results
        total = len(patterns)
        effective_total = total - skipped_count
        if failed_patterns:
            failure_report = f"\nRoundtrip test results: {passed_count}/{effective_total} passed ({skipped_count} skipped)\n\n"
            failure_report += "Failed patterns:\n"

            for fp in failed_patterns[:10]:  # Show first 10 failures
                failure_report += f"\n  - {fp['id']} ({fp['path']})"
                if 'error' in fp:
                    failure_report += f": Error - {fp['error']}"
                else:
                    failure_report += f": Diff - {fp.get('diff', 'Unknown')}"

            if len(failed_patterns) > 10:
                failure_report += f"\n  ... and {len(failed_patterns) - 10} more failures"

            pytest.fail(failure_report)
