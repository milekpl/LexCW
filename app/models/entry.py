"""
Entry model representing a dictionary entry in LIFT format.
"""

from typing import Dict, List, Any, Optional, Union
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
        # Extract senses before calling super to avoid double processing
        senses_data = kwargs.pop('senses', [])
        
        super().__init__(id_, **kwargs)
        self.lexical_unit: Dict[str, str] = kwargs.get('lexical_unit', {})
        self.citations: List[Dict[str, Any]] = kwargs.get('citations', [])
        self.pronunciations: Dict[str, str] = kwargs.get('pronunciations', {})
        self.variant_forms: List[Dict[str, Any]] = kwargs.get('variant_forms', [])
        self.grammatical_info: Optional[str] = kwargs.get('grammatical_info')
        self.relations: List[Dict[str, Any]] = kwargs.get('relations', [])
        self.notes: Dict[str, str] = kwargs.get('notes', {})
        self.custom_fields: Dict[str, Any] = kwargs.get('custom_fields', {})
        
        # Handle senses - convert dicts to Sense objects if needed
        self.senses = []
        for sense_data in senses_data:
            if isinstance(sense_data, dict):
                # Import here to avoid circular imports
                from app.models.sense import Sense
                sense_obj = Sense(**sense_data)
                self.senses.append(sense_obj)
            else:
                # Already a Sense object
                self.senses.append(sense_data)
    
    def validate(self) -> bool:
        """
        Validate the entry.
        
        Returns:
            True if the entry is valid.
            
        Raises:
            ValidationError: If the entry is invalid.
        """
        errors = []
        
        # Validate required fields
        if not self.id:
            errors.append("Entry ID is required")
        
        if not self.lexical_unit:
            errors.append("Lexical unit is required")
        
        # Validate senses
        for i, sense in enumerate(self.senses):
            # Handle both Sense objects and dictionaries
            if hasattr(sense, 'id'):
                # Sense object
                if not sense.id:
                    errors.append(f"Sense at index {i} is missing an ID")
            elif isinstance(sense, dict):
                # Dictionary
                if 'id' not in sense:
                    errors.append(f"Sense at index {i} is missing an ID")
            else:
                errors.append(f"Sense at index {i} is not a valid Sense object or dictionary")
        
        if errors:
            raise ValidationError("Entry validation failed", errors)
        
        return True
    
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
            # Handle both Sense objects and dictionaries
            if hasattr(sense, 'id'):
                # Sense object
                if sense.id == sense_id:
                    del self.senses[i]
                    return True
            elif isinstance(sense, dict):
                # Dictionary
                if sense.get('id') == sense_id:
                    del self.senses[i]
                    return True
        
        return False
    
    @property
    def headword(self) -> str:
        """
        Get the headword (lexical unit) for display.
        
        Returns:
            The headword text in the primary language.
        """
        # Default to 'en' if available, otherwise take the first available language
        if 'en' in self.lexical_unit:
            return self.lexical_unit['en']
        elif self.lexical_unit:
            return next(iter(self.lexical_unit.values()))
        return ""
    
    def get_lexical_unit(self, lang: Optional[str] = None) -> str:
        """
        Get the lexical unit in the specified language.
        
        Args:
            lang: Language code to retrieve. If None, returns the first available.
            
        Returns:
            The lexical unit text in the specified language, or an empty string if not found.
        """
        # If a specific language is requested
        if lang:
            # Return the requested language or empty string if not found
            return self.lexical_unit.get(lang, "")
        
        # If no specific language is requested, return default
        if self.lexical_unit:
            # Default to primary language if available
            if 'en' in self.lexical_unit:
                return self.lexical_unit['en']
            # Otherwise return first available
            return next(iter(self.lexical_unit.values()))
        return ""
    
    def get_language_list(self) -> List[str]:
        """
        Get a list of languages available for this entry's lexical unit.
        
        Returns:
            List of language codes.
        """
        return list(self.lexical_unit.keys())
    
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
    
    def get_sense_by_id(self, sense_id: str) -> Optional[Any]:
        """
        Get a sense by ID.
        
        Args:
            sense_id: ID of the sense to get.
            
        Returns:
            Sense with the given ID, or None if not found.
        """
        for sense in self.senses:
            # Handle both Sense objects and dictionaries
            if hasattr(sense, 'id'):
                # Sense object
                if sense.id == sense_id:
                    return sense
            elif isinstance(sense, dict):
                # Dictionary
                if sense.get('id') == sense_id:
                    return sense
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entry to a dictionary, including computed properties.
        
        Returns:
            Dictionary representation of the entry.
        """
        result = super().to_dict()
        
        # Add computed properties
        result['headword'] = self.headword
        
        # Convert senses to dictionaries if they're Sense objects
        if 'senses' in result and result['senses']:
            converted_senses = []
            for sense in result['senses']:
                if hasattr(sense, 'to_dict'):
                    # It's a Sense object
                    converted_senses.append(sense.to_dict())
                else:
                    # It's already a dict
                    converted_senses.append(sense)
            result['senses'] = converted_senses
        
        return result
