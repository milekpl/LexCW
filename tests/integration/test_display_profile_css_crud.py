"""Integration tests for Display Profile CSS CRUD operations.

Tests the full lifecycle of custom CSS in display profiles:
- Create profile with custom CSS
- Read/retrieve CSS from profile
- Update CSS in existing profile
- Delete profile with CSS
- Verify CSS is applied in rendering
"""

import pytest


@pytest.mark.integration
class TestDisplayProfileCSSCRUD:
    """Test CRUD operations on display profile custom CSS."""

    def test_create_profile_with_custom_css(self, app, cleanup_display_profiles):
        """Test creating a profile with custom CSS."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            with app.app_context():
                from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        custom_css = """
            .lexical-unit { font-weight: bold; color: #333; }
            .sense { margin-left: 1em; }
            .definition[lang='pl'] { font-style: italic; }
        """
        
        profile = service.create_profile(
            name="Test CSS Profile",
            description="Profile with custom CSS",
            custom_css=custom_css,
            elements=[{
                'lift_element': 'lexical-unit',
                'css_class': 'lexical-unit',
                'display_order': 0
            }]
        )
        
        assert profile.id is not None
        assert profile.custom_css == custom_css
        assert profile.name == "Test CSS Profile"

    def test_read_profile_custom_css(self, app):
        """Test reading custom CSS from a profile."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            with app.app_context():
                from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
            
            custom_css = ".example { color: red; }"
            
            # Create profile
            created = service.create_profile(
                name="Read Test Profile",
                custom_css=custom_css
            )
            
            # Read it back
            profile = service.get_profile(created.id)
            
            assert profile is not None
            assert profile.custom_css == custom_css

    def test_update_profile_custom_css(self, app):
        """Test updating custom CSS in an existing profile."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        original_css = ".old { color: blue; }"
        updated_css = ".new { color: green; }"
        
        # Create profile
        profile = service.create_profile(
            name="Update Test Profile",
            custom_css=original_css
        )
        
        # Update CSS
        updated = service.update_profile(
            profile.id,
            custom_css=updated_css
        )
        
        assert updated.custom_css == updated_css
        assert updated.custom_css != original_css

    def test_delete_profile_with_custom_css(self, app):
        """Test deleting a profile that has custom CSS."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        # Create profile
        profile = service.create_profile(
            name="Delete Test Profile",
            custom_css=".test { font-size: 12px; }"
        )
        
        profile_id = profile.id
        
        # Delete it
        service.delete_profile(profile_id)
        
        # Verify it's gone
        deleted = service.get_profile(profile_id)
        assert deleted is None

    def test_custom_css_persists_in_to_dict(self, app):
        """Test that custom CSS is included in to_dict() serialization."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        custom_css = ".serialization-test { margin: 10px; }"
        
        profile = service.create_profile(
            name="Serialization Test",
            custom_css=custom_css
        )
        
        profile_dict = profile.to_dict()
        
        assert 'custom_css' in profile_dict
        assert profile_dict['custom_css'] == custom_css

    def test_custom_css_in_export_import(self, app):
        """Test that custom CSS survives export/import cycle."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        custom_css = ".export-import { padding: 5px; }"
        
        # Create and export
        profile = service.create_profile(
            name="Export Test",
            custom_css=custom_css,
            elements=[{
                'lift_element': 'sense',
                'css_class': 'sense',
                'display_order': 0
            }]
        )
        
        exported = service.export_profile(profile.id)
        
        # Delete original
        service.delete_profile(profile.id)
        
        # Import
        imported = service.import_profile(exported, overwrite=False)
        
        assert imported.custom_css == custom_css

    def test_css_applied_in_rendering(self, app):
        """Test that custom CSS is actually applied when rendering entries."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            from app.services.css_mapping_service import CSSMappingService
            
            from app.models.workset_models import db
        
        service = DisplayProfileService()
        css_service = CSSMappingService()
        
        custom_css = """
            .test-class { color: purple; font-size: 16px; }
        """
        
        # Create profile with CSS
        profile = service.create_profile(
            name="Rendering Test",
            custom_css=custom_css,
            number_senses=False,  # Disable auto-numbering for this test
            elements=[{
                'lift_element': 'lexical-unit',
                'css_class': 'test-class',
                'display_order': 0
            }]
        )
        
        # Commit to ensure it's saved
        db.session.commit()
        
        # Sample LIFT XML
        entry_xml = """
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        """
        
        # Render
        html = css_service.render_entry(entry_xml, profile)
        
        # Verify CSS is embedded in output
        assert '<style>' in html
        assert '.test-class' in html
        assert 'color: purple' in html

    def test_global_settings_persist(self, app):
        """Test that global settings (show_subentries, number_senses) persist."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        profile = service.create_profile(
            name="Global Settings Test",
            show_subentries=True,
            number_senses=False
        )
        
        assert profile.show_subentries is True
        assert profile.number_senses is False
        
        # Read back
        retrieved = service.get_profile(profile.id)
        assert retrieved.show_subentries is True
        assert retrieved.number_senses is False

    def test_sense_numbering_css_injection(self, app):
        """Test that sense numbering CSS is auto-injected when enabled."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            from app.services.css_mapping_service import CSSMappingService
            
            from app.models.workset_models import db
        
        service = DisplayProfileService()
        css_service = CSSMappingService()
        
        # Create profile with numbering enabled
        profile = service.create_profile(
            name="Numbering Test",
            number_senses=True,
            elements=[{
                'lift_element': 'sense',
                'css_class': 'sense',
                'display_order': 0
            }]
        )
        
        db.session.commit()
        
        entry_xml = """
            <entry id="test_entry">
                <sense id="s1">
                    <definition><form lang="en"><text>first</text></form></definition>
                </sense>
                <sense id="s2">
                    <definition><form lang="en"><text>second</text></form></definition>
                </sense>
            </entry>
        """
        
        html = css_service.render_entry(entry_xml, profile)
        
        # Verify numbering CSS is injected
        assert 'counter-reset: sense-counter' in html
        assert 'counter-increment: sense-counter' in html
        assert '.sense::before' in html

    def test_empty_custom_css(self, app):
        """Test handling of empty/None custom CSS."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        # Create with None
        profile1 = service.create_profile(
            name="No CSS Test 1",
            custom_css=None
        )
        assert profile1.custom_css is None
        
        # Create with empty string
        profile2 = service.create_profile(
            name="No CSS Test 2",
            custom_css=""
        )
        assert profile2.custom_css == ""

    def test_css_with_special_characters(self, app):
        """Test CSS containing special characters and quotes."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        # CSS with quotes, brackets, etc.
        custom_css = """
            .element::before { content: "→ "; }
            .element[lang="pl"] { font-family: 'Arial', sans-serif; }
            .element > span { margin: 0; }
        """
        
        profile = service.create_profile(
            name="Special Chars Test",
            custom_css=custom_css
        )
        
        assert profile.custom_css == custom_css
        
        # Verify it survives round-trip
        retrieved = service.get_profile(profile.id)
        assert retrieved.custom_css == custom_css

    def test_conditional_sense_numbering_single_sense(self, app):
        """Test that conditional numbering doesn't number entries with single sense."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            from app.services.css_mapping_service import CSSMappingService
            from app.models.workset_models import db
            
            service = DisplayProfileService()
            css_service = CSSMappingService()
        
        # Create profile with conditional numbering enabled
        profile = service.create_profile(
            name="Conditional Numbering Test",
            number_senses=True,
            number_senses_if_multiple=True,
            elements=[{
                'lift_element': 'sense',
                'css_class': 'sense',
                'display_order': 0
            }]
        )
        
        db.session.commit()
        
        # Entry with SINGLE sense
        entry_xml = """
            <entry id="test_entry">
                <sense id="s1">
                    <definition><form lang="en"><text>only meaning</text></form></definition>
                </sense>
            </entry>
        """
        
        html = css_service.render_entry(entry_xml, profile)
        
        # Verify numbering CSS is NOT injected for single sense
        assert 'counter-reset: sense-counter' not in html
        assert 'counter-increment: sense-counter' not in html
        assert '.sense::before' not in html

    def test_conditional_sense_numbering_multiple_senses(self, app):
        """Test that conditional numbering DOES number entries with multiple senses."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            from app.services.css_mapping_service import CSSMappingService
            from app.models.workset_models import db
            
            service = DisplayProfileService()
            css_service = CSSMappingService()
        
        # Create profile with conditional numbering enabled
        profile = service.create_profile(
            name="Conditional Numbering Multi Test",
            number_senses=True,
            number_senses_if_multiple=True,
            elements=[{
                'lift_element': 'sense',
                'css_class': 'sense',
                'display_order': 0
            }]
        )
        
        db.session.commit()
        
        # Entry with MULTIPLE senses
        entry_xml = """
            <entry id="test_entry">
                <sense id="s1">
                    <definition><form lang="en"><text>first meaning</text></form></definition>
                </sense>
                <sense id="s2">
                    <definition><form lang="en"><text>second meaning</text></form></definition>
                </sense>
            </entry>
        """
        
        html = css_service.render_entry(entry_xml, profile)
        
        # Verify numbering CSS IS injected for multiple senses
        assert 'counter-reset: sense-counter' in html
        assert 'counter-increment: sense-counter' in html
        assert '.sense::before' in html

    def test_number_senses_if_multiple_field_persistence(self, app):
        """Test that number_senses_if_multiple field persists correctly."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        # Create profile with number_senses_if_multiple=True
        profile = service.create_profile(
            name="Persistence Test",
            number_senses=True,
            number_senses_if_multiple=True
        )
        
        assert profile.number_senses_if_multiple is True
        
        # Verify it persists after retrieval
        retrieved = service.get_profile(profile.id)
        assert retrieved.number_senses_if_multiple is True
        
        # Verify it's in to_dict()
        profile_dict = retrieved.to_dict()
        assert profile_dict['number_senses_if_multiple'] is True

    def test_update_number_senses_if_multiple(self, app):
        """Test updating the number_senses_if_multiple field."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        # Create profile with conditional numbering disabled
        profile = service.create_profile(
            name="Update Test",
            number_senses=True,
            number_senses_if_multiple=False
        )
        
        assert profile.number_senses_if_multiple is False
        
        # Update to enable conditional numbering
        updated = service.update_profile(
            profile.id,
            number_senses_if_multiple=True
        )
        
        assert updated.number_senses_if_multiple is True
        
        # Verify persistence
        retrieved = service.get_profile(profile.id)
        assert retrieved.number_senses_if_multiple is True

    def test_import_export_with_number_senses_if_multiple(self, app):
        """Test that import/export preserves number_senses_if_multiple."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            
            service = DisplayProfileService()
        
        # Create profile with conditional numbering
        profile = service.create_profile(
            name="Import/Export Test",
            description="Test profile",
            number_senses=True,
            number_senses_if_multiple=True,
            custom_css=".test { color: red; }"
        )
        
        # Export
        exported = service.export_profile(profile.id)
        assert exported['number_senses_if_multiple'] is True
        
        # Import with new name
        exported['name'] = "Imported Profile"
        imported = service.import_profile(exported, overwrite=False)
        
        # Verify field was imported
        assert imported.number_senses_if_multiple is True
        assert imported.number_senses is True
        assert imported.custom_css == ".test { color: red; }"

    def test_conditional_numbering_with_nested_senses(self, app):
        """Test conditional numbering with nested subsenses."""
        with app.app_context():
            from app.services.display_profile_service import DisplayProfileService
            from app.services.css_mapping_service import CSSMappingService
            from app.models.workset_models import db
            
            service = DisplayProfileService()
            css_service = CSSMappingService()
        
        profile = service.create_profile(
            name="Nested Senses Test",
            number_senses=True,
            number_senses_if_multiple=True,
            elements=[{
                'lift_element': 'sense',
                'css_class': 'sense',
                'display_order': 0
            }]
        )
        
        db.session.commit()
        
        # Entry with nested subsenses (counts as multiple senses)
        entry_xml = """
            <entry id="test_entry">
                <sense id="s1">
                    <definition><form lang="en"><text>first</text></form></definition>
                    <sense id="s1.1">
                        <definition><form lang="en"><text>subsense</text></form></definition>
                    </sense>
                </sense>
            </entry>
        """
        
        html = css_service.render_entry(entry_xml, profile)
        
        # With 2 total senses (including subsense), numbering should be applied
        assert 'counter-reset: sense-counter' in html

