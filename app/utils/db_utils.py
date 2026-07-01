"""
Database utility helpers for safe transaction handling.
"""

import logging
import re
from typing import Optional

from flask_sqlalchemy import SQLAlchemy


def safe_commit(db: SQLAlchemy, log_context: str = "") -> None:
    """
    Commit the current session with automatic rollback on failure.

    Prevents poisoned-session state where a failed commit leaves the
    session unusable for subsequent operations. Equivalent callers
    that previously used bare ``db.session.commit()`` should use this
    helper instead.

    Args:
        db: The Flask-SQLAlchemy instance whose session to commit.
        log_context: Optional label for log messages (e.g. function name).

    Raises:
        The original exception from session.commit() after rolling back.
    """
    logger = logging.getLogger(__name__)
    try:
        db.session.commit()
    except Exception as exc:
        logger.error(
            "Database commit failed%s: %s",
            f" ({log_context})" if log_context else "",
            exc,
            exc_info=True,
        )
        try:
            db.session.rollback()
        except Exception as rb_exc:
            logger.error("Rollback after failed commit also failed: %s", rb_exc)
        raise


def escape_xquery_string(value: str) -> str:
    """
    Escape a string value for safe embedding in an XQuery string literal
    (single-quoted or double-quoted).

    XQuery string literal rules:
    - In a single-quoted string, a literal single-quote is escaped by doubling: ''.
    - In a double-quoted string, a literal double-quote is escaped by doubling: "".

    This function escapes for *both* contexts by doubling both quote types,
    plus it strips or rejects any non-printable characters.

    Args:
        value: The raw string value to escape.

    Returns:
        A safe string suitable for interpolation inside an XQuery string literal.
    """
    if not isinstance(value, str):
        value = str(value)
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value.replace("'", "''").replace('"', '""')


def safe_bulk_delete(db: SQLAlchemy, model, *filters, log_context: str = "") -> int:
    """
    Execute a bulk delete and commit with rollback on failure.

    Prefer ORM iteration + session.delete() for models with cascade
    dependencies.  This helper exists for callers that consciously
    choose bulk ``query.delete()`` for performance.

    Args:
        db: Flask-SQLAlchemy instance.
        model: SQLAlchemy model class.
        *filters: Filter expressions (e.g. ``Model.column == value``).

    Returns:
        Number of rows deleted.

    Raises:
        The original exception after rolling back.
    """
    logger = logging.getLogger(__name__)
    try:
        count = model.query.filter(*filters).delete(synchronize_session='fetch')
        db.session.commit()
        logger.debug("Bulk delete on %s removed %d rows", model.__tablename__, count)
        return count
    except Exception as exc:
        logger.error(
            "Bulk delete failed%s: %s",
            f" ({log_context})" if log_context else "",
            exc,
            exc_info=True,
        )
        try:
            db.session.rollback()
        except Exception as rb_exc:
            logger.error("Rollback after bulk delete also failed: %s", rb_exc)
        raise
