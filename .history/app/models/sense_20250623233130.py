"""
Sense model representing a sense in a dictionary entry.
"""

from typing import Dict, List, Any, Optional
from app.models.base import BaseModel
from app.utils.exceptions import ValidationError


class Sense(BaseModel):
    """
    Sense model representing a sense in a dictionary entry.
    
    Attributes:
        id: Unique identifier for the sense.
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
        super().__init__(id_, **kwargs)
        self.glosses: Dict[str, str] = kwargs.get('glosses', {})
        self.definitions: Dict[str, str] = kwargs.get('definitions', {})
        self.grammatical_info: Optional[str] = kwargs.get('grammatical_info')
        self.examples: List[Dict[str, Any]] = kwargs.get('examples', [])
        self.relations: List[Dict[str, Any]] = kwargs.get('relations', [])
        self.notes: Dict[str, str] = kwargs.get('notes', {})
        self.custom_fields: Dict[str, Any] = kwargs.get('custom_fields', {})
    
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
    
    def get_example_by_id(self, example_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an example by ID.
        
        Args:
            example_id: ID of the example to get.
            
        Returns:
            Example with the given ID, or None if not found.
        """
        for example in self.examples:
            if example.get('id') == example_id:
                return example
        
        return None
