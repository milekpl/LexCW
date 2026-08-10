"""Helper utilities for creating/cleaning BaseX test databases.

Provides deterministic operations used by tests to create a single
session test DB and perform per-test cleanup in a DRY way.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from typing import List, Optional, Tuple

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

        # Add minimal empty lift and ranges using add_resource
        # (bypasses Docker filesystem isolation — sends content over socket)
        try:
            admin.add_resource("minimal_lift.xml", LIFT_EMPTY_DOC, db_name=db_name)
        except Exception as e:
            logger.warning("Failed to add minimal lift doc to %s: %s", db_name, e)

        try:
            admin.add_resource("ranges.xml", LIFT_RANGES_CONTENT, db_name=db_name)
        except Exception as e:
            logger.warning("Failed to add ranges doc to %s: %s", db_name, e)
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
            try:
                admin.add_resource("minimal_lift.xml", LIFT_EMPTY_DOC, db_name=db_name)
            except Exception as e:
                logger.warning("Failed to add minimal lift after cleanup for %s: %s", db_name, e)

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


# ============================================================================
# In-memory (ramdisk) BaseX server + fast XQuery-based DB reset
#
# The e2e/unit suites were slow because every test DROPPED and re-CREATEd its
# BaseX database, re-running the disk indexer each time (~1000 leftover
# test_* DB dirs were found in ~/basex/data). Instead:
#   1. pytest starts one BaseX server per session, with its data directory on
#      a ramdisk (/dev/shm when available) so all index I/O stays in memory.
#   2. Each test resets a pre-built "gold" database with tiny XQuery updates
#      (db:delete + db:add) instead of DROP/CREATE — the DB stays open and
#      the indexer is never re-run for the whole database.
# ============================================================================


def _find_basex_classpath() -> Optional[str]:
    """Locate a BaseX installation (repo ``basex/``, then ``~/basex``).

    Returns a Java classpath string (``BaseX.jar`` + ``lib/*``) or None.
    """
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'basex')),
        os.path.expanduser('~/basex'),
    ]
    for base in candidates:
        jar = os.path.join(base, 'BaseX.jar')
        if os.path.isfile(jar):
            return f"{jar}{os.pathsep}{os.path.join(base, 'lib', '*')}"
    return None


def _basex_reachable(port: int) -> bool:
    """True if a BaseX server on ``port`` accepts admin/admin connections."""
    try:
        from BaseXClient.BaseXClient import Session
        session = Session('localhost', port, 'admin', 'admin')
        session.close()
        return True
    except Exception:
        return False


def _cleanup_orphaned_test_servers() -> bool:
    """Kill stale ramdisk BaseX servers orphaned by killed pytest runs.

    When pytest itself is SIGKILLed (e.g. by a ``timeout`` wrapper), its
    teardown never runs and the BaseX JVM it started is reparented to init
    (ppid == 1) and stays alive on the test port with a leaked ramdisk data
    dir. A later session would otherwise *reuse* that orphan.

    Only processes that (a) match our own ramdisk data-dir pattern
    (``basex_pytest_*``), (b) run ``org.basex.BaseXServer`` as an actual JVM,
    AND (c) are reparented orphans (ppid == 1) are killed. A server owned by
    a live pytest session — even a different one — is left alone: since
    ``initialize_database`` sends content over the socket (no server-side file
    reads), sharing a running server across sessions is safe, and concurrent
    sessions use unique database names. A real dev server (different DBPATH)
    is never touched.

    Returns True if at least one process was killed.
    """
    killed_any = False
    try:
        out = subprocess.run(
            ['ps', '-eo', 'pid=,ppid=,args='],
            capture_output=True, text=True, timeout=5,
        ).stdout or ''
    except Exception:
        return False
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3:
            continue
        pid_str, ppid_str, args = parts
        if 'org.basex.BaseXServer' not in args or 'basex_pytest_' not in args:
            continue
        # Only actual JVM processes — a shell/python wrapper whose command line
        # merely *contains* the marker strings (e.g. via inline code) must not
        # be killed.
        if os.path.basename(args.split()[0]) != 'java':
            continue
        if ppid_str != '1':  # only genuinely orphaned JVMs
            continue
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        logger.warning("Killing orphaned test BaseX server (pid %s): %s", pid, args.strip()[:120])
        try:
            subprocess.run(['kill', str(pid)], timeout=5)
            killed_any = True
        except Exception:
            pass
    return killed_any


@contextmanager
def basex_server_context(port: Optional[int] = None, timeout: float = 30.0):
    """Context manager providing a BaseX server backed by a ramdisk data dir.

    - Data lives under ``/dev/shm`` when available (else the system temp dir),
      so every database/index write stays in memory.
    - Reuses an already-running BaseX server (e.g. the dev server) when one
      answers admin/admin on the port — no second JVM is started.
    - Otherwise starts ``org.basex.BaseXServer`` on the given port with a
      fresh data dir. BaseX 12 generates a random password on a fresh data
      dir, so the admin password is bootstrapped to ``admin`` at startup via
      ``-c "ALTER PASSWORD admin admin"`` (verified against BaseX 12.1).

    Yields True if this context started the server, False if it reused one
    (or could not start one — availability fixtures will then skip tests).
    """
    port = port or int(os.getenv('BASEX_PORT', '1984'))

    # Kill any orphaned ramdisk test servers from SIGKILLed runs BEFORE the
    # reachability check, so we never "reuse" a stale JVM whose filesystem
    # view (e.g. /tmp) no longer matches this process's. Only genuinely
    # orphaned JVMs (ppid == 1) are killed — servers owned by a live pytest
    # session or a dev setup are left alone.
    if _cleanup_orphaned_test_servers():
        time.sleep(1.0)  # let the orphaned JVM die and free the port

    if _basex_reachable(port):
        logger.info("BaseX already running on port %d — reusing it", port)
        yield False
        return

    classpath = _find_basex_classpath()
    if not classpath or not shutil.which('java'):
        logger.warning("BaseX jar or java not found — tests requiring BaseX will skip")
        yield False
        return

    ram_root = '/dev/shm' if os.path.isdir('/dev/shm') else tempfile.gettempdir()
    # Unique per-process dir: two concurrent pytest runs must never share (and
    # then delete) each other's live data dir.
    data_dir = tempfile.mkdtemp(prefix='basex_pytest_', dir=ram_root)
    # Deterministic bootstrap: drop any previous users.xml so the
    # `ALTER PASSWORD` startup command applies cleanly.
    users_file = os.path.join(data_dir, 'users.xml')
    if os.path.exists(users_file):
        os.remove(users_file)

    proc = subprocess.Popen(
        ['java', f'-Dorg.basex.DBPATH={data_dir}', '-cp', classpath,
         'org.basex.BaseXServer', f'-p{port}', '-c', 'ALTER PASSWORD admin admin'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _basex_reachable(port):
                logger.info("Started in-memory BaseX on port %d (ramdisk: %s)", port, data_dir)
                yield True
                return
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        logger.warning("BaseX did not become reachable on port %d", port)
        yield False
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        shutil.rmtree(data_dir, ignore_errors=True)


def reset_basex_database(db_name: str, resources: List[Tuple[str, str]]) -> None:
    """Restore a BaseX test DB to pristine state via XQuery updates.

    Replaces the old DROP DB + CREATE DB + ADD pattern: the database stays
    open and only its resources are swapped, so the indexer is never re-run
    for the whole database (the main e2e slowness fix).

    All existing resources are deleted first — the app persists each created
    entry as its own ``<entry-id>.xml`` resource, so deleting only the gold
    resources would leak entries from one test into the next — then the
    pristine ``resources`` are re-added.

    Args:
        db_name:   Database to reset.
        resources: ``(resource_path, content)`` pairs describing pristine
                   state.
    """
    admin = _admin_connector()
    try:
        admin.connect()
        # A destructive test may have dropped the DB entirely — recreate it.
        try:
            listed = admin.execute_query("xquery db:list()")
            if db_name not in (listed or '').split():
                admin.execute_command(f"CREATE DB {db_name}")
        except Exception:
            pass
        # Delete every existing resource (tolerantly) so no per-entry
        # resources created by previous tests survive the reset.
        try:
            res_list = admin.execute_query(f"xquery db:list('{db_name}')")
            for resource in (res_list or '').splitlines():
                resource = resource.strip()
                if not resource:
                    continue
                try:
                    admin.execute_command(f'XQUERY db:delete("{db_name}", "{resource}")')
                except Exception:
                    pass  # resource may have been deleted concurrently
        except Exception as e:
            # Never degrade silently: if we can't enumerate resources, the
            # reset would leak data from the previous test — fail loudly.
            raise RuntimeError(
                f"Cannot enumerate resources of {db_name} for reset: {e}"
            ) from e
        # Restore the pristine gold resources.
        for path, content in resources:
            admin.add_resource(path, content, db_name=db_name)
        logger.info("Reset BaseX DB %s via XQuery (%d gold resources)", db_name, len(resources))
    finally:
        try:
            admin.disconnect()
        except Exception:
            pass
