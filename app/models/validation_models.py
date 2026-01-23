"""
Validation Rule Models.

Database models for project-specific validation rules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.workset_models import db


class ProjectValidationRule(db.Model):
    """
    Project-specific validation rule storage.

    Each project can have its own set of validation rules that override
    or extend the default system rules.
    """
    __tablename__ = 'project_validation_rules'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    rule_id = db.Column(db.String(50), nullable=False, index=True)
    rule_config = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'rule_id', name='uq_project_rule_id'),
    )

    def __repr__(self) -> str:
        return f"<ProjectValidationRule {self.project_id}:{self.rule_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'rule_id': self.rule_id,
            'rule_config': self.rule_config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'is_active': self.is_active
        }

    def to_rule_config(self) -> Dict[str, Any]:
        """Return just the rule configuration (without metadata)."""
        return self.rule_config

    @classmethod
    def create_from_config(
        cls,
        project_id: str,
        rule_id: str,
        config: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> 'ProjectValidationRule':
        """Create a new validation rule from configuration dict."""
        rule = cls(
            project_id=project_id,
            rule_id=rule_id,
            rule_config=config,
            created_by=created_by
        )
        return rule

    @staticmethod
    def get_rules_for_project(project_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all active rules for a project.

        Args:
            project_id: The project identifier
            include_inactive: Whether to include inactive rules

        Returns:
            List of rule configurations
        """
        query = db.session.query(ProjectValidationRule).filter(
            ProjectValidationRule.project_id == project_id
        )

        if not include_inactive:
            query = query.filter(ProjectValidationRule.is_active == True)

        rules = query.order_by(ProjectValidationRule.rule_id).all()
        return [rule.to_rule_config() for rule in rules]

    @staticmethod
    def save_rules_for_project(
        project_id: str,
        rules: List[Dict[str, Any]],
        created_by: Optional[str] = None
    ) -> int:
        """
        Save a batch of rules for a project.

        This performs an upsert - existing rules are updated, new rules are created,
        rules not in the list are deactivated.

        Args:
            project_id: The project identifier
            rules: List of rule configurations
            created_by: User who made the changes

        Returns:
            Number of rules saved
        """
        existing_rules = db.session.query(ProjectValidationRule).filter(
            ProjectValidationRule.project_id == project_id
        ).all()

        existing_by_id = {r.rule_id: r for r in existing_rules}
        incoming_ids = {r.get('rule_id') for r in rules if r.get('rule_id')}

        saved_count = 0

        # Update or create rules
        for rule_config in rules:
            rule_id = rule_config.get('rule_id')
            if not rule_id:
                continue

            if rule_id in existing_by_id:
                # Update existing
                rule = existing_by_id[rule_id]
                rule.rule_config = rule_config
                rule.updated_at = datetime.utcnow()
                saved_count += 1
            else:
                # Create new
                rule = ProjectValidationRule.create_from_config(
                    project_id=project_id,
                    rule_id=rule_id,
                    config=rule_config,
                    created_by=created_by
                )
                db.session.add(rule)
                saved_count += 1

        # Deactivate rules not in the incoming list
        for rule_id, rule in existing_by_id.items():
            if rule_id not in incoming_ids:
                rule.is_active = False

        db.session.commit()
        return saved_count

    @staticmethod
    def add_rules_for_project(
        project_id: str,
        rules: List[Dict[str, Any]],
        created_by: Optional[str] = None
    ) -> int:
        """
        Add new rules for a project without modifying existing rules.

        This method ONLY creates new rules - it does NOT update or deactivate
        existing rules. Use this when you want to merge rules without losing
        existing configurations.

        Args:
            project_id: The project identifier
            rules: List of new rule configurations to add
            created_by: User who made the changes

        Returns:
            Number of rules added
        """
        existing_rules = db.session.query(ProjectValidationRule).filter(
            ProjectValidationRule.project_id == project_id
        ).all()

        existing_by_id = {r.rule_id: r for r in existing_rules}

        added_count = 0

        # Only create new rules, don't touch existing ones
        for rule_config in rules:
            rule_id = rule_config.get('rule_id')
            if not rule_id:
                continue

            if rule_id in existing_by_id:
                # Skip - rule already exists
                continue

            # Create new rule
            rule = ProjectValidationRule.create_from_config(
                project_id=project_id,
                rule_id=rule_id,
                config=rule_config,
                created_by=created_by
            )
            db.session.add(rule)
            added_count += 1

        if added_count > 0:
            db.session.commit()

        return added_count

    @staticmethod
    def delete_rules_for_project(project_id: str) -> int:
        """
        Delete all rules for a project.

        Args:
            project_id: The project identifier

        Returns:
            Number of rules deleted
        """
        count = db.session.query(ProjectValidationRule).filter(
            ProjectValidationRule.project_id == project_id
        ).delete()

        db.session.commit()
        return count

    @staticmethod
    def get_rule_by_id(project_id: str, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific rule by ID for a project.

        Args:
            project_id: The project identifier
            rule_id: The rule identifier

        Returns:
            Rule configuration or None
        """
        rule = db.session.query(ProjectValidationRule).filter(
            ProjectValidationRule.project_id == project_id,
            ProjectValidationRule.rule_id == rule_id,
            ProjectValidationRule.is_active == True
        ).first()

        return rule.to_rule_config() if rule else None


class ValidationRuleTemplate(db.Model):
    """
    Storage for validation rule templates.

    Templates are predefined sets of rules that can be applied to projects.
    """
    __tablename__ = 'validation_rule_templates'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)  # Basic, Academic, Bilingual, Research
    rules = db.Column(db.JSON, nullable=False)
    is_system = db.Column(db.Boolean, default=False)  # System templates cannot be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ValidationRuleTemplate {self.template_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'rules': self.rules,
            'is_system': self.is_system
        }

    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        """Get all available templates."""
        templates = db.session.query(ValidationRuleTemplate).all()
        return [t.to_dict() for t in templates]

    @staticmethod
    def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID."""
        template = db.session.query(ValidationRuleTemplate).filter(
            ValidationRuleTemplate.template_id == template_id
        ).first()

        return template.to_dict() if template else None

    @staticmethod
    def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
        """Get templates by category."""
        templates = db.session.query(ValidationRuleTemplate).filter(
            ValidationRuleTemplate.category == category
        ).all()
        return [t.to_dict() for t in templates]

    @staticmethod
    def create_template(
        template_id: str,
        name: str,
        rules: List[Dict[str, Any]],
        description: str = None,
        category: str = None,
        is_system: bool = False
    ) -> 'ValidationRuleTemplate':
        """Create a new template."""
        template = ValidationRuleTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            rules=rules,
            is_system=is_system
        )
        db.session.add(template)
        db.session.commit()
        return template
