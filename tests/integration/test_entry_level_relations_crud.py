"""
Test suite for entry-level relations CRUD operations.

This module tests that variant relations, component relations, and regular relations
are properly preserved in round-trip CRUD operations (Create, Read, Update, Delete).
"""
from __future__ import annotations

import pytest
from app.models.entry import Entry, Relation
from app.parsers.lift_parser import LIFTParser
from app.services.dictionary_service import DictionaryService
from app.utils.multilingual_form_processor import process_entry_form_data
from app.database.mock_connector import MockDatabaseConnector


@pytest.mark.integration
class TestEntryLevelRelationsCRUD:
    """Test entry-level relations CRUD operations."""
    
    @pytest.mark.integration
    def test_variant_relations_round_trip(self):
        """Test that variant relations are preserved in round-trip operations."""
        # Create entry with variant relations
        original_xml = '''
        <entry id="variant_test" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>fast</text></form>
            </lexical-unit>
            <relation type="_component-lexeme" ref="fast_base" order="0">
                <trait name="variant-type" value="Stopień najwyższy"/>
            </relation>
            <relation type="_component-lexeme" ref="fast_adv" order="1">
                <trait name="variant-type" value="Adverb Form"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries) == 1
        entry = entries[0]
        
        # Verify variant relations
        variant_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'variant-type' in rel.traits
        ]
        assert len(variant_relations) == 2
        assert variant_relations[0].traits['variant-type'] == "Stopień najwyższy"
        assert variant_relations[1].traits['variant-type'] == "Adverb Form"
        
        # Generate back to XML
        regenerated_xml = parser.generate_lift_string(entries)
        
        # Parse again to verify round-trip
        reparsed_entries = parser.parse_string(regenerated_xml)
        reparsed_entry = reparsed_entries[0]
        
        # Verify round-trip integrity
        reparsed_variant_relations = [
            rel for rel in reparsed_entry.relations 
            if hasattr(rel, 'traits') and 'variant-type' in rel.traits
        ]
        assert len(reparsed_variant_relations) == 2
        assert reparsed_variant_relations[0].traits['variant-type'] == "Stopień najwyższy"
        assert reparsed_variant_relations[1].traits['variant-type'] == "Adverb Form"
    
    @pytest.mark.integration
    def test_component_relations_round_trip(self):
        """Test that component relations are preserved in round-trip operations."""
        # Create entry with component relations
        original_xml = '''
        <entry id="component_test" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>basketball</text></form>
            </lexical-unit>
            <relation type="_component-lexeme" ref="basket" order="0">
                <trait name="complex-form-type" value="Compound"/>
                <trait name="is-primary" value="true"/>
            </relation>
            <relation type="_component-lexeme" ref="ball" order="1">
                <trait name="complex-form-type" value="Compound"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries) == 1
        entry = entries[0]
        
        # Verify component relations
        component_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(component_relations) == 2
        assert component_relations[0].traits['complex-form-type'] == "Compound"
        assert component_relations[0].traits['is-primary'] == "true"
        assert component_relations[1].traits['complex-form-type'] == "Compound"
        
        # Generate back to XML
        regenerated_xml = parser.generate_lift_string(entries)
        
        # Parse again to verify round-trip
        reparsed_entries = parser.parse_string(regenerated_xml)
        reparsed_entry = reparsed_entries[0]
        
        # Verify round-trip integrity
        reparsed_component_relations = [
            rel for rel in reparsed_entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(reparsed_component_relations) == 2
        assert reparsed_component_relations[0].traits['complex-form-type'] == "Compound"
        assert reparsed_component_relations[1].traits['complex-form-type'] == "Compound"
    
    @pytest.mark.integration
    def test_mixed_relations_round_trip(self):
        """Test that mixed relation types are preserved in round-trip operations."""
        # Create entry with mixed relation types
        original_xml = '''
        <entry id="mixed_test" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <!-- Regular semantic relation -->
            <relation type="synonym" ref="synonym_entry"/>
            <!-- Variant relation -->
            <relation type="_component-lexeme" ref="variant_entry">
                <trait name="variant-type" value="Spelling Variant"/>
            </relation>
            <!-- Component relation -->
            <relation type="_component-lexeme" ref="component_entry">
                <trait name="complex-form-type" value="Compound"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries) == 1
        entry = entries[0]
        
        # Verify all relation types
        assert len(entry.relations) == 3
        
        # Regular relation
        regular_relations = [rel for rel in entry.relations if rel.type == "synonym"]
        assert len(regular_relations) == 1
        
        # Variant relations
        variant_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'variant-type' in rel.traits
        ]
        assert len(variant_relations) == 1
        assert variant_relations[0].traits['variant-type'] == "Spelling Variant"
        
        # Component relations
        component_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(component_relations) == 1
        assert component_relations[0].traits['complex-form-type'] == "Compound"
        
        # Generate back to XML
        regenerated_xml = parser.generate_lift_string(entries)
        
        # Parse again to verify round-trip
        reparsed_entries = parser.parse_string(regenerated_xml)
        reparsed_entry = reparsed_entries[0]
        
        # Verify round-trip integrity
        assert len(reparsed_entry.relations) == 3
        
        reparsed_regular_relations = [rel for rel in reparsed_entry.relations if rel.type == "synonym"]
        assert len(reparsed_regular_relations) == 1
        
        reparsed_variant_relations = [
            rel for rel in reparsed_entry.relations 
            if hasattr(rel, 'traits') and 'variant-type' in rel.traits
        ]
        assert len(reparsed_variant_relations) == 1
        assert reparsed_variant_relations[0].traits['variant-type'] == "Spelling Variant"
        
        reparsed_component_relations = [
            rel for rel in reparsed_entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(reparsed_component_relations) == 1
        assert reparsed_component_relations[0].traits['complex-form-type'] == "Compound"


@pytest.mark.integration
class TestFormDataProcessing:
    """Test form data processing for relations."""
    
    @pytest.mark.integration
    def test_variant_relations_form_processing(self):
        """Test that variant relations form data is properly processed."""
        form_data = {
            'id': 'test_entry',
            'lexical_unit.en': 'test',
            'variant_relations[0].ref': 'variant1',
            'variant_relations[0].type': '_component-lexeme',
            'variant_relations[0].variant_type': 'Spelling Variant',
            'variant_relations[0].order': '0',
            'variant_relations[1].ref': 'variant2',
            'variant_relations[1].type': '_component-lexeme',
            'variant_relations[1].variant_type': 'Alternative Form',
            'variant_relations[1].order': '1',
        }
        
        # Import the specific function for variant relations processing
        from app.utils.multilingual_form_processor import process_variant_relations_form_data
        
        # Process variant relations specifically
        variant_relations = process_variant_relations_form_data(form_data)
        
        # Should have 2 relations
        assert len(variant_relations) == 2
        
        # Both should be _component-lexeme with variant-type traits
        for relation in variant_relations:
            assert relation['type'] == '_component-lexeme'
            assert 'traits' in relation
            assert 'variant-type' in relation['traits']
        
        # Check specific values
        assert variant_relations[0]['traits']['variant-type'] == 'Spelling Variant'
        assert variant_relations[1]['traits']['variant-type'] == 'Alternative Form'


@pytest.mark.integration
class TestComplexFormComponentsCRUD:
    """Test complex form components CRUD operations."""
    
    @pytest.mark.integration
    def test_component_relations_xml_serialization(self):
        """Test that component relations are properly serialized to XML."""
        # Create entry with component relations
        original_xml = '''
        <entry id="component_test" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>basketball</text></form>
            </lexical-unit>
            <relation type="_component-lexeme" ref="basket" order="0">
                <trait name="complex-form-type" value="Compound"/>
            </relation>
            <relation type="_component-lexeme" ref="ball" order="1">
                <trait name="complex-form-type" value="Compound"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries) == 1
        entry = entries[0]
        
        # Verify component relations
        component_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(component_relations) == 2
        assert component_relations[0].traits['complex-form-type'] == "Compound"
        assert component_relations[1].traits['complex-form-type'] == "Compound"
        
        # Generate back to XML
        regenerated_xml = parser.generate_lift_string(entries)
        
        # Parse again to verify round-trip
        reparsed_entries = parser.parse_string(regenerated_xml)
        reparsed_entry = reparsed_entries[0]
        
        # Verify round-trip integrity
        reparsed_component_relations = [
            rel for rel in reparsed_entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(reparsed_component_relations) == 2
        assert reparsed_component_relations[0].traits['complex-form-type'] == "Compound"
        assert reparsed_component_relations[1].traits['complex-form-type'] == "Compound"
    
    @pytest.mark.integration
    def test_components_form_processing(self):
        """Test that components form data is properly processed."""
        form_data = {
            'id': 'test_entry',
            'lexical_unit.en': 'basketball',
            'components[0].ref': 'basket',
            'components[0].type': 'Compound',
            'components[0].order': '0',
            'components[1].ref': 'ball',
            'components[1].type': 'Compound',
            'components[1].order': '1',
        }
        
        # Import the specific function for components processing
        from app.utils.multilingual_form_processor import process_components_form_data, merge_form_data_with_entry_data
        
        # Process components specifically
        components = process_components_form_data(form_data)
        
        # Should have 2 components
        assert len(components) == 2
        
        # Both should be _component-lexeme with complex-form-type traits
        for component in components:
            assert component['type'] == '_component-lexeme'
            assert 'traits' in component
            assert 'complex-form-type' in component['traits']
        
        # Check specific values
        assert components[0]['traits']['complex-form-type'] == 'Compound'
        assert components[1]['traits']['complex-form-type'] == 'Compound'
        
        # Now test full form processing
        processed_data = merge_form_data_with_entry_data(form_data, None)
        
        # Check that components are converted to relations with traits
        assert 'relations' in processed_data
        relations = processed_data['relations']
        
        # Should have 2 relations
        assert len(relations) == 2
        
        # Both should be _component-lexeme with complex-form-type traits
        for relation in relations:
            assert relation['type'] == '_component-lexeme'
            assert 'traits' in relation
            assert 'complex-form-type' in relation['traits']
        
        # Check specific values
        assert relations[0]['traits']['complex-form-type'] == 'Compound'
        assert relations[1]['traits']['complex-form-type'] == 'Compound'


@pytest.mark.integration
class TestDictionaryServiceIntegration:
    """Test dictionary service integration for relations."""
    
    @pytest.mark.integration
    def test_variant_relations_persistence(self):
        """Test that variant relations persist through dictionary service operations."""
        # Create mock database
        mock_db = MockDatabaseConnector()
        
        # Create dictionary service
        dict_service = DictionaryService(mock_db)
        
        # Create entry with variant relations
        entry = Entry(
            id_="test_entry",
            lexical_unit={"en": "test"},
            senses=[{"definition": {"en": "test definition"}}]
        )
        
        # Add variant relation
        variant_relation = Relation(
            type="_component-lexeme",
            ref="variant_entry"
        )
        variant_relation.traits = {"variant-type": "Spelling Variant"}
        entry.relations = [variant_relation]
        
        # Save entry to dictionary (using the correct method)
        dict_service.create_entry(entry)
        
        # Retrieve entry
        retrieved_entry = dict_service.get_entry("test_entry")
        
        # Verify variant relation is preserved
        assert retrieved_entry is not None
        assert len(retrieved_entry.relations) == 1
        assert retrieved_entry.relations[0].type == "_component-lexeme"
        assert hasattr(retrieved_entry.relations[0], 'traits')
        assert 'variant-type' in retrieved_entry.relations[0].traits
        assert retrieved_entry.relations[0].traits['variant-type'] == "Spelling Variant"


@pytest.mark.integration
class TestComponentLoading:
    """Test that components are properly loaded into the form."""
    
    @pytest.mark.integration
    def test_component_loading_into_form(self):
        """Test that component relations are loaded into the form for editing."""
        # Create entry with component relations
        original_xml = '''
        <entry id="component_loading_test" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>basketball</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="en"><text>a sport</text></form>
                </definition>
            </sense>
            <relation type="_component-lexeme" ref="basket" order="0">
                <trait name="complex-form-type" value="Compound"/>
            </relation>
            <relation type="_component-lexeme" ref="ball" order="1">
                <trait name="complex-form-type" value="Compound"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries) == 1
        entry = entries[0]
        
        # Get component relations
        component_relations = entry.get_component_relations()
        
        # Verify component relations
        assert len(component_relations) == 2
        assert component_relations[0]['ref'] == 'basket'
        assert component_relations[0]['complex_form_type'] == 'Compound'
        assert component_relations[1]['ref'] == 'ball'
        assert component_relations[1]['complex_form_type'] == 'Compound'
        
        # Verify that components would be loaded into form
        # This simulates what happens in the template
        components_for_handler = [
            {
                'id': comp['ref'],
                'headword': comp.get('ref_display_text', comp['ref']),
                'type': comp['complex_form_type'],
                'order': comp.get('order', 0)
            }
            for comp in component_relations
        ]
        
        assert len(components_for_handler) == 2
        assert components_for_handler[0]['id'] == 'basket'
        assert components_for_handler[0]['type'] == 'Compound'
        assert components_for_handler[1]['id'] == 'ball'
        assert components_for_handler[1]['type'] == 'Compound'


@pytest.mark.integration
class TestRelationFiltering:
    """Test that relations are properly filtered and displayed in the correct sections."""
    
    @pytest.mark.integration
    def test_component_lexeme_relations_filtering(self):
        """Test that _component-lexeme relations are properly filtered from regular relations."""
        
    @pytest.mark.integration
    def test_component_relations_without_enrichment(self):
        """Test that component relations work even when target entries cannot be enriched."""
        
    @pytest.mark.integration
    def test_component_lexeme_without_traits(self):
        """Test that _component-lexeme relations without proper traits are handled correctly."""
        # Create entry with a _component-lexeme relation that has no traits
        entry = Entry(
            id_="no_traits_test",
            lexical_unit={"en": "test"},
            senses=[{"definition": {"en": "test definition"}}]
        )
        
        # Add _component-lexeme relation without traits
        bad_relation = Relation(type="_component-lexeme", ref="some_entry")
        # No traits added
        
        entry.relations = [bad_relation]
        
        # Test filtering logic (simulating what the template does)
        filtered_relations = [
            rel for rel in entry.relations
            if rel.type != '_component-lexeme'
        ]
        
        # Should filter out the _component-lexeme relation
        assert len(filtered_relations) == 0
        
        # Test variant relations extraction
        variant_relations = entry.get_complete_variant_relations(None)
        assert len(variant_relations) == 0
        
        # Test component relations extraction
        component_relations = entry.get_component_relations(None)
        assert len(component_relations) == 0
        
        # The relation without proper traits should not appear in any section
        
    @pytest.mark.integration
    def test_component_relations_without_enrichment(self):
        """Test that component relations work even when target entries cannot be enriched."""
        # Create entry with component relations but no dict_service for enrichment
        entry = Entry(
            id_="no_enrich_test",
            lexical_unit={"en": "test"},
            senses=[{"definition": {"en": "test definition"}}]
        )
        
        # Add component relation
        component_relation = Relation(type="_component-lexeme", ref="missing_entry")
        component_relation.traits = {"complex-form-type": "Compound"}
        
        entry.relations = [component_relation]
        
        # Test component relations extraction without dict_service
        component_relations = entry.get_component_relations(None)
        
        # Should still extract the component relation
        assert len(component_relations) == 1
        assert component_relations[0]['ref'] == 'missing_entry'
        assert component_relations[0]['complex_form_type'] == 'Compound'
        
        # ref_display_text should not be present when no enrichment is available
        assert 'ref_display_text' not in component_relations[0]
        # ref_lexical_unit should also not be present
        assert 'ref_lexical_unit' not in component_relations[0]
        # But ref should still be present
        assert component_relations[0]['ref'] == 'missing_entry'
        
    @pytest.mark.integration
    def test_component_lexeme_relations_filtering(self):
        """Test that _component-lexeme relations are properly filtered from regular relations."""
        # Create entry with mixed relation types
        entry = Entry(
            id_="filter_test",
            lexical_unit={"en": "test"},
            senses=[{"definition": {"en": "test definition"}}]
        )
        
        # Add regular relation
        regular_relation = Relation(type="synonym", ref="synonym_entry")
        
        # Add variant relation
        variant_relation = Relation(type="_component-lexeme", ref="variant_entry")
        variant_relation.traits = {"variant-type": "Spelling Variant"}
        
        # Add component relation
        component_relation = Relation(type="_component-lexeme", ref="component_entry")
        component_relation.traits = {"complex-form-type": "Compound"}
        
        entry.relations = [regular_relation, variant_relation, component_relation]
        
        # Test filtering logic (simulating what the template does)
        filtered_relations = [
            rel for rel in entry.relations
            if not (rel.type == '_component-lexeme' and rel.traits and 
                   ('variant-type' in rel.traits or 'complex-form-type' in rel.traits))
        ]
        
        # Should only have the regular relation
        assert len(filtered_relations) == 1
        assert filtered_relations[0].type == "synonym"
        
        # Test variant relations extraction
        variant_relations = entry.get_complete_variant_relations(None)
        assert len(variant_relations) == 1
        assert variant_relations[0]['ref'] == 'variant_entry'
        assert variant_relations[0]['variant_type'] == 'Spelling Variant'
        
        # Test component relations extraction
        component_relations = entry.get_component_relations(None)
        assert len(component_relations) == 1
        assert component_relations[0]['ref'] == 'component_entry'
        assert component_relations[0]['complex_form_type'] == 'Compound'


@pytest.mark.integration
class TestEndToEndComponentFlow:
    """Test end-to-end flow for adding and saving components."""
    
    @pytest.mark.integration
    def test_component_add_and_save_flow(self):
        """Test that adding a component through the form and saving preserves the component relation."""
        # This test would require a full end-to-end test with Playwright
        # to simulate the actual user flow of adding a component
        # For now, we'll add a placeholder to remind us to create this test
        assert True  # Placeholder for future end-to-end test


@pytest.mark.integration
class TestCompleteRelationsRoundTrip:
    """Test complete round-trip for all relation types."""
    
    @pytest.mark.integration
    def test_complete_relations_round_trip(self):
        """Test that all relation types are preserved in a complete round-trip."""
        # Create entry with all types of relations
        original_xml = '''
        <entry id="complete_test" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="en"><text>test definition</text></form>
                </definition>
            </sense>
            <!-- Regular semantic relation -->
            <relation type="synonym" ref="synonym_entry"/>
            <!-- Variant relation -->
            <relation type="_component-lexeme" ref="variant_entry">
                <trait name="variant-type" value="Spelling Variant"/>
            </relation>
            <!-- Component relation -->
            <relation type="_component-lexeme" ref="component_entry">
                <trait name="complex-form-type" value="Compound"/>
            </relation>
        </entry>
        '''
        
        parser = LIFTParser(validate=False)
        
        # Parse original
        entries = parser.parse_string(original_xml)
        assert len(entries) == 1
        entry = entries[0]
        
        # Verify all relation types
        assert len(entry.relations) == 3
        
        # Regular relation
        regular_relations = [rel for rel in entry.relations if rel.type == "synonym"]
        assert len(regular_relations) == 1
        
        # Variant relations
        variant_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'variant-type' in rel.traits
        ]
        assert len(variant_relations) == 1
        assert variant_relations[0].traits['variant-type'] == "Spelling Variant"
        
        # Component relations
        component_relations = [
            rel for rel in entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(component_relations) == 1
        assert component_relations[0].traits['complex-form-type'] == "Compound"
        
        # Generate back to XML
        regenerated_xml = parser.generate_lift_string(entries)
        
        # Parse again to verify round-trip
        reparsed_entries = parser.parse_string(regenerated_xml)
        reparsed_entry = reparsed_entries[0]
        
        # Verify round-trip integrity
        assert len(reparsed_entry.relations) == 3
        
        reparsed_regular_relations = [rel for rel in reparsed_entry.relations if rel.type == "synonym"]
        assert len(reparsed_regular_relations) == 1
        
        reparsed_variant_relations = [
            rel for rel in reparsed_entry.relations 
            if hasattr(rel, 'traits') and 'variant-type' in rel.traits
        ]
        assert len(reparsed_variant_relations) == 1
        assert reparsed_variant_relations[0].traits['variant-type'] == "Spelling Variant"
        
        reparsed_component_relations = [
            rel for rel in reparsed_entry.relations 
            if hasattr(rel, 'traits') and 'complex-form-type' in rel.traits
        ]
        assert len(reparsed_component_relations) == 1
        assert reparsed_component_relations[0].traits['complex-form-type'] == "Compound"
