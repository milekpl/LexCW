"""
CSS Mapping Service for display profile management.

This is a placeholder implementation for test compatibility.
The full implementation should be completed as part of the CSS specification plan.
"""

from __future__ import annotations

import json
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.display_profile import DisplayProfile


class CSSMappingService:
    """Service for managing display profiles and rendering entries with CSS styling."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the CSS mapping service.

        Args:
            storage_path: Path to store display profiles (for testing)
        """
        self.storage_path = storage_path
        self._profiles: Dict[str, DisplayProfile] = {}
        self._logger = logging.getLogger(__name__)
        if storage_path and storage_path.exists():
            self._load_profiles()

    def create_profile(self, profile_data: Dict[str, Any]) -> DisplayProfile:
        """Create a new display profile.
        
        Args:
            profile_data: Dictionary containing profile configuration
            
        Returns:
            The created DisplayProfile instance
        """
        profile_id = str(uuid.uuid4())
        profile_data_copy = profile_data.copy()
        profile_data_copy["profile_id"] = profile_id
        
        profile = DisplayProfile(**profile_data_copy)
        self._profiles[profile_id] = profile
        self._save_profiles()
        return profile

    def get_profile(self, profile_id: str) -> Optional[DisplayProfile]:
        """Get a display profile by ID.
        
        Args:
            profile_id: The profile ID to retrieve
            
        Returns:
            The DisplayProfile instance or None if not found
        """
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[DisplayProfile]:
        """List all display profiles.
        
        Returns:
            List of all DisplayProfile instances
        """
        return list(self._profiles.values())

    def update_profile(self, profile_id: str, update_data: Dict[str, Any]) -> Optional[DisplayProfile]:
        """Update an existing display profile.
        
        Args:
            profile_id: The profile ID to update
            update_data: Dictionary containing updates
            
        Returns:
            The updated DisplayProfile instance or None if not found
        """
        if profile_id not in self._profiles:
            return None
            
        profile = self._profiles[profile_id]
        for key, value in update_data.items():
            setattr(profile, key, value)
            
        self._save_profiles()
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a display profile.
        
        Args:
            profile_id: The profile ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            self._save_profiles()
            return True
        return False

    def render_entry(self, entry_xml: str, profile: DisplayProfile) -> str:
        """Render an entry XML with the given display profile.

        Args:
            entry_xml: The LIFT entry XML to render
            profile: The display profile to use

        Returns:
            HTML representation of the entry
        """
        try:
            # Simple fallback implementation for now
            # Parse the XML to extract basic information
            import xml.etree.ElementTree as ET

            # Remove namespaces for simpler parsing
            clean_xml = self._remove_namespaces(entry_xml)

            try:
                root = ET.fromstring(clean_xml)
            except ET.ParseError as e:
                self._logger.error(f"Failed to parse entry XML: {str(e)}")
                return f'<div class="entry-render-error">Invalid XML: {str(e)}</div>'

            # Extract basic entry information
            entry_content = []

            # Try to find common LIFT elements
            elements_to_extract = ['lexical-unit', 'pronunciation', 'sense', 'definition', 'gloss']

            for element_name in elements_to_extract:
                elements = root.findall(f".//{element_name}")
                for element in elements:
                    text_content = self._extract_text_content(element)
                    if text_content:
                        entry_content.append(f'<div class="{element_name}">{text_content}</div>')

            if not entry_content:
                entry_content.append('<div class="entry-empty">No content found in entry</div>')

            # Wrap the output with profile-specific container
            return f'<div class="entry-rendered-with-{profile.profile_name}">{"".join(entry_content)}</div>'

        except Exception as e:
            self._logger.error(f"Failed to render entry: {str(e)}")
            return f'<div class="entry-render-error">Error rendering entry: {str(e)}</div>'

    def _load_profiles(self) -> None:
        """Load profiles from storage file."""
        if not self.storage_path or not self.storage_path.exists():
            return
            
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for profile_data in data:
                    profile = DisplayProfile(**profile_data)
                    if profile.profile_id:
                        self._profiles[profile.profile_id] = profile
        except (json.JSONDecodeError, KeyError):
            # If the file is corrupted, start with empty profiles
            pass

    def _save_profiles(self) -> None:
        """Save profiles to storage file."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            data = [profile.dict() for profile in self._profiles.values()]
            json.dump(data, f, indent=2)

    def _remove_namespaces(self, xml_string: str) -> str:
        """Remove namespace declarations from XML to simplify parsing."""
        import re
        # Remove namespace declarations
        clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', xml_string)
        # Remove namespace prefixes
        clean_xml = re.sub(r'<([a-z]+):', r'<\1', clean_xml)
        clean_xml = re.sub(r'</([a-z]+):', r'</\1', clean_xml)
        return clean_xml

    def _extract_text_content(self, element: Any) -> str:
        """Extract text content from a LIFT element, handling nested structures."""
        if hasattr(element, 'text') and element.text and element.text.strip():
            return element.text.strip()

        # Handle nested elements
        content_parts: List[str] = []
        if hasattr(element, '__iter__'):
            for child in element:
                child_text = self._extract_text_content(child)
                if child_text:
                    content_parts.append(child_text)

        return ' '.join(content_parts) if content_parts else ""