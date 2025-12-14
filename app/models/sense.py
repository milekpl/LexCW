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
        illustrations: List of illustration dictionaries with 'href' and optional 'label' (multilingual).
    """
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize a sense.
        
        LIFT format: flat structure {lang: text} for glosses and definitions.
        
        Args:
            id_: Unique identifier for the sense.
            **kwargs: Additional attributes to set on the sense.
        """
        # Initialize attributes - LIFT FLAT FORMAT {lang: text}
        self.glosses: dict[str, str] = kwargs.pop('glosses', {})
        self.definitions: dict[str, str] = kwargs.pop('definitions', {})
        self.grammatical_info = kwargs.pop('grammatical_info', None)
        self.grammatical_traits: dict[str, str] | None = kwargs.pop('grammatical_traits', None)
        self.examples = kwargs.pop('examples', [])
        self.relations = kwargs.pop('relations', [])
        self.notes = kwargs.pop('notes', {})
        self.custom_fields = kwargs.pop('custom_fields', {})
        self.traits: dict[str, str] = kwargs.pop('traits', {})
        self.illustrations: list[dict[str, Any]] = kwargs.pop('illustrations', [])
        
        # LIFT 0.13: Literal meaning field - stores literal meaning of compounds/idioms (multitext) - Day 28
        literal_meaning_value = kwargs.pop('literal_meaning', None)
        if isinstance(literal_meaning_value, dict):
            self.literal_meaning: Optional[Dict[str, str]] = literal_meaning_value
        else:
            self.literal_meaning: Optional[Dict[str, str]] = None
        
        # LIFT-aligned fields: usage_type (list) and domain_type (single value)
        # usage_type supports multiple values and is stored as a list
        usage_type_value = kwargs.pop('usage_type', [])
        if isinstance(usage_type_value, str):
            # If it's a string, split semicolon-separated LIFT format into list
            self.usage_type: list[str] = [v.strip() for v in usage_type_value.split(';') if v.strip()]
        elif isinstance(usage_type_value, list):
            self.usage_type: list[str] = usage_type_value
        else:
            self.usage_type: list[str] = []

        # domain_type is a single optional string value (entry-level domain_type is handled on Entry)
        domain_type_value = kwargs.pop('domain_type', None)
        if isinstance(domain_type_value, str):
            self.domain_type: Optional[str] = domain_type_value.strip() if domain_type_value.strip() else None
        elif isinstance(domain_type_value, list):
            # If provided as a list (legacy or parser output), take the first non-empty value
            first = next((v for v in domain_type_value if isinstance(v, str) and v.strip()), None)
            self.domain_type: Optional[str] = first.strip() if first else None
        elif domain_type_value is None:
            self.domain_type: Optional[str] = None
        else:
            # Convert non-string values to string
            self.domain_type = str(domain_type_value) if domain_type_value else None

        # Handle gloss and definition - LIFT flat format {lang: text}
        # Only accept dict format
        if 'gloss' in kwargs:
            gloss_value = kwargs.pop('gloss')
            if not isinstance(gloss_value, dict):
                raise ValueError(f"Sense 'gloss' must be a dict in LIFT flat format {{lang: text}}, got {type(gloss_value)}")
            self.glosses = gloss_value

        if 'definition' in kwargs:
            def_value = kwargs.pop('definition')
            if not isinstance(def_value, dict):
                raise ValueError(f"Sense 'definition' must be a dict in LIFT flat format {{lang: text}}, got {type(def_value)}")
            self.definitions = def_value

        # Validate format
        if not isinstance(self.glosses, dict):
            self.glosses = {}
        if not isinstance(self.definitions, dict):
            self.definitions = {}
        if not isinstance(self.notes, dict):
            self.notes = {}
        if not isinstance(self.custom_fields, dict):
            self.custom_fields = {}

        # LIFT 0.13: Subsenses (recursive sense structure) - Day 22
        subsenses_value = kwargs.pop('subsenses', [])
        self.subsenses: List['Sense'] = []
        if isinstance(subsenses_value, list):
            for subsense_data in subsenses_value:
                if isinstance(subsense_data, Sense):
                    self.subsenses.append(subsense_data)
                elif isinstance(subsense_data, dict):
                    # Recursively create Sense objects for subsenses
                    self.subsenses.append(Sense.from_dict(subsense_data))

        # LIFT 0.13: Reversals (bilingual dictionary support) - Day 24-25
        reversals_value = kwargs.pop('reversals', [])
        self.reversals: List[Dict[str, Any]] = []
        if isinstance(reversals_value, list):
            for reversal_data in reversals_value:
                if isinstance(reversal_data, dict):
                    # Validate basic reversal structure
                    # Optional: type attribute, forms dict, optional main element, optional grammatical_info
                    self.reversals.append(reversal_data)

        # LIFT 0.13: Annotations (editorial workflow) - Day 26-27
        annotations_value = kwargs.pop('annotations', [])
        self.annotations: List[Dict[str, Any]] = []
        if isinstance(annotations_value, list):
            for annotation_data in annotations_value:
                if isinstance(annotation_data, dict):
                    # Validate annotation structure: name is required
                    self.annotations.append(annotation_data)

        # LIFT 0.13: FieldWorks Standard Custom Fields - Day 28
        # Exemplar field - stores exemplar form for the sense (multitext)
        exemplar_value = kwargs.pop('exemplar', None)
        if isinstance(exemplar_value, dict):
            self.exemplar: Optional[Dict[str, str]] = exemplar_value
        else:
            self.exemplar: Optional[Dict[str, str]] = None

        # Scientific name field - stores scientific/Latin name for biological terms (multitext)
        scientific_name_value = kwargs.pop('scientific_name', None)
        if isinstance(scientific_name_value, dict):
            self.scientific_name: Optional[Dict[str, str]] = scientific_name_value
        else:
            self.scientific_name: Optional[Dict[str, str]] = None

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
        # LIFT flat format: values are strings, not dicts
        has_nonempty_gloss = any(
            isinstance(val, str) and val.strip()
            for val in self.glosses.values()
        )
        has_nonempty_definition = any(
            isinstance(val, str) and val.strip()
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
            'ref': target_id
        })
    
    def enrich_relations_with_display_text(self, dict_service=None) -> list[dict]:
        """
        Enrich sense relations with display text from target senses.
        
        Args:
            dict_service: Dictionary service to look up target entries/senses
            
        Returns:
            List of enriched relation dictionaries with ref_display_text and ref_gloss
        """
        if not dict_service or not self.relations:
            return self.relations
            
        enriched_relations = []
        
        for relation in self.relations:
            enriched = relation.copy()
            
            try:
                # The ref format is typically: entry_id_sense_id or just sense_id
                ref = relation.get('ref', '')
                if not ref:
                    enriched_relations.append(enriched)
                    continue
                
                # Try to parse the sense ID to get entry and sense IDs
                # Format could be: "entry_id_sense_guid" or just "sense_guid"
                # We need to search for the sense across all entries
                
                # For now, try to extract entry_id from the ref
                # Common pattern: "word_sense_guid" or just "sense_guid"
                parts = ref.rsplit('_', 1)  # Split from right to get last part as sense ID
                
                # Search all entries to find the one with this sense
                all_entries, _ = dict_service.list_entries(limit=None)
                
                target_entry = None
                target_sense = None
                
                for entry in all_entries:
                    for sense in entry.senses:
                        if sense.id == ref or (hasattr(sense, 'id_') and sense.id_ == ref):
                            target_entry = entry
                            target_sense = sense
                            break
                    if target_sense:
                        break
                
                if target_entry and target_sense:
                    # Get headword from entry
                    enriched['ref_display_text'] = target_entry.get_lexical_unit()
                    
                    # Get gloss or definition from sense
                    if target_sense.glosses:
                        # Get first available gloss
                        first_gloss = next(iter(target_sense.glosses.values()), '')
                        enriched['ref_gloss'] = first_gloss
                    elif target_sense.definitions:
                        # Fallback to definition
                        first_def = next(iter(target_sense.definitions.values()), '')
                        enriched['ref_gloss'] = first_def
                        
            except Exception:
                # If resolution fails, just use the relation as-is
                pass
                
            enriched_relations.append(enriched)
            
        return enriched_relations
    
    def add_definition(self, language: str, text: str) -> None:
        """
        Add a definition to the sense in LIFT flat format.
        Args:
            language: Language code (e.g., 'en', 'pl').
            text: Definition text.
        """
        self.definitions[language] = text
    
    def add_gloss(self, language: str, text: str) -> None:
        """
        Add a gloss to the sense in LIFT flat format.
        Args:
            language: Language code (e.g., 'en', 'pl').
            text: Gloss text.
        """
        self.glosses[language] = text
    
    @property
    def definition(self) -> dict[str, str]:
        """
        Get the full multilingual definition dict for display or serialization.
        LIFT flat format: {lang: text}
        Returns:
            The full definitions dict (lang -> text).
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
    def gloss(self) -> dict[str, str]:
        """
        Get the full multilingual gloss dict for display or serialization.
        LIFT flat format: {lang: text}
        Returns:
            The full glosses dict (lang -> text).
        """
        return self.glosses

    @gloss.setter
    def gloss(self, value: dict[str, str]) -> None:
        """
        Set the full multilingual glosses dict.
        LIFT flat format: {lang: text}
        Args:
            value: Dict of glosses by language.
        """
        if isinstance(value, dict):
            self.glosses = value
    
    def get_definition(self, lang: Optional[str] = None) -> str:
        """
        Get the definition in the specified language.
        LIFT flat format: values are strings directly.
        
        Args:
            lang: Language code to retrieve. If None, returns the default.
            
        Returns:
            The definition text in the specified language, or empty string if not found.
        """
        if lang:
            return self.definitions.get(lang, '')
        # Return first available definition or call property
        if self.definitions:
            return next(iter(self.definitions.values()), '')
        return ''
    
    def get_gloss(self, lang: Optional[str] = None) -> str:
        """
        Get the gloss in the specified language.
        LIFT flat format: values are strings directly.
        
        Args:
            lang: Language code to retrieve. If None, returns the default.
            
        Returns:
            The gloss text in the specified language, or empty string if not found.
        """
        if lang:
            return self.glosses.get(lang, '')
        # Return first available gloss or call property
        if self.glosses:
            return next(iter(self.glosses.values()), '')
        return ''
    
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
        
        # Convert Example objects to dicts
        if 'examples' in result and result['examples']:
            result['examples'] = [
                ex.to_dict() if hasattr(ex, 'to_dict') else ex 
                for ex in result['examples']
            ]
        
        # Add computed properties for template compatibility
        result['definition'] = self.definition
        result['gloss'] = self.gloss
        
        # LIFT 0.13: Include subsenses (recursive)
        if hasattr(self, 'subsenses') and self.subsenses:
            result['subsenses'] = [
                subsense.to_dict() if isinstance(subsense, Sense) else subsense
                for subsense in self.subsenses
            ]
        else:
            result['subsenses'] = []
        
        # LIFT 0.13: Include reversals - Day 24-25
        if hasattr(self, 'reversals') and self.reversals:
            result['reversals'] = self.reversals
        else:
            result['reversals'] = []
        
        # LIFT 0.13: Include annotations - Day 26-27
        if hasattr(self, 'annotations') and self.annotations:
            result['annotations'] = self.annotations
        else:
            result['annotations'] = []
        
        # LIFT 0.13: FieldWorks Standard Custom Fields - Day 28
        if hasattr(self, 'exemplar') and self.exemplar:
            result['exemplar'] = self.exemplar
        else:
            result['exemplar'] = None
        
        if hasattr(self, 'scientific_name') and self.scientific_name:
            result['scientific_name'] = self.scientific_name
        else:
            result['scientific_name'] = None
        
        if hasattr(self, 'literal_meaning') and self.literal_meaning:
            result['literal_meaning'] = self.literal_meaning
        else:
            result['literal_meaning'] = None
        
        return result

    def to_display_dict(self) -> Dict[str, Any]:
        """
        Convert the sense to a dictionary for display, simplifying multilingual fields.
        LIFT flat format: values are strings directly (not nested dicts with 'text' key).
        """
        result = super().to_dict()

        # Convert Example objects to dicts
        if 'examples' in result and result['examples']:
            result['examples'] = [
                ex.to_dict() if hasattr(ex, 'to_dict') else ex 
                for ex in result['examples']
            ]

        # Simplify definition - LIFT flat format {lang: text}
        definition_text = ''
        if self.definitions:
            if 'en' in self.definitions:
                val = self.definitions['en']
                # Handle both flat (string) and nested (dict with 'text') formats for compatibility
                definition_text = val if isinstance(val, str) else val.get('text', '')
            elif self.definitions:
                first_lang = next(iter(self.definitions))
                val = self.definitions[first_lang]
                definition_text = val if isinstance(val, str) else val.get('text', '')
        result['definition'] = definition_text

        # Simplify gloss - LIFT flat format {lang: text}
        gloss_text = ''
        if self.glosses:
            if 'en' in self.glosses:
                val = self.glosses['en']
                # Handle both flat (string) and nested (dict with 'text') formats for compatibility
                gloss_text = val if isinstance(val, str) else val.get('text', '')
            elif self.glosses:
                first_lang = next(iter(self.glosses))
                val = self.glosses[first_lang]
                gloss_text = val if isinstance(val, str) else val.get('text', '')
        result['gloss'] = gloss_text

        return result
