"""
Example model representing an example in a dictionary sense.
"""

from typing import Dict, Any, Optional, List
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
        source: Optional source reference (Day 47-48).
        note: Optional multilingual note (Day 47-48).
        traits: Dictionary of trait key-value pairs.
    """
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize an example.
        
        Args:
            id_: Unique identifier for the example.
            **kwargs: Additional attributes to set on the example.
        """
        # Initialize attributes first
        self.form: Dict[str, str] = kwargs.get('form', {})
        self.translations: Dict[str, str] = kwargs.get('translations', {})
        self.notes: Dict[str, str] = kwargs.get('notes', {})
        self.custom_fields: Dict[str, Any] = kwargs.get('custom_fields', {})
        self.traits: Dict[str, str] = kwargs.get('traits', {})
        # Day 47-48: Add source and note attributes
        self.source: Optional[str] = kwargs.get('source')
        self.note: Optional[Dict[str, str]] = kwargs.get('note')
        
        # Handle form_text convenience parameter before calling super().__init__
        if 'form_text' in kwargs and isinstance(kwargs['form_text'], str):
            # Add to form dict if it's empty
            if not self.form:
                self.form['en'] = kwargs['form_text']
        
        # Now call parent __init__ with remaining kwargs
        parent_kwargs = {k: v for k, v in kwargs.items() 
                        if k not in ['form', 'translations', 'notes', 'custom_fields', 'form_text', 'source', 'note', 'traits']}
        super().__init__(id_, **parent_kwargs)  # type: ignore
    
    @property
    def form_text(self) -> str:
        """
        Get the first available form text.
        
        Returns:
            The first form text if form is a dict, otherwise the form as string.
        """
        if not self.form:
            return ''
        if isinstance(self.form, dict):
            return next(iter(self.form.values())) if self.form else ''
        else:
            return str(self.form)
    
    @form_text.setter
    def form_text(self, value: str) -> None:
        """
        Set the form text. Updates the form dict with the provided text.
        
        Args:
            value: The form text to set.
        """
        # Set to default language 'en' if no specific language is set
        if not self.form:
            self.form['en'] = value
        else:
            # Update the first available language
            first_lang = next(iter(self.form.keys()))
            self.form[first_lang] = value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the example to a dictionary.
        
        Returns:
            Dictionary representation of the example.
        """
        result = super().to_dict()
        # Add form_text property to the dict
        result['form_text'] = self.form_text
        # Day 47-48: Add source and note if present
        if self.source:
            result['source'] = self.source
        if self.note:
            result['note'] = self.note
        return result

    def validate(self) -> bool:
        """
        Validate the example.
        
        Returns:
            True if the example is valid.
            
        Raises:
            ValidationError: If the example is invalid.
        """
        errors: list[str] = []
        
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
        form_text_value = self.form_text
        return f"Example(id={self.id}, form_text={form_text_value})"
