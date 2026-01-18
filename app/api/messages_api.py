"""
Messages API blueprint for entry discussions and notifications.
"""

from flask import Blueprint, request, jsonify, g
from app.services.message_service import MessageService
from app.utils.auth_decorators import login_required, project_access_required

messages_api_bp = Blueprint("messages_api", __name__, url_prefix="/api/messages")


@messages_api_bp.route("/entries/<entry_id>", methods=["GET"])
@login_required
def get_entry_messages(entry_id):
    """
    Get all messages for an entry.
    ---
    tags:
      - Messages
    parameters:
      - in: path
        name: entry_id
        type: string
        required: true
      - in: query
        name: workset_id
        type: integer
        description: Filter by workset
      - in: query
        name: include_replies
        type: boolean
        default: true
    responses:
      200:
        description: List of messages
    """
    workset_id = request.args.get("workset_id", type=int)
    include_replies = request.args.get("include_replies", "true").lower() == "true"

    messages = MessageService.get_entry_messages(
        entry_id=entry_id, workset_id=workset_id, include_replies=include_replies
    )

    return jsonify(
        {
            "messages": [
                msg.to_dict(include_replies=include_replies) for msg in messages
            ],
            "count": len(messages),
        }
    ), 200


@messages_api_bp.route("/entries/<entry_id>", methods=["POST"])
@login_required
def create_entry_message(entry_id):
    """
    Create a message for an entry.
    ---
    tags:
      - Messages
    parameters:
      - in: path
        name: entry_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - message_text
          properties:
            message_text:
              type: string
            workset_id:
              type: integer
            recipient_user_id:
              type: integer
            parent_message_id:
              type: integer
    responses:
      201:
        description: Message created
      400:
        description: Validation error
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    message_text = data.get("message_text")
    if not message_text:
        return jsonify({"error": "Message text is required"}), 400

    message, error = MessageService.create_message(
        entry_id=entry_id,
        sender_user_id=g.current_user.id,
        message_text=message_text,
        workset_id=data.get("workset_id"),
        recipient_user_id=data.get("recipient_user_id"),
        parent_message_id=data.get("parent_message_id"),
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify(
        {"message": "Message created successfully", "data": message.to_dict()}
    ), 201


@messages_api_bp.route("/<int:message_id>", methods=["GET"])
@login_required
def get_message_thread(message_id):
    """
    Get a message thread (message and all replies).
    ---
    tags:
      - Messages
    parameters:
      - in: path
        name: message_id
        type: integer
        required: true
    responses:
      200:
        description: Message thread
      404:
        description: Message not found
    """
    thread = MessageService.get_message_thread(message_id)

    if not thread:
        return jsonify({"error": "Message not found"}), 404

    return jsonify(
        {"thread": [msg.to_dict() for msg in thread], "count": len(thread)}
    ), 200


@messages_api_bp.route("/<int:message_id>/read", methods=["PUT"])
@login_required
def mark_message_read(message_id):
    """
    Mark a message as read.
    ---
    tags:
      - Messages
    parameters:
      - in: path
        name: message_id
        type: integer
        required: true
    responses:
      200:
        description: Message marked as read
      403:
        description: Not authorized
      404:
        description: Message not found
    """
    success, error = MessageService.mark_message_as_read(message_id, g.current_user.id)

    if error:
        status_code = 404 if "not found" in error.lower() else 403
        return jsonify({"error": error}), status_code

    return jsonify({"message": "Message marked as read"}), 200


@messages_api_bp.route("/<int:message_id>", methods=["DELETE"])
@login_required
def delete_message(message_id):
    """
    Delete a message.
    ---
    tags:
      - Messages
    parameters:
      - in: path
        name: message_id
        type: integer
        required: true
    responses:
      200:
        description: Message deleted
      403:
        description: Not authorized
      404:
        description: Message not found
    """
    success, error = MessageService.delete_message(message_id, g.current_user.id)

    if error:
        status_code = 404 if "not found" in error.lower() else 403
        return jsonify({"error": error}), status_code

    return jsonify({"message": "Message deleted successfully"}), 200


@messages_api_bp.route("/unread", methods=["GET"])
@login_required
def get_unread_messages():
    """
    Get all unread messages for current user.
    ---
    tags:
      - Messages
    responses:
      200:
        description: List of unread messages
    """
    messages = MessageService.get_user_unread_messages(g.current_user.id)

    return jsonify(
        {"messages": [msg.to_dict() for msg in messages], "count": len(messages)}
    ), 200


@messages_api_bp.route("/notifications", methods=["GET"])
@login_required
def get_notifications():
    """
    Get notifications for current user.
    ---
    tags:
      - Messages
    parameters:
      - in: query
        name: unread_only
        type: boolean
        default: false
      - in: query
        name: limit
        type: integer
        default: 50
    responses:
      200:
        description: List of notifications
    """
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = request.args.get("limit", 50, type=int)

    notifications = MessageService.get_user_notifications(
        g.current_user.id, unread_only=unread_only, limit=limit
    )

    return jsonify(
        {
            "notifications": [notif.to_dict() for notif in notifications],
            "count": len(notifications),
            "unread_count": MessageService.get_unread_notification_count(
                g.current_user.id
            ),
        }
    ), 200


@messages_api_bp.route("/notifications/<int:notification_id>/read", methods=["PUT"])
@login_required
def mark_notification_read(notification_id):
    """
    Mark a notification as read.
    ---
    tags:
      - Messages
    parameters:
      - in: path
        name: notification_id
        type: integer
        required: true
    responses:
      200:
        description: Notification marked as read
      403:
        description: Not authorized
      404:
        description: Notification not found
    """
    success, error = MessageService.mark_notification_as_read(
        notification_id, g.current_user.id
    )

    if error:
        status_code = 404 if "not found" in error.lower() else 403
        return jsonify({"error": error}), status_code

    return jsonify({"message": "Notification marked as read"}), 200


@messages_api_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """
    Mark all notifications as read for current user.
    ---
    tags:
      - Messages
    responses:
      200:
        description: All notifications marked as read
    """
    count = MessageService.mark_all_notifications_as_read(g.current_user.id)

    return jsonify({"message": "All notifications marked as read", "count": count}), 200
