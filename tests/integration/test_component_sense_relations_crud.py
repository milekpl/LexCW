"""
Integration tests for Component and Sense Relation CRUD operations.

Tests full CRUD (Create, Read, Update, Delete) functionality for:
- Complex form components (entry-level)
- Sense relations (sense-level)

Includes circularity detection validation.
"""

from __future__ import annotations

import pytest
import json
import os
from flask import url_for
from app import create_app
from app.models.entry import Entry, Relation
from app.models.sense import Sense
from app.services.dictionary_service import DictionaryService


@pytest.fixture
def sample_entries(dict_service_with_db):
    """Create sample entries for testing relationships."""
    dict_service = dict_service_with_db
    # Create main entry
    main_entry = Entry(
        id_="main_entry_001",
        lexical_unit={"en": "basketball"},
        senses=[
            Sense(
                id="sense_main_001",
                definition={"en": "A sport played with a ball and hoops"}
            )
        ]
    )
    
    # Create component entry 1
    component_entry_1 = Entry(
        id_="component_entry_001",
        lexical_unit={"en": "basket"},
        senses=[
            Sense(
                id="sense_comp_001",
                definition={"en": "A container"}
            )
        ]
    )
    
    # Create component entry 2
    component_entry_2 = Entry(
        id_="component_entry_002",
        lexical_unit={"en": "ball"},
        senses=[
            Sense(
                id="sense_comp_002",
                definition={"en": "A round object"}
            )
        ]
    )
    
    # Create target entry for sense relations
    target_entry = Entry(
        id_="target_entry_001",
        lexical_unit={"en": "sport"},
        senses=[
            Sense(
                id="sense_target_001",
                definition={"en": "Physical activity"}
            )
        ]
    )
    
    # Store entries
    dict_service_with_db.create_entry(main_entry)
    dict_service_with_db.create_entry(component_entry_1)
    dict_service_with_db.create_entry(component_entry_2)
    dict_service_with_db.create_entry(target_entry)
    
    return {
        'main': 'main_entry_001',
        'component1': 'component_entry_001',
        'component2': 'component_entry_002',
        'target': 'target_entry_001'
    }


