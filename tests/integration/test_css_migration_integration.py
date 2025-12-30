"""
Integration tests for the complete CSS migration system.

These tests verify that all components work together correctly
after the migration from JavaScript to Python backend.
"""

from __future__ import annotations

import pytest
from flask import Flask

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db
from app.services.css_mapping_service import CSSMappingService
from app.services.display_profile_service import DisplayProfileService


class TestCSSMigrationIntegration:
    """Integration tests for the complete CSS migration system."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self, app):
        """Clean up database before and after tests."""
        with app.app_context():
            from app.models.workset_models import db
            from app.models.display_profile import ProfileElement, DisplayProfile
            db.session.query(ProfileElement).delete()
            db.session.query(DisplayProfile).delete()
            db.session.commit()

    def test_complete_css_migration_integration(self, app: Flask) -> None:
        """Test complete integration of all CSS migration components."""
        with app.app_context():
            # Use DisplayProfileService to create a comprehensive profile
            profile_service = DisplayProfileService()
            
            # Create profile with multiple features
            profile = profile_service.create_profile(
                name="Complete Integration Test",
                description="Testing all CSS migration features"
            )
            
            # Add various element configurations with different features
            elements_data = [
                {
                    "lift_element": "lexical-unit",
                    "css_class": "headword",
                    "display_order": 1,
                    "visibility": "always",
                    "display_mode": "inline",
                    "prefix": "",
                    "suffix": "",
                    "config": {}
                },
                {
                    "lift_element": "pronunciation",
                    "css_class": "pronunciation",
                    "display_order": 2,
                    "visibility": "if-content",
                    "display_mode": "inline",
                    "config": {}
                },
                {
                    "lift_element": "grammatical-info",
                    "css_class": "pos",
                    "display_order": 3,
                    "visibility": "if-content",
                    "display_mode": "inline",
                    "config": {"display_aspect": "full"}
                },
                {
                    "lift_element": "definition",
                    "css_class": "definition",
                    "display_order": 4,
                    "visibility": "always",
                    "display_mode": "block",
                    "config": {}
                },
                {
                    "lift_element": "example",
                    "css_class": "example",
                    "display_order": 5,
                    "visibility": "if-content",
                    "display_mode": "block",
                    "config": {}
                },
                {
                    "lift_element": "relation",
                    "css_class": "relation",
                    "display_order": 6,
                    "visibility": "if-content",
                    "display_mode": "inline",
                    "config": {
                        "display_aspect": "label",
                        "filter": "synonym,antonym",
                        "separator": "; "
                    }
                },
                {
                    "lift_element": "trait",
                    "css_class": "trait",
                    "display_order": 7,
                    "visibility": "if-content",
                    "display_mode": "inline",
                    "config": {
                        "display_aspect": "label",
                        "filter": "semantic-domain"
                    }
                }
            ]
            
            for elem_data in elements_data:
                # Add display aspect if specified in config
                if "display_aspect" in elem_data["config"]:
                    profile_service.set_element_display_aspect(
                        profile.id,
                        elem_data["lift_element"],
                        elem_data["config"]["display_aspect"]
                    )
                
                # Update other element properties
                elem = profile_service.get_profile_element(
                    profile.id, elem_data["lift_element"]
                )
                if elem:
                    elem.css_class = elem_data["css_class"]
                    elem.display_order = elem_data["display_order"]
                    elem.visibility = elem_data["visibility"]
                    elem.display_mode = elem_data["display_mode"]
                    elem.prefix = elem_data.get("prefix", "")
                    elem.suffix = elem_data.get("suffix", "")
                    
                    # Add filter if specified
                    if "filter" in elem_data["config"]:
                        if not elem.config:
                            elem.config = {}
                        elem.config["filter"] = elem_data["config"]["filter"]
                    
                    # Add separator if specified
                    if "separator" in elem_data["config"]:
                        if not elem.config:
                            elem.config = {}
                        elem.config["separator"] = elem_data["config"]["separator"]
                    
                    db.session.add(elem)
            
            # Add custom CSS and other profile settings
            profile.custom_css = """
            .lift-entry-rendered {
                border: 1px solid #ddd;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .headword {
                color: #2c3e50;
                font-size: 1.3em;
                font-weight: bold;
            }
            .definition {
                color: #34495e;
                margin: 10px 0;
            }
            .example {
                color: #7f8c8d;
                font-style: italic;
                margin: 5px 0;
            }
            """
            profile.number_senses = True
            profile.show_subentries = False
            db.session.commit()
            
            # Now use CSSMappingService to render a complex entry
            css_service = CSSMappingService()
            
            # Complex LIFT XML with many features
            complex_xml = """
            <entry id="complete-test">
                <lexical-unit>
                    <form lang="en"><text>integration</text></form>
                </lexical-unit>
                <pronunciation>
                    <form lang="en-fonipa"><text>ˌɪntɪˈɡreɪʃən</text></form>
                </pronunciation>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The process of combining separate parts into a unified whole</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>The integration of different software components can be challenging</text></form>
                    </example>
                    <relation type="synonym" ref="entry-1" data-headword="combination"/>
                    <relation type="synonym" ref="entry-2" data-headword="unification"/>
                    <relation type="antonym" ref="entry-3" data-headword="separation"/>
                    <relation type="hypernym" ref="entry-4" data-headword="process"/>
                    <trait name="semantic-domain" value="process"/>
                    <trait name="register" value="formal"/>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The act of integrating or the state of being integrated</text></form>
                    </definition>
                    <example>
                        <form lang="en"><text>System integration is a critical phase in software development</text></form>
                    </example>
                    <relation type="synonym" ref="entry-5" data-headword="incorporation"/>
                </sense>
            </entry>
            """
            
            # Render the entry
            result = css_service.render_entry(complex_xml, profile)
            
            # Verify comprehensive functionality
            assert result is not None
            assert len(result) > 0
            
            # Check for custom CSS
            assert "<style>" in result
            assert "border: 1px solid #ddd" in result
            assert "color: #2c3e50" in result
            
            # Check for entry content
            assert "integration" in result
            assert "ˌɪntɪˈɡreɪʃən" in result  # Pronunciation
            
            # Check for display aspects
            assert "Noun" in result  # Full label for grammatical-info
            assert "Process" in result or "process" in result  # Label for semantic-domain trait
            
            # Check for filtering (should show synonym/antonym, not hypernym)
            assert "combination" in result
            assert "unification" in result
            assert "separation" in result
            assert "incorporation" in result
            # Hypernym should not appear (not in filter)
            assert "process" not in result or result.count("process") <= 2  # Only in trait, not relation
            
            # Check for sense numbering
            assert "counter-reset" in result
            assert "sense-counter" in result
            
            # Check for proper HTML structure
            assert "<div" in result
            assert "class=" in result
            assert "headword" in result
            assert "definition" in result
            assert "example" in result
            
            # Check for profile-specific CSS class
            assert "profile-complete-integration-test" in result

    def test_css_migration_backward_compatibility(self, app: Flask) -> None:
        """Test that CSS migration maintains backward compatibility."""
        with app.app_context():
            # Create a profile using the old-style configuration
            profile = DisplayProfile()
            profile.name = "Backward Compatibility Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add elements without using the new display aspect methods
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "lexical-unit"
            elem.css_class = "headword"
            elem.display_order = 1
            # No display aspect set - should use default behavior
            db.session.add(elem)
            db.session.commit()
            
            css_service = CSSMappingService()
            
            simple_xml = """
            <entry id="compat-test">
                <lexical-unit>
                    <form lang="en"><text>compatibility</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>The ability to work together without conflicts</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            result = css_service.render_entry(simple_xml, profile)
            
            # Should work with old-style profiles
            assert result is not None
            assert "compatibility" in result
            assert "entry-render-error" not in result

    def test_css_migration_error_recovery(self, app: Flask) -> None:
        """Test that CSS migration handles errors gracefully."""
        with app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Error Recovery Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add element with invalid display aspect (should be handled gracefully)
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = "relation"
            elem.css_class = "relation"
            # Don't set display aspect - should use default
            db.session.add(elem)
            db.session.commit()
            
            # Test with various problematic inputs
            test_cases = [
                ("Malformed XML", "<entry><unclosed-tag>"),
                ("Empty XML", ""),
                ("XML with missing elements", "<entry id='test'></entry>"),
                ("XML with invalid relation", """
                <entry id="test">
                    <lexical-unit>
                        <form lang="en"><text>test</text></form>
                    </lexical-unit>
                    <sense>
                        <relation ref="missing"/>
                    </sense>
                </entry>
                """),
            ]
            
            for test_name, test_xml in test_cases:
                result = service.render_entry(test_xml, profile)
                
                # Should handle all cases without crashing
                assert result is not None, f"Failed on {test_name}"
                assert "entry-render-error" in result or len(result) > 0, f"Failed on {test_name}"

    def test_css_migration_performance_under_load(self, app: Flask) -> None:
        """Test CSS migration performance with multiple rapid requests."""
        with app.app_context():
            service = CSSMappingService()
            
            profile = DisplayProfile()
            profile.name = "Performance Test"
            db.session.add(profile)
            db.session.commit()
            
            # Add several elements
            for i in range(5):
                elem = ProfileElement()
                elem.profile_id = profile.id
                elem.lift_element = f"element-{i}"
                elem.css_class = f"class-{i}"
                elem.display_order = i
                db.session.add(elem)
            db.session.commit()
            
            xml = """
            <entry id="perf-test">
                <lexical-unit>
                    <form lang="en"><text>performance</text></form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en"><text>Performance test entry</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            # Make multiple rapid requests
            import time
            start_time = time.time()
            
            for i in range(10):
                result = service.render_entry(xml, profile)
                assert result is not None
                assert "performance" in result
            
            end_time = time.time()
            
            # Should complete quickly
            assert (end_time - start_time) < 2.0  # Should handle 10 requests in < 2 seconds

    def test_css_migration_with_realistic_workflow(self, app: Flask) -> None:
        """Test a realistic workflow using both services together."""
        with app.app_context():
            # Step 1: User creates a profile using DisplayProfileService
            profile_service = DisplayProfileService()
            
            profile = profile_service.create_profile(
                name="Realistic Workflow Test",
                description="Testing realistic user workflow"
            )
            
            # Step 2: User adds elements with various configurations
            profile_service.set_element_display_aspect(profile.id, "relation", "label")
            profile_service.set_element_display_aspect(profile.id, "grammatical-info", "full")
            
            # Get elements and add filters
            relation_elem = profile_service.get_profile_element(profile.id, "relation")
            if relation_elem:
                relation_elem.config = {"filter": "synonym"}
                db.session.add(relation_elem)
            
            profile.custom_css = ".headword { font-weight: bold; }"
            profile.number_senses = True
            db.session.commit()
            
            # Step 3: User previews an entry
            css_service = CSSMappingService()
            
            preview_xml = """
            <entry id="workflow-test">
                <lexical-unit>
                    <form lang="en"><text>workflow</text></form>
                </lexical-unit>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A sequence of connected steps</text></form>
                    </definition>
                    <relation type="synonym" ref="entry-1" data-headword="process"/>
                    <relation type="antonym" ref="entry-2" data-headword="chaos"/>
                </sense>
                <sense>
                    <grammatical-info value="Noun"/>
                    <definition>
                        <form lang="en"><text>A systematic organization of tasks</text></form>
                    </definition>
                </sense>
            </entry>
            """
            
            preview_result = css_service.render_entry(preview_xml, profile)
            
            # Step 4: Verify preview shows expected results
            assert preview_result is not None
            assert "workflow" in preview_result
            assert "Noun" in preview_result  # Full label
            assert "process" in preview_result  # Filtered relation
            assert "chaos" not in preview_result  # Excluded by filter
            assert "counter-reset" in preview_result  # Sense numbering
            assert "font-weight: bold" in preview_result  # Custom CSS
            
            # Step 5: User saves the profile and uses it elsewhere
            saved_profile = profile_service.get_profile(profile.id)
            assert saved_profile is not None
            assert saved_profile.name == "Realistic Workflow Test"
            
            # Step 6: Verify the profile can be used consistently
            second_preview = css_service.render_entry(preview_xml, saved_profile)
            assert second_preview == preview_result  # Should be consistent


class TestCSSMigrationSystemIntegration:
    """System-level integration tests."""

    def test_css_migration_with_database_integration(self, app: Flask) -> None:
        """Test CSS migration with full database integration."""
        with app.app_context():
            # Create multiple profiles and test database operations
            profile_service = DisplayProfileService()
            css_service = CSSMappingService()
            
            # Create first profile
            profile1 = profile_service.create_profile(name="Database Test 1")
            profile_service.set_element_display_aspect(profile1.id, "relation", "label")
            profile1.custom_css = ".test1 { color: red; }"
            db.session.commit()
            
            # Create second profile
            profile2 = profile_service.create_profile(name="Database Test 2")
            profile_service.set_element_display_aspect(profile2.id, "relation", "abbr")
            profile2.custom_css = ".test2 { color: blue; }"
            db.session.commit()
            
            # Test XML
            test_xml = """
            <entry id="db-test">
                <lexical-unit>
                    <form lang="en"><text>database</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1" data-headword="storage"/>
                </sense>
            </entry>
            """
            
            # Render with both profiles
            result1 = css_service.render_entry(test_xml, profile1)
            result2 = css_service.render_entry(test_xml, profile2)
            
            # Both should work but produce different results
            assert result1 is not None
            assert result2 is not None
            assert "color: red" in result1
            assert "color: blue" in result2
            
            # One should show label, the other abbreviation
            assert "Synonym" in result1 or "synonym" in result1
            assert "syn" in result2 or "synonym" in result2
            
            # Verify profiles are properly saved in database
            retrieved1 = profile_service.get_profile(profile1.id)
            retrieved2 = profile_service.get_profile(profile2.id)
            
            assert retrieved1 is not None
            assert retrieved2 is not None
            assert retrieved1.name == "Database Test 1"
            assert retrieved2.name == "Database Test 2"
            
            # Test listing profiles
            all_profiles = profile_service.list_profiles()
            assert len(all_profiles) >= 2
            
            # Test deleting a profile
            delete_success = profile_service.delete_profile(profile1.id)
            assert delete_success is True
            
            # Verify it's gone
            deleted_profile = profile_service.get_profile(profile1.id)
            assert deleted_profile is None
            
            # Verify other profile still works
            result_after_delete = css_service.render_entry(test_xml, profile2)
            assert result_after_delete is not None
            assert "color: blue" in result_after_delete

    def test_css_migration_with_concurrent_operations(self, app: Flask) -> None:
        """Test CSS migration with concurrent-like operations."""
        with app.app_context():
            profile_service = DisplayProfileService()
            css_service = CSSMappingService()
            
            # Create a base profile
            base_profile = profile_service.create_profile(name="Concurrent Test")
            profile_service.set_element_display_aspect(base_profile.id, "relation", "label")
            db.session.commit()
            
            # Simulate concurrent operations by creating multiple profiles
            # based on the same template
            profiles = []
            test_xml = """
            <entry id="concurrent">
                <lexical-unit>
                    <form lang="en"><text>concurrent</text></form>
                </lexical-unit>
                <sense>
                    <relation type="synonym" ref="entry-1" data-headword="simultaneous"/>
                </sense>
            </entry>
            """
            
            for i in range(5):
                # Create profile variation
                profile = profile_service.create_profile(name=f"Concurrent Variation {i}")
                
                # Copy settings from base profile
                base_elements = profile_service.get_profile_elements(base_profile.id)
                for base_elem in base_elements:
                    new_elem = ProfileElement()
                    new_elem.profile_id = profile.id
                    new_elem.lift_element = base_elem.lift_element
                    new_elem.css_class = base_elem.css_class
                    new_elem.display_order = base_elem.display_order
                    new_elem.visibility = base_elem.visibility
                    # Note: display_mode is not a valid attribute, removed from copy
                    new_elem.prefix = base_elem.prefix
                    new_elem.suffix = base_elem.suffix
                    new_elem.config = base_elem.config.copy() if base_elem.config else None
                    
                    # Add display aspect
                    if base_elem.lift_element == "relation":
                        profile_service.set_element_display_aspect(
                            profile.id, "relation", "label"
                        )
                    
                    db.session.add(new_elem)
                
                profile.custom_css = f".variation-{i} {{ color: rgb({i*50}, {i*30}, {i*10}); }}"
                db.session.commit()
                
                profiles.append(profile)
                
                # Render with each profile
                result = css_service.render_entry(test_xml, profile)
                assert result is not None
                assert "concurrent" in result
                assert f"rgb({i*50}, {i*30}, {i*10})" in result
            
            # All profiles should still work
            for i, profile in enumerate(profiles):
                result = css_service.render_entry(test_xml, profile)
                assert result is not None
                assert f"rgb({i*50}, {i*30}, {i*10})" in result
            
            # Clean up
            for profile in profiles:
                profile_service.delete_profile(profile.id)
            
            # Verify cleanup - check that the created profiles are gone
            remaining_profiles = profile_service.list_profiles()
            profile_names = [p.name for p in remaining_profiles]
            for i in range(5):
                assert f"Concurrent Variation {i}" not in profile_names
