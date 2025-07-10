"""
Test suite for variant container functionality based on relation traits.

This module tests the extraction and display of variant types from LIFT relation elements
with variant-type traits, as specified in the project requirements.
"""

from __future__ import annotations

from app.models.entry import Entry, Relation


import pytest


@pytest.mark.integration
class TestVariantContainer:
    """Test variant container functionality based on relation traits."""

    @pytest.mark.integration
    def test_extract_variant_relations_from_traits(self):
        """Test extracting variant relations from relations with variant-type traits."""
        # Create test relations with and without variant-type traits
        relations = [
            Relation(
                type="_component-lexeme",
                ref="fast4_54ba6c3e-d22c-423c-b535-ee23456cafc1",
                traits={"variant-type": "Stopień najwyższy"},
                order=0,
            ),
            Relation(
                type="synonym",
                ref="quick_entry_id",
                traits={},  # No variant-type trait
            ),
            Relation(
                type="_component-lexeme",
                ref="take_a_test_36566d98-a69b-480f-ad72-0a90d481aeb3",
                traits={"variant-type": "Unspecified Variant"},
                order=1,
            ),
        ]

        # Create entry with these relations
        entry = Entry(id_="test_entry", lexical_unit={"en": "fast"}, relations=relations
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])

        # Extract variant relations
        variant_relations = entry.get_variant_relations()

        # Should return only relations with variant-type traits
        assert len(variant_relations) == 2

        # Check first variant relation (should be sorted by order)
        first_variant = variant_relations[0]
        assert first_variant["ref"] == "fast4_54ba6c3e-d22c-423c-b535-ee23456cafc1"
        assert first_variant["variant_type"] == "Stopień najwyższy"
        assert first_variant["type"] == "_component-lexeme"
        assert first_variant["order"] == 0

        # Check second variant relation
        second_variant = variant_relations[1]
        assert (
            second_variant["ref"] == "take_a_test_36566d98-a69b-480f-ad72-0a90d481aeb3"
        )
        assert second_variant["variant_type"] == "Unspecified Variant"
        assert second_variant["type"] == "_component-lexeme"
        assert second_variant["order"] == 1

    @pytest.mark.integration
    def test_extract_variant_relations_no_traits(self):
        """Test extracting variant relations when no variant-type traits exist."""
        # Create relations without variant-type traits
        relations = [
            Relation(type="synonym", ref="quick_entry_id", traits={}),
            Relation(
                type="antonym",
                ref="slow_entry_id",
                traits={"some-other-trait": "value"},
            ),
        ]

        entry = Entry(id_="test_entry", lexical_unit={"en": "fast"}, relations=relations
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])

        variant_relations = entry.get_variant_relations()

        # Should return empty list since no variant-type traits
        assert len(variant_relations) == 0

    @pytest.mark.integration
    def test_extract_variant_relations_without_order(self):
        """Test extracting variant relations when no order is specified."""
        relations = [
            Relation(
                type="_component-lexeme",
                ref="variant_b",
                traits={"variant-type": "Spelling variant"},
                # No order attribute
            ),
            Relation(
                type="_component-lexeme",
                ref="variant_a",
                traits={"variant-type": "Dialectal variant"},
                # No order attribute
            ),
        ]

        entry = Entry(id_="test_entry", lexical_unit={"en": "test"}, relations=relations
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])

        variant_relations = entry.get_variant_relations()

        # Should return relations, sorted by ref when no order
        assert len(variant_relations) == 2

        # Should be sorted by ref alphabetically
        assert variant_relations[0]["ref"] == "variant_a"
        assert variant_relations[0]["variant_type"] == "Dialectal variant"
        assert "order" not in variant_relations[0]

        assert variant_relations[1]["ref"] == "variant_b"
        assert variant_relations[1]["variant_type"] == "Spelling variant"
        assert "order" not in variant_relations[1]

    @pytest.mark.integration
    def test_entry_to_dict_includes_variant_relations(self):
        """Test that Entry.to_dict() includes variant_relations field."""
        relations = [
            Relation(
                type="_component-lexeme",
                ref="test_variant_id",
                traits={"variant-type": "Test Variant Type"},
                order=0,
            )
        ]

        entry = Entry(id_="test_entry", lexical_unit={"en": "test"}, relations=relations
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])

        entry_dict = entry.to_dict()

        # Should include variant_relations field
        assert "variant_relations" in entry_dict
        assert len(entry_dict["variant_relations"]) == 1

        variant_relation = entry_dict["variant_relations"][0]
        assert variant_relation["ref"] == "test_variant_id"
        assert variant_relation["variant_type"] == "Test Variant Type"
        assert variant_relation["type"] == "_component-lexeme"
        assert variant_relation["order"] == 0
