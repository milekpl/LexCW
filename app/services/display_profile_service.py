"""Display profile service for CRUD operations.

This module provides business logic for managing display profiles,
including creation, retrieval, update, and deletion operations.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.workset_models import db
from app.models.display_profile import DisplayProfile, ProfileElement
from app.services.lift_element_registry import LIFTElementRegistry


class DisplayProfileService:
    """Service for managing display profiles."""
    
    def __init__(self, registry: Optional[LIFTElementRegistry] = None):
        """Initialize the service.
        
        Args:
            registry: LIFT element registry for validation. If None, creates new instance.
        """
        self.registry = registry or LIFTElementRegistry()
    
    def create_profile(
        self,
        name: str,
        description: Optional[str] = None,
        custom_css: Optional[str] = None,
        show_subentries: bool = False,
        number_senses: bool = True,
        number_senses_if_multiple: bool = False,
        elements: Optional[List[Dict[str, Any]]] = None,
        is_default: bool = False,
        is_system: bool = False
    ) -> DisplayProfile:
        """Create a new display profile.
        
        Args:
            name: Profile name (must be unique)
            description: Optional profile description
            custom_css: Optional custom CSS styles for this profile
            show_subentries: Whether to display subentries recursively
            number_senses: Whether to auto-number senses with CSS counters
            number_senses_if_multiple: Only number senses if entry has multiple senses
            elements: List of element configurations
            is_default: Whether this is the default profile
            is_system: Whether this is a system profile (cannot be deleted)
            
        Returns:
            Created DisplayProfile instance
            
        Raises:
            ValueError: If profile with same name exists or validation fails
        """
        # Check for duplicate name
        existing = db.session.query(DisplayProfile).filter_by(name=name).first()
        if existing:
            raise ValueError(f"Profile with name '{name}' already exists")
        
        # If setting as default, unset other defaults
        if is_default:
            db.session.query(DisplayProfile).filter_by(is_default=True).update({'is_default': False})
        
        # Create profile
        profile = DisplayProfile(
            name=name,
            description=description,
            custom_css=custom_css,
            show_subentries=show_subentries,
            number_senses=number_senses,
            number_senses_if_multiple=number_senses_if_multiple,
            is_default=is_default,
            is_system=is_system
        )
        
        db.session.add(profile)
        db.session.flush()  # Get the profile ID
        
        # Add elements if provided
        if elements:
            for elem_config in elements:
                self._add_element_to_profile(profile, elem_config)
        
        db.session.commit()
        return profile
    
    def get_profile(self, profile_id: int) -> Optional[DisplayProfile]:
        """Get a profile by ID.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            DisplayProfile instance or None if not found
        """
        return db.session.query(DisplayProfile).filter_by(id=profile_id).first()
    
    def get_profile_by_name(self, name: str) -> Optional[DisplayProfile]:
        """Get a profile by name.
        
        Args:
            name: Profile name
            
        Returns:
            DisplayProfile instance or None if not found
        """
        return db.session.query(DisplayProfile).filter_by(name=name).first()
    
    def get_default_profile(self) -> Optional[DisplayProfile]:
        """Get the default display profile.
        
        Returns:
            Default DisplayProfile or None if no default set
        """
        profile = db.session.query(DisplayProfile).filter_by(is_default=True).first()
        if profile:
            # Force refresh from database to avoid stale data
            db.session.refresh(profile)
        return profile
    
    def list_profiles(
        self,
        include_system: bool = True,
        only_user_profiles: bool = False
    ) -> List[DisplayProfile]:
        """List all display profiles.
        
        Args:
            include_system: Whether to include system profiles
            only_user_profiles: If True, only return user-created profiles
            
        Returns:
            List of DisplayProfile instances
        """
        query = db.session.query(DisplayProfile)
        
        if only_user_profiles:
            query = query.filter_by(is_system=False)
        elif not include_system:
            query = query.filter_by(is_system=False)
        
        return query.order_by(DisplayProfile.name).all()
    
    def update_profile(
        self,
        profile_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_default: Optional[bool] = None,
        elements: Optional[List[Dict[str, Any]]] = None,
        custom_css: Optional[str] = None,
        show_subentries: Optional[bool] = None,
        number_senses: Optional[bool] = None,
        number_senses_if_multiple: Optional[bool] = None
    ) -> DisplayProfile:
        """Update an existing profile.
        
        Args:
            profile_id: Profile ID to update
            name: New name (must be unique)
            description: New description
            is_default: Set as default profile
            elements: New element configurations (replaces existing)
            custom_css: Custom CSS for rendering
            show_subentries: Whether to show subentries globally
            number_senses: Whether to auto-number senses with CSS
            number_senses_if_multiple: Only number senses if entry has multiple senses
            
        Returns:
            Updated DisplayProfile instance
            
        Raises:
            ValueError: If profile not found or validation fails
        """
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {profile_id} not found")
        
        if profile.is_system:
            raise ValueError("Cannot modify system profiles")
        
        # Update basic fields
        if name is not None and name != profile.name:
            # Check for duplicate name
            existing = db.session.query(DisplayProfile).filter_by(name=name).first()
            if existing and existing.id != profile_id:
                raise ValueError(f"Profile with name '{name}' already exists")
            profile.name = name
        
        if description is not None:
            profile.description = description
        
        if is_default is not None and is_default != profile.is_default:
            if is_default:
                # Unset other defaults
                db.session.query(DisplayProfile).filter(
                    DisplayProfile.id != profile_id,
                    DisplayProfile.is_default == True
                ).update({'is_default': False})
            profile.is_default = is_default
        
        # Update CSS and global settings
        if custom_css is not None:
            profile.custom_css = custom_css
        
        if show_subentries is not None:
            profile.show_subentries = show_subentries
        
        if number_senses is not None:
            profile.number_senses = number_senses
        
        if number_senses_if_multiple is not None:
            profile.number_senses_if_multiple = number_senses_if_multiple
        
        # Update elements if provided
        if elements is not None:
            # Remove existing elements
            db.session.query(ProfileElement).filter_by(profile_id=profile_id).delete()
            
            # Add new elements
            for elem_config in elements:
                self._add_element_to_profile(profile, elem_config)
        
        profile.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return profile
    
    def delete_profile(self, profile_id: int) -> None:
        """Delete a display profile.
        
        Args:
            profile_id: Profile ID to delete
            
        Raises:
            ValueError: If profile not found or is a system profile
        """
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {profile_id} not found")
        
        if profile.is_system:
            raise ValueError("Cannot delete system profiles")
        
        db.session.delete(profile)
        db.session.commit()
    
    def set_default_profile(self, profile_id: int) -> DisplayProfile:
        """Set a profile as the default.
        
        Args:
            profile_id: Profile ID to set as default
            
        Returns:
            Updated DisplayProfile instance
            
        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {profile_id} not found")
        
        # Unset other defaults
        db.session.query(DisplayProfile).filter(
            DisplayProfile.id != profile_id,
            DisplayProfile.is_default == True
        ).update({'is_default': False})
        
        profile.is_default = True
        db.session.commit()
        return profile
    
    def create_from_registry_default(
        self, 
        name: str = "Default Profile",
        description: Optional[str] = None
    ) -> DisplayProfile:
        """Create a profile from the registry's default configuration.
        
        Args:
            name: Name for the new profile
            description: Optional description for the profile
            
        Returns:
            Created DisplayProfile instance
        """
        default_elements = self.registry.create_default_profile_elements()
        
        if description is None:
            description = "Default profile created from LIFT element registry"
        
        return self.create_profile(
            name=name,
            description=description,
            elements=default_elements,
            is_default=False,
            is_system=False
        )
    
    def validate_element_config(self, config: Dict[str, Any]) -> bool:
        """Validate an element configuration.
        
        Args:
            config: Element configuration dict
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        is_valid, error_message = self.registry.validate_element_config(config)
        if not is_valid:
            raise ValueError(f"Invalid element configuration: {error_message}")
        return True
    
    def _add_element_to_profile(self, profile: DisplayProfile, config: Dict[str, Any]) -> ProfileElement:
        """Add an element to a profile.
        
        Args:
            profile: DisplayProfile instance
            config: Element configuration
            
        Returns:
            Created ProfileElement instance
        """
        # Validate configuration
        self.validate_element_config(config)
        
        element = ProfileElement(
            profile_id=profile.id,
            lift_element=config.get('lift_element') or config.get('element'),
            css_class=config.get('css_class', ''),
            visibility=config.get('visibility', 'if-content'),
            display_order=config.get('display_order') or config.get('order', 0),
            language_filter=config.get('language_filter', '*'),
            prefix=config.get('prefix'),
            suffix=config.get('suffix'),
            config=config.get('config')
        )
        
        db.session.add(element)
        return element
    
    def export_profile(self, profile_id: int) -> Dict[str, Any]:
        """Export a profile to a dictionary format.
        
        Args:
            profile_id: Profile ID to export
            
        Returns:
            Profile data as dictionary
            
        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {profile_id} not found")
        
        return profile.to_dict()
    
    def import_profile(self, data: Dict[str, Any], overwrite: bool = False) -> DisplayProfile:
        """Import a profile from dictionary data.
        
        Args:
            data: Profile data dictionary
            overwrite: If True and profile exists, update it; otherwise create new
            
        Returns:
            Created or updated DisplayProfile instance
        """
        name = data.get('name')
        if not name:
            raise ValueError("Profile name is required")
        
        existing = self.get_profile_by_name(name)
        
        if existing and not overwrite:
            raise ValueError(f"Profile with name '{name}' already exists")
        
        if existing and overwrite:
            # Update existing profile
            return self.update_profile(
                existing.id,
                description=data.get('description'),
                is_default=data.get('is_default', False),
                elements=data.get('elements', []),
                custom_css=data.get('custom_css'),
                show_subentries=data.get('show_subentries'),
                number_senses=data.get('number_senses'),
                number_senses_if_multiple=data.get('number_senses_if_multiple')
            )
        else:
            # Create new profile
            return self.create_profile(
                name=name,
                description=data.get('description'),
                elements=data.get('elements', []),
                is_default=data.get('is_default', False),
                is_system=data.get('is_system', False),
                custom_css=data.get('custom_css'),
                show_subentries=data.get('show_subentries', False),
                number_senses=data.get('number_senses', True),
                number_senses_if_multiple=data.get('number_senses_if_multiple', False)
            )
