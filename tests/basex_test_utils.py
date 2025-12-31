"""Helper utilities for creating/cleaning BaseX test databases.

Provides deterministic operations used by tests to create a single
session test DB and perform per-test cleanup in a DRY way.
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

from app.database.basex_connector import BaseXConnector

logger = logging.getLogger(__name__)

LIFT_EMPTY_DOC = '<?xml version="1.0" encoding="UTF-8"?>\n<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13"></lift>'
# Full ranges.xml content for testing - includes all ranges needed by tests
LIFT_RANGES_CONTENT = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info">
        <range-element id="Noun" label="Noun" abbrev="n"/>
        <range-element id="Verb" label="Verb" abbrev="v"/>
        <range-element id="Adjective" label="Adjective" abbrev="adj"/>
    </range>
    <range id="usage-type">
        <range-element id="dialect" label="Dialect"/>
        <range-element id="register" label="Register"/>
    </range>
    <range id="semantic-domain">
        <range-element id="sd-1" label="Semantic Domain 1"/>
        <range-element id="sd-2" label="Semantic Domain 2"/>
    </range>
    <range id="academic-domain">
        <range-element id="academics" label="Academics"/>
        <range-element id="general" label="General"/>
    </range>
    <range id="variant-type">
        <range-element id="spelling" label="Spelling Variant"/>
        <range-element id="dialectal" label="Dialectal Variant"/>
    </range>
</lift-ranges>'''


def _admin_connector() -> BaseXConnector:
    return BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )


def create_test_db(db_name: str) -> None:
    """Create (or recreate) a BaseX database and add minimal LIFT files.

    Doesn't raise on failure - callers should handle exceptions or log.
    Uses threading with timeout to avoid hanging when BaseX is not available.
    """
    import threading

    def _do_connect():
        admin = _admin_connector()
        try:
            admin.connect()
            return admin
        except Exception:
            return None

    # Use threading with timeout to avoid hanging
    result = {"connector": None, "error": None}
    done = threading.Event()

    def _run():
        try:
            result["connector"] = _do_connect()
        except Exception as e:
            result["error"] = e
        finally:
            done.set()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    done.wait(timeout=5)  # 5 second timeout (reduced for faster test discovery)

    if result["connector"] is None:
        # BaseX not available, silently skip
        return

    admin = result["connector"]
    try:
        try:
            admin.execute_command(f"DROP DB {db_name}")
        except Exception:
            pass
        admin.execute_command(f"CREATE DB {db_name}")

        # Add minimal empty lift and ranges
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(LIFT_EMPTY_DOC)
            tmp1 = f.name
        try:
            admin.execute_command(f'ADD "{tmp1}"')
        except Exception as e:
            logger.warning("Failed to add minimal lift doc to %s: %s", db_name, e)
        finally:
            try:
                os.unlink(tmp1)
            except Exception:
                pass

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(LIFT_RANGES_CONTENT)
            tmp2 = f.name
        try:
            admin.execute_command(f'ADD "{tmp2}"')
        except Exception as e:
            logger.warning("Failed to add ranges doc to %s: %s", db_name, e)
        finally:
            try:
                os.unlink(tmp2)
            except Exception:
                pass
    except Exception as e:
        logger.warning("Could not create test DB %s: %s", db_name, e)
    finally:
        try:
            admin.disconnect()
        except Exception:
            pass


def delete_all_lift_entries(db_name: str) -> None:
    """Delete all resources from the given database and add a minimal empty one.

    This properly cleans up the database by removing all resources (not just entry nodes)
    to prevent duplicate document accumulation when the ADD command is used multiple times.
    After cleanup, add one minimal lift document to ensure filtering and listing tests
    have predictable content.
    """
    admin = _admin_connector()
    try:
        admin.database = db_name
        admin.connect()
        try:
            # Delete all resources in the database using XQuery
            # This removes all documents from the database
            result = admin.execute_query("xquery db:list('" + db_name + "')")
            if result:
                for resource in result.strip().split('\n'):
                    resource = resource.strip()
                    if resource:
                        try:
                            # Use quotes around resource name to handle spaces/special chars
                            admin.execute_command(f'DROP "{resource}"')
                        except Exception:
                            pass  # Resource may have already been deleted or command failed

            # ensure at least one empty lift exists
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                f.write(LIFT_EMPTY_DOC)
                tmp = f.name
            try:
                admin.execute_command(f'ADD "{tmp}"')
            except Exception as e:
                logger.warning("Failed to add minimal lift after cleanup for %s: %s", db_name, e)
            finally:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

        finally:
            try:
                admin.disconnect()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Could not purge entries from %s: %s", db_name, e)


def drop_test_db(db_name: str) -> None:
    """Drop the provided test DB (best-effort, logs on failure)."""
    admin = _admin_connector()
    try:
        admin.connect()
        try:
            admin.execute_command(f"DROP DB {db_name}")
        finally:
            try:
                admin.disconnect()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Could not drop DB %s: %s", db_name, e)
