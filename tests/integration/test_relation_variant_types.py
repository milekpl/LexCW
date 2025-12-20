"""
Test suite for LIFT relation-based variant types functionality.

This module tests parsing and display of variant types from LIFT relation elements
with trait children, as specified in the project requirements.
"""
from __future__ import annotations

import pytest

from app.models.entry import Entry, Relation
from app.parsers.lift_parser import LIFTParser



@pytest.mark.integration
class TestRelationBasedVariants:
    """Test parsing and handling of relation-based variant types from LIFT XML."""
    
    @pytest.mark.integration
    def test_parse_relation_with_variant_type_trait(self):
        """Test parsing a relation with variant-type trait."""
        lift_xml = '''
        <entry id="test_entry" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>fast</text></form>
            </lexical-unit>
            <relation type="_component-lexeme" ref="fast4_54ba6c3e-d22c-423c-b535-ee23456cafc1" order="0">
                <trait name="variant-type" value="Stopień najwyższy"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        
        # Should have relations
        assert len(entry.relations) == 1
        relation = entry.relations[0]
        
        # Check relation basic properties
        assert relation.type == "_component-lexeme"
        assert relation.ref == "fast4_54ba6c3e-d22c-423c-b535-ee23456cafc1"
        
        # Check that relation has variant-type trait
        assert hasattr(relation, 'traits')
        assert 'variant-type' in relation.traits
        assert relation.traits['variant-type'] == "Stopień najwyższy"
    
    @pytest.mark.integration
    def test_parse_multiple_relations_with_variant_traits(self):
        """Test parsing multiple relations with different variant-type traits."""
        lift_xml = '''
        <entry id="test_entry" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <relation type="_component-lexeme" ref="test1_ref" order="0">
                <trait name="variant-type" value="Unspecified Variant"/>
            </relation>
            <relation type="_component-lexeme" ref="test2_ref" order="1">
                <trait name="variant-type" value="Stopień najwyższy"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        entry = entries[0]
        
        # Should have 2 relations
        assert len(entry.relations) == 2
        
        # Check first relation
        relation1 = entry.relations[0]
        assert relation1.type == "_component-lexeme"
        assert relation1.ref == "test1_ref"
        assert hasattr(relation1, 'traits')
        assert relation1.traits['variant-type'] == "Unspecified Variant"
        
        # Check second relation
        relation2 = entry.relations[1]
        assert relation2.type == "_component-lexeme" 
        assert relation2.ref == "test2_ref"
        assert hasattr(relation2, 'traits')
        assert relation2.traits['variant-type'] == "Stopień najwyższy"
    
    @pytest.mark.integration
    def test_generate_lift_with_relation_variant_traits(self):
        """Test generating LIFT XML from entry with relation-based variant traits."""
        # Create entry with relation containing variant-type trait
        entry = Entry(id_="test_entry",
            lexical_unit={"en": "test"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Create relation with traits - use a standard relation type that exists
        relation = Relation(
            type="synonym",  # Use synonym instead of _component-lexeme
            ref="test_ref_12345"
        )
        relation.traits = {"variant-type": "Stopień najwyższy"}
        entry.relations = [relation]
        
        parser = LIFTParser(validate=False)
        lift_xml = parser.generate_lift_string([entry])
        
        # Verify the generated XML contains the trait
        assert 'type="synonym"' in lift_xml
        assert 'ref="test_ref_12345"' in lift_xml
        assert 'name="variant-type"' in lift_xml
        assert 'value="Stopień najwyższy"' in lift_xml
    
    @pytest.mark.integration
    def test_get_variant_type_relations(self):
        """Test method to extract variant-type relations for UI display."""
        entry = Entry(id_="test_entry",
            lexical_unit={"en": "test"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Add regular relation (not variant-type)
        regular_relation = Relation(type="synonym", ref="synonym_ref")
        
        # Add variant-type relations
        variant_relation1 = Relation(type="_component-lexeme", ref="var1_ref")
        variant_relation1.traits = {"variant-type": "Stopień najwyższy"}
        
        variant_relation2 = Relation(type="_component-lexeme", ref="var2_ref") 
        variant_relation2.traits = {"variant-type": "Unspecified Variant"}
        
        entry.relations = [regular_relation, variant_relation1, variant_relation2]
        
        # Method to get variant-type relations
        variant_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'variant-type' in rel.traits
        ]
        
        assert len(variant_relations) == 2
        assert variant_relations[0].traits['variant-type'] == "Stopień najwyższy"
        assert variant_relations[1].traits['variant-type'] == "Unspecified Variant"
    
    @pytest.mark.integration
    def test_variant_type_round_trip(self):
        """Test round-trip integrity for relation-based variant types."""
        original_xml = '''
        <entry id="round_trip_test" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>fastest</text></form>
            </lexical-unit>
            <relation type="synonym" ref="fast_base_form" order="0">
                <trait name="variant-type" value="Stopień najwyższy"/>
                <trait name="is-primary" value="true"/>
                <trait name="complex-form-type" value="Compound"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries) == 1
        entry = entries[0]
        
        # Verify parsing
        assert len(entry.relations) == 1
        relation = entry.relations[0]
        assert hasattr(relation, 'traits')
        assert relation.traits['variant-type'] == "Stopień najwyższy"
        assert relation.traits['is-primary'] == "true"
        assert relation.traits['complex-form-type'] == "Compound"
        
        # Generate back to XML
        regenerated_xml = parser.generate_lift_string(entries)
        
        # Parse again
        reparsed_entries = parser.parse_string(regenerated_xml)
        assert len(reparsed_entries) == 1
        reparsed_entry = reparsed_entries[0]
        
        # Verify round-trip integrity
        assert len(reparsed_entry.relations) == 1
        reparsed_relation = reparsed_entry.relations[0]
        assert hasattr(reparsed_relation, 'traits')
        assert reparsed_relation.traits['variant-type'] == "Stopień najwyższy"
        assert reparsed_relation.traits['is-primary'] == "true"
        assert reparsed_relation.traits['complex-form-type'] == "Compound"
