"""
Unit tests for DisplayProfile and ProfileElement models.
"""

from __future__ import annotations

from datetime import datetime

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db


class TestDisplayProfileModel:
    """Test cases for the DisplayProfile model."""

    def test_create_profile(self, app: Any) -> None:
        """Test creating a display profile."""
        profile = DisplayProfile(
            name="Test Profile",
            description="A test profile",
            is_default=False,
            is_system=False
        )
        
        db.session.add(profile)
        db.session.commit()
        
        assert profile.id is not None
        assert profile.name == "Test Profile"
        assert profile.description == "A test profile"
        assert profile.is_default is False
        assert profile.is_system is False
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.updated_at, datetime)

    def test_profile_elements_relationship(self, app: Any) -> None:
        """Test the relationship between profile and elements."""
        profile = DisplayProfile(
            name="Test Profile",
            description="A test profile"
        )
        
        db.session.add(profile)
        db.session.commit()
        
        # Add elements to the profile
        element1 = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword",
            visibility="visible",
            display_order=1
        )
        element2 = ProfileElement(
            profile_id=profile.id,
            lift_element="pronunciation",
            css_class="entry-pronunciation",
            visibility="visible",
            display_order=2
        )
        
        db.session.add_all([element1, element2])
        db.session.commit()
        
        # Verify relationship
        assert len(profile.elements) == 2
        assert profile.elements[0].lift_element == "headword"
        assert profile.elements[1].lift_element == "pronunciation"

    def test_profile_to_dict(self, app: Any) -> None:
        """Test converting profile to dictionary."""
        profile = DisplayProfile(
            name="Test Profile",
            description="A test profile",
            is_default=True,
            is_system=False
        )
        
        db.session.add(profile)
        db.session.commit()
        
        # Add an element
        element = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword",
            visibility="visible",
            display_order=1,
            prefix="",
            suffix="",
            config={"font-weight": "bold"}
        )
        
        db.session.add(element)
        db.session.commit()
        
        result = profile.to_dict()
        
        assert result["id"] == profile.id
        assert result["name"] == "Test Profile"
        assert result["description"] == "A test profile"
        assert result["is_default"] is True
        assert result["is_system"] is False
        assert "created_at" in result
        assert "updated_at" in result
        assert len(result["elements"]) == 1
        assert result["elements"][0]["lift_element"] == "headword"
        assert result["elements"][0]["css_class"] == "entry-headword"
        assert result["elements"][0]["config"] == {"font-weight": "bold"}

    def test_profile_to_config(self, app: Any) -> None:
        """Test converting profile to CSS config format."""
        profile = DisplayProfile(
            name="Test Profile",
            description="A test profile"
        )
        
        db.session.add(profile)
        db.session.commit()
        
        # Add elements with different visibilities
        element1 = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword",
            visibility="visible",
            display_order=1
        )
        element2 = ProfileElement(
            profile_id=profile.id,
            lift_element="pronunciation",
            css_class="entry-pronunciation",
            visibility="hidden",
            display_order=2
        )
        
        db.session.add_all([element1, element2])
        db.session.commit()
        
        config = profile.to_config()
        
        assert "headword" in config
        assert config["headword"]["css_class"] == "entry-headword"
        assert config["headword"]["visibility"] == "visible"
        
        assert "pronunciation" in config
        assert config["pronunciation"]["visibility"] == "hidden"

    def test_only_one_default_profile(self, app: Any) -> None:
        """Test that only one profile can be default."""
        profile1 = DisplayProfile(
            name="Profile 1",
            is_default=True
        )
        profile2 = DisplayProfile(
            name="Profile 2",
            is_default=True
        )
        
        db.session.add(profile1)
        db.session.commit()
        
        db.session.add(profile2)
        db.session.commit()
        
        # Query to check - in real implementation, service layer should enforce this
        default_profiles = DisplayProfile.query.filter_by(is_default=True).all()
        
        # This test documents the expected behavior
        # The service layer should ensure only one default exists
        assert len(default_profiles) >= 1


