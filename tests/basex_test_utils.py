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
LIFT_RANGES_EMPTY = '<lift-ranges></lift-ranges>'


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
    """
    admin = _admin_connector()
    try:
        admin.connect()
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
                f.write(LIFT_RANGES_EMPTY)
                tmp2 = f.name
            try:
                admin.execute_command(f'ADD "{tmp2}"')
            except Exception as e:
                logger.warning("Failed to add minimal ranges doc to %s: %s", db_name, e)
            finally:
                try:
                    os.unlink(tmp2)
                except Exception:
                    pass

        finally:
            try:
                admin.disconnect()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Could not create test DB %s: %s", db_name, e)


def delete_all_lift_entries(db_name: str) -> None:
    """Delete all lift:entry nodes in the given database.

    Uses an XQuery update which is less disruptive than dropping/creating the DB
    and avoids issues with DB being opened by other sessions.
    After cleanup, add one minimal lift and a seeded sample entry to ensure
    filtering and listing tests have predictable content.
    """
    admin = _admin_connector()
    try:
        admin.database = db_name
        admin.connect()
        try:
            q = (
                "declare namespace lift = 'http://fieldworks.sil.org/schemas/lift/0.13'; "
                "delete node collection('%s')//lift:entry" % db_name
            )
            admin.execute_update(q)
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

            # Add a small seeded entry that tests may rely on (id: seed_app_001)
            seeded_entry = '''<?xml version="1.0" encoding="UTF-8"?>
<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
  <entry id="seed_app_001" dateCreated="2024-01-01T00:00:00Z" dateModified="2024-01-01T00:00:00Z">
    <lexical-unit>
      <form lang="en"><text>apple</text></form>
    </lexical-unit>
  </entry>
</lift>'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f2:
                f2.write(seeded_entry)
                tmp2 = f2.name
            try:
                admin.execute_command(f'ADD "{tmp2}"')
            except Exception as e:
                logger.warning("Failed to add seeded sample entry to %s: %s", db_name, e)
            finally:
                try:
                    os.unlink(tmp2)
                except Exception:
                    pass

            # Add a second seeded entry 'test_entry_1' with a sense 'sense_1_1' used by relation tests
            seeded_test_entry = '''<?xml version="1.0" encoding="UTF-8"?>
<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
  <entry id="test_entry_1" dateCreated="2024-01-01T00:00:00Z" dateModified="2024-01-01T00:00:00Z">
    <lexical-unit>
      <form lang="en"><text>testword</text></form>
    </lexical-unit>
    <sense id="sense_1_1">
      <gloss lang="en"><text>a test sense</text></gloss>
    </sense>
  </entry>
</lift>'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f3:
                f3.write(seeded_test_entry)
                tmp3 = f3.name
            try:
                admin.execute_command(f'ADD "{tmp3}"')
            except Exception as e:
                logger.warning("Failed to add seeded test entry to %s: %s", db_name, e)
            finally:
                try:
                    os.unlink(tmp3)
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
