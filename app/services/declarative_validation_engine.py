"""
Declarative validation engine - executes JSON-defined rules without hardcoded logic.

This engine interprets validation rules from JSON configuration and applies them to data
structures without requiring custom Python methods for each rule type.
"""

from typing import Any, Dict, List, Optional
import re
import json
from jsonpath_ng import parse
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error."""
    rule_id: str
    rule_name: str
    message: str
    path: str
    severity: str = "error"


@dataclass
class ValidationResult:
    """Result of validation containing errors and warnings."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]


class DeclarativeValidationEngine:
    """
    Purely declarative validation engine that executes rules from JSON config.
    No hardcoded validation methods - all logic defined in validation_rules.json.
    """
    
    def __init__(self, rules_file: str = 'validation_rules_v2.json', project_config: Optional[Dict[str, Any]] = None):
        """
        Initialize validation engine with rules from JSON file.
        
        Args:
            rules_file: Path to validation rules JSON file
            project_config: Optional project configuration for context
        """
        with open(rules_file, 'r', encoding='utf-8') as f:
            self.rules_config = json.load(f)
        
        self.project_config = project_config or {}
        self.rules = self.rules_config.get('rules', {})
    
    def validate_entry(self, entry_data: Dict[str, Any], validation_mode: str = "save") -> ValidationResult:
        """
        Validate entry data against all applicable rules.
        
        Args:
            entry_data: Entry data as dictionary
            validation_mode: "draft" or "save" - determines which rules to apply
        
        Returns:
            ValidationResult with errors and warnings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        for rule_id, rule_config in self.rules.items():
            # Check if rule applies to this validation mode
            rule_mode = rule_config.get('validation_mode', 'all')
            if rule_mode == 'save_only' and validation_mode == 'draft':
                continue
            
            # Execute the rule
            rule_errors = self._execute_rule(rule_id, rule_config, entry_data)
            
            # Categorize by priority
            for error in rule_errors:
                if rule_config.get('priority') == 'warning':
                    warnings.append(error)
                else:
                    errors.append(error)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _execute_rule(self, rule_id: str, rule_config: Dict[str, Any], data: Dict[str, Any]) -> List[ValidationError]:
        """
        Execute a single validation rule against data.
        
        Args:
            rule_id: Rule identifier
            rule_config: Rule configuration from JSON
            data: Data to validate
        
        Returns:
            List of validation errors found
        """
        errors: List[ValidationError] = []
        
        # Extract target values using JSONPath
        path = rule_config.get('path', '$')
        targets = self._extract_values(path, data)
        
        # If no targets found and condition is not "required", skip
        condition = rule_config.get('condition', {})
        if not targets and condition.get('type') != 'required':
            return errors
        
        # Check condition
        if not self._check_condition(condition, targets, data):
            return errors
        
        # Apply validation to each target
        validation = rule_config.get('validation', {})
        for target_path, target_value in targets:
            if not self._validate_value(target_value, validation, data):
                errors.append(ValidationError(
                    rule_id=rule_id,
                    rule_name=rule_config.get('name', rule_id),
                    message=rule_config.get('error_message', 'Validation failed'),
                    path=target_path,
                    severity='error' if rule_config.get('priority') == 'critical' else 'warning'
                ))
        
        return errors
    
    def _extract_values(self, path: str, data: Dict[str, Any]) -> List[tuple]:
        """
        Extract values from data using JSONPath expression.
        
        Args:
            path: JSONPath expression
            data: Data to query
        
        Returns:
            List of (path_string, value) tuples
        """
        try:
            jsonpath_expr = parse(path)
            matches = jsonpath_expr.find(data)
            return [(str(match.full_path), match.value) for match in matches]
        except Exception:
            # If path is invalid, check if it's a simple field reference
            if path.startswith('$.') and '.' not in path[2:] and '[' not in path:
                field = path[2:]
                if field in data:
                    return [(path, data[field])]
            return []
    
    def _check_condition(self, condition: Dict[str, Any], targets: List[tuple], data: Dict[str, Any]) -> bool:
        """
        Check if condition is met for applying validation.
        
        Args:
            condition: Condition configuration
            targets: Target values extracted
            data: Full data context
        
        Returns:
            True if condition is met, False otherwise
        """
        cond_type = condition.get('type', 'required')
        
        if cond_type == 'required':
            # Must have at least one non-None, non-empty target
            return any(val is not None and val != '' and val != {} and val != [] for _, val in targets)
        
        elif cond_type == 'if_present':
            # Only validate if field is present AND has non-empty content
            # Empty dicts/lists/strings should not trigger validation
            return any(
                val is not None and val != '' and val != {} and val != []
                for _, val in targets
            )
        
        elif cond_type == 'if_type':
            # Only validate if value is of specific type
            expected_type = condition.get('value_type', 'object')
            type_map = {'object': dict, 'array': list, 'string': str, 'number': (int, float)}
            return any(isinstance(val, type_map.get(expected_type, object)) for _, val in targets)
        
        elif cond_type == 'conditional':
            # Complex conditional logic
            when_clause = condition.get('when', {})
            return self._evaluate_logic(when_clause, data)
        
        return True
    
    def _validate_value(self, value: Any, validation: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Validate a single value against validation rules.
        
        Args:
            value: Value to validate
            validation: Validation configuration
            context: Full data context for complex validations
        
        Returns:
            True if valid, False otherwise
        """
        val_type = validation.get('type')
        
        # Type validation
        if val_type == 'string':
            if not isinstance(value, str):
                return False
            if 'minLength' in validation and len(value) < validation['minLength']:
                return False
            if 'pattern' in validation and not re.match(validation['pattern'], value):
                return False
        
        elif val_type == 'object':
            if not isinstance(value, dict):
                return False
            if 'minProperties' in validation and len(value) < validation['minProperties']:
                return False
            if 'keys_in' in validation:
                allowed_keys = set(validation['keys_in'])
                if not all(k in allowed_keys for k in value.keys()):
                    return False
        
        elif val_type == 'array':
            if not isinstance(value, list):
                return False
            if 'minItems' in validation and len(value) < validation['minItems']:
                return False
        
        elif val_type == 'logic':
            # Logical validation (OR, AND, NOT)
            return self._evaluate_logic(validation, context, value)
        
        elif val_type == 'object_has_non_empty_value':
            # Check if dict has at least one non-empty value
            if not isinstance(value, dict):
                return False
            return any(
                bool(str(v).strip()) if isinstance(v, str) 
                else bool(v.get('text', '').strip() if isinstance(v, dict) else str(v).strip())
                for v in value.values()
                if v is not None
            )
        
        elif val_type == 'non_empty_string':
            return isinstance(value, str) and bool(value.strip())
        
        elif val_type == 'object_unique_keys':
            # Object keys are unique by definition in JSON/Python dicts
            return True
        
        elif val_type == 'array_contains':
            # Check if array contains item with specific field value
            if not isinstance(value, list):
                return False
            field = validation.get('field')
            target = validation.get('value')
            return any(item.get(field) == target for item in value if isinstance(item, dict))
        
        elif val_type == 'max_nesting_depth':
            # Check maximum nesting depth
            field = validation.get('field')
            max_depth = validation.get('max_depth', 3)
            return self._check_nesting_depth(value, field, max_depth)
        
        elif val_type == 'equals':
            target = validation.get('value')
            return value == target
        
        return True
    
    def _evaluate_logic(self, logic: Dict[str, Any], context: Dict[str, Any], current_value: Any = None) -> bool:
        """
        Evaluate logical expressions (AND, OR, NOT).
        
        Args:
            logic: Logic configuration
            context: Full data context
            current_value: Current value being validated (for nested checks)
        
        Returns:
            Result of logical evaluation
        """
        operator = logic.get('operator', 'and')
        conditions = logic.get('conditions', [])
        
        if operator == 'or':
            # At least one condition must be true
            for cond in conditions:
                if self._evaluate_condition(cond, context, current_value):
                    return True
            return False
        
        elif operator == 'and':
            # All conditions must be true
            for cond in conditions:
                if not self._evaluate_condition(cond, context, current_value):
                    return False
            return True
        
        elif operator == 'not':
            # Negate the result
            if conditions:
                return not self._evaluate_logic(conditions[0], context, current_value)
            return True
        
        # Check 'not' wrapper
        if 'not' in logic:
            return not self._evaluate_logic(logic['not'], context, current_value)
        
        # Check 'path' and 'contains'
        if 'path' in logic and 'contains' in logic:
            targets = self._extract_values(logic['path'], context)
            contains = logic['contains']
            field = contains.get('field')
            value = contains.get('value')
            
            for _, target in targets:
                if isinstance(target, list):
                    if any(item.get(field) == value for item in target if isinstance(item, dict)):
                        return True
            return False
        
        return True
    
    def _evaluate_condition(self, condition: Dict[str, Any], context: Dict[str, Any], current_value: Any) -> bool:
        """
        Evaluate a single condition.
        
        Args:
            condition: Condition configuration
            context: Full data context
            current_value: Current value being validated
        
        Returns:
            True if condition is met
        """
        # If condition has nested logic operator, evaluate recursively
        if 'operator' in condition:
            return self._evaluate_logic(condition, context, current_value)
        
        # Extract value from path if specified
        if 'path' in condition:
            path = condition['path']
            # For relative paths, use current_value
            if isinstance(current_value, dict) and not path.startswith('$'):
                check_value = current_value.get(path)
            else:
                targets = self._extract_values(path, context)
                check_value = targets[0][1] if targets else None
        else:
            check_value = current_value
        
        # Type-specific checks
        cond_type = condition.get('type')
        
        if cond_type == 'object_has_non_empty_value':
            if not isinstance(check_value, dict):
                return False
            return any(
                bool(str(v).strip()) if isinstance(v, str)
                else bool(v.get('text', '').strip() if isinstance(v, dict) else str(v).strip())
                for v in check_value.values()
                if v is not None
            )
        
        elif cond_type == 'non_empty_string':
            return isinstance(check_value, str) and bool(check_value.strip())
        
        elif cond_type == 'equals':
            return check_value == condition.get('value')
        
        elif cond_type == 'array_contains':
            if not isinstance(check_value, list):
                return False
            field = condition.get('field')
            target = condition.get('value')
            return any(item.get(field) == target for item in check_value if isinstance(item, dict))
        
        return False
    
    def _check_nesting_depth(self, value: Any, field: str, max_depth: int, current_depth: int = 0) -> bool:
        """
        Check if nesting depth exceeds maximum.
        
        Args:
            value: Value to check
            field: Field name that contains nested items
            max_depth: Maximum allowed depth
            current_depth: Current depth level
        
        Returns:
            True if depth is within limit
        """
        if current_depth > max_depth:
            return False
        
        if isinstance(value, dict) and field in value:
            nested = value[field]
            if isinstance(nested, list):
                for item in nested:
                    if not self._check_nesting_depth(item, field, max_depth, current_depth + 1):
                        return False
        
        return True