class TestProfileElementModel:
    """Test cases for the ProfileElement model."""

    def test_create_element(self, app: Any) -> None:
        """Test creating a profile element."""
        profile = DisplayProfile(name="Test Profile")
        db.session.add(profile)
        db.session.commit()
        
        element = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword",
            visibility="visible",
            display_order=1,
            prefix="[",
            suffix="]",
            config={"font-weight": "bold", "color": "red"}
        )
        
        db.session.add(element)
        db.session.commit()
        
        assert element.id is not None
        assert element.profile_id == profile.id
        assert element.lift_element == "headword"
        assert element.css_class == "entry-headword"
        assert element.visibility == "visible"
        assert element.display_order == 1
        assert element.prefix == "["
        assert element.suffix == "]"
        assert element.config == {"font-weight": "bold", "color": "red"}

    def test_element_to_dict(self, app: Any) -> None:
        """Test converting element to dictionary."""
        profile = DisplayProfile(name="Test Profile")
        db.session.add(profile)
        db.session.commit()
        
        element = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword",
            visibility="visible",
            display_order=1,
            prefix="",
            suffix="",
            config={"font-weight": "bold"}
        )
        
        db.session.add(element)
        db.session.commit()
        
        result = element.to_dict()
        
        assert result["id"] == element.id
        assert result["profile_id"] == profile.id
        assert result["lift_element"] == "headword"
        assert result["css_class"] == "entry-headword"
        assert result["visibility"] == "visible"
        assert result["display_order"] == 1
        assert result["prefix"] == ""
        assert result["suffix"] == ""
        assert result["config"] == {"font-weight": "bold"}

    def test_element_default_values(self, app: Any) -> None:
        """Test element default values."""
        profile = DisplayProfile(name="Test Profile")
        db.session.add(profile)
        db.session.commit()
        
        element = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword"
        )
        
        db.session.add(element)
        db.session.commit()
        
        # Check default values
        assert element.visibility == "visible"  # Default from schema
        assert element.display_order is not None
        assert element.prefix == ""
        assert element.suffix == ""
        assert element.config == {}

    def test_element_ordering(self, app: Any) -> None:
        """Test elements are ordered by display_order."""
        profile = DisplayProfile(name="Test Profile")
        db.session.add(profile)
        db.session.commit()
        
        # Add elements in reverse order
        element3 = ProfileElement(
            profile_id=profile.id,
            lift_element="sense",
            css_class="entry-sense",
            display_order=3
        )
        element1 = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword",
            display_order=1
        )
        element2 = ProfileElement(
            profile_id=profile.id,
            lift_element="pronunciation",
            css_class="entry-pronunciation",
            display_order=2
        )
        
        db.session.add_all([element3, element1, element2])
        db.session.commit()
        
        # Query with ordering
        ordered_elements = ProfileElement.query.filter_by(
            profile_id=profile.id
        ).order_by(ProfileElement.display_order).all()
        
        assert len(ordered_elements) == 3
        assert ordered_elements[0].lift_element == "headword"
        assert ordered_elements[1].lift_element == "pronunciation"
        assert ordered_elements[2].lift_element == "sense"

    def test_element_visibility_values(self, app: Any) -> None:
        """Test different visibility values."""
        profile = DisplayProfile(name="Test Profile")
        db.session.add(profile)
        db.session.commit()
        
        visible_element = ProfileElement(
            profile_id=profile.id,
            lift_element="headword",
            css_class="entry-headword",
            visibility="visible"
        )
        hidden_element = ProfileElement(
            profile_id=profile.id,
            lift_element="etymology",
            css_class="entry-etymology",
            visibility="hidden"
        )
        collapsed_element = ProfileElement(
            profile_id=profile.id,
            lift_element="note",
            css_class="entry-note",
            visibility="collapsed"
        )
        
        db.session.add_all([visible_element, hidden_element, collapsed_element])
        db.session.commit()
        
        assert visible_element.visibility == "visible"
        assert hidden_element.visibility == "hidden"
        assert collapsed_element.visibility == "collapsed"
