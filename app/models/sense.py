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
        self.glosses: dict[str, dict[str, str]] = kwargs.pop('glosses', {})
        self.definitions: dict[str, dict[str, str]] = kwargs.pop('definitions', {})
        self.grammatical_info = kwargs.pop('grammatical_info', None)
        self.examples = kwargs.pop('examples', [])
        self.relations = kwargs.pop('relations', [])
        self.notes = kwargs.pop('notes', {})
        self.custom_fields = kwargs.pop('custom_fields', {})

        # Handle legacy property setters
        if 'gloss' in kwargs:
            gloss_value = kwargs.pop('gloss')
            if isinstance(gloss_value, dict):
                for lang, val in gloss_value.items():
                    if isinstance(val, dict):
                        self.glosses[lang] = val
                    else:
                        self.glosses[lang] = {"text": val}
            elif isinstance(gloss_value, str):
                self.glosses['en'] = {"text": gloss_value}

        if 'definition' in kwargs:
            def_value = kwargs.pop('definition')
            if isinstance(def_value, dict):
                for lang, val in def_value.items():
                    if isinstance(val, dict):
                        self.definitions[lang] = val
                    else:
                        self.definitions[lang] = {"text": val}
            elif isinstance(def_value, str):
                self.definitions['en'] = {"text": def_value}

        # Enforce that multilingual fields are always dicts (not strings)
        if not isinstance(self.glosses, dict):
            self.glosses = {}
        else:
            # Ensure all values are dicts with 'text' key
            for lang, val in list(self.glosses.items()):
                if not isinstance(val, dict):
                    self.glosses[lang] = {"text": val}
        if not isinstance(self.definitions, dict):
            self.definitions = {}
        else:
            for lang, val in list(self.definitions.items()):
                if not isinstance(val, dict):
                    self.definitions[lang] = {"text": val}
        if not isinstance(self.notes, dict):
            self.notes = {}
        if not isinstance(self.custom_fields, dict):
            self.custom_fields = {}

        # Now call super() with remaining kwargs
        super().__init__(id_, **kwargs)
    
    def validate(self) -> bool:
        """
        Validate the sense using the centralized validation system and enforce that at least one gloss or definition is non-empty.
        Returns:
            True if the sense is valid.
        Raises:
            ValidationError: If the sense is invalid.
        """
        from app.services.validation_engine import ValidationEngine

        # Check for at least one non-empty gloss or definition
        has_nonempty_gloss = any(
            isinstance(val, dict) and val.get("text", "").strip()
            for val in self.glosses.values()
        )
        has_nonempty_definition = any(
            isinstance(val, dict) and val.get("text", "").strip()
            for val in self.definitions.values()
        )
        if not (has_nonempty_gloss or has_nonempty_definition):
            raise ValidationError(
                "Sense must have at least one non-empty gloss or definition."
            )

        # Use centralized validation system as before
        sense_data = {
            'id': 'temp_entry_id',
            'lexical_unit': {'en': 'temp'},
            'senses': [self.to_dict()]
        }
        engine = ValidationEngine()
        result = engine.validate_entry(sense_data)

        # Collect all relevant errors (sense-specific and any that could apply to this sense)
        sense_errors = []
        for error in result.errors:
            if (
                'sense' in error.rule_id.lower() or
                'senses[0]' in error.message or
                'Sense at index 0' in error.message or
                error.rule_id.startswith('R2.')
            ):
                sense_errors.append(error.message)

        sense_dict = self.to_dict()
        if not sense_dict.get('id') or (isinstance(sense_dict['id'], str) and not sense_dict['id'].strip()):
            sense_errors.append("Sense ID is required and must be non-empty")

        if sense_errors:
            raise ValidationError("Sense validation failed", sense_errors)

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
        self.definitions[language] = {"text": text}
    
    @property
    def definition(self) -> dict[str, dict[str, str]]:
        """
        Get the full multilingual definition dict for display or serialization.
        Returns:
            The full definitions dict (lang -> {text: ...}).
        """
        return self.definitions

    @definition.setter
    def definition(self, value: dict[str, dict[str, str]]) -> None:
        """
        Set the full multilingual definitions dict.
        Args:
            value: Dict of definitions by language.
        """
        if isinstance(value, dict):
            self.definitions = value
    
    @property
    def gloss(self) -> dict[str, dict[str, str]]:
        """
        Get the full multilingual gloss dict for display or serialization.
        Returns:
            The full glosses dict (lang -> {text: ...}).
        """
        return self.glosses

    @gloss.setter
    def gloss(self, value: dict[str, dict[str, str]]) -> None:
        """
        Set the full multilingual glosses dict.
        Args:
            value: Dict of glosses by language.
        """
        if isinstance(value, dict):
            self.glosses = value
    
    def get_definition(self, lang: Optional[str] = None) -> str:
        """
        Get the definition in the specified language.
        
        Args:
            lang: Language code to retrieve. If None, returns the default.
            
        Returns:
            The definition text in the specified language, or empty string if not found.
        """
        if lang:
            val = self.definitions.get(lang)
            if isinstance(val, dict):
                return val.get("text", "")
            elif isinstance(val, str):
                return val
            return ""
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
            val = self.glosses.get(lang)
            if isinstance(val, dict):
                return val.get("text", "")
            elif isinstance(val, str):
                return val
            return ""
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
