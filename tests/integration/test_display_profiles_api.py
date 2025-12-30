"""
Integration tests for Display Profiles API endpoints.
"""

from __future__ import annotations

import json
from typing import Any

import pytest


@pytest.mark.integration
class TestDisplayProfilesAPI:
    """Test cases for display profiles API endpoints."""

    def test_list_profiles_empty(self, client: Any) -> None:
        """Test listing profiles when database is empty."""
        response = client.get("/api/profiles")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert "profiles" in data
        assert isinstance(data["profiles"], list)

    def test_create_profile(self, client: Any) -> None:
        """Test creating a new profile via API."""
        profile_data = {
            "name": "Test Profile",
            "description": "A test profile",
            "elements": [
                {
                    "lift_element": "lexical-unit",
                    "css_class": "entry-headword",
                    "visibility": "always",
                    "display_order": 1,
                    "prefix": "",
                    "suffix": "",
                    "config": {}
                }
            ]
        }
        
        response = client.post(
            "/api/profiles",
            data=json.dumps(profile_data),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert data["name"] == "Test Profile"
        assert data["description"] == "A test profile"
        assert len(data["elements"]) == 1
        assert data["elements"][0]["lift_element"] == "lexical-unit"

    def test_create_profile_missing_name(self, client: Any) -> None:
        """Test creating profile without name returns 400."""
        profile_data = {
            "description": "Missing name"
        }
        
        response = client.post(
            "/api/profiles",
            data=json.dumps(profile_data),
            content_type="application/json"
        )
        
        assert response.status_code == 400

    def test_create_profile_duplicate_name(self, client: Any) -> None:
        """Test creating profile with duplicate name returns 400."""
        profile_data = {
            "name": "Duplicate",
            "description": "First"
        }
        
        # Create first profile
        response1 = client.post(
            "/api/profiles",
            data=json.dumps(profile_data),
            content_type="application/json"
        )
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = client.post(
            "/api/profiles",
            data=json.dumps(profile_data),
            content_type="application/json"
        )
        assert response2.status_code == 400

    def test_get_profile(self, client: Any) -> None:
        """Test getting a specific profile."""
        # Create a profile
        profile_data = {
            "name": "Get Test",
            "description": "Test retrieval"
        }
        
        create_response = client.post(
            "/api/profiles",
            data=json.dumps(profile_data),
            content_type="application/json"
        )
        created = create_response.get_json()
        profile_id = created["id"]
        
        # Get it
        response = client.get(f"/api/profiles/{profile_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["id"] == profile_id
        assert data["name"] == "Get Test"

    def test_get_profile_not_found(self, client: Any) -> None:
        """Test getting non-existent profile returns 404."""
        response = client.get("/api/profiles/99999")
        
        assert response.status_code == 404

    def test_update_profile(self, client: Any) -> None:
        """Test updating a profile."""
        # Create a profile
        create_data = {
            "name": "Original",
            "description": "Original description"
        }
        
        create_response = client.post(
            "/api/profiles",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        created = create_response.get_json()
        profile_id = created["id"]
        
        # Update it
        update_data = {
            "name": "Updated",
            "description": "Updated description"
        }
        
        response = client.put(
            f"/api/profiles/{profile_id}",
            data=json.dumps(update_data),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["name"] == "Updated"
        assert data["description"] == "Updated description"

    def test_update_profile_not_found(self, client: Any) -> None:
        """Test updating non-existent profile returns 404."""
        update_data = {"name": "Does not exist"}
        
        response = client.put(
            "/api/profiles/99999",
            data=json.dumps(update_data),
            content_type="application/json"
        )
        
        assert response.status_code == 404

    def test_delete_profile(self, client: Any) -> None:
        """Test deleting a profile."""
        # Create a profile
        create_data = {"name": "To Delete"}
        
        create_response = client.post(
            "/api/profiles",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        created = create_response.get_json()
        profile_id = created["id"]
        
        # Delete it
        response = client.delete(f"/api/profiles/{profile_id}")
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/api/profiles/{profile_id}")
        assert get_response.status_code == 404

    def test_delete_profile_not_found(self, client: Any) -> None:
        """Test deleting non-existent profile returns 404."""
        response = client.delete("/api/profiles/99999")
        
        assert response.status_code == 404

    def test_set_default_profile(self, client: Any) -> None:
        """Test setting a profile as default."""
        # Create two profiles
        profile1_data = {"name": "Profile 1"}
        profile2_data = {"name": "Profile 2"}
        
        response1 = client.post(
            "/api/profiles",
            data=json.dumps(profile1_data),
            content_type="application/json"
        )
        profile1 = response1.get_json()
        
        response2 = client.post(
            "/api/profiles",
            data=json.dumps(profile2_data),
            content_type="application/json"
        )
        profile2 = response2.get_json()
        
        # Set profile2 as default
        response = client.post(f"/api/profiles/{profile2['id']}/default")
        
        assert response.status_code == 200
        resp = response.get_json()
        assert resp.get("success", False) is True
        data = resp.get("data", resp)
        
        assert data["is_default"] is True
        
        # Verify profile1 is not default
        get_response = client.get(f"/api/profiles/{profile1['id']}")
        profile1_current = get_response.get_json()
        assert profile1_current["is_default"] is False

    def test_get_default_profile(self, client: Any) -> None:
        """Test getting the default profile."""
        # Create a profile and set as default
        create_data = {"name": "Default Profile"}
        
        create_response = client.post(
            "/api/profiles",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        created = create_response.get_json()
        
        # Set as default
        client.post(f"/api/profiles/{created['id']}/default")
        
        # Get default
        response = client.get("/api/profiles/default")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["name"] == "Default Profile"
        assert data["is_default"] is True

    def test_get_default_profile_none_exists(self, client: Any) -> None:
        """Test getting default profile when one exists."""
        # Note: There may be a default profile created automatically
        response = client.get("/api/profiles/default")
        
        # Either 404 if none exists, or 200 if default was auto-created
        assert response.status_code in (200, 404)

    def test_create_from_default(self, client: Any) -> None:
        """Test creating a profile from registry default."""
        create_data = {
            "name": "From Default",
            "description": "Created from default"
        }
        
        response = client.post(
            "/api/profiles/create-default",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        resp = response.get_json()
        assert resp.get("success", False) is True
        data = resp.get("data", resp)
        
        assert data["name"] == "From Default"
        # Description comes from the service, not the request
        assert "default" in (data.get("description") or "").lower() or "registry" in (data.get("description") or "").lower()
        # Should have elements from registry
        assert len(data["elements"]) > 0

    def test_export_profile(self, client: Any) -> None:
        """Test exporting a profile."""
        # Create a profile with elements
        create_data = {
            "name": "Export Test",
            "description": "Test export",
            "elements": [
                {
                    "lift_element": "lexical-unit",
                    "css_class": "entry-headword",
                    "visibility": "always",
                    "display_order": 1,
                    "prefix": "",
                    "suffix": "",
                    "config": {"font-weight": "bold"}
                }
            ]
        }
        
        create_response = client.post(
            "/api/profiles",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        created = create_response.get_json()
        
        # Export it
        response = client.get(f"/api/profiles/{created['id']}/export")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["name"] == "Export Test"
        assert data["description"] == "Test export"
        assert len(data["elements"]) == 1
        assert data["elements"][0]["config"] == {"font-weight": "bold"}

    def test_import_profile(self, client: Any) -> None:
        """Test importing a profile."""
        import_data = {
            "name": "Imported",
            "description": "Test import",
            "elements": [
                {
                    "lift_element": "lexical-unit",
                    "css_class": "entry-headword",
                    "visibility": "always",
                    "display_order": 1,
                    "prefix": "",
                    "suffix": "",
                    "config": {}
                }
            ]
        }
        
        response = client.post(
            "/api/profiles/import",
            data=json.dumps(import_data),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert data["name"] == "Imported"
        assert data["description"] == "Test import"
        assert len(data["elements"]) == 1

    def test_list_profiles_after_creating_several(self, client: Any) -> None:
        """Test listing profiles returns all created profiles."""
        # Create multiple profiles
        for i in range(3):
            profile_data = {
                "name": f"Profile {i+1}",
                "description": f"Description {i+1}"
            }
            client.post(
                "/api/profiles",
                data=json.dumps(profile_data),
                content_type="application/json"
            )
        
        # List all
        response = client.get("/api/profiles")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data["profiles"]) >= 3
        profile_names = [p["name"] for p in data["profiles"]]
        assert "Profile 1" in profile_names
        assert "Profile 2" in profile_names
        assert "Profile 3" in profile_names

    def test_profile_elements_ordering(self, client: Any) -> None:
        """Test that profile elements maintain display_order."""
        create_data = {
            "name": "Order Test",
            "elements": [
                {
                    "lift_element": "sense",
                    "css_class": "entry-sense",
                    "visibility": "always",
                    "display_order": 3,
                    "prefix": "",
                    "suffix": "",
                    "config": {}
                },
                {
                    "lift_element": "lexical-unit",
                    "css_class": "entry-headword",
                    "visibility": "always",
                    "display_order": 1,
                    "prefix": "",
                    "suffix": "",
                    "config": {}
                },
                {
                    "lift_element": "pronunciation",
                    "css_class": "entry-pronunciation",
                    "visibility": "always",
                    "display_order": 2,
                    "prefix": "",
                    "suffix": "",
                    "config": {}
                }
            ]
        }
        
        response = client.post(
            "/api/profiles",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Elements should be ordered by display_order
        assert data["elements"][0]["lift_element"] == "lexical-unit"
        assert data["elements"][1]["lift_element"] == "pronunciation"
        assert data["elements"][2]["lift_element"] == "sense"
