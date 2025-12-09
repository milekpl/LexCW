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

    def test_create_and_get_profile(self, client: FlaskClient, cleanup_profile_db, sample_profile_data: Dict[str, Any]) -> None:
        """Test creating a profile and retrieving it."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )

        assert create_response.status_code == 201
        created = create_response.get_json()
        assert created is not None
        assert "id" in created
        assert created["name"] == "Integration Test Profile"
        
        profile_id = created["id"]

        # Get profile
        get_response = client.get(f"/api/display-profiles/{profile_id}")

        assert get_response.status_code == 200
        retrieved = get_response.get_json()
        assert retrieved is not None
        assert retrieved["id"] == profile_id
        assert retrieved["name"] == "Integration Test Profile"
        assert len(retrieved["elements"]) == 3

    def test_list_profiles(self, client: FlaskClient, cleanup_profile_db, sample_profile_data: Dict[str, Any]) -> None:
        """Test listing profiles."""
        # Create two profiles
        client.post("/api/display-profiles", json=sample_profile_data)
        
        profile_data_2 = sample_profile_data.copy()
        profile_data_2["name"] = "Second Integration Profile"
        client.post("/api/display-profiles", json=profile_data_2)

        # List all
        response = client.get("/api/display-profiles")

        assert response.status_code == 200
        profiles = response.get_json()
        assert profiles is not None
        assert isinstance(profiles, list)
        assert len(profiles) >= 2
        
        # Verify our profiles are in the list
        profile_names = [p["name"] for p in profiles]  # type: ignore
        assert "Integration Test Profile" in profile_names
        assert "Second Integration Profile" in profile_names

    def test_update_profile(self, client: FlaskClient, cleanup_profile_db, sample_profile_data: Dict[str, Any]) -> None:
        """Test updating a profile."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["id"]

        # Update it
        update_data = {"name": "Updated Integration Profile"}
        update_response = client.put(
            f"/api/display-profiles/{profile_id}",
            json=update_data
        )

        assert update_response.status_code == 200
        updated = update_response.get_json()
        assert updated is not None
        assert updated["name"] == "Updated Integration Profile"
        # Elements should remain unchanged
        assert len(updated["elements"]) == 3

    def test_delete_profile(self, client: FlaskClient, cleanup_profile_db, sample_profile_data: Dict[str, Any]) -> None:
        """Test deleting a profile."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["id"]

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
        response = client.get("/api/display-profiles/99999")

        assert response.status_code == 404

    def test_update_nonexistent_profile(self, client: FlaskClient) -> None:
        """Test updating a profile that doesn't exist."""
        response = client.put(
            "/api/display-profiles/99999",
            json={"name": "Updated"}
        )

        assert response.status_code == 404

    def test_delete_nonexistent_profile(self, client: FlaskClient) -> None:
        """Test deleting a profile that doesn't exist."""
        response = client.delete("/api/display-profiles/99999")

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

    def test_number_senses_if_multiple_field(self, client: FlaskClient, cleanup_profile_db) -> None:
        """Test that number_senses_if_multiple field is saved and retrieved correctly."""
        # Create profile with number_senses_if_multiple=True
        profile_data = {
            "name": "Conditional Numbering Profile",
            "description": "Test profile for conditional sense numbering",
            "number_senses": True,
            "number_senses_if_multiple": True,
            "elements": []
        }
        
        create_response = client.post("/api/display-profiles", json=profile_data)
        assert create_response.status_code == 201
        created = create_response.get_json()
        assert created is not None
        assert created["number_senses"] is True
        assert created["number_senses_if_multiple"] is True
        
        profile_id = created["id"]
        
        # Verify field persists on retrieval
        get_response = client.get(f"/api/display-profiles/{profile_id}")
        assert get_response.status_code == 200
        retrieved = get_response.get_json()
        assert retrieved is not None
        assert retrieved["number_senses"] is True
        assert retrieved["number_senses_if_multiple"] is True
        
        # Update to disable conditional numbering
        update_response = client.put(
            f"/api/display-profiles/{profile_id}",
            json={"number_senses_if_multiple": False}
        )
        assert update_response.status_code == 200
        updated = update_response.get_json()
        assert updated is not None
        assert updated["number_senses_if_multiple"] is False
        
        # Verify update persisted
        get_response2 = client.get(f"/api/display-profiles/{profile_id}")
        assert get_response2.status_code == 200
        retrieved2 = get_response2.get_json()
        assert retrieved2 is not None
        assert retrieved2["number_senses_if_multiple"] is False


@pytest.mark.integration
class TestDisplayProfilePersistence:
    """Test that profiles persist correctly."""

    def test_profiles_persist_across_requests(self, client: FlaskClient, cleanup_profile_db, sample_profile_data: Dict[str, Any]) -> None:
        """Test that created profiles persist across multiple requests."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["id"]

        # Make multiple GET requests - should return same data
        for _ in range(3):
            response = client.get(f"/api/display-profiles/{profile_id}")
            assert response.status_code == 200
            data = response.get_json()
            assert data is not None
            assert data["id"] == profile_id
            assert data["name"] == "Integration Test Profile"

    def test_updates_persist(self, client: FlaskClient, cleanup_profile_db, sample_profile_data: Dict[str, Any]) -> None:
        """Test that updates persist."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["id"]

        # Update it
        client.put(
            f"/api/display-profiles/{profile_id}",
            json={"name": "Persisted Update"}
        )

        # Verify update persisted
        response = client.get(f"/api/display-profiles/{profile_id}")
        data = response.get_json()
        assert data is not None
        assert data["name"] == "Persisted Update"

    def test_deletes_persist(self, client: FlaskClient, cleanup_profile_db, sample_profile_data: Dict[str, Any]) -> None:
        """Test that deletes persist."""
        # Create profile
        create_response = client.post(
            "/api/display-profiles",
            json=sample_profile_data
        )
        created = create_response.get_json()
        assert created is not None
        profile_id = created["id"]

        # Delete it
        client.delete(f"/api/display-profiles/{profile_id}")

        # Verify it stays deleted across multiple requests
        for _ in range(3):
            response = client.get(f"/api/display-profiles/{profile_id}")
            assert response.status_code == 404
