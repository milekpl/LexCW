"""
Message service for entry discussions and notifications.
"""

from typing import List, Optional
from datetime import datetime, timezone

from app.models.workset_models import db
from app.models.project_settings import User
from app.models.user_models import Message, Notification, ActivityLog


class MessageService:
    """Service for managing messages and notifications."""

    @staticmethod
    def create_message(
        entry_id: str,
        sender_user_id: int,
        message_text: str,
        workset_id: Optional[int] = None,
        recipient_user_id: Optional[int] = None,
        parent_message_id: Optional[int] = None,
    ) -> tuple[Optional[Message], Optional[str]]:
        """
        Create a new message for an entry.

        Args:
            entry_id: Entry this message is about
            sender_user_id: User sending the message
            message_text: Message content
            workset_id: Optional workset context
            recipient_user_id: Optional recipient for direct messages
            parent_message_id: Optional parent for threaded replies

        Returns:
            Tuple of (message, error_message)
        """
        if not message_text.strip():
            return None, "Message cannot be empty"

        # Create message
        message = Message(
            entry_id=entry_id,
            sender_user_id=sender_user_id,
            message_text=message_text.strip(),
            workset_id=workset_id,
            recipient_user_id=recipient_user_id,
            parent_message_id=parent_message_id,
        )

        db.session.add(message)
        db.session.commit()

        # Create notification for recipient if specified
        if recipient_user_id:
            sender = User.query.get(sender_user_id)
            notification = Notification(
                user_id=recipient_user_id,
                notification_type="message",
                title=f"New message from {sender.username if sender else 'user'}",
                message=message_text[:100],  # Truncate for notification
                link_url=f"/entries/{entry_id}#message-{message.id}",
                related_message_id=message.id,
                related_entry_id=entry_id,
            )
            db.session.add(notification)
            db.session.commit()

        # Log the message creation
        log = ActivityLog(
            user_id=sender_user_id,
            action="create_message",
            entity_type="entry",
            entity_id=entry_id,
            description=f"Created message on entry {entry_id}",
        )
        db.session.add(log)
        db.session.commit()

        return message, None

    @staticmethod
    def get_entry_messages(
        entry_id: str, workset_id: Optional[int] = None, include_replies: bool = True
    ) -> List[Message]:
        """
        Get all messages for an entry.

        Args:
            entry_id: Entry ID
            workset_id: Optional workset filter
            include_replies: Whether to include reply threads

        Returns:
            List of messages
        """
        query = Message.query.filter_by(entry_id=entry_id)

        if workset_id:
            query = query.filter_by(workset_id=workset_id)

        if not include_replies:
            query = query.filter_by(parent_message_id=None)

        return query.order_by(Message.created_at.asc()).all()

    @staticmethod
    def get_message_thread(message_id: int) -> List[Message]:
        """
        Get a message and all its replies.

        Args:
            message_id: Root message ID

        Returns:
            List of messages in thread
        """
        root_message = Message.query.get(message_id)
        if not root_message:
            return []

        thread = [root_message]
        if hasattr(root_message, "replies") and root_message.replies:
            thread.extend(root_message.replies)

        return thread

    @staticmethod
    def mark_message_as_read(
        message_id: int, user_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Mark a message as read.

        Args:
            message_id: Message ID
            user_id: User ID (must be recipient or admin)

        Returns:
            Tuple of (success, error_message)
        """
        message = Message.query.get(message_id)
        if not message:
            return False, "Message not found"

        # Verify user is recipient or admin
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        if message.recipient_user_id != user_id and not user.is_admin:
            return False, "Not authorized to mark this message as read"

        message.is_read = True
        db.session.commit()

        return True, None

    @staticmethod
    def delete_message(message_id: int, user_id: int) -> tuple[bool, Optional[str]]:
        """
        Delete a message.

        Args:
            message_id: Message ID
            user_id: User ID (must be sender or admin)

        Returns:
            Tuple of (success, error_message)
        """
        message = Message.query.get(message_id)
        if not message:
            return False, "Message not found"

        # Verify user is sender or admin
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        if message.sender_user_id != user_id and not user.is_admin:
            return False, "Not authorized to delete this message"

        # Log the deletion
        log = ActivityLog(
            user_id=user_id,
            action="delete_message",
            entity_type="entry",
            entity_id=message.entry_id,
            description=f"Deleted message {message_id} on entry {message.entry_id}",
        )
        db.session.add(log)

        db.session.delete(message)
        db.session.commit()

        return True, None

    @staticmethod
    def get_user_unread_messages(user_id: int) -> List[Message]:
        """Get all unread messages for a user."""
        return (
            Message.query.filter_by(recipient_user_id=user_id, is_read=False)
            .order_by(Message.created_at.desc())
            .all()
        )

    @staticmethod
    def create_notification(
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        related_entry_id: Optional[str] = None,
    ) -> Notification:
        """
        Create a notification for a user.

        Args:
            user_id: User to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            link_url: Optional link
            related_entry_id: Optional related entry

        Returns:
            Created notification
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link_url=link_url,
            related_entry_id=related_entry_id,
        )

        db.session.add(notification)
        db.session.commit()

        return notification

    @staticmethod
    def get_user_notifications(
        user_id: int, unread_only: bool = False, limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Maximum number of notifications

        Returns:
            List of notifications
        """
        query = Notification.query.filter_by(user_id=user_id)

        if unread_only:
            query = query.filter_by(is_read=False)

        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def mark_notification_as_read(
        notification_id: int, user_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID

        Returns:
            Tuple of (success, error_message)
        """
        notification = Notification.query.get(notification_id)
        if not notification:
            return False, "Notification not found"

        if notification.user_id != user_id:
            return False, "Not authorized"

        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.session.commit()

        return True, None

    @staticmethod
    def mark_all_notifications_as_read(user_id: int) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        count = Notification.query.filter_by(user_id=user_id, is_read=False).update(
            {"is_read": True, "read_at": datetime.now(timezone.utc)}
        )

        db.session.commit()

        return count

    @staticmethod
    def get_unread_notification_count(user_id: int) -> int:
        """Get count of unread notifications for a user."""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
