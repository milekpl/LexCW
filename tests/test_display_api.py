from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from app.models.display_profile import DisplayProfile


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


class TestDisplayAPI:
    """Tests for the Display Profile Management API."""

    def test_create_profile(self, client: FlaskClient, mock_css_mapping_service: MagicMock) -> None:
        """Test POST /api/display-profiles - creating a new profile."""
        # RED: Test fails because the API endpoint is not fully implemented.
        profile_data = {"profile_name": "API Test Profile", "elements": []}
        mock_css_mapping_service.create_profile.return_value = DisplayProfile(**profile_data)

        response = client.post("/api/display-profiles", json=profile_data)

        assert response.status_code == 201
        mock_css_mapping_service.create_profile.assert_called_once_with(profile_data)
        assert response.json["profile_name"] == "API Test Profile"

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

    def test_update_profile(self, client: FlaskClient) -> None:
        """Test PUT /api/display-profiles/{id} - updating a profile."""
        # RED: Test fails because the route raises NotImplementedError.
        with pytest.raises(NotImplementedError):
            client.put("/api/display-profiles/some-id", json={"profile_name": "Updated"})

    def test_delete_profile(self, client: FlaskClient) -> None:
        """Test DELETE /api/display-profiles/{id} - deleting a profile."""
        # RED: Test fails because the route raises NotImplementedError.
        with pytest.raises(NotImplementedError):
            client.delete("/api/display-profiles/some-id")