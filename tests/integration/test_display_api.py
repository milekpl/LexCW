"""
Display API tests.

NOTE: These tests are now enabled as the Display Profile Management API
has been implemented.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from app.models.display_profile import DisplayProfile
from app.services.css_mapping_service import CSSMappingService
from app.services.dictionary_service import DictionaryService

# Tests are now enabled as the feature has been implemented
# pytestmark = pytest.mark.skip(reason="Display Profile Management API is not yet implemented")


@pytest.fixture
def mock_css_mapping_service() -> MagicMock:
    """Fixture for a mocked CSSMappingService."""
    return MagicMock()


@pytest.fixture(autouse=True)
def setup_mocks(app, mock_css_mapping_service: MagicMock):
    """Patch the injector to return the mocked service."""
    with app.app_context():
        with patch("app.api.display.injector.get") as mock_injector_get:
            mock_injector_get.return_value = mock_css_mapping_service
            yield



@pytest.mark.integration
class TestDisplayAPI:
    """Tests for the Display Profile Management API."""

    @pytest.mark.integration
    def test_create_profile(self, client: FlaskClient, mock_css_mapping_service: MagicMock) -> None:
        """Test POST /api/display-profiles - creating a new profile."""
        # RED: Test fails because the API endpoint is not fully implemented.
        profile_data = {"profile_name": "API Test Profile", "elements": []}
        mock_css_mapping_service.create_profile.return_value = DisplayProfile(**profile_data)

        response = client.post("/api/display-profiles", json=profile_data)

        assert response.status_code == 201
        mock_css_mapping_service.create_profile.assert_called_once_with(profile_data)
        assert response.json["profile_name"] == "API Test Profile"

    @pytest.mark.integration
    def test_get_profile(self, client: FlaskClient, mock_css_mapping_service: MagicMock) -> None:
        """Test GET /api/display-profiles/{id} - retrieving a profile."""
        # RED: Test fails because the API endpoint is not fully implemented.
        profile_id = "test-profile-123"
        profile_data = {"profile_id": profile_id, "profile_name": "Get Test", "elements": []}
        mock_css_mapping_service.get_profile.return_value = DisplayProfile(**profile_data)

        response = client.get(f"/api/display-profiles/{profile_id}")

        assert response.status_code == 200
        mock_css_mapping_service.get_profile.assert_called_once_with(profile_id)
        assert response.json["profile_id"] == profile_id

    @pytest.mark.integration
    def test_list_profiles(self, client: FlaskClient, mock_css_mapping_service: MagicMock) -> None:
        """Test GET /api/display-profiles - listing all profiles."""
        # RED: Test fails because the API endpoint is not fully implemented.
        mock_css_mapping_service.list_profiles.return_value = [
            DisplayProfile(profile_name="Profile 1", elements=[]),
            DisplayProfile(profile_name="Profile 2", elements=[]),
        ]

        response = client.get("/api/display-profiles")

        assert response.status_code == 200
        mock_css_mapping_service.list_profiles.assert_called_once()
        assert len(response.json) == 2

    @pytest.mark.integration
    def test_update_profile(self, client: FlaskClient, mock_css_mapping_service: MagicMock) -> None:
        """Test PUT /api/display-profiles/{id} - updating a profile."""
        profile_id = "test-profile-123"
        update_data = {"profile_name": "Updated Profile", "elements": []}
        mock_css_mapping_service.update_profile.return_value = DisplayProfile(**update_data)

        response = client.put(f"/api/display-profiles/{profile_id}", json=update_data)

        assert response.status_code == 200
        mock_css_mapping_service.update_profile.assert_called_once_with(profile_id, update_data)
        assert response.json["profile_name"] == "Updated Profile"

    @pytest.mark.integration
    def test_delete_profile(self, client: FlaskClient, mock_css_mapping_service: MagicMock) -> None:
        """Test DELETE /api/display-profiles/{id} - deleting a profile."""
        profile_id = "test-profile-456"
        mock_css_mapping_service.delete_profile.return_value = True

        response = client.delete(f"/api/display-profiles/{profile_id}")

        assert response.status_code == 200
        mock_css_mapping_service.delete_profile.assert_called_once_with(profile_id)
        assert response.json["success"] == True
        assert response.json["message"] == "Profile deleted successfully"

    @pytest.mark.integration
    def test_preview_entry(self, client: FlaskClient, mock_css_mapping_service: MagicMock) -> None:
        """Test GET /api/display-profiles/entries/{id}/preview - previewing an entry."""
        entry_id = "test-entry-789"
        profile_id = "test-profile-123"
        mock_profile = DisplayProfile(profile_name="Preview Profile", elements=[])
        mock_css_mapping_service.get_profile.return_value = mock_profile

        # Mock the dictionary service and LIFT parser
        with patch("app.api.display.injector.get") as mock_injector_get:
            mock_dict_service = MagicMock()
            mock_dict_service.get_entry.return_value = MagicMock()

            def get_side_effect(service_type):
                if service_type == DictionaryService:
                    return mock_dict_service
                return mock_css_mapping_service

            mock_injector_get.side_effect = get_side_effect

            # Mock the LIFT parser
            with patch("app.api.display.LIFTParser") as mock_lift_parser:
                mock_parser_instance = MagicMock()
                mock_parser_instance.generate_lift_string.return_value = "<entry><lexical-unit>test</lexical-unit></entry>"
                mock_lift_parser.return_value = mock_parser_instance

                # Mock the render_entry method
                mock_css_mapping_service.render_entry.return_value = "<div class='entry'>test</div>"

                response = client.get(f"/api/display-profiles/entries/{entry_id}/preview?profile_id={profile_id}")

                assert response.status_code == 200
                mock_css_mapping_service.get_profile.assert_called_once_with(profile_id)
                mock_dict_service.get_entry.assert_called_once_with(entry_id)
                assert response.json["success"] == True
                assert response.json["entry_id"] == entry_id
                assert response.json["profile_id"] == profile_id
                assert "html" in response.json