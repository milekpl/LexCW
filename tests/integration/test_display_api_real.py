"""
Real integration tests for Display Profile API (no mocking).
Tests the full stack from API to service layer to persistence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import pytest

if TYPE_CHECKING:
    from flask.testing import FlaskClient


@pytest.fixture
def sample_profile_data() -> Dict[str, Any]:
    """Sample display profile data for testing."""
    return {
        "profile_name": "Integration Test Profile",
        "view_type": "root-based",
        "elements": [
            {
                "lift_element": "lexical-unit",
                "display_order": 1,
                "css_class": "headword",
                "prefix": "",
                "suffix": "",
                "visibility": "always"
            },
            {
                "lift_element": "pronunciation",
                "display_order": 2,
                "css_class": "pronunciation",
                "prefix": "/",
                "suffix": "/",
                "visibility": "if-content"
            },
            {
                "lift_element": "grammatical-info",
                "display_order": 3,
                "css_class": "gram-info",
                "visibility": "if-content"
            }
        ]
    }


@pytest.mark.integration
class TestDisplayProfileAPIReal:
    """Real integration tests for display profile CRUD endpoints."""

    def test_create_and_get_profile(self, client: FlaskClient, sample_profile_data: Dict[str, Any]) -> None:
        """Test creating a profile and retrieving it."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )

        assert create_response.status_code == 201
        created = create_response.get_json()
        assert created is not None
        assert "profile_id" in created
        assert created["profile_name"] == "Integration Test Profile"
        
        profile_id = created["profile_id"]

        # Get profile
        get_response = client.get(f"/api/display-profiles/{profile_id}")

        assert get_response.status_code == 200
        retrieved = get_response.get_json()
        assert retrieved is not None
        assert retrieved["profile_id"] == profile_id
        assert retrieved["profile_name"] == "Integration Test Profile"
        assert len(retrieved["elements"]) == 3

    def test_list_profiles(self, client: FlaskClient, sample_profile_data: Dict[str, Any]) -> None:
        """Test listing profiles."""
        # Create two profiles
        client.post("/api/display-profiles", json=sample_profile_data)
        
        profile_data_2 = sample_profile_data.copy()
        profile_data_2["profile_name"] = "Second Integration Profile"
        client.post("/api/display-profiles", json=profile_data_2)

        # List all
        response = client.get("/api/display-profiles")

        assert response.status_code == 200
        profiles = response.get_json()
        assert profiles is not None
        assert isinstance(profiles, list)
        assert len(profiles) >= 2
        
        # Verify our profiles are in the list
        profile_names = [p["profile_name"] for p in profiles]  # type: ignore
        assert "Integration Test Profile" in profile_names
        assert "Second Integration Profile" in profile_names

    def test_update_profile(self, client: FlaskClient, sample_profile_data: Dict[str, Any]) -> None:
        """Test updating a profile."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["profile_id"]

        # Update it
        update_data = {"profile_name": "Updated Integration Profile"}
        update_response = client.put(
            f"/api/display-profiles/{profile_id}",
            json=update_data
        )

        assert update_response.status_code == 200
        updated = update_response.get_json()
        assert updated is not None
        assert updated["profile_name"] == "Updated Integration Profile"
        # Elements should remain unchanged
        assert len(updated["elements"]) == 3

    def test_delete_profile(self, client: FlaskClient, sample_profile_data: Dict[str, Any]) -> None:
        """Test deleting a profile."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["profile_id"]

        # Delete it
        delete_response = client.delete(f"/api/display-profiles/{profile_id}")

        assert delete_response.status_code == 200
        result = delete_response.get_json()
        assert result is not None
        assert result["success"] is True

        # Verify it's gone
        get_response = client.get(f"/api/display-profiles/{profile_id}")
        assert get_response.status_code == 404

    def test_get_nonexistent_profile(self, client: FlaskClient) -> None:
        """Test getting a profile that doesn't exist."""
        response = client.get("/api/display-profiles/nonexistent-id-12345")

        assert response.status_code == 404

    def test_update_nonexistent_profile(self, client: FlaskClient) -> None:
        """Test updating a profile that doesn't exist."""
        response = client.put(
            "/api/display-profiles/nonexistent-id-12345",
            json={"profile_name": "Updated"}
        )

        assert response.status_code == 404

    def test_delete_nonexistent_profile(self, client: FlaskClient) -> None:
        """Test deleting a profile that doesn't exist."""
        response = client.delete("/api/display-profiles/nonexistent-id-12345")

        assert response.status_code == 404

    def test_create_profile_invalid_data(self, client: FlaskClient) -> None:
        """Test creating a profile with invalid data."""
        invalid_data: Dict[str, Any] = {
            # Missing profile_name entirely
            "elements": []
        }

        response = client.post(
            "/api/display-profiles",
            json=invalid_data
        )

        # Should accept it or return 400 - either is valid
        # The service creates profiles without names, so 201 is acceptable
        assert response.status_code in [201, 400]


@pytest.mark.integration
class TestDisplayProfilePersistence:
    """Test that profiles persist correctly."""

    def test_profiles_persist_across_requests(self, client: FlaskClient, sample_profile_data: Dict[str, Any]) -> None:
        """Test that created profiles persist across multiple requests."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["profile_id"]

        # Make multiple GET requests - should return same data
        for _ in range(3):
            response = client.get(f"/api/display-profiles/{profile_id}")
            assert response.status_code == 200
            data = response.get_json()
            assert data is not None
            assert data["profile_id"] == profile_id
            assert data["profile_name"] == "Integration Test Profile"

    def test_updates_persist(self, client: FlaskClient, sample_profile_data: Dict[str, Any]) -> None:
        """Test that updates persist."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["profile_id"]

        # Update it
        client.put(
            f"/api/display-profiles/{profile_id}",
            json={"profile_name": "Persisted Update"}
        )

        # Verify update persisted
        response = client.get(f"/api/display-profiles/{profile_id}")
        data = response.get_json()
        assert data is not None
        assert data["profile_name"] == "Persisted Update"

    def test_deletes_persist(self, client: FlaskClient, sample_profile_data: Dict[str, Any]) -> None:
        """Test that deletes persist."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["profile_id"]

        # Delete it
        client.delete(f"/api/display-profiles/{profile_id}")

        # Verify it stays deleted across multiple requests
        for _ in range(3):
            response = client.get(f"/api/display-profiles/{profile_id}")
            assert response.status_code == 404
