"""
Integration tests for CSS display of relations with headword resolution.
"""

from __future__ import annotations

import pytest
from app.services.css_mapping_service import CSSMappingService
from app.services.display_profile_service import DisplayProfileService
from app.models.entry import Entry


@pytest.mark.integration
class TestCSSRelationResolution:
    """Test suite for CSS rendering with resolved relation references."""

    def test_relation_resolves_to_headword_in_css_display(
        self, app, dict_service
    ) -> None:
        """Test that relations display headwords instead of IDs in CSS preview."""
        with app.app_context():
            # Create two entries - one to reference and one with the relation
            target_entry = Entry.from_dict({
                'id': 'target_entry_xyz',
                'lexical_unit': {'en': 'beautiful', 'pl': 'piękny'},
                'senses': [{
                    'id': 'sense1',
                    'definition': {'en': 'pleasing to the eye'},
                    'grammatical_info': 'Adjective'
                }]
            })
            dict_service.add_entry(target_entry)
            
            source_entry = Entry.from_dict({
                'id': 'source_entry_abc',
                'lexical_unit': {'en': 'pretty', 'pl': 'ładny'},
                'senses': [{
                    'id': 'sense1',
                    'definition': {'en': 'attractive'},
                    'grammatical_info': 'Adjective',
                    'relations': [{
                        'type': 'Synonym',
                        'ref': 'target_entry_xyz'
                    }]
                }]
            })
            dict_service.add_entry(source_entry)
            
            # Get display profile
            profile_service = DisplayProfileService()
            default_profile = profile_service.get_default_profile()
            if not default_profile:
                default_profile = profile_service.create_from_registry_default(
                    name="Test Profile",
                    description="Profile for testing"
                )
            
            # Get the entry XML
            db_name = dict_service.db_connector.database
            has_ns = dict_service._detect_namespace_usage()
            query = dict_service._query_builder.build_entry_by_id_query(
                'source_entry_abc', db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)
            
            # Render with CSS
            css_service = CSSMappingService()
            html = css_service.render_entry(entry_xml, profile=default_profile)
            
            # Verify the relation displays the headword, not the ID
            assert 'Synonym' in html, "Relation type should be displayed"
            assert 'beautiful' in html or 'piękny' in html, "Target entry headword should be displayed"
            assert 'target_entry_xyz' not in html, "Entry ID should NOT be displayed"
            
            # Clean up
            dict_service.delete_entry('source_entry_abc')
            dict_service.delete_entry('target_entry_xyz')

    def test_relation_fallback_when_target_not_found(
        self, app, dict_service
    ) -> None:
        """Test that relations fall back to showing ID when target entry doesn't exist."""
        with app.app_context():
            # Create entry with relation to non-existent entry
            entry = Entry.from_dict({
                'id': 'entry_with_broken_ref',
                'lexical_unit': {'en': 'test word'},
                'senses': [{
                    'id': 'sense1',
                    'definition': {'en': 'test definition'},
                    'relations': [{
                        'type': 'See also',
                        'ref': 'nonexistent_entry_id_999'
                    }]
                }]
            })
            dict_service.add_entry(entry)
            
            # Get display profile
            profile_service = DisplayProfileService()
            default_profile = profile_service.get_default_profile()
            if not default_profile:
                default_profile = profile_service.create_from_registry_default(
                    name="Test Profile",
                    description="Profile for testing"
                )
            
            # Get the entry XML
            db_name = dict_service.db_connector.database
            has_ns = dict_service._detect_namespace_usage()
            query = dict_service._query_builder.build_entry_by_id_query(
                'entry_with_broken_ref', db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)
            
            # Render with CSS
            css_service = CSSMappingService()
            html = css_service.render_entry(entry_xml, profile=default_profile)
            
            # Should fall back to showing the ID
            assert 'See also' in html, "Relation type should be displayed"
            assert 'nonexistent_entry_id_999' in html, "Should fall back to showing ID when headword unavailable"
            
            # Clean up
            dict_service.delete_entry('entry_with_broken_ref')

    def test_multiple_relations_all_resolved(
        self, app, dict_service
    ) -> None:
        """Test that multiple relations are all resolved to headwords."""
        with app.app_context():
            # Create multiple target entries
            synonym = Entry.from_dict({
                'id': 'synonym_entry',
                'lexical_unit': {'en': 'fast'},
                'senses': [{'id': 's1', 'definition': {'en': 'quick'}}]
            })
            antonym = Entry.from_dict({
                'id': 'antonym_entry',
                'lexical_unit': {'en': 'slow'},
                'senses': [{'id': 's1', 'definition': {'en': 'not fast'}}]
            })
            dict_service.add_entry(synonym)
            dict_service.add_entry(antonym)
            
            # Create entry with multiple relations
            entry = Entry.from_dict({
                'id': 'multi_relation_entry',
                'lexical_unit': {'en': 'rapid'},
                'senses': [{
                    'id': 'sense1',
                    'definition': {'en': 'happening quickly'},
                    'relations': [
                        {'type': 'Synonym', 'ref': 'synonym_entry'},
                        {'type': 'Antonym', 'ref': 'antonym_entry'}
                    ]
                }]
            })
            dict_service.add_entry(entry)
            
            # Get display profile
            profile_service = DisplayProfileService()
            default_profile = profile_service.get_default_profile()
            if not default_profile:
                default_profile = profile_service.create_from_registry_default(
                    name="Test Profile",
                    description="Profile for testing"
                )
            
            # Get the entry XML
            db_name = dict_service.db_connector.database
            has_ns = dict_service._detect_namespace_usage()
            query = dict_service._query_builder.build_entry_by_id_query(
                'multi_relation_entry', db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)
            
            # Render with CSS
            css_service = CSSMappingService()
            html = css_service.render_entry(entry_xml, profile=default_profile)
            
            # Both relations should show headwords
            assert 'Synonym' in html
            assert 'fast' in html
            assert 'Antonym' in html
            assert 'slow' in html
            # IDs should not be visible
            assert 'synonym_entry' not in html
            assert 'antonym_entry' not in html
            
            # Clean up
            dict_service.delete_entry('multi_relation_entry')
            dict_service.delete_entry('synonym_entry')
            dict_service.delete_entry('antonym_entry')
