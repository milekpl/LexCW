from __future__ import annotations

from pathlib import Path

import pytest

from app.models.display_profile import DisplayProfile
from app.services.css_mapping_service import CSSMappingService


@pytest.fixture
def css_mapping_service(tmp_path: Path) -> CSSMappingService:
    """Fixture for a CSSMappingService with temporary storage."""
    storage_file = tmp_path / "display_profiles.json"
    return CSSMappingService(storage_path=storage_file)


@pytest.fixture
def sample_profile_data() -> dict:
    return {
        "profile_name": "Web View",
        "view_type": "root-based",
        "elements": [
            {"lift_element": "lexical-unit", "display_order": 1, "css_class": "headword"},
            {"lift_element": "pronunciation", "display_order": 2, "css_class": "pronunciation"},
            {"lift_element": "sense", "display_order": 3, "css_class": "sense-block"},
        ],
    }


class TestCSSMappingService:
    """Tests for the CSS Mapping and Rendering Service."""

    def test_create_and_get_profile(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test creating a new display profile and retrieving it."""
        # RED: Test fails because create_profile is not implemented.
        created_profile = css_mapping_service.create_profile(sample_profile_data)
        assert created_profile.profile_name == "Web View"

        retrieved_profile = css_mapping_service.get_profile(created_profile.profile_id)
        assert retrieved_profile is not None
        assert retrieved_profile.profile_id == created_profile.profile_id

    def test_list_profiles(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test listing all display profiles."""
        # RED: Test fails because list_profiles is not implemented.
        css_mapping_service.create_profile(sample_profile_data)
        profiles = css_mapping_service.list_profiles()
        assert len(profiles) == 1
        assert profiles[0].profile_name == "Web View"

    def test_update_profile(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test updating an existing display profile."""
        # RED: Test fails because update_profile is not implemented.
        profile = css_mapping_service.create_profile(sample_profile_data)
        update_data = {"profile_name": "Updated Web View"}
        updated_profile = css_mapping_service.update_profile(profile.profile_id, update_data)
        assert updated_profile is not None
        assert updated_profile.profile_name == "Updated Web View"

    def test_delete_profile(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test deleting a display profile."""
        # RED: Test fails because delete_profile is not implemented.
        profile = css_mapping_service.create_profile(sample_profile_data)
        result = css_mapping_service.delete_profile(profile.profile_id)
        assert result is True
        assert css_mapping_service.get_profile(profile.profile_id) is None

    def test_render_simple_entry(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test rendering a simple LIFT entry to HTML."""
        # RED: Test fails because render_entry is not implemented.
        profile = DisplayProfile(**sample_profile_data)
        entry_xml = """
        <entry id="test1">
            <lexical-unit><form lang="en"><text>test</text></form></lexical-unit>
            <sense><definition><form lang="en"><text>an examination</text></form></definition></sense>
        </entry>
        """
        html = css_mapping_service.render_entry(entry_xml, profile)
        assert '<div class="headword">test</div>' in html
        assert '<div class="sense-block">' in html

    def test_element_order_is_respected(self, css_mapping_service: CSSMappingService) -> None:
        """Test that the display_order in the profile is respected."""
        # RED: Test fails because render_entry is not implemented.
        profile_data = {
            "profile_name": "Reordered View",
            "elements": [
                {"lift_element": "sense", "display_order": 1, "css_class": "sense-first"},
                {"lift_element": "lexical-unit", "display_order": 2, "css_class": "headword-second"},
            ],
        }
        profile = DisplayProfile(**profile_data)
        entry_xml = """
        <entry id="test1"><lexical-unit><form lang="en"><text>test</text></form></lexical-unit><sense><definition><form lang="en"><text>def</text></form></definition></sense></entry>
        """
        html = css_mapping_service.render_entry(entry_xml, profile)
        sense_pos = html.find("sense-first")
        headword_pos = html.find("headword-second")
        assert sense_pos != -1 and headword_pos != -1
        assert sense_pos < headword_pos

    def test_hide_empty_elements(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test that empty LIFT elements are not rendered in the HTML."""
        # RED: Test fails because render_entry is not implemented.
        profile = DisplayProfile(**sample_profile_data)
        entry_xml = """
        <entry id="test1"><lexical-unit><form lang="en"><text>test</text></form></lexical-unit><pronunciation /></entry>
        """
        html = css_mapping_service.render_entry(entry_xml, profile)
        assert '<div class="headword">test</div>' in html
        assert "pronunciation" not in html

    def test_root_based_grouping(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test that subentries are grouped under main entries in root-based view."""
        # RED: This is a complex test that will fail until grouping logic is implemented.
        pytest.fail("Root-based grouping test not yet implemented.")

    def test_list_view_renders_separately(self, css_mapping_service: CSSMappingService, sample_profile_data: dict) -> None:
        """Test that entries are rendered separately in list view."""
        # RED: This test will fail until list view logic is implemented.
        pytest.fail("List view rendering test not yet implemented.")