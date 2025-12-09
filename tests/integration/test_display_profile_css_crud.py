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

    def test_read_profile_custom_css(self, app, db_session):
        """Test reading custom CSS from a profile."""
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

    def test_update_profile_custom_css(self, app, db_session):
        """Test updating custom CSS in an existing profile."""
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

    def test_delete_profile_with_custom_css(self, app, db_session):
        """Test deleting a profile that has custom CSS."""
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

    def test_custom_css_persists_in_to_dict(self, app, db_session):
        """Test that custom CSS is included in to_dict() serialization."""
        service = DisplayProfileService()
        
        custom_css = ".serialization-test { margin: 10px; }"
        
        profile = service.create_profile(
            name="Serialization Test",
            custom_css=custom_css
        )
        
        profile_dict = profile.to_dict()
        
        assert 'custom_css' in profile_dict
        assert profile_dict['custom_css'] == custom_css

    def test_custom_css_in_export_import(self, app, db_session):
        """Test that custom CSS survives export/import cycle."""
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

    def test_css_applied_in_rendering(self, app, db_session):
        """Test that custom CSS is actually applied when rendering entries."""
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

    def test_global_settings_persist(self, app, db_session):
        """Test that global settings (show_subentries, number_senses) persist."""
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

    def test_sense_numbering_css_injection(self, app, db_session):
        """Test that sense numbering CSS is auto-injected when enabled."""
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

    def test_empty_custom_css(self, app, db_session):
        """Test handling of empty/None custom CSS."""
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

    def test_css_with_special_characters(self, app, db_session):
        """Test CSS containing special characters and quotes."""
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
