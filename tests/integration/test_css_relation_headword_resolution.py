"""
Integration tests for CSS display of relations with headword resolution.
"""

from __future__ import annotations

import pytest
from app.services.css_mapping_service import CSSMappingService
from app.services.display_profile_service import DisplayProfileService


@pytest.mark.integration
class TestCSSRelationHeadwordResolution:
    """Test suite for CSS rendering with resolved relation references."""

    def test_relation_displays_headword_not_id(self, app, populated_dict_service):
        """Test that relations display headwords instead of IDs in CSS preview."""
        with app.app_context():
            dict_service = populated_dict_service
            
            # Use existing test entries from populated service
            # Entry 'test1' should have a relation
            test_entry_id = None
            target_entry_id = None
            target_headword = None
            
            # Find an entry with a relation or create test data
            try:
                # Get all entries to find one with relations
                db_name = dict_service.db_connector.database
                has_ns = dict_service._detect_namespace_usage()
                
                # Create target entry first
                from app.models.entry import Entry
                target = Entry.from_dict({
                    'id': 'css_test_target',
                    'lexical_unit': {'en': 'target word', 'pl': 'słowo docelowe'},
                    'senses': [{
                        'id': 's1',
                        'definition': {'en': 'a target'},
                        'grammatical_info': 'Noun'
                    }]
                })
                dict_service.create_entry(target)
                target_entry_id = 'css_test_target'
                target_headword = 'target word'
                
                # Create source entry with relation
                source = Entry.from_dict({
                    'id': 'css_test_source',
                    'lexical_unit': {'en': 'source word'},
                    'senses': [{
                        'id': 's1',
                        'definition': {'en': 'a source'},
                        'grammatical_info': 'Noun',
                        'relations': [{
                            'type': 'Synonym',
                            'ref': target_entry_id
                        }]
                    }]
                })
                dict_service.create_entry(source)
                test_entry_id = 'css_test_source'
                
            except Exception as e:
                pytest.skip(f"Could not create test data: {e}")
            
            # Get display profile
            profile_service = DisplayProfileService()
            default_profile = profile_service.get_default_profile()
            if not default_profile:
                default_profile = profile_service.create_from_registry_default(
                    name="Test Profile",
                    description="Profile for testing"
                )
            
            # Get the entry XML
            query = dict_service._query_builder.build_entry_by_id_query(
                test_entry_id, db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)
            
            # Render with CSS
            css_service = CSSMappingService()
            html = css_service.render_entry(entry_xml, profile=default_profile, dict_service=dict_service)
            
            print(f"\n=== Rendered HTML ===\n{html}\n")
            
            # Verify the relation displays the headword, not the ID
            assert 'Synonym' in html, "Relation type should be displayed"
            assert target_headword in html, f"Target entry headword '{target_headword}' should be displayed"
            assert target_entry_id not in html, f"Entry ID '{target_entry_id}' should NOT be displayed"
            
            # Clean up
            try:
                dict_service.delete_entry(test_entry_id)
                dict_service.delete_entry(target_entry_id)
            except:
                pass  # Cleanup is best-effort

    def test_relation_shows_id_when_target_missing(self, app, populated_dict_service):
        """Test that relations fall back to showing ID when target doesn't exist."""
        with app.app_context():
            dict_service = populated_dict_service
            
            # Create entry with relation to non-existent entry
            from app.models.entry import Entry
            entry = Entry.from_dict({
                'id': 'css_test_broken_ref',
                'lexical_unit': {'en': 'test word'},
                'senses': [{
                    'id': 's1',
                    'definition': {'en': 'test definition'},
                    'relations': [{
                        'type': 'See also',
                        'ref': 'nonexistent_entry_xyz'
                    }]
                }]
            })
            dict_service.create_entry(entry)
            
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
                'css_test_broken_ref', db_name, has_ns
            )
            entry_xml = dict_service.db_connector.execute_query(query)
            
            # Render with CSS
            css_service = CSSMappingService()
            html = css_service.render_entry(entry_xml, profile=default_profile, dict_service=dict_service)
            
            print(f"\n=== Rendered HTML (broken ref) ===\n{html}\n")
            
            # Should fall back to showing the ID
            assert 'See also' in html, "Relation type should be displayed"
            assert 'nonexistent_entry_xyz' in html, "Should fall back to showing ID when headword unavailable"
            
            # Clean up
            try:
                dict_service.delete_entry('css_test_broken_ref')
            except:
                pass
