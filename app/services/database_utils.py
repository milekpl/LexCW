"""Shared database utilities for dictionary services."""

from __future__ import annotations
import logging
import time
import re
from typing import Optional, Union, List, Tuple

from app.database.basex_connector import BaseXConnector
from app.utils.exceptions import DatabaseError
from app.utils.constants import DB_NAME_NOT_CONFIGURED


logger = logging.getLogger(__name__)


def get_db_name(
    db_connector: Union[BaseXConnector, object],
    project_id: Optional[int] = None,
    logger: Optional[logging.Logger] = None
) -> str:
    """Resolve database name, checking project-specific settings if needed.

    This replaces duplicate patterns throughout the codebase where each method
    repeats the same logic for resolving database name from project ID.

    Args:
        db_connector: Database connector with .database property.
        project_id: Optional project ID to determine database.
        logger: Optional logger for debug messages.

    Returns:
        Database name string.

    Raises:
        DatabaseError: If no database is configured.
    """
    log = logger or logging.getLogger(__name__)

    db_name = getattr(db_connector, 'database', None)
    if not db_name:
        raise DatabaseError(DB_NAME_NOT_CONFIGURED)

    if project_id:
        try:
            from app.config_manager import ConfigManager
            from flask import current_app
            cm = current_app.injector.get(ConfigManager)
            settings = cm.get_settings_by_id(project_id)
            if settings and hasattr(settings, 'basex_db_name') and settings.basex_db_name:
                db_name = settings.basex_db_name
        except Exception as e:
            log.debug("Error getting db_name for project %s: %s", project_id, e)

    if not db_name:
        raise DatabaseError(DB_NAME_NOT_CONFIGURED)

    return db_name


def kill_blocking_sessions(
    connector: BaseXConnector,
    db_name: str,
    max_retries: int = 5,
    logger: Optional[logging.Logger] = None
) -> bool:
    """Kill BaseX sessions blocking database operations.

    Attempts to kill sessions that have the database open, then retries
    the DROP DB operation.

    Args:
        connector: Admin BaseXConnector for executing commands.
        db_name: Name of the database to clear.
        max_retries: Maximum number of retry attempts.
        logger: Optional logger for debug messages.

    Returns:
        True if successful, False otherwise.
    """
    log = logger or logging.getLogger(__name__)

    for attempt in range(1, max_retries + 1):
        try:
            connector.execute_command(f"DROP DB {db_name}")
            return True
        except Exception as e:
            errstr = str(e).lower()
            if "opened by another process" in errstr and attempt < max_retries:
                log.warning(
                    "DROP DB '%s' failed because DB is open in another process (attempt %d/%d), retrying...",
                    db_name,
                    attempt,
                    max_retries,
                )

                # Attempt to gather session info and kill sessions
                try:
                    sessions_info = connector.execute_command("SHOW SESSIONS")
                    if sessions_info:
                        log.warning("Found sessions that may hold DB open: %s", sessions_info)
                        lines = str(sessions_info).split('\n')
                        for line in lines:
                            m = re.search(r'(?:^|-\s+)([a-zA-Z0-9_-]+)\s+(?:\[|\d)', line)
                            if m:
                                user = m.group(1)
                                if user.lower() in ('username', 'session', 'sessions'):
                                    continue
                                try:
                                    connector.execute_command(f"KILL {user}")
                                    log.info("KILL command for user %s executed", user)
                                except Exception as ke:
                                    log.debug("Failed to kill session for user %s: %s", user, ke)
                except Exception as se:
                    log.debug("Failed to query/kill sessions: %s", se)

                log.info("Waiting 1s before retry...")
                time.sleep(1)
                continue
            log.error("Failed to DROP DB %s: %s", db_name, e)
            return False

    return True


def close_database_gracefully(
    connector: BaseXConnector,
    db_name: str,
    logger: Optional[logging.Logger] = None
) -> None:
    """Safely close database with error suppression.

    Args:
        connector: BaseXConnector to close.
        db_name: Name of the database to close.
        logger: Optional logger for debug messages.
    """
    log = logger or logging.getLogger(__name__)

    try:
        connector.execute_command(f"OPEN {db_name}")
        connector.execute_command("CLOSE")
    except DatabaseError as e:
        log.debug("Database close error (may be expected): %s", e)
    except Exception as e:
        log.warning("Unexpected error during disconnect: %s", e)


def list_database_names(
    connector: BaseXConnector,
    logger: Optional[logging.Logger] = None
) -> List[str]:
    """List all database names on the BaseX server.

    Args:
        connector: BaseXConnector to query.
        logger: Optional logger for debug messages.

    Returns:
        List of database names.
    """
    log = logger or logging.getLogger(__name__)

    try:
        result = connector.execute_command("LIST")
        if result:
            return [line.strip() for line in str(result).split('\n') if line.strip()]
    except Exception as e:
        log.warning("Failed to list databases: %s", e)

    return []
