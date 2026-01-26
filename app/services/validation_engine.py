"""
Centralized validation engine for the Lexicographic Curation Workbench.

This module implements the core validation engine that replaces scattered 
validation logic with a declarative, rule-based system using Schematron 
for XML and Jsontron-inspired validation for JSON.

Following TDD approach and project specification requirements.
"""

from __future__ import annotations

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum

import jsonpath_ng
import jsonschema
from flasgger import swag_from


class ValidationPriority(Enum):
    """Validation rule priority levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFORMATIONAL = "informational"


class ValidationCategory(Enum):
    """Validation rule categories."""
    ENTRY_LEVEL = "entry_level"
    SENSE_LEVEL = "sense_level"
    NOTE_VALIDATION = "note_validation"
    PRONUNCIATION = "pronunciation"
    RESOURCE_VALIDATION = "resource_validation"
    LANGUAGE_VALIDATION = "language_validation"
    DATE_VALIDATION = "date_validation"
    RELATION_VALIDATION = "relation_validation"
    HIERARCHICAL_VALIDATION = "hierarchical_validation"
    GENERAL = "general"
    SPELLING = "spelling"


@dataclass
class ValidationError:
    """Represents a validation error."""
    rule_id: str
    rule_name: str
    message: str
    path: str
    priority: ValidationPriority
    category: ValidationCategory
    value: Optional[Any] = None


@dataclass
class ValidationResult:
    """Represents the result of validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    info: List[ValidationError]
    
    @property
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return len(self.errors) > 0
    
    @property
    def error_count(self) -> int:
        """Total count of all validation issues."""
        return len(self.errors) + len(self.warnings) + len(self.info)


