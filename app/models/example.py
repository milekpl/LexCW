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
        
        # Handle form_text convenience parameter
        if 'form_text' in kwargs and isinstance(kwargs['form_text'], str):
            # Add to form dict if it's empty
            if not self.form:
                self.form['en'] = kwargs['form_text']
    
    @property
    def form_text(self) -> str:
        """
        Get the first available form text.
        
        Returns:
            The first form text if form is a dict, otherwise the form as string.
        """
        if isinstance(self.form, dict):
            return next(iter(self.form.values())) if self.form else ''
        return str(self.form) if self.form else ''

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

    def __str__(self) -> str:
        """Return string representation of the example."""
        form_text = getattr(self, 'form_text', '') or getattr(self, 'form', '')
        if isinstance(form_text, dict):
            # Get first available form  
            form_text = next(iter(form_text.values())) if form_text else ''
        return f"Example(id={self.id}, form_text={form_text})"
