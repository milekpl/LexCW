from __future__ import annotations

from contextlib import contextmanager
from flask import current_app
import logging

logger = logging.getLogger(__name__)

@contextmanager
def pg_conn():
    """Context manager that yields a PostgreSQL connection from the app pool
    and ensures it is returned to the pool via putconn() even if an error
    occurs. This prevents pool connection leakage and exhaustion.
    """
    pool = getattr(current_app, 'pg_pool', None)
    if pool is None:
        raise RuntimeError('PostgreSQL pool not configured')

    conn = pool.getconn()
    try:
        yield conn
    finally:
        try:
            pool.putconn(conn)
        except Exception as e:
            logger.warning('Failed to return connection to pool: %s', e)
            # As a last resort, close all connections to recover pool state
            try:
                pool.closeall()
            except Exception:
                pass
