"""Common API decorators for validation and error handling."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

from flask import jsonify, request

from app.utils.exceptions import DatabaseError, NotFoundError, ValidationError

F = TypeVar("F", bound=Callable[..., Any])


def require_json(func: F) -> F:
    """Ensure requests provide JSON payloads.

    Returns 400 if the request is not JSON or parsing fails.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if not request.is_json:
            return jsonify({"error": "Request must be application/json"}), 400

        if request.get_json(silent=True) is None:
            return jsonify({"error": "Invalid or empty JSON payload"}), 400

        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def handle_exceptions(func: F) -> F:
    """Catch common service exceptions and convert them to HTTP responses."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        try:
            return func(*args, **kwargs)
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 400
        except NotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except DatabaseError as exc:
            return jsonify({"error": str(exc)}), 500
        except Exception as exc:  # pragma: no cover - safety net
            return jsonify({"error": str(exc)}), 500

    return wrapper  # type: ignore[return-value]
