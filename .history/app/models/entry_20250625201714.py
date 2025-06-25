"""
Entry model representing a dictionary entry in LIFT format.
"""

from typing import Dict, List, Any, Optional
from app.models.base import BaseModel
from app.utils.exceptions import ValidationError


class Entry(BaseModel):
    """
    Entry model representing a dictionary entry in LIFT format.
    
    Attributes:
        id: Unique identifier for the entry.
        lexical_unit: Dictionary mapping language codes to lexical unit forms.
        citations: List of citation forms for the entry.
        pronunciations: Dictionary mapping writing system codes to pronunciation forms.
        variant_forms: List of variant forms for the entry.
        senses: List of sense objects for the entry.
        grammatical_info: Grammatical information for the entry.
        relations: List of semantic relations to other entries.
        notes: Dictionary mapping note types to note content.
        custom_fields: Dictionary of custom fields for the entry.
    """
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize an entry.
        
        Args:
            id_: Unique identifier for the entry.
            **kwargs: Additional attributes to set on the entry.
        """
        super().__init__(id_, **kwargs)
        self.lexical_unit: Dict[str, str] = kwargs.get('lexical_unit', {})
        self.citations: List[Dict[str, Any]] = kwargs.get('citations', [])
        self.pronunciations: Dict[str, str] = kwargs.get('pronunciations', {})
        self.variant_forms: List[Dict[str, Any]] = kwargs.get('variant_forms', [])
        self.senses: List[Dict[str, Any]] = kwargs.get('senses', [])
        self.grammatical_info: Optional[str] = kwargs.get('grammatical_info')
        self.relations: List[Dict[str, Any]] = kwargs.get('relations', [])
        self.notes: Dict[str, str] = kwargs.get('notes', {})
        self.custom_fields: Dict[str, Any] = kwargs.get('custom_fields', {})
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entry':
        """
        Create an Entry instance from a dictionary, with better error handling.
        
        Args:
            data: Dictionary containing entry data.
            
        Returns:
            Entry instance.
            
        Raises:
            ValidationError: If required fields are missing or invalid.
        """
        # Make a copy to avoid modifying the original dict
        entry_data = data.copy()
        
        # Extract the ID if present
        entry_id = entry_data.pop('id', None)
        
        # Create a new entry with the ID and data
        try:
            entry = cls(id_=entry_id, **entry_data)
            return entry
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error creating Entry from dict: %s", str(e), exc_info=True)
            logger.debug("Data: %s", data)
            raise ValidationError(f"Failed to create Entry object: {str(e)}")
    
    def add_sense(self, sense: Dict[str, Any]) -> None:
        """
        Add a sense to the entry.
        
        Args:
            sense: Sense to add.
        """
        if 'id' not in sense:
            raise ValidationError("Sense must have an ID")
        
        self.senses.append(sense)
    
    def remove_sense(self, sense_id: str) -> bool:
        """
        Remove a sense from the entry.
        
        Args:
            sense_id: ID of the sense to remove.
            
        Returns:
            True if the sense was removed, False if it was not found.
        """
        for i, sense in enumerate(self.senses):
            if sense.get('id') == sense_id:
                del self.senses[i]
                return True
        
        return False
    
    def add_relation(self, relation_type: str, target_id: str) -> None:
        """
        Add a semantic relation to the entry.
        
        Args:
            relation_type: Type of relation (e.g., 'synonym', 'antonym').
            target_id: ID of the target entry.
        """
        self.relations.append({
            'type': relation_type,
            'target_id': target_id
        })
    
    def add_pronunciation(self, writing_system: str, form: str) -> None:
        """
        Add a pronunciation to the entry.
        
        Args:
            writing_system: Writing system code (e.g., 'seh-fonipa').
            form: Pronunciation form.
        """
        self.pronunciations[writing_system] = form
    
    def get_sense_by_id(self, sense_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a sense by ID.
        
        Args:
            sense_id: ID of the sense to get.
            
        Returns:
            Sense with the given ID, or None if not found.
        """
        for sense in self.senses:
            if sense.get('id') == sense_id:
                return sense
        
        return None
