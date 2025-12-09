"""
Unit tests for DisplayProfileService.
"""

from __future__ import annotations

import pytest
from typing import Any
from flask import Flask

from app.services.display_profile_service import DisplayProfileService
from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db


class TestDisplayProfileService:
    """Test cases for DisplayProfileService CRUD operations."""

    def test_create_profile(self, app: Any) -> None:
        """Test creating a display profile."""
        service = DisplayProfileService()
        
        profile = service.create_profile(
            name="Test Profile",
            description="A test profile",
            elements=[
                {
                    "lift_element": "headword",
                    "css_class": "entry-headword",
                    "visibility": "visible",
                    "display_order": 1
                }
            ]
        )
        
        assert profile.id is not None
        assert profile.name == "Test Profile"
        assert profile.description == "A test profile"
        assert len(profile.elements) == 1
        assert profile.elements[0].lift_element == "headword"

    def test_create_profile_duplicate_name(self, app: Any) -> None:
        """Test creating a profile with duplicate name raises error."""
        service = DisplayProfileService()
        
        # Create first profile
        service.create_profile(
            name="Test Profile",
            description="First profile"
        )
        
        # Try to create duplicate
        try:
            service.create_profile(
                name="Test Profile",
                description="Second profile"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already exists" in str(e).lower()

    def test_get_profile(self, app: Any) -> None:
        """Test getting a profile by ID."""
        service = DisplayProfileService()
        
        # Create a profile
        created = service.create_profile(
            name="Test Profile",
            description="A test profile"
        )
        
        # Get it back
        retrieved = service.get_profile(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Profile"

    def test_get_profile_not_found(self, app: Any) -> None:
        """Test getting non-existent profile returns None."""
        service = DisplayProfileService()
        
        profile = service.get_profile(99999)
        
        assert profile is None

    def test_get_profile_by_name(self, app: Any) -> None:
        """Test getting a profile by name."""
        service = DisplayProfileService()
        
        # Create a profile
        service.create_profile(
            name="Test Profile",
            description="A test profile"
        )
        
        # Get it by name
        retrieved = service.get_profile_by_name("Test Profile")
        
        assert retrieved is not None
        assert retrieved.name == "Test Profile"

    def test_get_profile_by_name_not_found(self, app: Any) -> None:
        """Test getting non-existent profile by name returns None."""
        service = DisplayProfileService()
        
        profile = service.get_profile_by_name("Non-existent")
        
        assert profile is None

    def test_list_profiles(self, app: Any) -> None:
        """Test listing all profiles."""
        service = DisplayProfileService()
        
        # Create some profiles
        service.create_profile(name="Profile 1")
        service.create_profile(name="Profile 2")
        service.create_profile(name="Profile 3")
        
        profiles = service.list_profiles()
        
        assert len(profiles) >= 3
        profile_names = [p.name for p in profiles]
        assert "Profile 1" in profile_names
        assert "Profile 2" in profile_names
        assert "Profile 3" in profile_names

    def test_list_profiles_filter_system(self, app: Any) -> None:
        """Test listing profiles with system filter."""
        service = DisplayProfileService()
        
        # Create user and system profiles
        user_profile = DisplayProfile(name="User Profile", is_system=False)
        system_profile = DisplayProfile(name="System Profile", is_system=True)
        
        db.session.add_all([user_profile, system_profile])
        db.session.commit()
        
        # List only user profiles
        user_profiles = service.list_profiles(include_system=False)
        user_names = [p.name for p in user_profiles]
        
        assert "User Profile" in user_names
        assert "System Profile" not in user_names

    def test_update_profile(self, app: Any) -> None:
        """Test updating a profile."""
        service = DisplayProfileService()
        
        # Create a profile
        profile = service.create_profile(
            name="Original Name",
            description="Original description"
        )
        
        # Update it
        updated = service.update_profile(
            profile.id,
            name="Updated Name",
            description="Updated description"
        )
        
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"

    def test_update_profile_elements(self, app: Any) -> None:
        """Test updating profile elements."""
        service = DisplayProfileService()
        
        # Create a profile with one element
        profile = service.create_profile(
            name="Test Profile",
            elements=[
                {
                    "lift_element": "headword",
                    "css_class": "entry-headword",
                    "visibility": "visible",
                    "display_order": 1
                }
            ]
        )
        
        # Update elements
        updated = service.update_profile(
            profile.id,
            elements=[
                {
                    "lift_element": "headword",
                    "css_class": "entry-headword-updated",
                    "visibility": "visible",
                    "display_order": 1
                },
                {
                    "lift_element": "pronunciation",
                    "css_class": "entry-pronunciation",
                    "visibility": "visible",
                    "display_order": 2
                }
            ]
        )
        
        assert len(updated.elements) == 2
        assert updated.elements[0].css_class == "entry-headword-updated"
        assert updated.elements[1].lift_element == "pronunciation"

    def test_delete_profile(self, app: Any) -> None:
        """Test deleting a profile."""
        service = DisplayProfileService()
        
        # Create a profile
        profile = service.create_profile(name="To Delete")
        profile_id = profile.id
        
        # Delete it
        result = service.delete_profile(profile_id)
        
        assert result is True
        
        # Verify it's gone
        deleted = service.get_profile(profile_id)
        assert deleted is None

    def test_delete_system_profile_fails(self, app: Any) -> None:
        """Test that system profiles cannot be deleted."""
        service = DisplayProfileService()
        
        # Create a system profile
        system_profile = DisplayProfile(
            name="System Profile",
            is_system=True
        )
        db.session.add(system_profile)
        db.session.commit()
        
        # Try to delete it
        try:
            service.delete_profile(system_profile.id)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "system profile" in str(e).lower()

    def test_delete_default_profile_fails(self, app: Any) -> None:
        """Test that default profile cannot be deleted."""
        service = DisplayProfileService()
        
        # Create a default profile
        default_profile = DisplayProfile(
            name="Default Profile",
            is_default=True
        )
        db.session.add(default_profile)
        db.session.commit()
        
        # Try to delete it
        try:
            service.delete_profile(default_profile.id)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "default profile" in str(e).lower()

    def test_set_default_profile(self, app: Any) -> None:
        """Test setting a profile as default."""
        service = DisplayProfileService()
        
        # Create two profiles
        profile1 = service.create_profile(name="Profile 1")
        profile2 = service.create_profile(name="Profile 2")
        
        # Set profile1 as default
        service.set_default_profile(profile1.id)
        
        # Verify
        db.session.refresh(profile1)
        db.session.refresh(profile2)
        
        assert profile1.is_default is True
        assert profile2.is_default is False
        
        # Set profile2 as default
        service.set_default_profile(profile2.id)
        
        # Verify only profile2 is default
        db.session.refresh(profile1)
        db.session.refresh(profile2)
        
        assert profile1.is_default is False
        assert profile2.is_default is True

    def test_get_default_profile(self, app: Any) -> None:
        """Test getting the default profile."""
        service = DisplayProfileService()
        
        # Create profiles
        profile1 = service.create_profile(name="Profile 1")
        profile2 = service.create_profile(name="Profile 2")
        
        # Set profile2 as default
        service.set_default_profile(profile2.id)
        
        # Get default
        default = service.get_default_profile()
        
        assert default is not None
        assert default.id == profile2.id
        assert default.name == "Profile 2"

    def test_get_default_profile_none(self, app: Any) -> None:
        """Test getting default profile when none exists."""
        service = DisplayProfileService()
        
        # Make sure no defaults exist
        DisplayProfile.query.filter_by(is_default=True).delete()
        db.session.commit()
        
        default = service.get_default_profile()
        
        assert default is None

    def test_export_profile(self, app: Any) -> None:
        """Test exporting a profile to JSON."""
        service = DisplayProfileService()
        
        # Create a profile with elements
        profile = service.create_profile(
            name="Export Test",
            description="Test export",
            elements=[
                {
                    "lift_element": "headword",
                    "css_class": "entry-headword",
                    "visibility": "visible",
                    "display_order": 1,
                    "prefix": "",
                    "suffix": "",
                    "config": {"font-weight": "bold"}
                }
            ]
        )
        
        # Export it
        exported = service.export_profile(profile.id)
        
        assert exported["name"] == "Export Test"
        assert exported["description"] == "Test export"
        assert len(exported["elements"]) == 1
        assert exported["elements"][0]["lift_element"] == "headword"
        assert exported["elements"][0]["config"] == {"font-weight": "bold"}

    def test_import_profile(self, app: Any) -> None:
        """Test importing a profile from JSON."""
        service = DisplayProfileService()
        
        profile_data: dict[str, Any] = {
            "name": "Imported Profile",
            "description": "Test import",
            "elements": [
                {
                    "lift_element": "headword",
                    "css_class": "entry-headword",
                    "visibility": "visible",
                    "display_order": 1,
                    "prefix": "",
                    "suffix": "",
                    "config": {"font-weight": "bold"}
                },
                {
                    "lift_element": "pronunciation",
                    "css_class": "entry-pronunciation",
                    "visibility": "visible",
                    "display_order": 2,
                    "prefix": "",
                    "suffix": "",
                    "config": {}
                }
            ]
        }
        
        # Import it
        imported = service.import_profile(profile_data)
        
        assert imported.name == "Imported Profile"
        assert imported.description == "Test import"
        assert len(imported.elements) == 2
        assert imported.elements[0].lift_element == "headword"
        assert imported.elements[1].lift_element == "pronunciation"

    def test_import_profile_rename_if_exists(self, app: Any) -> None:
        """Test importing a profile renames if name exists."""
        service = DisplayProfileService()
        
        # Create existing profile
        service.create_profile(name="Test Profile")
        
        profile_data: dict[str, Any] = {
            "name": "Test Profile",
            "description": "Import test",
            "elements": []
        }
        
        # Import with same name
        imported = service.import_profile(profile_data)
        
        # Should be renamed
        assert imported.name.startswith("Test Profile")
        assert imported.name != "Test Profile"  # Should have suffix

    def test_create_from_registry_default(self, app: Any) -> None:
        """Test creating profile from registry default."""
        service = DisplayProfileService()
        
        # Create from default
        profile = service.create_from_registry_default(
            name="From Registry",
            description="Created from registry default"
        )
        
        assert profile.name == "From Registry"
        assert profile.description == "Created from registry default"
        # Should have elements from registry
        assert len(profile.elements) > 0

    def test_validate_element_config_valid(self, app: Any) -> None:
        """Test validating valid element config."""
        service = DisplayProfileService()
        
        config: dict[str, Any] = {
            "lift_element": "headword",
            "css_class": "entry-headword",
            "visibility": "visible",
            "display_order": 1
        }
        
        # Should not raise
        result = service.validate_element_config(config)
        assert result is True

    def test_validate_element_config_invalid_lift_element(self, app: Any) -> None:
        """Test validating config with invalid lift element."""
        service = DisplayProfileService()
        
        config: dict[str, Any] = {
            "lift_element": "invalid_element",
            "css_class": "entry-invalid",
            "visibility": "visible"
        }
        
        try:
            service.validate_element_config(config)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not found in registry" in str(e).lower()

    def test_validate_element_config_missing_required(self, app: Any) -> None:
        """Test validating config with missing required fields."""
        service = DisplayProfileService()
        
        config: dict[str, Any] = {
            "css_class": "entry-headword"
            # Missing lift_element
        }
        
        try:
            service.validate_element_config(config)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "lift_element" in str(e).lower()
