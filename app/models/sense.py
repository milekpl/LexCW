"""
Sense model representing a sense in a dictionary entry.
"""

from typing import Dict, List, Any, Optional, Union
from app.models.base import BaseModel
from app.utils.exceptions import ValidationError


class Sense(BaseModel):
    """
    Sense model representing a sense in a dictionary entry.
    
    Attributes:
        id: Unique identifier for the sense.
        glosses: Dictionary mapping language codes to gloss text.
        definitions: Dictionary mapping language codes to definition text.
        grammatical_info: Grammatical information for the sense.
        examples: List of example objects for the sense.
        relations: List of semantic relations to other senses.
        notes: Dictionary mapping note types to note content.
        custom_fields: Dictionary of custom fields for the sense.
    """
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize a sense.
        
        Args:
            id_: Unique identifier for the sense.
            **kwargs: Additional attributes to set on the sense.
        """
        # Initialize attributes first before calling super().__init__
        self.glosses = kwargs.pop('glosses', {})
        self.definitions = kwargs.pop('definitions', {})
        self.grammatical_info = kwargs.pop('grammatical_info', None)
        self.examples = kwargs.pop('examples', [])
        self.relations = kwargs.pop('relations', [])
        self.notes = kwargs.pop('notes', {})
        self.custom_fields = kwargs.pop('custom_fields', {})
        
        # Handle legacy property setters
        if 'gloss' in kwargs:
            gloss_value = kwargs.pop('gloss')
            if isinstance(gloss_value, dict):
                self.glosses.update(gloss_value)
            elif isinstance(gloss_value, str):
                self.glosses['en'] = gloss_value
        
        if 'definition' in kwargs:
            def_value = kwargs.pop('definition')
            if isinstance(def_value, dict):
                self.definitions.update(def_value)
            elif isinstance(def_value, str):
                self.definitions['en'] = def_value
        
        # Now call super() with remaining kwargs
        super().__init__(id_, **kwargs)
    
    def validate(self) -> bool:
        """
        Validate the sense.
        
        Returns:
            True if the sense is valid.
            
        Raises:
            ValidationError: If the sense is invalid.
        """
        errors = []
        
        # Validate required fields
        if not self.id:
            errors.append("Sense ID is required")
        
        if errors:
            raise ValidationError("Sense validation failed", errors)
        
        return True
    
    def add_example(self, example: Dict[str, Any]) -> None:
        """
        Add an example to the sense.
        
        Args:
            example: Example to add.
        """
        self.examples.append(example)
    
    def remove_example(self, example_id: str) -> bool:
        """
        Remove an example from the sense.
        
        Args:
            example_id: ID of the example to remove.
            
        Returns:
            True if the example was removed, False if it was not found.
        """
        for i, example in enumerate(self.examples):
            if example.get('id') == example_id:
                del self.examples[i]
                return True
        
        return False
    
    def add_relation(self, relation_type: str, target_id: str) -> None:
        """
        Add a semantic relation to the sense.
        
        Args:
            relation_type: Type of relation (e.g., 'synonym', 'antonym').
            target_id: ID of the target sense.
        """
        self.relations.append({
            'type': relation_type,
            'target_id': target_id
        })
    
    def add_definition(self, language: str, text: str) -> None:
        """
        Add a definition to the sense.
        
        Args:
            language: Language code (e.g., 'en', 'pl').
            text: Definition text.
        """
        self.definitions[language] = text
    
    @property
    def definition(self) -> str:
        """
        Get the definition text for display.
        
        Returns:
            The definition text in the primary language or first available.
        """
        if 'en' in self.definitions:
            return self.definitions['en']
        elif self.definitions:
            return next(iter(self.definitions.values()))
        return ""
    
    @definition.setter
    def definition(self, value: Any) -> None:
        """
        Set the definition. Can be a string (sets 'en') or dict.
        
        Args:
            value: String or dict of definitions by language.
        """
        if isinstance(value, dict):
            self.definitions.update(value)
        elif isinstance(value, str):
            self.definitions['en'] = value
    
    @property
    def gloss(self) -> str:
        """
        Get the gloss text for display.
        
        Returns:
            The gloss text in the primary language or first available.
        """
        if 'en' in self.glosses:
            return self.glosses['en']
        elif self.glosses:
            return next(iter(self.glosses.values()))
        return ""
    
    @gloss.setter
    def gloss(self, value: Any) -> None:
        """
        Set the gloss. Can be a string (sets 'en') or dict.
        
        Args:
            value: String or dict of glosses by language.
        """
        if isinstance(value, dict):
            self.glosses.update(value)
        elif isinstance(value, str):
            self.glosses['en'] = value
    
    def get_definition(self, lang: Optional[str] = None) -> str:
        """
        Get the definition in the specified language.
        
        Args:
            lang: Language code to retrieve. If None, returns the default.
            
        Returns:
            The definition text in the specified language, or empty string if not found.
        """
        if lang:
            return self.definitions.get(lang, "")
        return self.definition
    
    def get_gloss(self, lang: Optional[str] = None) -> str:
        """
        Get the gloss in the specified language.
        
        Args:
            lang: Language code to retrieve. If None, returns the default.
            
        Returns:
            The gloss text in the specified language, or empty string if not found.
        """
        if lang:
            return self.glosses.get(lang, "")
        return self.gloss
    
    def get_available_definition_languages(self) -> List[str]:
        """
        Get a list of languages available for definitions.
        
        Returns:
            List of language codes.
        """
        return list(self.definitions.keys())
    
    def get_available_gloss_languages(self) -> List[str]:
        """
        Get a list of languages available for glosses.
        
        Returns:
            List of language codes.
        """
        return list(self.glosses.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the sense to a dictionary, including computed properties.
        
        Returns:
            Dictionary representation of the sense.
        """
        result = super().to_dict()
        
        # Add computed properties for template compatibility
        result['definition'] = self.definition
        result['gloss'] = self.gloss
        
        return result
