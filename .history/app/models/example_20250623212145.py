"""
Example model representing an example in a dictionary sense.
"""

from typing import Dict, Any, Optional
from app.models.base import BaseModel
from app.utils.exceptions import ValidationError


class Example(BaseModel):
    """
    Example model representing an example in a dictionary sense.
    
    Attributes:
        id: Unique identifier for the example.
        form: Dictionary mapping language codes to example text.
        translations: Dictionary mapping language codes to translation text.
        notes: Dictionary mapping note types to note content.
        custom_fields: Dictionary of custom fields for the example.
    """
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize an example.
        
        Args:
            id_: Unique identifier for the example.
            **kwargs: Additional attributes to set on the example.
        """
        super().__init__(id_, **kwargs)
        self.form: Dict[str, str] = kwargs.get('form', {})
        self.translations: Dict[str, str] = kwargs.get('translations', {})
        self.notes: Dict[str, str] = kwargs.get('notes', {})
        self.custom_fields: Dict[str, Any] = kwargs.get('custom_fields', {})
    
    def validate(self) -> bool:
        """
        Validate the example.
        
        Returns:
            True if the example is valid.
            
        Raises:
            ValidationError: If the example is invalid.
        """
        errors = []
        
        # Validate required fields
        if not self.form:
            errors.append("Example form is required")
        
        if errors:
            raise ValidationError("Example validation failed", errors)
        
        return True
    
    def add_translation(self, language: str, text: str) -> None:
        """
        Add a translation to the example.
        
        Args:
            language: Language code (e.g., 'en', 'pl').
            text: Translation text.
        """
        self.translations[language] = text
    
    def set_form(self, language: str, text: str) -> None:
        """
        Set the form of the example in a specific language.
        
        Args:
            language: Language code (e.g., 'en', 'pl').
            text: Example text.
        """
        self.form[language] = text