@pytest.mark.integration
class TestComponentCRUD:
    """Test CRUD operations for complex form components."""
    
    def test_create_component_relation(self, client, dict_service_with_db, sample_entries):
        """Test adding a new component to an entry."""
        # Add component via form submission
        form_data = {
            'id': sample_entries['main'],
            'lexical_unit[en]': 'basketball',
            'components[0].ref': sample_entries['component1'],
            'components[0].type': 'compound',
            'components[0].order': '0',
        }
        
        response = client.post(
            f"/entries/{sample_entries['main']}/edit",
            data=form_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        # Verify response
        assert response.status_code in [200, 302]
        
        # Verify component was added
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        component_relations = entry.get_component_relations(dict_service_with_db)
        
        assert len(component_relations) > 0
        assert any(comp['ref'] == sample_entries['component1'] for comp in component_relations)
        assert any(comp['complex_form_type'] == 'compound' for comp in component_relations)
    
    def test_read_component_relations(self, client, sample_entries):
        """Test reading component relations from the edit page."""
        response = client.get(f"/entries/{sample_entries['main']}/edit")
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for component search interface
        assert 'component-search-input' in html
        assert 'component-search-btn' in html
        assert 'new-component-type' in html
    
    def test_add_multiple_components(self, client, dict_service_with_db, sample_entries):
        """Test adding multiple components to an entry."""
        form_data = {
            'id': sample_entries['main'],
            'lexical_unit[en]': 'basketball',
            'components[0].ref': sample_entries['component1'],
            'components[0].type': 'compound',
            'components[0].order': '0',
            'components[1].ref': sample_entries['component2'],
            'components[1].type': 'compound',
            'components[1].order': '1',
        }
        
        response = client.post(
            f"/entries/{sample_entries['main']}/edit",
            data=form_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        assert response.status_code in [200, 302]
        
        # Verify both components were added
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        component_relations = entry.get_component_relations(dict_service_with_db)
        
        assert len(component_relations) >= 2
        component_refs = [comp['ref'] for comp in component_relations]
        assert sample_entries['component1'] in component_refs
        assert sample_entries['component2'] in component_refs
    
    def test_component_circularity_detection_backend(self, client, dict_service_with_db, sample_entries):
        """Test that backend prevents circular component references."""
        # Try to add entry as its own component
        form_data = {
            'id': sample_entries['main'],
            'lexical_unit[en]': 'basketball',
            'components[0].ref': sample_entries['main'],  # Circular reference!
            'components[0].type': 'compound',
            'components[0].order': '0',
        }
        
        response = client.post(
            f"/entries/{sample_entries['main']}/edit",
            data=form_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        # Entry should still update, but validation should flag the issue
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        
        # Validate the entry
        from app.services.validation_engine import ValidationEngine
        validator = ValidationEngine(rules_file='validation_rules_v2.json')
        result = validator.validate_entry(entry.to_dict())
        
        # Should have circularity error
        circular_errors = [
            error for error in result.errors 
            if 'circular' in error.message.lower()
        ]
        assert len(circular_errors) > 0


@pytest.mark.integration
class TestSenseRelationCRUD:
    """Test CRUD operations for sense relations."""
    
    def test_create_sense_relation(self, client, dict_service_with_db, sample_entries):
        """Test adding a sense relation."""
        form_data = {
            'id': sample_entries['main'],
            'lexical_unit[en]': 'basketball',
            'senses[0].id': 'sense_main_001',
            'senses[0].definition[en]': 'A sport',
            'senses[0].relations[0].type': 'synonim',
            'senses[0].relations[0].ref': 'sense_target_001',
        }
        
        response = client.post(
            f"/entries/{sample_entries['main']}/edit",
            data=form_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        assert response.status_code in [200, 302]
        
        # Verify sense relation was added
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        assert len(entry.senses) > 0
        
        sense = entry.senses[0]
        if hasattr(sense, 'relations') and sense.relations:
            assert len(sense.relations) > 0
            assert sense.relations[0].get('type') == 'synonim'
            assert sense.relations[0].get('ref') == 'sense_target_001'
    
    def test_read_sense_relations(self, client, dict_service_with_db, sample_entries):
        """Test reading sense relations from the edit page."""
        # First add a sense relation
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        if entry.senses:
            sense = entry.senses[0]
            sense.relations = [
                {'type': 'synonim', 'ref': 'sense_target_001'}
            ]
            dict_service_with_db.update_entry(entry)
        
        # Get the edit page
        response = client.get(f"/entries/{sample_entries['main']}/edit")
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for sense relation interface elements (updated to current template classes)
        assert 'sense-relation-target' in html
        # Relation type select should be present
        assert 'sense-lexical-relation-select' in html
    
    def test_update_sense_relation(self, client, dict_service_with_db, sample_entries):
        """Test updating an existing sense relation."""
        # First add a relation
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        if entry.senses:
            sense = entry.senses[0]
            sense.relations = [
                {'type': 'synonim', 'ref': 'old_sense_ref'}
            ]
            dict_service_with_db.update_entry(entry)
        
        # Update the relation
        form_data = {
            'id': sample_entries['main'],
            'lexical_unit[en]': 'basketball',
            'senses[0].id': 'sense_main_001',
            'senses[0].definition[en]': 'A sport',
            'senses[0].relations[0].type': 'antonim',  # Changed type
            'senses[0].relations[0].ref': 'sense_target_001',  # Changed ref
        }
        
        response = client.post(
            f"/entries/{sample_entries['main']}/edit",
            data=form_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        assert response.status_code in [200, 302]
        
        # Verify relation was updated
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        sense = entry.senses[0]
        if hasattr(sense, 'relations') and sense.relations:
            assert sense.relations[0].get('type') == 'antonim'
            assert sense.relations[0].get('ref') == 'sense_target_001'
    
    def test_delete_sense_relation(self, client, dict_service_with_db, sample_entries):
        """Test removing a sense relation."""
        # First add a relation
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        if entry.senses:
            sense = entry.senses[0]
            sense.relations = [
                {'type': 'synonim', 'ref': 'sense_target_001'}
            ]
            dict_service_with_db.update_entry(entry)
        
        # Remove the relation by not including it in the form
        form_data = {
            'id': sample_entries['main'],
            'lexical_unit[en]': 'basketball',
            'senses[0].id': 'sense_main_001',
            'senses[0].definition[en]': 'A sport',
            # No relations submitted
        }
        
        response = client.post(
            f"/entries/{sample_entries['main']}/edit",
            data=form_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        assert response.status_code in [200, 302]
        
        # Verify relation was removed
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        sense = entry.senses[0]
        
        # Relations should be empty or None
        if hasattr(sense, 'relations'):
            assert not sense.relations or len(sense.relations) == 0
    
    def test_sense_relation_circularity_detection_backend(self, client, dict_service_with_db, sample_entries):
        """Test that backend prevents circular sense references within same entry."""
        # Try to add sense relation to another sense in the same entry
        form_data = {
            'id': sample_entries['main'],
            'lexical_unit[en]': 'basketball',
            'senses[0].id': 'sense_main_001',
            'senses[0].definition[en]': 'A sport',
            'senses[0].relations[0].type': 'synonim',
            'senses[0].relations[0].ref': f"{sample_entries['main']}_sense_main_001",  # Circular!
        }
        
        response = client.post(
            f"/entries/{sample_entries['main']}/edit",
            data=form_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        # Entry should update, but validation should flag it
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        
        # Validate the entry
        from app.services.validation_engine import ValidationEngine
        validator = ValidationEngine(rules_file='validation_rules_v2.json')
        result = validator.validate_entry(entry.to_dict())
        
        # Should have circularity error
        circular_errors = [
            error for error in result.errors 
            if 'circular' in error.message.lower()
        ]
        assert len(circular_errors) > 0


@pytest.mark.integration
class TestSearchIntegration:
    """Test search functionality for components and sense relations."""
    
    def test_search_api_for_components(self, client, dict_service_with_db, sample_entries):
        """Test that search API returns entries for component selection."""
        response = client.get('/api/search?q=ball&limit=10')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'entries' in data
        assert isinstance(data['entries'], list)
        
        # Should find entries with 'ball' in them
        if data['entries']:
            # Check structure
            entry = data['entries'][0]
            assert 'id' in entry
            assert 'lexical_unit' in entry or 'headword' in entry
    
    def test_search_api_for_sense_relations(self, client, dict_service_with_db, sample_entries):
        """Test that search API returns entries with senses for sense relation selection."""
        response = client.get('/api/search?q=sport&limit=10')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'entries' in data
        
        # Check that entries have senses
        if data['entries']:
            entry = data['entries'][0]
            if 'senses' in entry:
                assert isinstance(entry['senses'], list)
                if entry['senses']:
                    sense = entry['senses'][0]
                    assert 'id' in sense


@pytest.mark.integration
class TestEnrichmentDisplay:
    """Test that component and sense relation enrichment works correctly."""
    
    def test_component_enrichment_displays_headword(self, client, dict_service_with_db, sample_entries):
        """Test that component relations show the referenced entry's headword."""
        # Add component relation
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        entry.relations = [
            Relation(
                type='_component-lexeme',
                ref=sample_entries['component1'],
                traits={'complex-form-type': 'compound'}
            )
        ]
        dict_service_with_db.update_entry(entry)
        
        # Get edit page
        response = client.get(f"/entries/{sample_entries['main']}/edit")
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Should display the component's headword
        assert 'basket' in html  # The component entry's lexical unit
    
    def test_sense_relation_enrichment_displays_headword_and_gloss(self, client, dict_service_with_db, sample_entries):
        """Test that sense relations show the target sense's headword and gloss."""
        # Add sense relation
        entry = dict_service_with_db.get_entry(sample_entries['main'])
        if entry.senses:
            sense = entry.senses[0]
            sense.relations = [
                {'type': 'synonim', 'ref': 'sense_target_001'}
            ]
            dict_service_with_db.update_entry(entry)
        
        # Get edit page
        response = client.get(f"/entries/{sample_entries['main']}/edit")
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # The template should call enrichment, which searches for the target
        # Check that the page loaded without errors
        assert 'sense-relation' in html or 'Sense Relations' in html


@pytest.mark.integration
class TestUIScriptLoading:
    """Test that required JavaScript files are loaded."""
    
    def test_component_search_script_loaded(self, client, sample_entries):
        """Test that component-search.js is loaded on edit page."""
        response = client.get(f"/entries/{sample_entries['main']}/edit")
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        assert 'component-search.js' in html
    
    def test_sense_relation_search_script_loaded(self, client, sample_entries):
        """Test that sense-relation-search.js is loaded on edit page."""
        response = client.get(f"/entries/{sample_entries['main']}/edit")
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        assert 'sense-relation-search.js' in html


@pytest.mark.integration
class TestValidationRules:
    """Test that validation rules catch circularity issues."""
    
    def test_validation_rule_r811_component_circularity(self, dict_service_with_db, sample_entries):
        """Test validation rule R8.1.1 catches component circular references."""
        from app.services.validation_engine import ValidationEngine
        
        # Create entry with circular component reference
        entry_dict = {
            'id': sample_entries['main'],
            'lexical_unit': {'en': 'test'},
            'relations': [
                {
                    'type': '_component-lexeme',
                    'ref': sample_entries['main'],  # Circular!
                    'traits': {'complex-form-type': 'compound'}
                }
            ]
        }
        
        validator = ValidationEngine(rules_file='validation_rules_v2.json')
        result = validator.validate_entry(entry_dict)
        
        # Should have R8.1.1 error
        rule_errors = [e for e in result.errors if e.rule_id == 'R8.1.1']
        assert len(rule_errors) > 0
        assert 'circular' in rule_errors[0].message.lower()
    
    def test_validation_rule_r812_sense_circularity(self, dict_service_with_db, sample_entries):
        """Test validation rule R8.1.2 catches sense circular references."""
        from app.services.validation_engine import ValidationEngine
        
        # Create entry with circular sense reference
        entry_dict = {
            'id': sample_entries['main'],
            'lexical_unit': {'en': 'test'},
            'senses': [
                {
                    'id': 'sense_001',
                    'definition': {'en': 'test'},
                    'relations': [
                        {
                            'type': 'synonim',
                            'ref': f"{sample_entries['main']}_sense_001"  # Circular!
                        }
                    ]
                }
            ]
        }
        
        validator = ValidationEngine(rules_file='validation_rules_v2.json')
        result = validator.validate_entry(entry_dict)
        
        # Should have R8.1.2 error
        rule_errors = [e for e in result.errors if e.rule_id == 'R8.1.2']
        assert len(rule_errors) > 0
        assert 'circular' in rule_errors[0].message.lower()
    
    def test_validation_rule_r813_entry_relation_circularity(self, dict_service_with_db, sample_entries):
        """Test validation rule R8.1.3 catches entry relation circular references."""
        from app.services.validation_engine import ValidationEngine
        
        # Create entry with circular entry-level relation
        entry_dict = {
            'id': sample_entries['main'],
            'lexical_unit': {'en': 'test'},
            'relations': [
                {
                    'type': 'synonym',  # Not _component-lexeme
                    'ref': sample_entries['main']  # Circular!
                }
            ]
        }
        
        validator = ValidationEngine(rules_file='validation_rules_v2.json')
        result = validator.validate_entry(entry_dict)
        
        # Should have R8.1.3 error
        rule_errors = [e for e in result.errors if e.rule_id == 'R8.1.3']
        assert len(rule_errors) > 0
        assert 'circular' in rule_errors[0].message.lower()
