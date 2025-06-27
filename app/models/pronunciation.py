"""
Pronunciation model representing a pronunciation in a dictionary entry.
"""

from typing import Dict, Any, Optional
from app.models.base import BaseModel
from app.utils.exceptions import ValidationError


class Pronunciation(BaseModel):
    """
    Pronunciation model representing a pronunciation in a dictionary entry.
    
    Attributes:
        id: Unique identifier for the pronunciation.
        form: Dictionary mapping writing system codes to pronunciation forms.
        audio_path: Path to the audio file.
        dialect: Dialect of the pronunciation (e.g., 'US', 'UK').
        notes: Dictionary mapping note types to note content.
        custom_fields: Dictionary of custom fields for the pronunciation.
    """
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize a pronunciation.
        
        Args:
            id_: Unique identifier for the pronunciation.
            **kwargs: Additional attributes to set on the pronunciation.
        """
        super().__init__(id_, **kwargs)
        self.form: Dict[str, str] = kwargs.get('form', {})
        self.audio_path: Optional[str] = kwargs.get('audio_path')
        self.dialect: Optional[str] = kwargs.get('dialect')
        self.notes: Dict[str, str] = kwargs.get('notes', {})
        self.custom_fields: Dict[str, Any] = kwargs.get('custom_fields', {})
    
    def validate(self) -> bool:
        """
        Validate the pronunciation.
        
        Returns:
            True if the pronunciation is valid.
            
        Raises:
            ValidationError: If the pronunciation is invalid.
        """
        errors = []
        
        # Validate required fields
        if not self.form:
            errors.append("Pronunciation form is required")
        
        if errors:
            raise ValidationError("Pronunciation validation failed", errors)
        
        return True
    
    def set_form(self, writing_system: str, form: str) -> None:
        """
        Set the form of the pronunciation in a specific writing system.
        
        Args:
            writing_system: Writing system code (e.g., 'seh-fonipa').
            form: Pronunciation form.
        """
        self.form[writing_system] = form
    
    def set_audio_path(self, audio_path: str) -> None:
        """
        Set the path to the audio file.
        
        Args:
            audio_path: Path to the audio file.
        """
        self.audio_path = audio_path

    def __str__(self) -> str:
        """Return string representation of the pronunciation."""
        form_text = getattr(self, 'form', '') or ''
        if isinstance(form_text, dict):
            # Get first available form
            form_text = next(iter(form_text.values())) if form_text else ''
        return f"Pronunciation(id={self.id}, form={form_text})"