class ValidationEngine:
    # Cache for compiled JSONPath expressions
    _jsonpath_cache: dict[str, Any] = {}
    """
    Core validation engine implementing centralized validation rules.

    This engine loads validation rules from configuration and applies them
    to JSON data from entry forms, replacing scattered model validation.

    Supports project-specific rules that override or extend the default rules.
    """

    # Class-level cache for rules and custom functions
    _rules_cache: dict[str, dict[str, Any]] = {}
    _custom_functions_cache: dict[str, Any] = {}
    _rules_file_loaded: Optional[str] = None
    # Project-specific rules cache: {project_id: {rule_id: rule_config}}
    _project_rules_cache: dict[str, dict[str, Dict[str, Any]]] = {}

    def __init__(
        self,
        rules_file: Optional[str] = None,
        project_config: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        project_rules: Optional[Dict[str, Dict[str, Any]]] = None,
        existing_entry_ids: Optional[Set[str]] = None
    ):
        """
        Initialize the validation engine.

        Args:
            rules_file: Path to validation rules JSON file
            project_config: Optional project configuration with source/target languages
            project_id: Optional project identifier for loading project-specific rules
            project_rules: Optional pre-loaded project-specific rules dict
            existing_entry_ids: Optional set of existing entry IDs for relation target validation
        """
        self.rules_file = rules_file or "validation_rules.json"
        self.project_config = project_config or {}
        self.project_id = project_id

        # Store existing entry IDs for relation target validation
        self._existing_entry_ids = existing_entry_ids

        # Always reload rules to ensure validation_mode changes are picked up
        self._load_rules(project_rules=project_rules)
        ValidationEngine._rules_file_loaded = self.rules_file
        self.rules: Dict[str, Dict[str, Any]] = ValidationEngine._rules_cache
        self.custom_functions: Dict[str, Any] = ValidationEngine._custom_functions_cache

    def _load_rules(
        self,
        rules_file: Optional[str] = None,
        project_rules: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> None:
        """Load validation rules from configuration file or project-specific rules.

        If project_rules is provided, use those rules instead of loading from file.
        If project_id was set, try to load from project rules cache or database.
        """
        # Priority order:
        # 1. Explicitly passed project_rules
        # 2. Project rules from cache (if project_id set)
        # 3. Load from database if project_id available
        # 4. Fall back to default rules from file

        if project_rules:
            # Use explicitly provided project rules
            self._compile_and_cache_rules(project_rules)
            ValidationEngine._rules_cache = project_rules
            return

        # Try to load project-specific rules from database
        if self.project_id:
            db_rules = self._load_project_rules_from_db()
            if db_rules:
                self._compile_and_cache_rules(db_rules)
                ValidationEngine._rules_cache = db_rules
                ValidationEngine._project_rules_cache[self.project_id] = db_rules
                return

        # Load default rules from file
        try:
            rules_path = Path(self.rules_file if rules_file else self.rules_file)
            if not rules_path.is_absolute():
                # Look for rules file relative to this module
                base_path = Path(__file__).parent.parent.parent
                # Also check for validation_rules_v2.json
                v2_path = base_path / "validation_rules_v2.json"
                if v2_path.exists():
                    rules_path = v2_path
                else:
                    rules_path = base_path / self.rules_file

            with open(rules_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                rules = config.get('rules', {})
                custom_functions = config.get('custom_functions', {})

                # Compile regex patterns
                for rule_id, rule_config in rules.items():
                    validation = rule_config.get('validation', {})
                    pattern = validation.get('pattern')
                    if pattern:
                        try:
                            validation['compiled_pattern'] = re.compile(pattern)
                        except re.error as e:
                            raise ValueError(f"Invalid regex '{pattern}' in rule {rule_id}: {e}")

                    not_pattern = validation.get('not_pattern')
                    if not_pattern:
                        try:
                            validation['compiled_not_pattern'] = re.compile(not_pattern)
                        except re.error as e:
                            raise ValueError(f"Invalid regex '{not_pattern}' in rule {rule_id}: {e}")

                ValidationEngine._rules_cache = rules
                ValidationEngine._custom_functions_cache = custom_functions
        except FileNotFoundError:
            raise FileNotFoundError(f"Validation rules file not found: {self.rules_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in validation rules file: {e}")

    def _load_project_rules_from_db(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Load project-specific rules from database.

        Returns:
            Dictionary of rule_id -> rule_config, or None if no project rules exist
        """
        if not self.project_id:
            return None

        # Check cache first
        if self.project_id in ValidationEngine._project_rules_cache:
            return ValidationEngine._project_rules_cache[self.project_id]

        # Try to load from database
        try:
            from app.models.workset_models import db
            from app.models.validation_models import ProjectValidationRule

            # Use current_app for proper Flask context
            from flask import current_app

            with current_app.app_context():
                rules = ProjectValidationRule.get_rules_for_project(self.project_id)
                if not rules:
                    return None

                # Convert list of rules to dict keyed by rule_id
                rules_dict: Dict[str, Dict[str, Any]] = {}
                for rule in rules:
                    rule_id = rule.get('rule_id')
                    if rule_id:
                        rules_dict[rule_id] = rule

                return rules_dict if rules_dict else None

        except Exception as e:
            # Log but don't fail - use default rules
            import logging
            logging.getLogger(__name__).warning(
                f"Could not load project rules for {self.project_id}: {e}"
            )
            return None

    def _compile_and_cache_rules(self, rules: Dict[str, Dict[str, Any]]) -> None:
        """Compile regex patterns and cache rules.

        Args:
            rules: Dictionary of rule_id -> rule_config
        """
        for rule_id, rule_config in rules.items():
            validation = rule_config.get('validation', {})

            # Skip if already compiled
            if 'compiled_pattern' in validation:
                continue

            pattern = validation.get('pattern')
            if pattern:
                try:
                    validation['compiled_pattern'] = re.compile(pattern)
                except re.error as e:
                    raise ValueError(f"Invalid regex '{pattern}' in rule {rule_id}: {e}")

            not_pattern = validation.get('not_pattern')
            if not_pattern:
                try:
                    validation['compiled_not_pattern'] = re.compile(not_pattern)
                except re.error as e:
                    raise ValueError(f"Invalid regex '{not_pattern}' in rule {rule_id}: {e}")

    @classmethod
    def clear_project_cache(cls, project_id: Optional[str] = None) -> None:
        """Clear the project rules cache.

        Args:
            project_id: Optional specific project to clear, or None to clear all
        """
        if project_id:
            cls._project_rules_cache.pop(project_id, None)
        else:
            cls._project_rules_cache.clear()

    @classmethod
    def set_project_rules(cls, project_id: str, rules: Dict[str, Dict[str, Any]]) -> None:
        """Set project-specific rules directly (bypassing database).

        Useful for testing or when rules are already loaded.

        Args:
            project_id: The project identifier
            rules: Dictionary of rule_id -> rule_config
        """
        cls._project_rules_cache[project_id] = rules

    def validate_json(self, data: Dict[str, Any], validation_mode: str = "save") -> ValidationResult:
        """
        Validate JSON data against all applicable rules.
        
        Args:
            data: Dictionary representing entry data from form
            validation_mode: Validation mode - "save", "delete", "draft", or "all"
            
        Returns:
            ValidationResult containing all validation issues
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        info: List[ValidationError] = []
        
        for rule_id, rule_config in self.rules.items():
            # Skip server-side only rules if this is client-side validation
            if not rule_config.get('client_side', True):
                continue
                
            # Check validation mode restrictions
            rule_mode = rule_config.get('validation_mode', 'all')
            if rule_mode == 'save_only' and validation_mode in ['delete', 'draft']:
                continue
            elif rule_mode == 'delete_only' and validation_mode != 'delete':
                continue
            elif rule_mode == 'draft_only' and validation_mode not in ['draft', 'all']:
                continue
                
            validation_errors = self._apply_rule(rule_id, rule_config, data)
            
            # Categorize errors by priority
            for error in validation_errors:
                if error.priority == ValidationPriority.CRITICAL:
                    errors.append(error)
                elif error.priority == ValidationPriority.WARNING:
                    warnings.append(error)
                else:
                    info.append(error)
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, info)
    
    def _apply_rule(self, rule_id: str, rule_config: Dict[str, Any], data: Dict[str, Any]) -> List[ValidationError]:
        """Apply a single validation rule to the data."""
        errors: List[ValidationError] = []
        
        try:
            path = rule_config['path']
            condition = rule_config['condition']
            validation = rule_config['validation']
            # Use cached compiled JSONPath if available
            if path in ValidationEngine._jsonpath_cache:
                jsonpath_expr = ValidationEngine._jsonpath_cache[path]
            else:
                jsonpath_expr = jsonpath_ng.parse(path)
                ValidationEngine._jsonpath_cache[path] = jsonpath_expr
            matches = jsonpath_expr.find(data)
            
            # Extract condition type - it can be either a string or a dict with 'type' key
            condition_type = condition if isinstance(condition, str) else condition.get('type')

            # Handle different condition types
            if condition_type == "required":
                # For array element paths like $.senses[*].id, only validate if elements exist
                # Don't require the elements themselves to exist
                if '[*]' in path:
                    # This is an array element path - only validate existing elements
                    # Check if this is a custom validation function
                    if validation.get('type') == 'custom' and validation.get('custom_function'):
                        custom_errors = self._apply_custom_validation(rule_id, rule_config, data, matches)
                        errors.extend(custom_errors)
                    else:
                        for match in matches:
                            if not self._validate_value(match.value, validation):
                                errors.append(self._create_error(rule_id, rule_config, str(match.full_path), match.value))
                else:
                    # This is a direct field path - require it to exist
                    if not matches:
                        errors.append(self._create_error(rule_id, rule_config, path, None))
                    else:
                        # Validate each match
                        for match in matches:
                            if not self._validate_value(match.value, validation):
                                errors.append(self._create_error(rule_id, rule_config, str(match.full_path), match.value))
            
            elif condition_type == "if_present":
                # Only validate if the field is present
                # Check if this is a custom validation function
                if validation.get('type') == 'custom' and validation.get('custom_function'):
                    custom_errors = self._apply_custom_validation(rule_id, rule_config, data, matches)
                    errors.extend(custom_errors)
                else:
                    # Standard validation
                    for match in matches:
                        if match.value is not None and not self._validate_value(match.value, validation):
                            errors.append(self._create_error(rule_id, rule_config, str(match.full_path), match.value))
            
            elif condition_type == "custom":
                # Handle custom validation functions
                custom_errors = self._apply_custom_validation(rule_id, rule_config, data, matches)
                errors.extend(custom_errors)

            elif condition_type == "conditional":
                # Handle conditional validation - only apply if condition is met
                when_clause = condition.get('when')
                if when_clause:
                    # Evaluate the condition
                    condition_met = self._evaluate_condition(when_clause, data)
                    if condition_met:
                        # Condition is met, apply the validation
                        if not matches:
                            # Field is missing but condition requires it - error
                            errors.append(self._create_error(rule_id, rule_config, path, None))
                        else:
                            # Field exists, validate each match
                            for match in matches:
                                if not self._validate_value(match.value, validation):
                                    errors.append(self._create_error(rule_id, rule_config, str(match.full_path), match.value))
                    # If condition not met, skip validation (this is the conditional behavior)
                else:
                    # No when clause, treat as optional validation
                    pass
                
        except Exception as e:
            # Log validation rule application error
            errors.append(ValidationError(
                rule_id=rule_id,
                rule_name=rule_config.get('name', 'unknown'),
                message=f"Error applying validation rule: {str(e)}",
                path="",
                priority=ValidationPriority.CRITICAL,
                category=ValidationCategory.ENTRY_LEVEL
            ))
        
        return errors
    
    def validate_entry(self, entry_data: Union[Dict[str, Any], Any], validation_mode: str = "save") -> ValidationResult:
        """
        Validate an entry object or dictionary against all validation rules.
        
        This is the main integration point for model validation.
        
        Args:
            entry_data: Entry object or dictionary to validate
            validation_mode: Validation mode - "save", "delete", "draft", or "all"
            
        Returns:
            ValidationResult containing all validation issues
        """
        # Convert entry object to dictionary if needed
        if isinstance(entry_data, dict):
            data = entry_data
        elif hasattr(entry_data, 'to_dict') and callable(getattr(entry_data, 'to_dict')):
            data = entry_data.to_dict()
        elif hasattr(entry_data, '__dict__'):
            data = self._convert_object_to_dict(entry_data)
        else:
            # Try to treat as dict-like
            try:
                data = dict(entry_data)
            except (TypeError, ValueError):
                raise ValueError(f"Cannot convert entry data to dictionary: {type(entry_data)}")
            
        return self.validate_json(data, validation_mode)
    
    def validate_xml(self, xml_string: str, validation_mode: str = "save") -> ValidationResult:
        """
        Validate LIFT XML entry against all validation rules.
        
        This method parses LIFT XML into an Entry object, converts it to a dictionary,
        and validates using the same rules as validate_json().
        
        Args:
            xml_string: LIFT XML string for a single entry
            validation_mode: Validation mode - "save", "delete", "draft", or "all"
            
        Returns:
            ValidationResult containing all validation issues
            
        Raises:
            ValueError: If XML parsing fails or XML is invalid
        """
        try:
            from app.parsers.lift_parser import LIFTParser
            
            # Parse LIFT XML to Entry object
            parser = LIFTParser(validate=False)  # Don't validate during parsing
            entries = parser.parse_string(xml_string)
            if not entries:
                raise ValueError("No entries found in XML")
            entry = entries[0]
            
            # Convert Entry to dictionary
            entry_dict = entry.to_dict()
            
            # Validate using existing JSON validation
            return self.validate_json(entry_dict, validation_mode)
            
        except ImportError as e:
            # LIFTParser not available
            return ValidationResult(False, [
                ValidationError(
                    rule_id="XML_PARSER_ERROR",
                    rule_name="xml_parsing",
                    message=f"XML parser not available: {str(e)}",
                    path="",
                    priority=ValidationPriority.CRITICAL,
                    category=ValidationCategory.ENTRY_LEVEL
                )
            ], [], [])
        except Exception as e:
            # XML parsing or conversion failed
            return ValidationResult(False, [
                ValidationError(
                    rule_id="XML_PARSING_ERROR",
                    rule_name="xml_parsing",
                    message=f"Failed to parse XML: {str(e)}",
                    path="",
                    priority=ValidationPriority.CRITICAL,
                    category=ValidationCategory.ENTRY_LEVEL
                )
            ], [], [])
    
    def _convert_object_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert an entry object to a dictionary for validation."""
        result: Dict[str, Any] = {}
        
        # Basic attributes
        for attr in ['id', 'guid', 'lexical_unit', 'senses', 'notes', 
                     'pronunciations', 'variants', 'relations', 'date_created', 
                     'date_modified']:
            if hasattr(obj, attr):
                value = getattr(obj, attr)
                if value is not None:
                    result[attr] = value
        
        # Convert sense objects to dictionaries
        if 'senses' in result and result['senses']:
            converted_senses: List[Dict[str, Any]] = []
            for sense in result['senses']:
                if hasattr(sense, 'to_dict') and callable(getattr(sense, 'to_dict')):
                    converted_senses.append(sense.to_dict())
                elif hasattr(sense, '__dict__'):
                    sense_dict: Dict[str, Any] = {}
                    for sense_attr in ['id', 'definition', 'gloss', 'examples', 
                                     'grammatical_info', 'subsenses', 'variants']:
                        if hasattr(sense, sense_attr):
                            sense_value = getattr(sense, sense_attr)
                            if sense_value is not None:
                                sense_dict[sense_attr] = sense_value
                    converted_senses.append(sense_dict)
                elif isinstance(sense, dict):
                    converted_senses.append(sense)
                else:
                    # Try to convert to dict
                    try:
                        converted_senses.append(dict(sense))
                    except (TypeError, ValueError):
                        # Skip invalid sense
                        continue
            result['senses'] = converted_senses
        
        return result
    
    def _validate_value(self, value: Any, validation: Dict[str, Any]) -> bool:
        """Validate a single value against validation rules."""
        val_type = validation.get('type')
        
        if val_type == 'string':
            if not isinstance(value, str):
                return False
            
            # Check minimum length
            min_length = validation.get('minLength')
            if min_length is not None and len(value) < min_length:
                return False
                
            # Check maximum length
            max_length = validation.get('maxLength')
            if max_length is not None and len(value) > max_length:
                return False
                
            # Check pattern
            # Use precompiled regex
            pattern = validation.get('compiled_pattern')
            if pattern and not pattern.match(value):
                return False
                
            # Check not_pattern (validation fails if pattern is found)
            not_pattern = validation.get('compiled_not_pattern')
            if not_pattern and not_pattern.search(value):
                return False
                        
        elif val_type == 'array':
            if not isinstance(value, list):
                return False
                
            # Check minimum items
            min_items = validation.get('minItems')
            if min_items is not None and len(value) < min_items:
                return False
                
            # Check maximum items
            max_items = validation.get('maxItems')
            if max_items is not None and len(value) > max_items:
                return False
                
        elif val_type == 'object':
            if not isinstance(value, dict):
                return False
                
            # Check minimum properties
            min_properties = validation.get('minProperties')
            if min_properties is not None and len(value) < min_properties:
                return False
                
            # Check maximum properties
            max_properties = validation.get('maxProperties')
            if max_properties is not None and len(value) > max_properties:
                return False
                
        elif val_type == 'number':
            if not isinstance(value, (int, float)):
                return False
                
            # Check minimum value
            minimum = validation.get('minimum')
            if minimum is not None and value < minimum:
                return False
                
            # Check maximum value
            maximum = validation.get('maximum')
            if maximum is not None and value > maximum:
                return False
                
        elif val_type == 'boolean':
            if not isinstance(value, bool):
                return False

        elif val_type == 'hunspell':
            # Hunspell spelling validation
            lang_code = validation.get('lang_code', 'en_US')
            min_word_length = validation.get('minWordLength', 3)
            ignore_words = validation.get('ignoreWords', [])

            # Extract words from value
            import re
            words = re.findall(r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b", str(value))

            for word in words:
                if len(word) < min_word_length:
                    continue
                if word.lower() in [w.lower() for w in ignore_words]:
                    continue

                # Check spelling using hunspell
                from app.services.dictionary_loader import get_dictionary_loader
                loader = get_dictionary_loader()
                hunspell = loader.load_system_dictionary(lang_code)

                if hunspell and not hunspell.spell(word):
                    return False  # Misspelling found

        return True

    def _evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate a conditional clause.

        Args:
            condition: Condition dict with 'not' and/or 'path' and 'contains' keys
            data: The data to evaluate against

        Returns:
            True if condition is met, False otherwise
        """
        try:
            # Handle negation
            is_negated = 'not' in condition

            # Get the condition to evaluate
            eval_condition = condition.get('not', condition)

            # Get the path to check
            path = eval_condition.get('path')
            if not path:
                return True  # No path to check, condition passes

            # Parse and evaluate the JSONPath
            if path in ValidationEngine._jsonpath_cache:
                jsonpath_expr = ValidationEngine._jsonpath_cache[path]
            else:
                jsonpath_expr = jsonpath_ng.parse(path)
                ValidationEngine._jsonpath_cache[path] = jsonpath_expr

            matches = jsonpath_expr.find(data)

            # Check for 'contains' clause
            contains = eval_condition.get('contains')
            if contains:
                # Check if any match contains the specified field/value
                field = contains.get('field')
                value = contains.get('value')
                result = False  # Initialize result

                for match in matches:
                    if isinstance(match.value, dict):
                        if field in match.value:
                            actual_value = match.value[field]
                            # If value is not specified, just check field existence
                            if value is None:
                                result = True
                                break
                            elif isinstance(actual_value, list):
                                if value in actual_value:
                                    result = True
                                    break
                            elif actual_value == value:
                                result = True
                                break
            else:
                # No contains clause - check if path exists
                result = len(matches) > 0

            # Apply negation if needed
            if is_negated:
                result = not result

            return result

        except Exception as e:
            # On error, be conservative - don't apply validation
            self.logger.warning(f"Error evaluating condition: {e}")
            return False

    def _apply_custom_validation(self, rule_id: str, rule_config: Dict[str, Any], 
                                data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """Apply custom validation functions."""
        errors: List[ValidationError] = []
        custom_function = rule_config['validation'].get('custom_function')
        
        if custom_function == 'validate_sense_content_or_variant':
            errors.extend(self._validate_sense_content_or_variant(rule_id, rule_config, data))
        elif custom_function == 'validate_sense_required_non_variant':
            errors.extend(self._validate_sense_required_non_variant(rule_id, rule_config, data))
        elif custom_function == 'validate_unique_note_types':
            errors.extend(self._validate_unique_note_types(rule_id, rule_config, data))
        elif custom_function == 'validate_note_content':
            errors.extend(self._validate_note_content(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_synonym_antonym_exclusion':
            errors.extend(self._validate_synonym_antonym_exclusion(rule_id, rule_config, data))
        elif custom_function == 'validate_subsense_depth':
            errors.extend(self._validate_subsense_depth(rule_id, rule_config, data))
        elif custom_function == 'validate_unique_languages_in_multitext':
            errors.extend(self._validate_unique_languages_in_multitext(rule_id, rule_config, data))
        elif custom_function == 'validate_language_codes':
            errors.extend(self._validate_language_codes(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_language_code_format':
            errors.extend(self._validate_language_code_format(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_pronunciation_language_codes':
            errors.extend(self._validate_pronunciation_language_codes(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_date_fields':
            errors.extend(self._validate_date_fields(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_definition_content_source_lang_exception':
            errors.extend(self._validate_definition_content_source_lang_exception(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_multilingual_note_structure':
            errors.extend(self._validate_multilingual_note_structure(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_pos_consistency':
            errors.extend(self._validate_pos_consistency(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_conflicting_pos':
            errors.extend(self._validate_conflicting_pos(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_no_circular_components':
            errors.extend(self._validate_no_circular_components(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_no_circular_sense_relations':
            errors.extend(self._validate_no_circular_sense_relations(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_no_circular_entry_relations':
            errors.extend(self._validate_no_circular_entry_relations(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_relation_targets_exist':
            errors.extend(self._validate_relation_targets_exist(rule_id, rule_config, data))
        elif custom_function == 'validate_ipa_characters':
            errors.extend(self._validate_ipa_characters(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_no_double_stress':
            errors.extend(self._validate_no_double_stress(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_no_double_length':
            errors.extend(self._validate_no_double_length(rule_id, rule_config, data, matches))
        elif custom_function == 'validate_hunspell_spelling':
            errors.extend(self._validate_hunspell_spelling(rule_id, rule_config, data, matches))

        return errors
    
    def _validate_sense_content_or_variant(self, rule_id: str, rule_config: Dict[str, Any], 
                                         data: Dict[str, Any]) -> List[ValidationError]:
        """R2.1.2: Validate that sense has definition, gloss, or variant reference."""
        errors: List[ValidationError] = []
        
        # Check if this entry is a variant form (has _component-lexeme relation)
        relations = data.get('relations', [])
        is_variant_entry = any(
            rel.get('type') == '_component-lexeme' 
            for rel in relations
        )
        
        # If this is a variant entry, it doesn't need sense definitions/glosses
        if is_variant_entry:
            return errors
        
        senses = data.get('senses', [])
        for i, sense in enumerate(senses):
            # Handle both string and multilingual dictionary formats
            definition = sense.get('definition', '')
            if isinstance(definition, dict):
                # IMPORTANT: Source language definitions are COMPLETELY OPTIONAL!
                # Check if there's ANY language with content (source or target)
                has_definition = any(
                    bool(str(v).strip()) if isinstance(v, str) else bool(v.get('text', '').strip() if isinstance(v, dict) else str(v).strip())
                    for k, v in definition.items() 
                    if k != 'lang' and v
                )
            else:
                # String format - validate normally
                has_definition = bool(str(definition).strip()) if definition else False
                
            gloss = sense.get('gloss', '')
            if isinstance(gloss, dict):
                # IMPORTANT: Source language glosses are COMPLETELY OPTIONAL!
                # Check if there's ANY language with content (source or target)
                has_gloss = any(
                    bool(str(v).strip()) if isinstance(v, str) else bool(v.get('text', '').strip() if isinstance(v, dict) else str(v).strip())
                    for k, v in gloss.items() 
                    if k != 'lang' and v
                )
            else:
                has_gloss = bool(str(gloss).strip()) if gloss else False
                
            variant_of = sense.get('variant_of', '')
            has_variant_ref = bool(str(variant_of).strip()) if variant_of else False
            
            # Also check if the sense itself references a variant
            is_variant_sense = bool(sense.get('is_variant', False))
            
            if not (has_definition or has_gloss or has_variant_ref or is_variant_sense):
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config['name'],
                    message=rule_config['error_message'],
                    path=f"$.senses[{i}]",
                    priority=ValidationPriority(rule_config['priority']),
                    category=ValidationCategory(rule_config['category'])
                ))
        
        return errors
    
    def _validate_sense_required_non_variant(self, rule_id: str, rule_config: Dict[str, Any], 
                                           data: Dict[str, Any]) -> List[ValidationError]:
        """R1.1.3: Validate that at least one sense is required, except for variant entries."""
        errors: List[ValidationError] = []
        
        # Check if this entry is a variant form (has _component-lexeme relation with variant-type trait)
        relations = data.get('relations', [])
        is_variant_entry = any(
            rel.get('type') == '_component-lexeme' and 
            isinstance(rel.get('traits'), dict) and 
            'variant-type' in rel.get('traits', {})
            for rel in relations
        )
        
        # If this is a variant entry, it doesn't need senses
        if is_variant_entry:
            return errors
        
        # For non-variant entries, check if there is at least one sense
        senses = data.get('senses', [])
        if not senses or len(senses) == 0:
            errors.append(ValidationError(
                rule_id=rule_id,
                rule_name=rule_config['name'],
                message=rule_config['error_message'],
                path="$.senses",
                priority=ValidationPriority(rule_config['priority']),
                category=ValidationCategory(rule_config['category'])
            ))
        
        return errors
    
    def _validate_unique_note_types(self, rule_id: str, rule_config: Dict[str, Any], 
                                   data: Dict[str, Any]) -> List[ValidationError]:
        """R3.1.1: Validate that note types are unique per entry."""
        errors: List[ValidationError] = []
        
        notes = data.get('notes', {})
        if isinstance(notes, dict):
            # Notes as object with type as key - inherently unique
            return errors
        elif isinstance(notes, list):
            # Notes as array with type property
            seen_types: set[str] = set()
            for i, note in enumerate(notes):
                if isinstance(note, dict):
                    note_type = note.get('type')
                    if note_type and note_type in seen_types:
                        errors.append(ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config['name'],
                            message=rule_config['error_message'],
                            path=f"$.notes[{i}].type",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=note_type
                        ))
                    if note_type:
                        seen_types.add(note_type)
        
        return errors
    
    def _validate_note_content(self, rule_id: str, rule_config: Dict[str, Any],
                               data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R3.1.2: Validate that note content is non-empty for simple string notes.
        
        Skips multilingual notes (objects) as they are validated by R3.1.3.
        """
        errors: List[ValidationError] = []
        
        notes = data.get('notes', {})
        if not isinstance(notes, dict):
            return errors
        
        for note_type, note_content in notes.items():
            # Only validate simple string notes
            if isinstance(note_content, str):
                # Check if content is empty or whitespace-only
                if not note_content or not note_content.strip():
                    errors.append(ValidationError(
                        rule_id=rule_id,
                        rule_name=rule_config['name'],
                        message=rule_config['error_message'],
                        path=f"$.notes.{note_type}",
                        priority=ValidationPriority(rule_config['priority']),
                        category=ValidationCategory(rule_config['category']),
                        value=note_content
                    ))
            # Skip objects (multilingual notes) - they're validated by R3.1.3
        
        return errors
    
    def _validate_synonym_antonym_exclusion(self, rule_id: str, rule_config: Dict[str, Any], 
                                          data: Dict[str, Any]) -> List[ValidationError]:
        """R8.5.2: Validate no conflicting synonym/antonym relations."""
        errors: List[ValidationError] = []
        
        relations = data.get('relations', [])
        targets_by_type: Dict[str, set[str]] = {'synonym': set(), 'antonym': set()}
        
        for relation in relations:
            if isinstance(relation, dict):
                rel_type = str(relation.get('type', '')).lower()
                target = str(relation.get('target', ''))
                
                if rel_type in targets_by_type and target:
                    targets_by_type[rel_type].add(target)
        
        # Check for conflicting relations
        conflicting_targets = targets_by_type['synonym'] & targets_by_type['antonym']
        for target in conflicting_targets:
            errors.append(ValidationError(
                rule_id=rule_id,
                rule_name=rule_config['name'],
                message=rule_config['error_message'].format(target=target),
                path="$.relations",
                priority=ValidationPriority(rule_config['priority']),
                category=ValidationCategory(rule_config['category']),
                value=target
            ))
        
        return errors
    
    def _validate_subsense_depth(self, rule_id: str, rule_config: Dict[str, Any], 
                                data: Dict[str, Any]) -> List[ValidationError]:
        """R8.7.1: Validate subsense nesting depth limits."""
        errors: List[ValidationError] = []
        
        def check_depth(senses: List[Any], current_depth: int = 0, path_prefix: str = "$.senses") -> None:
            if current_depth > 3:
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config['name'],
                    message=rule_config['error_message'],
                    path=path_prefix,
                    priority=ValidationPriority(rule_config['priority']),
                    category=ValidationCategory(rule_config['category'])
                ))
                return
            
            for i, sense in enumerate(senses):
                if isinstance(sense, dict):
                    subsenses = sense.get('subsenses', [])
                    if subsenses and isinstance(subsenses, list):
                        check_depth(subsenses, current_depth + 1, f"{path_prefix}[{i}].subsenses")
        
        senses = data.get('senses', [])
        if isinstance(senses, list):
            check_depth(senses)
        
        return errors
    
    def _validate_unique_languages_in_multitext(self, rule_id: str, rule_config: Dict[str, Any], 
                                              data: Dict[str, Any]) -> List[ValidationError]:
        """R8.2.2: Validate unique language codes in multitext content."""
        errors: List[ValidationError] = []
        
        # This would be implemented based on specific multitext structure in your data
        # Placeholder for now
        
        return errors
    
    def _validate_language_codes(self, rule_id: str, rule_config: Dict[str, Any], 
                                data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R1.2.3: Validate language codes against approved project list (DEPRECATED - use format validation)."""
        errors: List[ValidationError] = []
        
        allowed_languages = rule_config['validation'].get('allowed_languages', [])
        
        # If no allowed languages specified, skip validation (permissive mode)
        if not allowed_languages:
            return errors
        
        for match in matches:
            if isinstance(match.value, dict):
                # Check all language codes in the dictionary
                for lang_code in match.value.keys():
                    if lang_code not in allowed_languages:
                        errors.append(ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config['name'],
                            message=rule_config['error_message'].replace('{value}', lang_code),
                            path=f"{match.full_path}.{lang_code}",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=lang_code
                        ))
        
        return errors
    
    def _validate_language_code_format(self, rule_id: str, rule_config: Dict[str, Any], 
                                      data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """Validate language codes follow RFC 4646 format (flexible for LIFT standard)."""
        import re
        errors: List[ValidationError] = []
        
        # RFC 4646 simplified pattern: language[-script][-region][-variant]
        # Examples: en, pl, seh-fonipa, qaa-x-spec, pt-br, zh-hans-cn
        # Note: Codes must be lowercase, no underscores
        rfc4646_pattern = re.compile(r'^[a-z]{2,3}(-[a-z0-9]+)*$')
        
        # Blacklist of codes that match the pattern but are invalid
        # 'ipa' is not a valid ISO 639 language code; use 'seh-fonipa' for IPA
        invalid_codes = {'ipa'}
        
        # Get lexical unit
        lexical_unit = data.get('lexical_unit', {})
        if isinstance(lexical_unit, dict):
            for lang_code in lexical_unit.keys():
                if lang_code in invalid_codes:
                    errors.append(ValidationError(
                        rule_id=rule_id,
                        rule_name=rule_config['name'],
                        message=f"Invalid language code '{lang_code}'. For IPA transcriptions, use 'seh-fonipa'",
                        path=f"$.lexical_unit.{lang_code}",
                        priority=ValidationPriority(rule_config.get('priority', 'warning')),
                        category=ValidationCategory(rule_config['category']),
                        value=lang_code
                    ))
                elif not rfc4646_pattern.match(lang_code):
                    errors.append(ValidationError(
                        rule_id=rule_id,
                        rule_name=rule_config['name'],
                        message=rule_config['error_message'].replace('{value}', lang_code),
                        path=f"$.lexical_unit.{lang_code}",
                        priority=ValidationPriority(rule_config.get('priority', 'warning')),
                        category=ValidationCategory(rule_config['category']),
                        value=lang_code
                    ))
        
        return errors
    
    def _validate_pronunciation_language_codes(self, rule_id: str, rule_config: Dict[str, Any], 
                                              data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R4.1.1: Validate pronunciation language codes."""
        errors: List[ValidationError] = []
        
        allowed_languages = rule_config['validation'].get('allowed_languages', [])
        
        for match in matches:
            if isinstance(match.value, dict):
                # Check all language codes in the pronunciation dictionary
                for lang_code in match.value.keys():
                    if lang_code not in allowed_languages:
                        errors.append(ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config['name'],
                            message=rule_config['error_message'].replace('{value}', str(lang_code)),
                            path=f"{match.full_path}.{lang_code}",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=str(lang_code)
                        ))
        
        return errors

    def _validate_date_fields(self, rule_id: str, rule_config: Dict[str, Any], 
                             data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R8.3.1: Validate date fields throughout the entry data."""
        import re
        errors: List[ValidationError] = []
        
        pattern = rule_config['validation'].get('pattern', '')
        regex = re.compile(pattern) if pattern else None
        
        def check_dates_recursive(obj: Any, path: str = "$") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}"
                    # Skip GenDate custom fields (Day 36-37) - they use YYYYMMDD format, not ISO 8601
                    # GenDate fields are named like "CustomFldEntry-Date", "CustomFldSense-FirstRecorded", etc.
                    is_gendate_field = ('CustomFld' in key and 'Date' in key) or (path.endswith('.traits') and 'date' in key.lower())
                    
                    if 'date' in key.lower() and isinstance(value, str) and not is_gendate_field:
                        # This is a standard date field (not GenDate), validate it
                        if regex and not regex.match(value):
                            errors.append(ValidationError(
                                rule_id=rule_id,
                                rule_name=rule_config['name'],
                                message=rule_config['error_message'],
                                path=new_path,
                                priority=ValidationPriority(rule_config['priority']),
                                category=ValidationCategory(rule_config['category']),
                                value=value
                            ))
                    else:
                        check_dates_recursive(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_dates_recursive(item, f"{path}[{i}]")
        
        # Check entire data structure for date fields
        check_dates_recursive(data)
        
        return errors
    
    def _create_error(self, rule_id: str, rule_config: Dict[str, Any], 
                     path: str, value: Any) -> ValidationError:
        """Create a ValidationError instance."""
        message = rule_config['error_message']
        
        # Handle message templates
        if '{value}' in message and value is not None:
            message = message.replace('{value}', str(value))
        if '{key}' in message and hasattr(value, '__name__'):
            message = message.replace('{key}', str(value.__name__))
        
        return ValidationError(
            rule_id=rule_id,
            rule_name=rule_config['name'],
            message=message,
            path=path,
            priority=ValidationPriority(rule_config['priority']),
            category=ValidationCategory(rule_config['category']),
            value=value
        )
    
    def _validate_definition_content_source_lang_exception(self, rule_id: str, rule_config: Dict[str, Any], 
                                                          data: Dict[str, Any], matches: Any) -> List[ValidationError]:
        """R2.2.1: Validate definition content with source language exceptions.
        
        Definition/gloss text must be non-empty, except for source language definitions
        which can be empty since the headword itself is in that language.
        
        Only allows completely empty definitions (all languages empty AND all are source language)
        since the user might be removing the definition field. If non-source language keys exist
        with empty values, that's an error.
        """
        errors: List[ValidationError] = []
        
        # Get source language from project config or entry
        if self.project_config and 'source_language' in self.project_config:
            source_lang_config = self.project_config['source_language']
            target_lang = source_lang_config.get('code', '') if isinstance(source_lang_config, dict) else ''
        else:
            target_lang = data.get('lexical-unit', {}).get('lang', '')
        
        for match in matches:
            sense_data = match.value
            if not isinstance(sense_data, dict):
                continue
                
            definition = sense_data.get('definition', {})
            if not isinstance(definition, dict):
                continue
            
            # Check each definition/gloss language
            for lang_code, text in definition.items():
                # Skip empty check for source language (target language)
                if lang_code == target_lang:
                    continue
                    
                # For non-source languages, text must be non-empty IF the key exists
                # Extract actual text value if it's a dict with 'text' key
                actual_text = text
                if isinstance(text, dict) and 'text' in text:
                    actual_text = text['text']
                
                if actual_text is not None and not str(actual_text).strip():
                    errors.append(ValidationError(
                        rule_id=rule_id,
                        rule_name=rule_config['name'],
                        message=rule_config['error_message'],
                        path=f"{match.full_path}.definition.{lang_code}",
                        priority=ValidationPriority(rule_config['priority']),
                        category=ValidationCategory(rule_config['category']),
                        value=actual_text
                    ))
        
        return errors
    
    def _validate_multilingual_note_structure(self, rule_id: str, rule_config: Dict[str, Any], 
                                             data: Dict[str, Any], matches: Any) -> List[ValidationError]:
        """R3.1.3: Validate multilingual note structure.
        
        Checks that multilingual notes use valid language codes from project settings.
        """
        errors: List[ValidationError] = []
        
        notes = data.get('notes', {})
        if not notes or not isinstance(notes, dict):
            return errors
        
        # Get valid language codes from project config
        valid_langs = set()
        if self.project_config:
            source_lang = self.project_config.get('source_language', {})
            if isinstance(source_lang, dict) and 'code' in source_lang:
                valid_langs.add(source_lang['code'])
            target_langs = self.project_config.get('target_languages', [])
            for lang in target_langs:
                if isinstance(lang, dict) and 'code' in lang:
                    valid_langs.add(lang['code'])
        
        # If no project config, accept any RFC 4646 format (lowercase, hyphens)
        rfc4646_pattern = re.compile(r'^[a-z]{2,3}(-[a-z0-9]+)*$')
        
        # Blacklist of codes that match the pattern but are invalid
        # 'ipa' is not a valid ISO 639 language code; use 'seh-fonipa' for IPA
        invalid_codes = {'ipa'}
        
        for note_type, note_content in notes.items():
            if isinstance(note_content, dict):
                # Multilingual note
                for lang_code in note_content.keys():
                    if lang_code in invalid_codes:
                        errors.append(ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config['name'],
                            message=f"Invalid language code '{lang_code}'. For IPA transcriptions, use 'seh-fonipa'",
                            path=f"$.notes.{note_type}.{lang_code}",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=lang_code
                        ))
                    elif valid_langs and lang_code not in valid_langs:
                        errors.append(ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config['name'],
                            message=f"Language code '{lang_code}' not configured for this project",
                            path=f"$.notes.{note_type}.{lang_code}",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=lang_code
                        ))
                    elif not valid_langs and not rfc4646_pattern.match(lang_code):
                        errors.append(ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config['name'],
                            message=f"Invalid language code format: '{lang_code}'",
                            path=f"$.notes.{note_type}.{lang_code}",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=lang_code
                        ))
        
        return errors
    
    def _validate_pos_consistency(self, rule_id: str, rule_config: Dict[str, Any], 
                                  data: Dict[str, Any], matches: Any) -> List[ValidationError]:
        """R6.1.1: Validate part-of-speech consistency between entry and senses.
        
        If entry has POS, ALL senses with POS must match it (strict consistency).
        """
        errors: List[ValidationError] = []
        
        entry_pos = data.get('grammatical_info', '')
        if not entry_pos:
            return errors
        
        senses = data.get('senses', [])
        for i, sense in enumerate(senses):
            sense_pos = sense.get('grammatical_info', '')
            if sense_pos and sense_pos != entry_pos:
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config['name'],
                    message=f"Sense POS '{sense_pos}' differs from entry POS '{entry_pos}'",
                    path=f"$.senses[{i}].grammatical_info",
                    priority=ValidationPriority(rule_config['priority']),
                    category=ValidationCategory(rule_config['category']),
                    value=sense_pos
                ))
        
        return errors
    
    def _validate_conflicting_pos(self, rule_id: str, rule_config: Dict[str, Any], 
                                  data: Dict[str, Any], matches: Any) -> List[ValidationError]:
        """R6.1.2: Validate that conflicting sense POS values require manual entry POS."""
        errors: List[ValidationError] = []
        
        senses = data.get('senses', [])
        if len(senses) < 2:
            return errors
        
        # Collect all sense POS values
        sense_pos_values = set()
        for sense in senses:
            pos = sense.get('grammatical_info', '')
            if pos:
                sense_pos_values.add(pos)
        
        # If senses have conflicting POS, entry must have POS set
        if len(sense_pos_values) > 1:
            entry_pos = data.get('grammatical_info', '')
            if not entry_pos:
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config['name'],
                    message=rule_config['error_message'],
                    path="$.grammatical_info",
                    priority=ValidationPriority(rule_config['priority']),
                    category=ValidationCategory(rule_config['category']),
                    value=None
                ))
        
        return errors


    def _validate_no_circular_components(self, rule_id: str, rule_config: Dict[str, Any],
                                        data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R8.1.1: Validate that component relations don't reference the entry itself."""
        errors: List[ValidationError] = []
        entry_id = data.get('id')
        
        if not entry_id:
            return errors
        
        relations = data.get('relations', [])
        for idx, relation in enumerate(relations):
            if not isinstance(relation, dict):
                continue
                
            if relation.get('type') == '_component-lexeme':
                ref = relation.get('ref')
                if ref and ref == entry_id:
                    errors.append(
                        ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config.get('name', ''),
                            message=rule_config.get('error_message', 'Component relation cannot reference the entry itself'),
                            path=f"$.relations[{idx}].ref",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=ref
                        )
                    )
        
        return errors


    def _validate_no_circular_sense_relations(self, rule_id: str, rule_config: Dict[str, Any],
                                             data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R8.1.2: Validate that sense relations don't reference senses within the same entry."""
        errors: List[ValidationError] = []
        entry_id = data.get('id')
        
        if not entry_id:
            return errors
        
        senses = data.get('senses', [])
        for sense_idx, sense in enumerate(senses):
            if not isinstance(sense, dict):
                continue
                
            sense_relations = sense.get('relations', [])
            for rel_idx, relation in enumerate(sense_relations):
                if not isinstance(relation, dict):
                    continue
                    
                ref = relation.get('ref')
                if not ref:
                    continue
                
                # Check if ref points to a sense in the same entry
                # Format can be: "entry_id_sense_id" or just "sense_guid"
                # If it starts with entry_id, it's a circular reference
                if ref.startswith(entry_id):
                    errors.append(
                        ValidationError(
                            rule_id=rule_id,
                            rule_name=rule_config.get('name', ''),
                            message=rule_config.get('error_message', 'Sense relation cannot reference a sense within the same entry'),
                            path=f"$.senses[{sense_idx}].relations[{rel_idx}].ref",
                            priority=ValidationPriority(rule_config['priority']),
                            category=ValidationCategory(rule_config['category']),
                            value=ref
                        )
                    )
        
        return errors


    def _validate_no_circular_entry_relations(self, rule_id: str, rule_config: Dict[str, Any],
                                             data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R8.1.3: Validate that entry-level relations don't reference the entry itself."""
        errors: List[ValidationError] = []
        entry_id = data.get('id')
        
        if not entry_id:
            return errors
        
        relations = data.get('relations', [])
        for idx, relation in enumerate(relations):
            if not isinstance(relation, dict):
                continue
                
            # Skip component-lexeme relations (handled by R8.1.1)
            if relation.get('type') == '_component-lexeme':
                continue
                
            ref = relation.get('ref')
            if ref and ref == entry_id:
                errors.append(
                    ValidationError(
                        rule_id=rule_id,
                        rule_name=rule_config.get('name', ''),
                        message=rule_config.get('error_message', 'Entry relation cannot reference the entry itself'),
                        path=f"$.relations[{idx}].ref",
                        priority=ValidationPriority(rule_config['priority']),
                        category=ValidationCategory(rule_config['category']),
                        value=ref
                    )
                )
        
        return errors

    def _validate_relation_targets_exist(self, rule_id: str, rule_config: Dict[str, Any],
                                         data: Dict[str, Any]) -> List[ValidationError]:
        """R5.3.1: Validate that all relation targets exist in the dictionary.

        This checks both entry-level relations and sense-level relations
        to ensure that referenced entry IDs actually exist.
        """
        errors: List[ValidationError] = []

        # Get set of existing entry IDs (from constructor parameter)
        existing_ids = getattr(self, '_existing_entry_ids', None)

        # If no existing IDs provided, skip validation (can't check without reference)
        if not existing_ids:
            return errors

        entry_id = data.get('id', '')

        # Check entry-level relations
        relations = data.get('relations', [])
        for idx, relation in enumerate(relations):
            if not isinstance(relation, dict):
                continue

            # Skip component-lexeme relations (internal references, not semantic relations)
            rel_type = relation.get('type', '')
            if rel_type == '_component-lexeme':
                continue

            target = relation.get('ref') or relation.get('target')
            if target and target not in existing_ids:
                errors.append(
                    self._create_error(rule_id, rule_config, f"$.relations[{idx}].ref", target)
                )

        # Check sense-level relations
        senses = data.get('senses', [])
        for sense_idx, sense in enumerate(senses):
            if not isinstance(sense, dict):
                continue

            sense_relations = sense.get('relations', [])
            for rel_idx, relation in enumerate(sense_relations):
                if not isinstance(relation, dict):
                    continue

                target = relation.get('ref') or relation.get('target')
                if target and target not in existing_ids:
                    errors.append(
                        self._create_error(rule_id, rule_config, f"$.senses[{sense_idx}].relations[{rel_idx}].ref", target)
                    )

        return errors

    def _validate_ipa_characters(self, rule_id: str, rule_config: Dict[str, Any],
                                  data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R4.1.2: Validate IPA characters in pronunciation values."""
        import re
        errors: List[ValidationError] = []

        # IPA characters plus basic Latin letters (for fallback transcription)
        # Includes Latin Extended-A (0100-024F) which has IPA chars like ŋ
        ipa_pattern = re.compile(
            r'^[\u0100-\u024F\u0250-\u02AF\u02B0-\u02FF\u0300-\u036F\u1D00-\u1D7F\u1DC0-\u1DFF'
            r'\u2090-\u209Fˌˈː.ˑʔʰ͡ⱱəɛɪɔʊæɐɑɒɓɕɗɖɟɡɠɣɦɧɨɭɲɳɴɵɸɹɻɾʀʁʂʃʈʊʋʌʍʎʏʐʑʒʔʕʘʙʛʜʝʞʟʠʡʢʣʥʦʧʨ'
            r'a-zA-Z ]+$'
        )

        pronunciations = data.get('pronunciations', {})
        if not isinstance(pronunciations, dict):
            return errors

        for lang_code, pron_value in pronunciations.items():
            if not isinstance(pron_value, str):
                continue

            # Skip empty strings
            if not pron_value:
                continue

            # Check if all characters are valid IPA or ASCII letters
            if not ipa_pattern.match(pron_value):
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config['name'],
                    message=rule_config['error_message'],
                    path=f"$.pronunciations.{lang_code}",
                    priority=ValidationPriority(rule_config['priority']),
                    category=ValidationCategory(rule_config['category']),
                    value=pron_value[:20] + '...' if len(pron_value) > 20 else pron_value
                ))

        return errors

    def _validate_no_double_stress(self, rule_id: str, rule_config: Dict[str, Any],
                                    data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R4.2.1: Validate no double stress markers in pronunciation values."""
        errors: List[ValidationError] = []

        pronunciations = data.get('pronunciations', {})
        if not isinstance(pronunciations, dict):
            return errors

        # Double stress markers: ˈˈ or ˌˌ or combinations
        double_stress_pattern = re.compile(r'[ˈˌ][ˈˌ]')

        for lang_code, pron_value in pronunciations.items():
            if not isinstance(pron_value, str):
                continue

            if double_stress_pattern.search(pron_value):
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config['name'],
                    message=rule_config['error_message'],
                    path=f"$.pronunciations.{lang_code}",
                    priority=ValidationPriority(rule_config['priority']),
                    category=ValidationCategory(rule_config['category']),
                    value=pron_value
                ))

        return errors

    def _validate_no_double_length(self, rule_id: str, rule_config: Dict[str, Any],
                                    data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """R4.2.2: Validate no double length markers in pronunciation values."""
        errors: List[ValidationError] = []

        pronunciations = data.get('pronunciations', {})
        if not isinstance(pronunciations, dict):
            return errors

        # Double length markerːː
        double_length_pattern = re.compile(r'ːː')

        for lang_code, pron_value in pronunciations.items():
            if not isinstance(pron_value, str):
                continue

            if double_length_pattern.search(pron_value):
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config['name'],
                    message=rule_config['error_message'],
                    path=f"$.pronunciations.{lang_code}",
                    priority=ValidationPriority(rule_config['priority']),
                    category=ValidationCategory(rule_config['category']),
                    value=pron_value
                ))

        return errors

    def _get_hunspell_for_language(self, lang_code: str) -> Optional[Any]:
        """Get hunspell dictionary for a language code with fallback logic.

        Tries the following in order:
        1. Exact match (e.g., 'en_US')
        2. Base language + '_' + common variants (e.g., 'en' -> 'en_US')
        3. Base language alone (e.g., 'en')

        Args:
            lang_code: Language code to look up

        Returns:
            Hunspell instance or None if not found
        """
        from app.services.dictionary_loader import get_dictionary_loader
        loader = get_dictionary_loader()

        hunspell = loader.load_system_dictionary(lang_code)
        if hunspell:
            return hunspell

        # Try common locale variants for 2-letter codes
        if len(lang_code) == 2:
            common_variants = [f'{lang_code}_US', f'{lang_code}_GB', f'{lang_code}_{lang_code.upper()}']
            for variant in common_variants:
                hunspell = loader.load_system_dictionary(variant)
                if hunspell:
                    return hunspell

        # Try base language alone (e.g., 'en' from 'en_US')
        if '_' in lang_code:
            base_lang = lang_code.split('_')[0]
            hunspell = loader.load_system_dictionary(base_lang)
            if hunspell:
                return hunspell

        return None

    def _validate_hunspell_spelling(self, rule_id: str, rule_config: Dict[str, Any],
                                     data: Dict[str, Any], matches: List[Any]) -> List[ValidationError]:
        """Custom validation: Check spelling using hunspell dictionaries.

        Configuration:
        - lang_code: Language code for dictionary (default: en_US, ignored if auto_detect_languages is true)
        - auto_detect_languages: Extract language code from JSON path (default: true for multilingual support)
        - minWordLength: Minimum word length to check (default: 3)
        - ignoreWords: List of words to ignore
        - targetField: JSONPath to the field to validate (if matches not provided)

        Returns list of ValidationError for any misspellings found.
        """
        import re
        errors: List[ValidationError] = []

        # Get configuration
        validation_config = rule_config.get('validation', {})
        lang_code = validation_config.get('lang_code', 'en_US')
        auto_detect = validation_config.get('auto_detect_languages', True)  # Default to True for multilingual
        min_word_length = validation_config.get('minWordLength', 3)
        ignore_words = validation_config.get('ignoreWords', [])
        error_message = rule_config.get('error_message', 'Spelling error detected')

        # Build ignore set for fast lookup
        ignore_set = {w.lower() for w in ignore_words}

        # Process each match
        for match in matches:
            value = match.value
            if not isinstance(value, str):
                continue

            # Determine which language dictionary to use
            if auto_detect:
                # Extract language code from the match path (e.g., "lexical_unit.en" -> "en")
                path_str = str(match.full_path)
                path_parts = path_str.split('.')
                # Try to find a language code pattern (e.g., "en", "en_US", "pl", "seh")
                detected_lang = None
                for part in reversed(path_parts):
                    # Check if it looks like a language code
                    if part and (len(part) in (2, 5) or '-' in part):
                        # Simple heuristic: language codes are 2 chars (en, pl) or 5 chars (en_US)
                        # or contain hyphen (seh-fonipa)
                        detected_lang = part
                        break
                target_lang = detected_lang if detected_lang else lang_code
            else:
                target_lang = lang_code

            # Load the dictionary for this specific language with fallback logic
            hunspell = self._get_hunspell_for_language(target_lang)

            if not hunspell:
                # Dictionary not available for this language, skip validation
                # This is intentional - we don't want to flag errors for languages without dictionaries
                continue

            # Extract words
            words = re.findall(r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b", value)

            for word in words:
                word_lower = word.lower()

                # Skip short words and ignored words
                if len(word_lower) < min_word_length:
                    continue
                if word_lower in ignore_set:
                    continue

                # Check spelling
                if not hunspell.spell(word):
                    # Get suggestions
                    suggestions = hunspell.suggest(word)[:3]
                    suggestion_text = f" (suggestions: {', '.join(suggestions)})" if suggestions else ""

                    errors.append(ValidationError(
                        rule_id=rule_id,
                        rule_name=rule_config['name'],
                        message=f"{error_message}: '{word}'{suggestion_text}",
                        path=str(match.full_path),
                        priority=ValidationPriority(rule_config.get('priority', 'warning')),
                        category=ValidationCategory(rule_config.get('category', 'language_validation')),
                        value=word
                    ))

        return errors


class SchematronValidator:
    """
    Schematron validator for XML validation.
    
    This class integrates with lxml's ISO Schematron support to validate LIFT XML
    against the Schematron rules we defined.
    """
    
    def __init__(self, schema_file: Optional[str] = None):
        """
        Initialize Schematron validator.
        
        Args:
            schema_file: Path to Schematron schema file
        """
        self.schema_file = schema_file or "schemas/lift_validation.sch"
        self._validator: Any = None
        self._setup_validator()
    
    def _setup_validator(self) -> None:
        """Set up Schematron validator.

        Prefer lxml ISO Schematron (XSLT1) when schema queryBinding allows it.
        If schema requires XSLT2, attempt to compile and use Saxon-HE if configured.
        """
        schema_path = Path(self.schema_file)
        if not schema_path.is_absolute():
            schema_path = Path(__file__).parent.parent.parent / self.schema_file

        if not schema_path.exists():
            # Schema missing - leave validator None
            self._validator = None
            self._xslt2_reason = f"Schematron schema file not found: {schema_path}"
            return

        # Detect whether schema requires xslt2
        try:
            from lxml import etree
            schema_doc = etree.parse(str(schema_path))
            root = schema_doc.getroot()
            query_binding = root.get('queryBinding') or root.get('{http://purl.oclc.org/dsdl/schematron}queryBinding')
            if query_binding and query_binding.strip().lower().startswith('xslt2'):
                # XSLT2 required - try to set up Saxon-based validator
                saxon_jar = os.getenv('SAXON_JAR')
                xsl_path = os.getenv('SCHEMATRON_XSL', 'tools/schematron/iso_svrl_for_xslt2.xsl')
                if not saxon_jar or not Path(saxon_jar).exists():
                    self._validator = None
                    self._xslt2_reason = 'xslt2_required_no_saxon'
                    return

                # Ensure the iso_svrl_for_xslt2.xsl exists or download it
                try:
                    self._ensure_iso_svrl_xslt2(xsl_path)
                except Exception:
                    self._validator = None
                    self._xslt2_reason = 'xslt2_required_missing_iso_xsl'
                    return

                # Compile schema into an XSLT validator using Saxon
                try:
                    compiled_dir = Path('compiled/schematron')
                    compiled_dir.mkdir(parents=True, exist_ok=True)
                    compiled_xsl = compiled_dir / (schema_path.stem + '.xsl')

                    # Recompile if missing or schema changed
                    if not compiled_xsl.exists() or compiled_xsl.stat().st_mtime < schema_path.stat().st_mtime:
                        cmd = [
                            'java', '-jar', saxon_jar,
                            f'-s:{schema_path}',
                            f'-xsl:{xsl_path}',
                            f'-o:{compiled_xsl}'
                        ]
                        import subprocess
                        subprocess.run(cmd, check=True, timeout=60)

                    # Mark validator as Saxon-based
                    self._validator = ('saxon', str(compiled_xsl))
                    self._saxon_jar = saxon_jar
                    return

                except Exception:
                    self._validator = None
                    self._xslt2_reason = 'xslt2_compile_failed'
                    return

            # Fallback: try lxml isoschematron if available
            try:
                from lxml import isoschematron
                self._validator = isoschematron.Schematron(schema_doc)
                return
            except Exception:
                self._validator = None
                self._xslt2_reason = 'lxml_schematron_unavailable'
                return

        except Exception:
            # Any parsing/setup error -> leave validator None
            self._validator = None
            self._xslt2_reason = 'schematron_setup_error'
            return

    def _ensure_iso_svrl_xslt2(self, xsl_path: str) -> None:
        """Ensure the ISO SVRL XSLT2 stylesheet exists locally.

        If it's not present, attempt to download it from the canonical Schematron repository.
        """
        from urllib.request import urlretrieve

        xsl_file = Path(xsl_path)
        if xsl_file.exists():
            return

        # Ensure parent dir exists
        xsl_file.parent.mkdir(parents=True, exist_ok=True)

        # Canonical remote URL (raw content of iso_svrl_for_xslt2.xsl)
        url = os.getenv('SCHEMATRON_ISO_XSL_URL', 'https://raw.githubusercontent.com/Schematron/schematron/master/trunk/iso-schematron-xslt2/iso_svrl_for_xslt2.xsl')
        urlretrieve(url, str(xsl_file))
        if not xsl_file.exists():
            raise RuntimeError('Failed to download iso_svrl_for_xslt2.xsl')
    
    def validate_xml(self, xml_content: str) -> ValidationResult:
        """
        Validate XML content against Schematron rules.

        Args:
            xml_content: XML string to validate

        Returns:
            ValidationResult with any Schematron violations
        """
        try:
            from lxml import etree

            if self._validator is None:
                self._setup_validator()
                if self._validator is None:
                    # Provide a clear reason why Schematron validator isn't initialized
                    reason = getattr(self, '_xslt2_reason', 'not_configured')
                    return ValidationResult(False, [
                        ValidationError(
                            rule_id="SCHEMATRON_ERROR",
                            rule_name="schematron_setup",
                            message=f"Schematron validator not initialized: {reason}",
                            path="",
                            priority=ValidationPriority.CRITICAL,
                            category=ValidationCategory.ENTRY_LEVEL
                        )
                    ], [], [])

            errors: List[ValidationError] = []
            warnings: List[ValidationError] = []
            info: List[ValidationError] = []

            # Saxon-based validator (XSLT2)
            if isinstance(self._validator, tuple) and self._validator[0] == 'saxon':
                compiled_xsl = self._validator[1]
                saxon_jar = getattr(self, '_saxon_jar', None)
                if not saxon_jar or not Path(saxon_jar).exists():
                    return ValidationResult(False, [
                        ValidationError(
                            rule_id="SCHEMATRON_ERROR",
                            rule_name="saxon_not_available",
                            message="Saxon JAR not available for XSLT2 Schematron validation",
                            path="",
                            priority=ValidationPriority.CRITICAL,
                            category=ValidationCategory.ENTRY_LEVEL
                        )
                    ], [], [])

                import subprocess
                import tempfile

                with tempfile.NamedTemporaryFile(mode='w+', suffix='.xml', delete=False) as xml_file:
                    xml_file.write(xml_content)
                    xml_path = xml_file.name

                with tempfile.NamedTemporaryFile(mode='w+', suffix='.svrl.xml', delete=False) as svrl_file:
                    svrl_path = svrl_file.name

                try:
                    cmd = ['java', '-jar', saxon_jar, f'-s:{xml_path}', f'-xsl:{compiled_xsl}', f'-o:{svrl_path}']
                    subprocess.run(cmd, check=True, timeout=30)

                    svrl_doc = etree.parse(svrl_path)
                    ns = {'svrl': 'http://purl.oclc.org/dsdl/svrl'}
                    for failed in svrl_doc.findall('.//svrl:failed-assert', namespaces=ns):
                        text_el = failed.find('svrl:text', namespaces=ns)
                        msg = text_el.text if text_el is not None else ''.join(failed.itertext())
                        location = failed.get('location') or ''
                        errors.append(ValidationError(
                            rule_id=self._extract_rule_id(msg),
                            rule_name='schematron_validation',
                            message=msg.strip(),
                            path=location,
                            priority=ValidationPriority.CRITICAL,
                            category=ValidationCategory.ENTRY_LEVEL
                        ))

                    is_valid = len(errors) == 0
                    return ValidationResult(is_valid, errors, warnings, info)

                except subprocess.CalledProcessError as e:
                    return ValidationResult(False, [
                        ValidationError(
                            rule_id="SCHEMATRON_ERROR",
                            rule_name="saxon_error",
                            message=f"Saxon execution failed: {str(e)}",
                            path="",
                            priority=ValidationPriority.CRITICAL,
                            category=ValidationCategory.ENTRY_LEVEL
                        )
                    ], [], [])

                finally:
                    try:
                        Path(xml_path).unlink()
                    except Exception:
                        pass
                    try:
                        Path(svrl_path).unlink()
                    except Exception:
                        pass

            # lxml-based validator
            xml_doc = etree.fromstring(xml_content.encode('utf-8'))
            is_valid = self._validator.validate(xml_doc)
            if not is_valid:
                error_log = self._validator.error_log
                for error in error_log:
                    errors.append(ValidationError(
                        rule_id=self._extract_rule_id(str(error.message)),
                        rule_name='schematron_validation',
                        message=str(error.message),
                        path=f'line {error.line}' if error.line else '',
                        priority=ValidationPriority.CRITICAL,
                        category=ValidationCategory.ENTRY_LEVEL
                    ))

            return ValidationResult(is_valid, errors, warnings, info)

        except Exception as e:
            return ValidationResult(False, [
                ValidationError(
                    rule_id="SCHEMATRON_ERROR",
                    rule_name="schematron_setup",
                    message=f"Schematron validation error: {str(e)}",
                    path="",
                    priority=ValidationPriority.CRITICAL,
                    category=ValidationCategory.ENTRY_LEVEL
                )
            ], [], [])
    
    def _extract_rule_id(self, message: str) -> str:
        """Extract rule ID from Schematron error message."""
        # Messages should start with rule ID like "R1.1.1 Violation:"
        import re
        match = re.match(r'^([A-Z]\d+\.\d+\.\d+)', message)
        return match.group(1) if match else "UNKNOWN"


class ValidationRulesSchemaValidator:
    """
    Validates the validation_rules.json file itself against a JSON Schema.
    
    This ensures that user edits to validation_rules.json maintain proper structure,
    catching syntax errors and structural issues before they cause runtime problems.
    """
    
    def __init__(self, schema_file: Optional[str] = None):
        """
        Initialize the schema validator.
        
        Args:
            schema_file: Path to JSON Schema file for validation rules
        """
        self.schema_file = schema_file or "schemas/validation_rules.schema.json"
        self._schema: Optional[Dict[str, Any]] = None
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load the JSON Schema from file."""
        try:
            schema_path = Path(self.schema_file)
            if not schema_path.is_absolute():
                # Look for schema file relative to this module
                schema_path = Path(__file__).parent.parent.parent / self.schema_file
            
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                self._schema = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load validation rules schema: {str(e)}")
    
    def validate_rules_file(self, rules_file: Optional[str] = None) -> ValidationResult:
        """
        Validate a validation_rules.json file against the schema.
        
        Args:
            rules_file: Path to validation_rules.json file (defaults to standard location)
        
        Returns:
            ValidationResult with any schema validation errors
        """
        rules_path = Path(rules_file or "validation_rules.json")
        if not rules_path.is_absolute():
            rules_path = Path(__file__).parent.parent.parent / rules_path
        
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        rule_id="JSON_SYNTAX",
                        rule_name="json_syntax",
                        message=f"Invalid JSON syntax in validation_rules.json: {str(e)}",
                        path=f"line {e.lineno}, column {e.colno}",
                        priority=ValidationPriority.CRITICAL,
                        category=ValidationCategory.ENTRY_LEVEL
                    )
                ],
                warnings=[],
                info=[]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        rule_id="FILE_ERROR",
                        rule_name="file_error",
                        message=f"Cannot read validation_rules.json: {str(e)}",
                        path=str(rules_path),
                        priority=ValidationPriority.CRITICAL,
                        category=ValidationCategory.ENTRY_LEVEL
                    )
                ],
                warnings=[],
                info=[]
            )
        
        # Validate against schema
        try:
            jsonschema.validate(instance=rules_data, schema=self._schema)
            return ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        except jsonschema.ValidationError as e:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        rule_id="SCHEMA_VIOLATION",
                        rule_name="schema_validation",
                        message=f"Schema validation error: {e.message}",
                        path='.'.join(str(p) for p in e.absolute_path) if e.absolute_path else str(e.path),
                        priority=ValidationPriority.CRITICAL,
                        category=ValidationCategory.ENTRY_LEVEL,
                        value=e.instance
                    )
                ],
                warnings=[],
                info=[]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        rule_id="VALIDATION_ERROR",
                        rule_name="validation_error",
                        message=f"Schema validation failed: {str(e)}",
                        path="",
                        priority=ValidationPriority.CRITICAL,
                        category=ValidationCategory.ENTRY_LEVEL
                    )
                ],
                warnings=[],
                info=[]
            )


# Custom validation functions for server-side only validation
def validate_file_exists(file_path: str) -> bool:
    """
    Validate that a file exists on the file system.
    
    Used for R8.1.1 and R8.1.2 media/illustration validation.
    """
    if not file_path:
        return False
    
    # Handle different URI schemes
    if file_path.startswith('file://'):
        file_path = file_path[7:]  # Remove file:// prefix
    
    return os.path.exists(file_path)


def validate_abbreviation_expansion_length(relation_data: Dict[str, Any]) -> bool:
    """
    Validate abbreviation-expansion relationship length logic.
    
    Used for R8.5.1 semantic validation.
    """
    rel_type = relation_data.get('type', '').lower()
    source = relation_data.get('source', '')
    target = relation_data.get('target', '')
    
    if rel_type == 'abbreviation' and len(target) <= len(source):
        return False  # Expansion should be longer than abbreviation
    elif rel_type == 'expansion' and len(target) >= len(source):
        return False  # Abbreviation should be shorter than expansion
    
    return True
