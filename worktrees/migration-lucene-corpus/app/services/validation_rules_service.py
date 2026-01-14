"""
Validation Rules Service.

Provides CRUD operations and management for project-specific validation rules.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask

from app.models.workset_models import db
from app.models.validation_models import ProjectValidationRule, ValidationRuleTemplate


logger = logging.getLogger(__name__)


class ValidationRulesService:
    """
    Service for managing validation rules.

    Handles project-specific rule storage, template loading, and rule testing.
    """

    def __init__(self, app: Optional[Flask] = None) -> None:
        """Initialize the service."""
        self.app = app
        self._default_rules_cache: Optional[Dict[str, Any]] = None
        self._template_files_cache: Optional[List[Dict[str, Any]]] = None

    def init_app(self, app: Flask) -> None:
        """Initialize with Flask application context."""
        self.app = app

    # ========== Template Loading Methods ==========

    def _load_templates_from_files(self) -> List[Dict[str, Any]]:
        """Load templates from JSON files in the templates directory.

        Returns:
            List of template configurations
        """
        if self._template_files_cache is not None:
            return self._template_files_cache

        templates: List[Dict[str, Any]] = []
        templates_dir = Path(__file__).parent.parent / "data" / "validation_templates"

        if not templates_dir.exists():
            logger.warning(f"Templates directory not found: {templates_dir}")
            self._template_files_cache = templates
            return templates

        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    # Ensure template has rules as a list
                    if 'rules' in template_data and isinstance(template_data['rules'], dict):
                        # Convert rules dict to list format
                        rules_list = []
                        for rule_id, rule_config in template_data['rules'].items():
                            rule_config['rule_id'] = rule_id
                            rules_list.append(rule_config)
                        template_data['rules'] = rules_list
                    templates.append(template_data)
            except Exception as e:
                logger.error(f"Error loading template {template_file}: {e}")

        self._template_files_cache = templates
        return templates

    def get_template_from_file(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template from file system.

        Args:
            template_id: The template identifier

        Returns:
            Template configuration or None
        """
        templates = self._load_templates_from_files()
        for template in templates:
            if template.get('template_id') == template_id:
                return template
        return None

    def get_templates_from_files(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available templates from file system.

        Args:
            category: Optional category filter

        Returns:
            List of template configurations
        """
        templates = self._load_templates_from_files()

        if category:
            templates = [t for t in templates if t.get('category') == category]

        return templates

    def get_project_rules(self, project_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all validation rules for a project.

        Args:
            project_id: The project identifier
            include_inactive: Whether to include inactive rules

        Returns:
            List of rule configurations
        """
        if not self.app:
            raise RuntimeError("Service not initialized with Flask app")

        with self.app.app_context():
            return ProjectValidationRule.get_rules_for_project(project_id, include_inactive)

    def save_project_rules(
        self,
        project_id: str,
        rules: List[Dict[str, Any]],
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save validation rules for a project.

        Args:
            project_id: The project identifier
            rules: List of rule configurations
            created_by: User who made the changes

        Returns:
            Summary of save operation
        """
        if not self.app:
            raise RuntimeError("Service not initialized with Flask app")

        with self.app.app_context():
            # Validate rules before saving
            validation_errors = self._validate_rules(rules)
            if validation_errors:
                return {
                    'success': False,
                    'errors': validation_errors,
                    'rules_saved': 0
                }

            count = ProjectValidationRule.save_rules_for_project(
                project_id=project_id,
                rules=rules,
                created_by=created_by
            )

            return {
                'success': True,
                'rules_saved': count,
                'errors': []
            }

    def delete_project_rules(self, project_id: str) -> int:
        """
        Delete all rules for a project.

        Args:
            project_id: The project identifier

        Returns:
            Number of rules deleted
        """
        if not self.app:
            raise RuntimeError("Service not initialized with Flask app")

        with self.app.app_context():
            return ProjectValidationRule.delete_rules_for_project(project_id)

    def get_project_rule(self, project_id: str, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific rule for a project.

        Args:
            project_id: The project identifier
            rule_id: The rule identifier

        Returns:
            Rule configuration or None
        """
        if not self.app:
            raise RuntimeError("Service not initialized with Flask app")

        with self.app.app_context():
            return ProjectValidationRule.get_rule_by_id(project_id, rule_id)

    def get_effective_rules(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get effective rules for a project.

        If the project has custom rules, return those.
        Otherwise, return the default rules.

        Args:
            project_id: The project identifier

        Returns:
            List of effective rule configurations
        """
        project_rules = self.get_project_rules(project_id)

        if project_rules:
            return project_rules

        # Fall back to default rules
        return self.get_default_rules()

    def get_default_rules(self) -> List[Dict[str, Any]]:
        """
        Get the default validation rules.

        Loads from validation_rules_v2.json in the app data directory.

        Returns:
            List of default rule configurations
        """
        if self._default_rules_cache is not None:
            return self._default_rules_cache

        try:
            # Look in multiple locations for the default rules file
            app_dir = Path(__file__).parent.parent
            rules_file = app_dir / 'data' / 'validation_rules_v2.json'

            # Also check the project root (where validation_rules_v2.json actually is)
            root_file = Path(__file__).parent.parent.parent / 'validation_rules_v2.json'

            if root_file.exists():
                rules_file = root_file
            elif not rules_file.exists():
                logger.warning(f"Default validation rules file not found: {rules_file}")
                self._default_rules_cache = []
                return self._default_rules_cache

            with open(rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Extract rules from the format used by validation engine
                if 'rules' in data:
                    rules_dict = data['rules']
                    # Convert dict to list format with rule_id included
                    if isinstance(rules_dict, dict):
                        self._default_rules_cache = []
                        for rule_id, rule_config in rules_dict.items():
                            rule_config = dict(rule_config)  # Make a copy
                            rule_config['rule_id'] = rule_id
                            self._default_rules_cache.append(rule_config)
                    else:
                        self._default_rules_cache = rules_dict
                elif isinstance(data, list):
                    self._default_rules_cache = data
                else:
                    self._default_rules_cache = []
        except Exception as e:
            logger.error(f"Error loading default validation rules: {e}")
            self._default_rules_cache = []

        return self._default_rules_cache

    def get_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available validation rule templates.

        First checks database, then falls back to file-based templates.
        Combines results, preferring database entries.

        Args:
            category: Optional category filter

        Returns:
            List of template configurations
        """
        if not self.app:
            raise RuntimeError("Service not initialized with Flask app")

        with self.app.app_context():
            # Get database templates
            db_templates: List[Dict[str, Any]] = []
            if category:
                db_templates = ValidationRuleTemplate.get_templates_by_category(category)
            else:
                db_templates = ValidationRuleTemplate.get_all_templates()

            # Get file-based templates
            file_templates = self.get_templates_from_files(category)

            # Create set of existing template_ids from database
            existing_ids = {t.get('template_id') for t in db_templates}

            # Add file templates that don't exist in database
            for file_template in file_templates:
                if file_template.get('template_id') not in existing_ids:
                    db_templates.append(file_template)

            return db_templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template.

        First checks database, then falls back to file-based template.

        Args:
            template_id: The template identifier

        Returns:
            Template configuration or None
        """
        if not self.app:
            raise RuntimeError("Service not initialized with Flask app")

        with self.app.app_context():
            # Check database first
            db_template = ValidationRuleTemplate.get_template_by_id(template_id)
            if db_template:
                return db_template

            # Fall back to file-based template
            return self.get_template_from_file(template_id)

    def initialize_project_rules(
        self,
        project_id: str,
        template_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize validation rules for a new project.

        Args:
            project_id: The project identifier
            template_id: Optional template to use (defaults to basic)
            created_by: User who initialized the rules

        Returns:
            Summary of initialization
        """
        if not self.app:
            raise RuntimeError("Service not initialized with Flask app")

        with self.app.app_context():
            # Check if project already has rules
            existing_rules = ProjectValidationRule.get_rules_for_project(project_id)
            if existing_rules:
                return {
                    'success': False,
                    'message': 'Project already has validation rules',
                    'rules_count': len(existing_rules)
                }

            # Get rules from template or defaults
            if template_id:
                template = ValidationRuleTemplate.get_template_by_id(template_id)
                if template:
                    rules = template.get('rules', [])
                else:
                    return {
                        'success': False,
                        'message': f'Template not found: {template_id}'
                    }
            else:
                # Use default rules
                rules = self.get_default_rules()

            # Save rules for project
            count = ProjectValidationRule.save_rules_for_project(
                project_id=project_id,
                rules=rules,
                created_by=created_by
            )

            return {
                'success': True,
                'message': f'Initialized {count} validation rules',
                'rules_count': count,
                'source': 'template' if template_id else 'defaults'
            }

    def test_rule(
        self,
        rule_config: Dict[str, Any],
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test a validation rule against sample data.

        Args:
            rule_config: The rule configuration to test
            test_data: Sample data to validate against

        Returns:
            Validation result with 'valid' boolean and 'errors' list
        """
        from app.services.validation_engine import ValidationEngine

        # Create a temporary engine with just the test rule
        test_rules = {rule_config.get('rule_id', 'test'): rule_config}
        engine = ValidationEngine(project_rules=test_rules)

        try:
            result = engine.validate_entry(test_data, validation_mode="save")

            return {
                'valid': result.is_valid,
                'errors': [e.message for e in result.errors],
                'warnings': [e.message for e in result.warnings],
                'info': [e.message for e in result.info]
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Rule configuration error: {str(e)}"],
                'warnings': [],
                'info': []
            }

    def export_rules(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Export validation rules for a project.

        Args:
            project_id: The project identifier

        Returns:
            Export data with metadata, or None if no rules
        """
        rules = self.get_project_rules(project_id, include_inactive=False)

        if not rules:
            return None

        return {
            'project_id': project_id,
            'exported_at': datetime.utcnow().isoformat(),
            'version': '1.0',
            'rules': rules
        }

    def import_rules(
        self,
        project_id: str,
        import_data: Dict[str, Any],
        replace: bool = False,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import validation rules for a project.

        Args:
            project_id: The project identifier
            import_data: The imported rule data
            replace: If True, replace all existing rules
            created_by: User who imported the rules

        Returns:
            Summary of import operation
        """
        rules = import_data.get('rules', [])

        if not rules:
            return {
                'success': False,
                'message': 'No rules found in import data'
            }

        with self.app.app_context():
            if replace:
                # Delete existing rules first
                ProjectValidationRule.delete_rules_for_project(project_id)

            # Save imported rules
            count = ProjectValidationRule.save_rules_for_project(
                project_id=project_id,
                rules=rules,
                created_by=created_by
            )

            return {
                'success': True,
                'message': f'Imported {count} validation rules',
                'rules_count': count
            }

    def _validate_rules(self, rules: List[Dict[str, Any]]) -> List[str]:
        """
        Validate rule configurations before saving.

        Args:
            rules: List of rule configurations

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for i, rule in enumerate(rules):
            rule_errors = self._validate_rule_config(rule, i)
            errors.extend(rule_errors)

        return errors

    def _validate_rule_config(
        self,
        rule: Dict[str, Any],
        index: int
    ) -> List[str]:
        """
        Validate a single rule configuration.

        Args:
            rule: Rule configuration
            index: Rule index for error messages

        Returns:
            List of validation errors
        """
        errors = []
        prefix = f"Rule[{index}]"

        # Required fields
        if not rule.get('rule_id'):
            errors.append(f"{prefix}: rule_id is required")
        if not rule.get('name'):
            errors.append(f"{prefix}: name is required")

        # Validate condition type
        valid_condition_types = ['required', 'if_present', 'custom', 'prohibited']
        condition = rule.get('condition', {})
        condition_type = condition.get('type') if condition else None
        if condition_type and condition_type not in valid_condition_types:
            errors.append(
                f"{prefix}: invalid condition type '{condition_type}', "
                f"must be one of {valid_condition_types}"
            )

        # Validate validation type
        valid_validation_types = ['string', 'array', 'object', 'number', 'boolean', 'custom']
        validation = rule.get('validation', {})
        validation_type = validation.get('type') if validation else None
        if validation_type and validation_type not in valid_validation_types:
            errors.append(
                f"{prefix}: invalid validation type '{validation_type}', "
                f"must be one of {valid_validation_types}"
            )

        # Validate priority
        valid_priorities = ['critical', 'warning', 'informational']
        priority = rule.get('priority')
        if priority and priority not in valid_priorities:
            errors.append(
                f"{prefix}: invalid priority '{priority}', "
                f"must be one of {valid_priorities}"
            )

        # Validate category
        valid_categories = [
            'entry_level', 'sense_level', 'note_validation',
            'pronunciation_level', 'relations_level', 'general'
        ]
        category = rule.get('category')
        if category and category not in valid_categories:
            errors.append(
                f"{prefix}: invalid category '{category}', "
                f"must be one of {valid_categories}"
            )

        # Validate JSONPath if present
        path = rule.get('path')
        if path:
            try:
                import jsonpath_ng
                jsonpath_ng.parse(path)
            except Exception:
                errors.append(f"{prefix}: invalid JSONPath expression '{path}'")

        # Validate pattern if present
        validation = rule.get('validation', {})
        pattern = validation.get('pattern') or validation.get('not_pattern')
        if pattern:
            try:
                import re
                re.compile(pattern)
            except Exception:
                errors.append(f"{prefix}: invalid regex pattern '{pattern}'")

        return errors


# Singleton instance for use across the application
_validation_rules_service: Optional[ValidationRulesService] = None


def get_validation_rules_service() -> ValidationRulesService:
    """Get or create the validation rules service singleton.

    If the service hasn't been initialized with a Flask app, returns a
    new instance without app context (limited functionality).
    """
    global _validation_rules_service
    if _validation_rules_service is None:
        _validation_rules_service = ValidationRulesService()
    return _validation_rules_service


def init_validation_rules_service(app=None) -> ValidationRulesService:
    """Initialize the validation rules service with a Flask app.

    Args:
        app: Flask application instance

    Returns:
        Initialized ValidationRulesService
    """
    global _validation_rules_service
    _validation_rules_service = ValidationRulesService(app=app)
    return _validation_rules_service
