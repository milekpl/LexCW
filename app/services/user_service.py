"""
User management service for user operations and project roles.
"""

from typing import List, Optional
from datetime import datetime, timezone

from app.models.workset_models import db
from app.models.project_settings import User, ProjectSettings
from app.models.user_models import ProjectRole, UserRole, ActivityLog, Notification


class UserManagementService:
    """Service for managing users and project memberships."""

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID."""
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username."""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email."""
        return User.query.filter_by(email=email).first()

    @staticmethod
    def list_users(active_only: bool = True) -> List[User]:
        """List all users."""
        query = User.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(User.created_at.desc()).all()

    @staticmethod
    def deactivate_user(user_id: int, admin_user_id: int) -> tuple[bool, Optional[str]]:
        """
        Deactivate a user account.

        Args:
            user_id: ID of user to deactivate
            admin_user_id: ID of admin performing the action

        Returns:
            Tuple of (success, error_message)
        """
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        user.is_active = False
        db.session.commit()

        # Log the deactivation
        log = ActivityLog(
            user_id=admin_user_id,
            action="deactivate_user",
            entity_type="user",
            entity_id=str(user_id),
            description=f"User {user.username} deactivated",
        )
        db.session.add(log)
        db.session.commit()

        return True, None

    @staticmethod
    def reactivate_user(user_id: int, admin_user_id: int) -> tuple[bool, Optional[str]]:
        """
        Reactivate a user account.

        Args:
            user_id: ID of user to reactivate
            admin_user_id: ID of admin performing the action

        Returns:
            Tuple of (success, error_message)
        """
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        user.is_active = True
        db.session.commit()

        # Log the reactivation
        log = ActivityLog(
            user_id=admin_user_id,
            action="reactivate_user",
            entity_type="user",
            entity_id=str(user_id),
            description=f"User {user.username} reactivated",
        )
        db.session.add(log)
        db.session.commit()

        return True, None

    @staticmethod
    def add_user_to_project(
        user_id: int, project_id: int, role: UserRole, granted_by_user_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Add a user to a project with a specific role.

        Args:
            user_id: User to add
            project_id: Project to add user to
            role: Role to grant
            granted_by_user_id: User granting access

        Returns:
            Tuple of (success, error_message)
        """
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        # Check if project exists
        project = ProjectSettings.query.get(project_id)
        if not project:
            return False, "Project not found"

        # Check if user already has a role
        existing_role = ProjectRole.query.filter_by(
            user_id=user_id, project_id=project_id
        ).first()

        if existing_role:
            return False, "User already has access to this project"

        # Add the role
        project_role = ProjectRole(
            user_id=user_id,
            project_id=project_id,
            role=role,
            granted_by_user_id=granted_by_user_id,
        )
        db.session.add(project_role)
        db.session.commit()

        # Log the addition
        log = ActivityLog(
            user_id=granted_by_user_id,
            action="add_project_member",
            entity_type="project",
            entity_id=str(project_id),
            project_id=project_id,
            changes={"user_id": user_id, "role": role.value},
            description=f"Added {user.username} to project with role {role.value}",
        )
        db.session.add(log)
        db.session.commit()

        # Create notification for the user
        notification = Notification(
            user_id=user_id,
            notification_type="project_access",
            title="Added to Project",
            message=f'You have been added to project "{project.project_name}" with {role.value} access.',
            link_url=f"/projects/{project_id}",
        )
        db.session.add(notification)
        db.session.commit()

        return True, None

    @staticmethod
    def remove_user_from_project(
        user_id: int, project_id: int, removed_by_user_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Remove a user from a project.

        Args:
            user_id: User to remove
            project_id: Project to remove user from
            removed_by_user_id: User performing the removal

        Returns:
            Tuple of (success, error_message)
        """
        # Find the role
        project_role = ProjectRole.query.filter_by(
            user_id=user_id, project_id=project_id
        ).first()

        if not project_role:
            return False, "User does not have access to this project"

        # Get user for logging
        user = User.query.get(user_id)

        # Remove the role
        db.session.delete(project_role)
        db.session.commit()

        # Log the removal
        log = ActivityLog(
            user_id=removed_by_user_id,
            action="remove_project_member",
            entity_type="project",
            entity_id=str(project_id),
            project_id=project_id,
            changes={"user_id": user_id},
            description=f"Removed {user.username if user else user_id} from project",
        )
        db.session.add(log)
        db.session.commit()

        return True, None

    @staticmethod
    def update_user_project_role(
        user_id: int, project_id: int, new_role: UserRole, updated_by_user_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Update a user's role in a project.

        Args:
            user_id: User whose role to update
            project_id: Project
            new_role: New role
            updated_by_user_id: User performing the update

        Returns:
            Tuple of (success, error_message)
        """
        # Find the role
        project_role = ProjectRole.query.filter_by(
            user_id=user_id, project_id=project_id
        ).first()

        if not project_role:
            return False, "User does not have access to this project"

        old_role = project_role.role
        project_role.role = new_role
        db.session.commit()

        # Get user for logging
        user = User.query.get(user_id)

        # Log the update
        log = ActivityLog(
            user_id=updated_by_user_id,
            action="update_project_role",
            entity_type="project",
            entity_id=str(project_id),
            project_id=project_id,
            changes={
                "user_id": user_id,
                "old_role": old_role.value,
                "new_role": new_role.value,
            },
            description=f"Updated {user.username if user else user_id} role from {old_role.value} to {new_role.value}",
        )
        db.session.add(log)
        db.session.commit()

        return True, None

    @staticmethod
    def get_user_projects(user_id: int) -> List[dict]:
        """
        Get all projects a user has access to.

        Args:
            user_id: User ID

        Returns:
            List of project dictionaries with role information
        """
        roles = ProjectRole.query.filter_by(user_id=user_id).all()

        projects = []
        for role in roles:
            if role.project:
                projects.append(
                    {
                        "project": role.project.serialization_dict,
                        "project_id": role.project_id,
                        "role": role.role.value,
                        "granted_at": role.granted_at.isoformat()
                        if role.granted_at
                        else None,
                    }
                )

        return projects

    @staticmethod
    def get_project_members(project_id: int) -> List[dict]:
        """
        Get all members of a project.

        Args:
            project_id: Project ID

        Returns:
            List of user dictionaries with role information
        """
        roles = ProjectRole.query.filter_by(project_id=project_id).all()

        members = []
        for role in roles:
            if role.user:
                members.append(
                    {
                        "user": role.user.to_dict(),
                        "role": role.role.value,
                        "granted_at": role.granted_at.isoformat()
                        if role.granted_at
                        else None,
                        "granted_by": role.granted_by.to_dict()
                        if role.granted_by
                        else None,
                    }
                )

        return members

    @staticmethod
    def has_project_access(user_id: int, project_id: int) -> bool:
        """Check if user has access to a project."""
        # Check if user is admin
        user = User.query.get(user_id)
        if user and user.is_admin:
            return True

        # Check if user has a role in the project
        role = ProjectRole.query.filter_by(
            user_id=user_id, project_id=project_id
        ).first()

        return role is not None

    @staticmethod
    def get_user_role_in_project(user_id: int, project_id: int) -> Optional[UserRole]:
        """Get user's role in a project."""
        # Check if user is admin
        user = User.query.get(user_id)
        if user and user.is_admin:
            return UserRole.ADMIN

        # Get user's role
        role = ProjectRole.query.filter_by(
            user_id=user_id, project_id=project_id
        ).first()

        return role.role if role else None
