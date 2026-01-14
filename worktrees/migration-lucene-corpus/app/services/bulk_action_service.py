"""
Bulk Action Service - Action application logic for bulk operations.

Provides execution of bulk actions including:
- Set/Clear/Append/Prepend on fields
- Add/Remove/Replace relations
- Copy from related entries
- Pipeline chaining
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import copy

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of bulk actions."""
    SET = 'set'
    CLEAR = 'clear'
    APPEND = 'append'
    PREPEND = 'prepend'
    ADD_RELATION = 'add_relation'
    REMOVE_RELATION = 'remove_relation'
    REPLACE_RELATION = 'replace_relation'
    COPY_FROM_RELATED = 'copy_from_related'
    PIPELINE = 'pipeline'


@dataclass
class BulkAction:
    """Represents a single bulk action."""
    action: str
    field: Optional[str] = None
    value: Any = None
    target_entry_id: Optional[str] = None
    from_field: Optional[str] = None
    to_field: Optional[str] = None
    relation_type: Optional[str] = None
    old_target: Optional[str] = None
    new_target: Optional[str] = None
    target_in_field: Optional[str] = None
    steps: Optional[List[BulkAction]] = None
    ranges: Optional[Dict[str, List[str]]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BulkAction':
        """Create from dictionary."""
        steps = None
        if data.get('steps'):
            steps = [cls.from_dict(s) for s in data['steps']]

        return cls(
            action=data.get('action', ''),
            field=data.get('field'),
            value=data.get('value'),
            target_entry_id=data.get('target_entry_id'),
            from_field=data.get('from_field'),
            to_field=data.get('to_field'),
            relation_type=data.get('relation_type'),
            old_target=data.get('old_target'),
            new_target=data.get('new_target'),
            target_in_field=data.get('target_in_field'),
            steps=steps,
            ranges=data.get('ranges')
        )


class BulkActionService:
    """Service for executing bulk actions on entries."""

    # Fields that can be modified
    MODIFIABLE_FIELDS = {
        'lexical_unit': 'lexical_unit',
        'lexical_unit.en': 'lexical_unit',
        'grammatical_info': 'grammatical_info',
        'grammatical_info.trait': 'grammatical_info',
        'traits': 'traits',
        'senses': 'senses',
        'senses.*': 'senses',
        'senses.definition': 'senses_definition',
        'senses.gloss': 'senses_gloss',
        'senses.example': 'senses_example',
        'examples': 'examples',
        'pronunciation': 'pronunciation',
    }

    def __init__(self, dictionary_service):
        """
        Initialize the BulkActionService.

        Args:
            dictionary_service: DictionaryService instance.
        """
        self.dictionary = dictionary_service

    def validate_action(self, action: BulkAction) -> Tuple[bool, List[str]]:
        """
        Validate an action before execution.

        Args:
            action: Action to validate.

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []

        # Validate action type
        valid_actions = {a.value for a in ActionType}
        if action.action not in valid_actions:
            errors.append(f"Invalid action type: {action.action}")
            return False, errors

        # Validate field for field-modifying actions
        field_actions = {ActionType.SET.value, ActionType.CLEAR.value,
                        ActionType.APPEND.value, ActionType.PREPEND.value}
        if action.action in field_actions and not action.field:
            errors.append(f"Action '{action.action}' requires a field")

        # Validate relation actions
        relation_actions = {ActionType.ADD_RELATION.value, ActionType.REMOVE_RELATION.value}
        if action.action in relation_actions and not action.relation_type:
            errors.append(f"Action '{action.action}' requires relation_type")

        # Validate copy_from_related
        if action.action == ActionType.COPY_FROM_RELATED.value:
            if not action.from_field and not action.target_in_field:
                errors.append("copy_from_related requires from_field or target_in_field")
            if not action.to_field:
                errors.append("copy_from_related requires to_field")

        # Validate ranges if provided
        if action.ranges:
            errors.extend(self._validate_ranges(action))

        return len(errors) == 0, errors

    def _validate_ranges(self, action: BulkAction) -> List[str]:
        """Validate that action values are within allowed ranges."""
        errors = []

        # This would check against LIFT ranges
        # For now, just basic validation
        if action.ranges.get('allowed_values'):
            if action.value and action.value not in action.ranges['allowed_values']:
                errors.append(f"Value '{action.value}' not in allowed values: {action.ranges['allowed_values']}")

        if action.ranges.get('allowed_types'):
            if action.relation_type and action.relation_type not in action.ranges['allowed_types']:
                errors.append(f"Relation type '{action.relation_type}' not in allowed types")

        return errors

    def execute_action(
        self,
        entry_id: str,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a single action on an entry.

        Args:
            entry_id: Entry ID to modify.
            action: Action to execute.
            related_entries: Optional dict of related entry data for cross-entry ops.
            dry_run: If True, only return what would change.

        Returns:
            Result dict with status, entry_id, and change details.
        """
        try:
            entry = self.dictionary.get_entry(entry_id)
            if not entry:
                return {
                    'entry_id': entry_id,
                    'status': 'error',
                    'error': 'Entry not found'
                }

            # Store original state for diff
            original = copy.deepcopy(entry.to_dict())

            # Execute action based on type
            if action.action == ActionType.SET.value:
                result = self._action_set(entry, action)
            elif action.action == ActionType.CLEAR.value:
                result = self._action_clear(entry, action)
            elif action.action == ActionType.APPEND.value:
                result = self._action_append(entry, action)
            elif action.action == ActionType.PREPEND.value:
                result = self._action_prepend(entry, action)
            elif action.action == ActionType.ADD_RELATION.value:
                result = self._action_add_relation(entry, action, related_entries)
            elif action.action == ActionType.REMOVE_RELATION.value:
                result = self._action_remove_relation(entry, action)
            elif action.action == ActionType.REPLACE_RELATION.value:
                result = self._action_replace_relation(entry, action)
            elif action.action == ActionType.COPY_FROM_RELATED.value:
                result = self._action_copy_from_related(entry, action, related_entries)
            elif action.action == ActionType.PIPELINE.value:
                return self._action_pipeline(entry_id, action, related_entries, dry_run)
            else:
                return {
                    'entry_id': entry_id,
                    'status': 'error',
                    'error': f"Unknown action: {action.action}"
                }

            if dry_run:
                # Return diff without saving
                new_state = entry.to_dict()
                return {
                    'entry_id': entry_id,
                    'status': 'would_change',
                    'changes': self._compute_diff(original, new_state),
                    'dry_run': True
                }

            # Actually save the entry
            if result['status'] == 'changed':
                self.dictionary.update_entry(entry)

            return result

        except Exception as e:
            logger.error(f"Action execution failed for {entry_id}: {e}")
            return {
                'entry_id': entry_id,
                'status': 'error',
                'error': str(e)
            }

    def preview_action(
        self,
        entry_id: str,
        action_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Preview what would change without applying modifications.

        Args:
            entry_id: Entry ID to preview.
            action_data: Action dict with type, field, value, etc.

        Returns:
            Preview dict with change details.
        """
        try:
            # Build action object from dict
            action = BulkAction(
                action=action_data.get('type', 'set'),
                field=action_data.get('field'),
                value=action_data.get('value'),
                relation_type=action_data.get('relation_type'),
            )

            # Validate action
            errors = self.validate_action(action)
            if errors:
                return {
                    'id': entry_id,
                    'would_change': False,
                    'error': '; '.join(errors)
                }

            # Get entry without modifying
            entry = self.dictionary.get_entry(entry_id)
            if not entry:
                return {
                    'id': entry_id,
                    'would_change': False,
                    'error': 'Entry not found'
                }

            # Get current value
            current_value = self._get_field_value(entry, action.field)

            # Compute what would change
            would_change = True
            change_description = ''

            if action.action == ActionType.SET.value:
                new_value = action.value
                if current_value == new_value:
                    would_change = False
                else:
                    change_description = f"Would change {action.field} from '{current_value}' to '{new_value}'"
            elif action.action == ActionType.CLEAR.value:
                if current_value is None or current_value == '':
                    would_change = False
                else:
                    change_description = f"Would clear {action.field} (currently: '{current_value}')"
            elif action.action in (ActionType.APPEND.value, ActionType.PREPEND.value):
                new_value = str(current_value or '') + str(action.value) if action.action == ActionType.APPEND.value else str(action.value) + str(current_value or '')
                change_description = f"Would change {action.field} from '{current_value}' to '{new_value}'"
            elif action.action == ActionType.ADD_RELATION.value:
                change_description = f"Would add {action.relation_type or 'relation'} to target"
            elif action.action == ActionType.REMOVE_RELATION.value:
                change_description = f"Would remove {action.relation_type or 'relation'} relation"
            else:
                change_description = f"Would apply {action.action} to {action.field}"

            return {
                'id': entry_id,
                'would_change': would_change,
                'current_value': current_value,
                'new_value': action.value if action.action == ActionType.SET.value else None,
                'change_description': change_description
            }

        except Exception as e:
            logger.error(f"Preview failed for {entry_id}: {e}")
            return {
                'id': entry_id,
                'would_change': False,
                'error': str(e)
            }

    def _action_set(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute set action."""
        field = action.field
        old_value = self._get_field_value(entry, field)
        self._set_field_value(entry, field, action.value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': old_value,
            'new_value': action.value
        }

    def _action_clear(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute clear action."""
        field = action.field
        old_value = self._get_field_value(entry, field)
        self._set_field_value(entry, field, None)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': old_value,
            'new_value': None
        }

    def _action_append(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute append action."""
        field = action.field
        current = self._get_field_value(entry, field) or ''
        new_value = str(current) + str(action.value)
        self._set_field_value(entry, field, new_value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': current,
            'new_value': new_value
        }

    def _action_prepend(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute prepend action."""
        field = action.field
        current = self._get_field_value(entry, field) or ''
        new_value = str(action.value) + str(current)
        self._set_field_value(entry, field, new_value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': current,
            'new_value': new_value
        }

    def _action_add_relation(
        self,
        entry,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute add_relation action."""
        # Resolve target entry ID
        target_id = action.target_entry_id

        # Handle ${related.id} template
        if target_id and target_id.startswith('${') and related_entries:
            target_id = related_entries.get('id', target_id)

        if not target_id:
            return {
                'entry_id': entry.id,
                'status': 'error',
                'error': 'No target entry ID for relation'
            }

        # Check if relation already exists
        existing = entry.get_related_entries_by_type(action.relation_type)
        if any(r.ref == target_id for r in existing):
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Relation already exists'
            }

        # Add relation
        entry.add_relation(action.relation_type, target_id)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'relation_type': action.relation_type,
            'target_id': target_id,
            'action': 'added'
        }

    def _action_remove_relation(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute remove_relation action."""
        target_id = action.target_entry_id

        if not target_id:
            return {
                'entry_id': entry.id,
                'status': 'error',
                'error': 'No target entry ID for relation'
            }

        # Remove relation
        removed = entry.remove_relation(action.relation_type, target_id)

        if removed:
            return {
                'entry_id': entry.id,
                'status': 'changed',
                'relation_type': action.relation_type,
                'target_id': target_id,
                'action': 'removed'
            }
        else:
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Relation not found'
            }

    def _action_replace_relation(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute replace_relation action."""
        old_id = action.old_target
        new_id = action.new_target

        if not old_id or not new_id:
            return {
                'entry_id': entry.id,
                'status': 'error',
                'error': 'Both old_target and new_target required'
            }

        # Check if old relation exists
        existing = entry.get_related_entries_by_type(action.relation_type)
        if not any(r.ref == old_id for r in existing):
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Old relation not found'
            }

        # Replace relation
        entry.remove_relation(action.relation_type, old_id)
        entry.add_relation(action.relation_type, new_id)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'relation_type': action.relation_type,
            'old_target': old_id,
            'new_target': new_id
        }

    def _action_copy_from_related(
        self,
        entry,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute copy_from_related action."""
        # Get source value
        source_value = None

        if action.target_in_field and related_entries:
            # Get value from related entry
            related_entry = related_entries.get('entry')
            if related_entry:
                source_value = self._get_field_value(related_entry, action.from_field)

        if source_value is None:
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'No source value found'
            }

        # Get current target value
        current_target = self._get_field_value(entry, action.to_field)

        # Skip if target already has same value
        if current_target == source_value:
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Target already has same value'
            }

        # Copy value
        self._set_field_value(entry, action.to_field, source_value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'from_field': action.from_field,
            'to_field': action.to_field,
            'old_value': current_target,
            'new_value': source_value
        }

    def _action_pipeline(
        self,
        entry_id: str,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute pipeline of actions."""
        if not action.steps:
            return {
                'entry_id': entry_id,
                'status': 'error',
                'error': 'Pipeline has no steps'
            }

        results = []
        current_related = related_entries

        for i, step in enumerate(action.steps):
            result = self.execute_action(entry_id, step, current_related, dry_run)
            results.append({
                'step': i + 1,
                'action': step.action,
                'result': result
            })

            # Update related entries if step modified relations
            if step.action == ActionType.ADD_RELATION.value and result['status'] == 'changed':
                # Re-fetch entry to get updated relations
                entry = self.dictionary.get_entry(entry_id)
                if entry and step.relation_type:
                    related = entry.get_related_entries_by_type(step.relation_type)
                    if related:
                        current_related = {
                            'id': related[0].ref,
                            'entry': self.dictionary.get_entry(related[0].ref)
                        }

        return {
            'entry_id': entry_id,
            'status': 'completed',
            'steps': len(action.steps),
            'results': results
        }

    def _get_field_value(self, entry, field: str) -> Any:
        """Get field value from entry using dotted path."""
        parts = field.split('.')
        obj = entry

        for part in parts:
            if part.isdigit():
                # Array index
                if hasattr(obj, '__getitem__') and len(obj) > int(part):
                    obj = obj[int(part)]
                else:
                    return None
            elif hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None

        # Handle special cases
        if hasattr(obj, 'to_dict'):
            obj = obj.to_dict()
        elif hasattr(obj, '__iter__') and not isinstance(obj, str):
            obj = list(obj)

        return obj

    def _set_field_value(self, entry, field: str, value: Any) -> None:
        """Set field value on entry using dotted path."""
        parts = field.split('.')
        obj = entry
        parent = None
        last_part = parts[-1]

        # Navigate to parent
        for part in parts[:-1]:
            if part.isdigit():
                if hasattr(obj, '__getitem__'):
                    obj = obj[int(part)]
                else:
                    return
            elif hasattr(obj, part):
                parent = obj
                obj = getattr(obj, part)
                if hasattr(obj, 'to_dict'):
                    obj = obj.to_dict()
            else:
                return

        # Set value
        if hasattr(obj, last_part):
            if last_part == 'trait' and hasattr(obj, 'value'):
                # Handle grammatical_info trait
                obj.value = value
            elif hasattr(obj, last_part):
                setattr(obj, last_part, value)

    def _compute_diff(self, original: Dict, new: Dict) -> List[Dict]:
        """Compute diff between two entry dicts."""
        changes = []

        def compare(orig, nev, path=''):
            if isinstance(orig, dict) and isinstance(nev, dict):
                for key in set(orig.keys()) | set(nev.keys()):
                    opath = f'{path}.{key}' if path else key
                    if key not in orig:
                        changes.append({
                            'field': opath,
                            'old_value': None,
                            'new_value': nev[key]
                        })
                    elif key not in nev:
                        changes.append({
                            'field': opath,
                            'old_value': orig[key],
                            'new_value': None
                        })
                    elif orig[key] != nev[key]:
                        if not isinstance(orig[key], (dict, list)):
                            changes.append({
                                'field': opath,
                                'old_value': orig[key],
                                'new_value': nev[key]
                            })
                        else:
                            compare(orig[key], nev[key], opath)
            elif isinstance(orig, list) and isinstance(nev, list):
                if orig != nev:
                    changes.append({
                        'field': path,
                        'old_value': orig,
                        'new_value': nev
                    })

        compare(original, new)
        return changes
